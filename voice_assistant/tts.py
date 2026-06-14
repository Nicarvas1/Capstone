import base64
import os
import tempfile


def sintetizar(texto: str) -> str:
    """Generate speech and return base64-encoded WAV. Returns '' on failure."""
    try:
        import pyttsx3
        engine = pyttsx3.init()

        # Find a Spanish voice on Windows (Microsoft Sabina / Helena / etc.)
        voices = engine.getProperty("voices")
        for voice in voices:
            name_lower = voice.name.lower()
            id_lower = voice.id.lower()
            if any(k in name_lower or k in id_lower
                   for k in ("sabina", "helena", "spanish", "es-mx", "es-es", "es_")):
                engine.setProperty("voice", voice.id)
                break

        engine.setProperty("rate", 155)   # words per minute
        engine.setProperty("volume", 1.0)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = f.name

        engine.save_to_file(texto, tmp)
        engine.runAndWait()

        with open(tmp, "rb") as f:
            data = f.read()
        os.unlink(tmp)
        return base64.b64encode(data).decode()

    except Exception:
        return ""
