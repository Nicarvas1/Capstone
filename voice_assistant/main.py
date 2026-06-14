import asyncio
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .session import ConversationSession
from .stt import transcribir
from .llm import procesar_mensaje, generar_word_desde_formulario
from .tts import sintetizar

BASE_DIR     = Path(__file__).parent
PROJECT_DIR  = BASE_DIR.parent
INFORMES_DIR = PROJECT_DIR / "informes_generados"

app = FastAPI(title="Asistente PIE — Voz")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

executor = ThreadPoolExecutor(max_workers=2)
sessions: dict[str, ConversationSession] = {}

BIENVENIDA = (
    "¡Hola! Soy tu asistente para generar el Informe a la Familia PIE. "
    "Cuéntame los datos del estudiante: nombre completo, RUT, fecha de nacimiento, "
    "edad, curso y establecimiento educacional. Puedes hablar o escribir."
)


@app.get("/")
async def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/descargar/{filename}")
async def descargar(filename: str):
    safe = Path(filename).name
    path = INFORMES_DIR / safe
    if not path.exists():
        return {"error": "Archivo no encontrado"}
    return FileResponse(
        str(path),
        filename=safe,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


async def _procesar_texto(ws: WebSocket, session: ConversationSession,
                          texto: str, loop: asyncio.AbstractEventLoop,
                          tts_enabled_ref: list):
    """Shared handler: run LLM and send response."""
    await ws.send_json({"type": "status", "text": "Pensando..."})
    try:
        respuesta, accion, extra = await loop.run_in_executor(
            executor, procesar_mensaje, session, texto
        )
    except Exception as e:
        await ws.send_json({"type": "error", "text": f"Error del asistente: {e}"})
        return

    payload: dict = {
        "type": "response",
        "text": respuesta,
        "accion": accion,
        "etapa": session.etapa,
    }
    if accion == "mostrar_formulario" and extra:
        payload["borrador"] = extra
    if accion == "documento_listo" and extra:
        payload["download_url"] = extra.get("url", "")

    await ws.send_json(payload)

    # Optional TTS
    if tts_enabled_ref[0]:
        audio_b64 = await loop.run_in_executor(executor, sintetizar, respuesta)
        if audio_b64:
            await ws.send_json({"type": "tts_audio", "audio": audio_b64})


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    sid = str(uuid.uuid4())
    session = ConversationSession(sid)
    sessions[sid] = session
    loop = asyncio.get_event_loop()
    tts_ref = [False]  # mutable ref so inner functions can read it

    await ws.send_json(
        {"type": "response", "text": BIENVENIDA, "accion": "continuar", "etapa": 1}
    )

    try:
        while True:
            data = await ws.receive()

            # ── Binary: audio from VAD ─────────────────────────────────────
            if "bytes" in data and data["bytes"]:
                audio_bytes: bytes = data["bytes"]
                await ws.send_json({"type": "status", "text": "Transcribiendo..."})
                try:
                    texto = await loop.run_in_executor(executor, transcribir, audio_bytes)
                except Exception as e:
                    await ws.send_json({"type": "error", "text": f"Error al transcribir: {e}"})
                    continue

                if not texto:
                    await ws.send_json({"type": "status", "text": "No se detectó habla. Intenta de nuevo."})
                    continue

                await ws.send_json({"type": "transcription", "text": texto})
                await _procesar_texto(ws, session, texto, loop, tts_ref)

            # ── Text message ───────────────────────────────────────────────
            elif "text" in data and data["text"]:
                try:
                    msg = json.loads(data["text"])
                except Exception:
                    continue

                mtype = msg.get("type", "")

                # Typed chat message (skip STT)
                if mtype == "text_message":
                    texto = msg.get("text", "").strip()
                    if texto:
                        await ws.send_json({"type": "user_echo", "text": texto})
                        await _procesar_texto(ws, session, texto, loop, tts_ref)

                # Form submitted → generate Word
                elif mtype == "generar_word":
                    form_datos = msg.get("datos", {})
                    await ws.send_json({"type": "status", "text": "Generando documento..."})
                    try:
                        filename = await loop.run_in_executor(
                            executor, generar_word_desde_formulario, session, form_datos
                        )
                        session.word_filename = filename
                        await ws.send_json({
                            "type": "response",
                            "text": "¡Documento generado! Haz clic en el botón de descarga.",
                            "accion": "documento_listo",
                            "etapa": session.etapa,
                            "download_url": f"/descargar/{filename}",
                        })
                    except Exception as e:
                        await ws.send_json({"type": "error", "text": f"Error al generar: {e}"})

                # TTS toggle
                elif mtype == "tts_toggle":
                    tts_ref[0] = msg.get("enabled", False)

                # TTS on-demand for a specific text
                elif mtype == "tts_request":
                    text_to_speak = msg.get("text", "")
                    if text_to_speak:
                        audio_b64 = await loop.run_in_executor(executor, sintetizar, text_to_speak)
                        if audio_b64:
                            await ws.send_json({"type": "tts_audio", "audio": audio_b64})

                # Reset conversation
                elif mtype == "reset":
                    session = ConversationSession(sid)
                    sessions[sid] = session
                    tts_ref[0] = False
                    await ws.send_json(
                        {"type": "response", "text": BIENVENIDA, "accion": "continuar", "etapa": 1}
                    )

    except WebSocketDisconnect:
        sessions.pop(sid, None)
