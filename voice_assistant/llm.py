"""LLM logic for the voice assistant — same stage flow as the Streamlit app."""

import json
import re
from pathlib import Path

from docxtpl import DocxTemplate
from langchain_ollama import OllamaLLM

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = OllamaLLM(model="llama3.1")
    return _llm


def _extraer_json(texto: str):
    try:
        start = texto.find("{")
        end = texto.rfind("}")
        if start != -1 and end != -1:
            s = texto[start : end + 1]
            s = re.sub(r",\s*\}", "}", s)
            s = re.sub(r",\s*\]", "]", s)
            return json.loads(s)
    except Exception:
        pass
    return None


def procesar_mensaje(session, texto: str) -> tuple:
    """
    Returns (respuesta, accion, extra_data).
    accion values:
      "continuar"          - keep talking
      "etapa1_completa"    - moved to stage 2
      "etapa2_completa"    - moved to stage 3
      "etapa3_completa"    - moved to stage 4 (ask AI draft?)
      "solicitar_info"     - stage 4: asking for info to generate draft
      "mostrar_formulario" - show editable form (extra_data = borrador dict)
      "documento_listo"    - Word generated, extra_data = {"url": ...}
    """
    llm = _get_llm()
    session.mensajes.append({"rol": "user", "contenido": texto})
    historial = "\n".join(
        f"{'Usuario' if m['rol'] == 'user' else 'Asistente'}: {m['contenido']}"
        for m in session.mensajes
    )

    if session.etapa == 1:
        return _etapa1(session, historial, llm)
    elif session.etapa == 2:
        return _etapa2(session, historial, llm)
    elif session.etapa == 3:
        return _etapa3(session, historial, llm)
    elif session.etapa == 4:
        return _etapa4(session, historial, llm, texto)

    return "No sé en qué etapa estoy. Intenta reiniciar.", "continuar", None


# ─── ETAPA 1: Datos del estudiante ────────────────────────────────────────────

def _etapa1(session, historial, llm):
    prompt_check = f"""Analiza el historial y extrae los datos del estudiante en JSON puro.
{{
  "nombre": "nombre completo del alumno o 'FALTA'",
  "rut": "RUT del alumno o 'FALTA'",
  "fecha_nacimiento": "fecha de nacimiento o 'FALTA'",
  "edad": "edad (ej: 11 años) o 'FALTA'",
  "curso": "curso y letra (ej: 5° Básico B) o 'FALTA'",
  "establecimiento": "colegio o 'FALTA'"
}}
Si un dato no se menciona, pon 'FALTA'. No inventes.
Historial:
{historial}
Responde ÚNICAMENTE con el JSON:"""

    datos = _extraer_json(llm.invoke(prompt_check))
    campos = ["nombre", "rut", "fecha_nacimiento", "edad", "curso", "establecimiento"]
    if datos:
        for k in campos:
            if k not in datos:
                datos[k] = "FALTA"
        faltantes = [k for k, v in datos.items() if "FALTA" in str(v).upper() or not v]
    else:
        faltantes = campos

    if not faltantes:
        session.datos_estudiante = datos
        session.etapa = 2
        msg = ("¡Perfecto! Ya tengo todos los datos del estudiante. "
               "Ahora necesito tus datos como profesional: nombre completo, RUT, "
               "cargo o rol, teléfono, email y la fecha de entrega del informe.")
        session.mensajes.append({"rol": "assistant", "contenido": msg})
        return msg, "etapa1_completa", None

    prompt_hablar = f"""Eres un asistente amable ayudando a un profesional de educación PIE.
Faltan estos datos del estudiante: {', '.join(faltantes)}.
Haz UNA sola pregunta natural y breve para obtener esos datos.
Historial:
{historial}"""
    respuesta = llm.invoke(prompt_hablar)
    session.mensajes.append({"rol": "assistant", "contenido": respuesta})
    return respuesta, "continuar", None


# ─── ETAPA 2: Datos del profesional ───────────────────────────────────────────

def _etapa2(session, historial, llm):
    prompt_check = f"""Analiza el historial y extrae los datos del profesional en JSON puro.
{{
  "nombre_prof": "nombre completo o 'FALTA'",
  "rut_prof": "RUT o 'FALTA'",
  "rol": "cargo/rol profesional o 'FALTA'",
  "telefono": "teléfono o 'FALTA'",
  "email": "email o 'FALTA'",
  "fecha_entrega_informe": "fecha de entrega del informe (no fecha de nacimiento) o 'FALTA'"
}}
Si un dato no se menciona, pon 'FALTA'. No inventes.
Historial:
{historial}
Responde ÚNICAMENTE con el JSON:"""

    datos = _extraer_json(llm.invoke(prompt_check))
    campos = ["nombre_prof", "rut_prof", "rol", "telefono", "email", "fecha_entrega_informe"]
    if datos:
        for k in campos:
            if k not in datos:
                datos[k] = "FALTA"
        faltantes = [k for k, v in datos.items() if "FALTA" in str(v).upper() or not v]
    else:
        faltantes = campos

    if not faltantes:
        session.datos_profesional = datos
        session.etapa = 3
        msg = ("¡Perfecto! Ya tengo tus datos. "
               "Ahora necesito los datos del apoderado o persona que recibirá el informe: "
               "nombre completo, RUT, nombre social, teléfono, email, "
               "relación con el estudiante y quiénes estarán presentes en la reunión.")
        session.mensajes.append({"rol": "assistant", "contenido": msg})
        return msg, "etapa2_completa", None

    prompt_hablar = f"""Eres un asistente amable. Hablas con el profesional que redactará el informe.
Faltan sus propios datos: {', '.join(faltantes)}.
(Nota: fecha_entrega_informe es la fecha de entrega del informe, no fecha de nacimiento.)
Haz UNA sola pregunta natural y breve.
Historial:
{historial}"""
    respuesta = llm.invoke(prompt_hablar)
    session.mensajes.append({"rol": "assistant", "contenido": respuesta})
    return respuesta, "continuar", None


# ─── ETAPA 3: Datos del receptor (apoderado) ──────────────────────────────────

def _etapa3(session, historial, llm):
    prompt_check = f"""Analiza el historial y extrae los datos del receptor/apoderado en JSON puro.
{{
  "nombre_rec": "nombre completo o 'FALTA'",
  "rut_rec": "RUT o 'FALTA'",
  "nombre_social_rec": "nombre social o 'FALTA'",
  "telefono_rec": "teléfono o 'FALTA'",
  "email_rec": "email o 'FALTA'",
  "relacion_rec": "relación (madre, padre, abuelo, tutor...) o 'FALTA'",
  "presencia_rec": "personas presentes en la reunión o 'FALTA'"
}}
Si un dato no se menciona, pon 'FALTA'. No inventes.
Historial:
{historial}
Responde ÚNICAMENTE con el JSON:"""

    datos = _extraer_json(llm.invoke(prompt_check))
    campos = ["nombre_rec", "rut_rec", "nombre_social_rec", "telefono_rec",
              "email_rec", "relacion_rec", "presencia_rec"]
    if datos:
        for k in campos:
            if k not in datos:
                datos[k] = "FALTA"
        faltantes = [k for k, v in datos.items() if "FALTA" in str(v).upper() or not v]
    else:
        faltantes = campos

    if not faltantes:
        session.borrador.update({
            "nombre_receptor": datos.get("nombre_rec", ""),
            "rut_receptor": datos.get("rut_rec", ""),
            "nombre_social_receptor": datos.get("nombre_social_rec", ""),
            "telefono_receptor": datos.get("telefono_rec", ""),
            "email_receptor": datos.get("email_rec", ""),
            "relacion_receptor": datos.get("relacion_rec", ""),
            "presencia_receptor": datos.get("presencia_rec", ""),
        })
        session.etapa = 4
        session.decision_ia = "esperando"
        msg = ("¡Listo! Tengo todos los datos de identificación. "
               "¿Deseas que la inteligencia artificial redacte el contenido técnico del informe "
               "a partir de antecedentes que me proporciones? Responde sí o no.")
        session.mensajes.append({"rol": "assistant", "contenido": msg})
        return msg, "etapa3_completa", None

    prompt_hablar = f"""Eres un asistente amable ayudando a un profesional de educación.
Faltan datos del apoderado: {', '.join(faltantes)}.
Haz UNA sola pregunta natural y breve.
Historial:
{historial}"""
    respuesta = llm.invoke(prompt_hablar)
    session.mensajes.append({"rol": "assistant", "contenido": respuesta})
    return respuesta, "continuar", None


# ─── ETAPA 4: Decisión IA / mostrar formulario ────────────────────────────────

def _etapa4(session, historial, llm, texto_usuario):
    clean = re.sub(r"[^\w\s]", "", texto_usuario.lower())
    palabras = clean.split()
    afirmaciones = {"si", "sí", "yes", "claro", "dale", "ok", "bueno", "adelante", "s"}
    negaciones = {"no", "n", "manual", "directamente", "sin"}
    es_si = bool(afirmaciones & set(palabras))
    es_no = bool(negaciones & set(palabras)) and not es_si

    if session.decision_ia == "esperando":
        if es_si:
            session.decision_ia = "solicitando_info"
            msg = ("Perfecto. Cuéntame los antecedentes del estudiante: historial clínico, "
                   "resultados de evaluaciones, observaciones del docente, o cualquier "
                   "información relevante para el informe.")
            session.mensajes.append({"rol": "assistant", "contenido": msg})
            return msg, "solicitar_info", None

        elif es_no:
            session.decision_ia = "completado"
            msg = ("Entendido. He abierto el formulario con todos los campos del informe. "
                   "Puedes completarlos y generar el documento.")
            session.mensajes.append({"rol": "assistant", "contenido": msg})
            return msg, "mostrar_formulario", dict(session.borrador)

        else:
            msg = "No entendí. ¿Deseas que la IA redacte el contenido del informe? Responde sí o no."
            session.mensajes.append({"rol": "assistant", "contenido": msg})
            return msg, "continuar", None

    elif session.decision_ia == "solicitando_info":
        session.decision_ia = "completado"
        # Generate AI draft and populate borrador
        borrador_ia = _generar_borrador_ia(session, historial, llm)
        session.borrador.update(borrador_ia)
        msg = ("¡Borrador generado! He completado el formulario con la propuesta de la IA. "
               "Revisa y edita los campos antes de generar el documento.")
        session.mensajes.append({"rol": "assistant", "contenido": msg})
        return msg, "mostrar_formulario", dict(session.borrador)

    else:
        msg = "El formulario ya está abierto abajo. Edita los campos y haz clic en Generar Word."
        session.mensajes.append({"rol": "assistant", "contenido": msg})
        return msg, "continuar", None


def _generar_borrador_ia(session, contexto, llm) -> dict:
    """Asks the LLM to fill in the content fields and returns a dict."""
    prompt = f"""Actúa como un experto psicopedagogo y redactor de informes PIE en Chile (Decreto 170).
Analiza la información y redacta el informe técnico de forma profesional, formal y detallada.

Información:
{contexto}

Genera un JSON con estas claves exactas:
{{
  "motivo_evaluacion": "Ingreso" o "Reevaluacion",
  "instrumentos_aplicados": "...",
  "fecha_evaluacion": "...",
  "diagnostico_nee": "...",
  "fortalezas_pedagogicas": "...",
  "necesidades_pedagogicas": "...",
  "fortalezas_sociales": "...",
  "necesidades_sociales": "...",
  "trabajo_colaborativo": "...",
  "apoyos_hogar": "...",
  "acuerdos_compromisos": "...",
  "fechas_evaluacion": "..."
}}
Responde ÚNICAMENTE con el JSON puro."""
    try:
        respuesta = llm.invoke(prompt)
        match = re.search(r"\{.*\}", respuesta, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    return {}


# ─── Generar Word desde datos del formulario ──────────────────────────────────

def generar_word_desde_formulario(session, form_datos: dict) -> str:
    """Generates the Word document from frontend form data. Returns filename."""
    est  = session.datos_estudiante
    prof = session.datos_profesional
    motivo = form_datos.get("motivo_evaluacion", "Ingreso")

    datos_finales = {
        # Estudiante
        "nombre_estudiante":          est.get("nombre", ""),
        "nombre_social_estudiante":   est.get("nombre", ""),
        "rut_estudiante":             est.get("rut", ""),
        "fecha_nacimiento_estudiante":est.get("fecha_nacimiento", ""),
        "edad_estudiante":            est.get("edad", ""),
        "curso_estudiante":           est.get("curso", ""),
        "establecimiento_estudiante": est.get("establecimiento", ""),
        # Profesional
        "nombre_profesional":         prof.get("nombre_prof", ""),
        "nombre_social_profesional":  prof.get("nombre_prof", ""),
        "rut_profesional":            prof.get("rut_prof", ""),
        "rol_profesional":            prof.get("rol", ""),
        "telefono_profesional":       prof.get("telefono", ""),
        "email_profesional":          prof.get("email", ""),
        "fecha_informe":              prof.get("fecha_entrega_informe", ""),
        # Checkboxes motivo
        "check_ingreso":              "☒" if motivo == "Ingreso" else "☐",
        "check_reevaluacion":         "☒" if motivo == "Reevaluación" else "☐",
        # Checkboxes apoderado
        "check_titular":  "☒" if form_datos.get("tipo_apoderado") == "Apoderado/a titular" else "☐",
        "check_suplente": "☒" if form_datos.get("tipo_apoderado") == "Apoderado/a suplente" else "☐",
        "check_poder_si": "☒" if form_datos.get("poder_simple") == "Sí" else "☐",
        "check_poder_no": "☒" if form_datos.get("poder_simple") == "No" else "☐",
    }
    # Merge all form fields (includes receptor + content fields)
    datos_finales.update(form_datos)

    base_dir     = Path(__file__).parent.parent
    template     = base_dir / "planillas" / "plantilla_informe.docx"
    output_dir   = base_dir / "informes_generados"
    output_dir.mkdir(exist_ok=True)

    nombre_clean = est.get("nombre", "Estudiante").replace(" ", "_")
    filename     = f"Informe_Voz_{nombre_clean}.docx"

    doc = DocxTemplate(str(template))
    doc.render(datos_finales)
    doc.save(str(output_dir / filename))
    return filename
