import streamlit as st
import json
import os
import re
from docxtpl import DocxTemplate
from langchain_ollama import OllamaLLM
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader

# ==========================================
# CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Evaluación Psicopedagógica", page_icon="🧠", layout="centered")
st.title("🧠 Informe de Evaluación Psicopedagógica 2026")
st.write("Completa el formulario conversando conmigo para generar el informe oficial.")

@st.cache_resource
def cargar_modelo():
    return OllamaLLM(model="llama3.1")

modelo = cargar_modelo()

def extraer_json(texto):
    try:
        start = texto.find('{')
        end = texto.rfind('}')
        if start != -1 and end != -1:
            json_str = texto[start:end+1]
            json_str = re.sub(r',\s*\}', '}', json_str)
            json_str = re.sub(r',\s*\]', ']', json_str)
            return json.loads(json_str)
    except:
        pass
    return None

# ==========================================
# INICIALIZACIÓN DE ESTADO
# ==========================================
if "psico_uploader_key" not in st.session_state:
    st.session_state.psico_uploader_key = 0
if "psico_mensajes" not in st.session_state:
    st.session_state.psico_mensajes = []
if "psico_texto_pendiente" not in st.session_state:
    st.session_state.psico_texto_pendiente = ""
if "psico_archivo_actual" not in st.session_state:
    st.session_state.psico_archivo_actual = ""
if "psico_etapa" not in st.session_state:
    st.session_state.psico_etapa = 1
if "psico_datos_estudiante" not in st.session_state:
    st.session_state.psico_datos_estudiante = {}
if "psico_datos_profesional" not in st.session_state:
    st.session_state.psico_datos_profesional = {}
if "psico_datos_docente" not in st.session_state:
    st.session_state.psico_datos_docente = {}
if "psico_mostrar_panel" not in st.session_state:
    st.session_state.psico_mostrar_panel = None
if "psico_decision_ia" not in st.session_state:
    st.session_state.psico_decision_ia = None
if "psico_file_ready" not in st.session_state:
    st.session_state.psico_file_ready = None
if "psico_borrador" not in st.session_state:
    st.session_state.psico_borrador = {
        "motivo_evaluacion": "Ingreso",
        "otro_motivo": "",
        "instrumentos_psico": "",
        "historia_escolar_psico": "",
        "analisis_cog_fortalezas": "",
        "analisis_cog_dificultades": "",
        "analisis_com_fortalezas": "",
        "analisis_com_dificultades": "",
        "analisis_soc_fortalezas": "",
        "analisis_soc_dificultades": "",
        "analisis_apr_fortalezas": "",
        "analisis_apr_dificultades": "",
        "analisis_mot_fortalezas": "",
        "analisis_mot_dificultades": "",
        "analisis_aut_fortalezas": "",
        "analisis_aut_dificultades": "",
        "analisis_sen_fortalezas": "",
        "analisis_sen_dificultades": "",
        "sint_cog_progresos": "",
        "sint_cog_obstaculos": "",
        "sint_cog_factores": "",
        "sint_cog_estrategias": "",
        "sint_com_necesidades": "",
        "sint_com_obstaculos": "",
        "sint_soc_fortalezas": "",
        "sint_soc_necesidades": "",
        "sint_soc_obstaculos": "",
        "sint_soc_estrategias": "",
        "sint_apr_fortalezas": "",
        "sint_apr_necesidades": "",
        "sint_apr_obstaculos": "",
        "sint_apr_estrategias": "",
        "sint_mot_necesidades": "",
        "sint_mot_obstaculos": "",
        "sint_mot_estrategias": "",
        "sint_aut_necesidades": "",
        "sint_aut_obstaculos": "",
        "sint_aut_estrategias": "",
        "sint_sen_necesidades": "",
        "sint_sen_obstaculos": "",
        "conclusion_areas": "",
        "conclusion_general": "",
        "sug_establecimiento": "",
        "sug_equipo_aula": "",
        "sug_estudiante": "",
        "sug_familia": "",
        "sug_instituciones": "",
    }

# ==========================================
# BARRA LATERAL
# ==========================================
with st.sidebar:
    st.header("⚙️ Opciones")
    if st.button("🧹 Nuevo Estudiante / Limpiar"):
        for key in list(st.session_state.keys()):
            if key.startswith("psico_"):
                del st.session_state[key]
        st.rerun()

# ==========================================
# CARGA DE ARCHIVOS
# ==========================================
archivo_subido = st.file_uploader(
    "Sube antecedentes (PDF o Word)",
    type=['pdf', 'docx'],
    key=st.session_state.psico_uploader_key
)

if archivo_subido is not None:
    if st.session_state.psico_archivo_actual != archivo_subido.name:
        with st.spinner("Adjuntando archivo..."):
            os.makedirs("temp", exist_ok=True)
            ruta_temp = os.path.join("temp", archivo_subido.name)
            with open(ruta_temp, "wb") as f:
                f.write(archivo_subido.getbuffer())
            try:
                if archivo_subido.name.endswith('.pdf'):
                    loader = PyPDFLoader(ruta_temp)
                else:
                    loader = Docx2txtLoader(ruta_temp)
                docs = loader.load()
                texto = "\n".join([d.page_content for d in docs])
                st.session_state.psico_texto_pendiente = f"--- INICIO '{archivo_subido.name}' ---\n{texto}\n--- FIN ---"
                st.session_state.psico_archivo_actual = archivo_subido.name
                st.success(f"📎 '{archivo_subido.name}' adjuntado. Escribe algo para procesarlo.")
            except Exception as e:
                st.error(f"Error al leer el archivo: {e}")

# ==========================================
# CHAT - MOSTRAR HISTORIAL
# ==========================================
for mensaje in st.session_state.psico_mensajes:
    if mensaje.get("mostrar", "") != "":
        with st.chat_message(mensaje["rol"]):
            st.markdown(mensaje.get("mostrar", mensaje["contenido"]))

prompt = st.chat_input("Escribe aquí...")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    if st.session_state.psico_texto_pendiente:
        st.session_state.psico_mensajes.append({
            "rol": "user",
            "contenido": f"Contexto del documento:\n{st.session_state.psico_texto_pendiente}\n\nInstrucción: {prompt}",
            "mostrar": prompt
        })
        st.session_state.psico_texto_pendiente = ""
    else:
        st.session_state.psico_mensajes.append({"rol": "user", "contenido": prompt, "mostrar": prompt})

    historial_texto = ""
    for m in st.session_state.psico_mensajes:
        rol = "Usuario" if m["rol"] == "user" else "Asistente"
        historial_texto += f"{rol}: {m['contenido']}\n"

    with st.chat_message("assistant"):
        with st.spinner("Procesando..."):

            # ─── ETAPA 1: DATOS DEL ESTUDIANTE ───────────────────────────
            if st.session_state.psico_etapa == 1:
                prompt_check = f"""Analiza el historial y extrae los datos del estudiante en JSON puro.
Plantilla:
{{
  "nombre": "nombre completo o 'FALTA'",
  "rut": "RUT o 'FALTA'",
  "fecha_nacimiento": "fecha de nacimiento o 'FALTA'",
  "edad": "edad o 'FALTA'",
  "curso": "curso y letra o 'FALTA'",
  "establecimiento": "colegio o 'FALTA'",
  "fecha_evaluacion": "fecha de la evaluacion psicopedagogica o 'FALTA'",
  "diagnostico": "diagnostico del estudiante o 'FALTA'",
  "fecha_emision_diagnostico": "fecha de emision del diagnostico o 'FALTA'"
}}
Si un dato no se menciona, pon 'FALTA'. No inventes.
Historial:
{historial_texto}
Responde UNICAMENTE con el JSON:"""
                check_json = modelo.invoke(prompt_check)
                datos = extraer_json(check_json)
                campos = ["nombre", "rut", "fecha_nacimiento", "edad", "curso", "establecimiento", "fecha_evaluacion", "diagnostico", "fecha_emision_diagnostico"]
                if datos:
                    for k in campos:
                        if k not in datos:
                            datos[k] = "FALTA"
                    faltantes = [k for k, v in datos.items() if "FALTA" in str(v).upper() or v == ""]
                else:
                    faltantes = campos

                if len(faltantes) == 0:
                    st.session_state.psico_datos_estudiante = datos
                    st.session_state.psico_etapa = 2
                    st.info("✅ Datos del estudiante completos. Pasando a Fase 2: Datos del Profesional...")
                    msg = "¡Perfecto! Ya tengo los datos del estudiante. Ahora necesito tus datos como profesional: Nombre completo, RUT, Profesión y N° de Registro profesional."
                    st.session_state.psico_mensajes.append({"rol": "assistant", "contenido": msg, "mostrar": msg})
                    st.rerun()
                else:
                    prompt_hablar = f"""Eres un asistente amable ayudando a un psicopedagogo a redactar un informe.
Faltan estos datos del estudiante: {', '.join(faltantes)}.
Dirígete al profesional de forma natural y pídele los datos faltantes en UNA sola pregunta.
Historial:
{historial_texto}"""
                    respuesta = modelo.invoke(prompt_hablar)
                    st.markdown(respuesta)
                    st.session_state.psico_mensajes.append({"rol": "assistant", "contenido": respuesta, "mostrar": respuesta})

            # ─── ETAPA 2: DATOS DEL PROFESIONAL ──────────────────────────
            elif st.session_state.psico_etapa == 2:
                prompt_check = f"""Analiza el historial y extrae los datos del profesional psicopedagogo en JSON puro.
Plantilla:
{{
  "nombre_prof": "nombre completo o 'FALTA'",
  "rut_prof": "RUT o 'FALTA'",
  "profesion_prof": "profesion/titulo o 'FALTA'",
  "registro_prof": "numero de registro profesional o 'FALTA'"
}}
Si un dato no se menciona, pon 'FALTA'. No inventes.
Historial:
{historial_texto}
Responde UNICAMENTE con el JSON:"""
                check_json = modelo.invoke(prompt_check)
                datos = extraer_json(check_json)
                campos = ["nombre_prof", "rut_prof", "profesion_prof", "registro_prof"]
                if datos:
                    for k in campos:
                        if k not in datos:
                            datos[k] = "FALTA"
                    faltantes = [k for k, v in datos.items() if "FALTA" in str(v).upper() or v == ""]
                else:
                    faltantes = campos

                if len(faltantes) == 0:
                    st.session_state.psico_datos_profesional = datos
                    st.session_state.psico_etapa = 3
                    st.info("✅ Datos del profesional completos. Pasando a Fase 3: Datos del Docente de Aula...")
                    msg = "¡Excelente! Ahora necesito los datos del docente de aula que también emite este informe: Nombre completo, RUT y Profesión."
                    st.session_state.psico_mensajes.append({"rol": "assistant", "contenido": msg, "mostrar": msg})
                    st.rerun()
                else:
                    prompt_hablar = f"""Eres un asistente amable. Estás hablando con el psicopedagogo.
Faltan estos datos del propio profesional: {', '.join(faltantes)}.
(Nota: 'registro_prof' es el numero de registro profesional, no fecha de nacimiento).
Hazle UNA sola pregunta natural para obtener los datos faltantes.
Historial:
{historial_texto}"""
                    respuesta = modelo.invoke(prompt_hablar)
                    st.markdown(respuesta)
                    st.session_state.psico_mensajes.append({"rol": "assistant", "contenido": respuesta, "mostrar": respuesta})

            # ─── ETAPA 3: DATOS DEL DOCENTE DE AULA ──────────────────────
            elif st.session_state.psico_etapa == 3:
                prompt_check = f"""Analiza el historial y extrae los datos del docente de aula en JSON puro.
Plantilla:
{{
  "nombre_docente": "nombre completo del docente o 'FALTA'",
  "rut_docente": "RUT del docente o 'FALTA'",
  "profesion_docente": "profesion del docente (ej: Profesor de Ed. Basica) o 'FALTA'"
}}
Si un dato no se menciona, pon 'FALTA'. No inventes.
Historial:
{historial_texto}
Responde UNICAMENTE con el JSON:"""
                check_json = modelo.invoke(prompt_check)
                datos = extraer_json(check_json)
                campos = ["nombre_docente", "rut_docente", "profesion_docente"]
                if datos:
                    for k in campos:
                        if k not in datos:
                            datos[k] = "FALTA"
                    faltantes = [k for k, v in datos.items() if "FALTA" in str(v).upper() or v == ""]
                else:
                    faltantes = campos

                if len(faltantes) == 0:
                    st.session_state.psico_datos_docente = datos
                    st.session_state.psico_etapa = 4
                    st.session_state.psico_decision_ia = "esperando"
                    st.info("✅ Datos del docente completos. Pasando a Fase 4: Contenido del Informe...")
                    msg = ("¡Perfecto! Ya tengo todos los datos de identificación.\n\n"
                           "¿Deseas que la IA redacte un borrador del contenido del informe "
                           "a partir de antecedentes que me proporciones (responde **Sí**), "
                           "o prefieres rellenar el formulario de manera manual (responde **No**)?")
                    st.session_state.psico_mensajes.append({"rol": "assistant", "contenido": msg, "mostrar": msg})
                    st.rerun()
                else:
                    prompt_hablar = f"""Eres un asistente amable ayudando a un psicopedagogo.
Faltan estos datos del docente de aula: {', '.join(faltantes)}.
Hazle UNA sola pregunta natural al profesional para obtener los datos del docente faltantes.
Historial:
{historial_texto}"""
                    respuesta = modelo.invoke(prompt_hablar)
                    st.markdown(respuesta)
                    st.session_state.psico_mensajes.append({"rol": "assistant", "contenido": respuesta, "mostrar": respuesta})

            # ─── ETAPA 4: CONTENIDO DEL INFORME ──────────────────────────
            elif st.session_state.psico_etapa == 4:
                user_reply = prompt.strip().lower()

                if st.session_state.psico_decision_ia == "esperando":
                    user_clean = re.sub(r'[^\w\s]', '', user_reply)
                    palabras = user_clean.split()
                    afirmaciones = ["si", "sí", "yes", "s", "ia", "redactar", "borrador"]
                    negaciones = ["no", "n", "manual", "directamente"]
                    es_si = any(p in afirmaciones for p in palabras)
                    es_no = any(p in negaciones for p in palabras)

                    if es_si and not es_no:
                        st.session_state.psico_decision_ia = "solicitando_info"
                        msg = ("¡Excelente! Por favor escribe aquí los antecedentes clínicos, "
                               "resultados de evaluaciones, observaciones del estudiante o sube un "
                               "archivo con la información. La IA redactará el borrador del informe.")
                        st.markdown(msg)
                        st.session_state.psico_mensajes.append({"rol": "assistant", "contenido": msg, "mostrar": msg})
                    elif es_no:
                        st.session_state.psico_decision_ia = "no"
                        st.session_state.psico_mostrar_panel = "manual"
                        msg = "Entendido. He habilitado el formulario completo abajo para que lo completes manualmente."
                        st.markdown(msg)
                        st.session_state.psico_mensajes.append({"rol": "assistant", "contenido": msg, "mostrar": msg})
                    else:
                        msg = "Disculpa, no entendí. ¿Deseas que la IA redacte el borrador? Responde **Sí** o **No**."
                        st.markdown(msg)
                        st.session_state.psico_mensajes.append({"rol": "assistant", "contenido": msg, "mostrar": msg})

                elif st.session_state.psico_decision_ia == "solicitando_info":
                    st.markdown("Recibido. Analizando la información y redactando el borrador...")

                    contexto = ""
                    for msg in st.session_state.psico_mensajes:
                        if msg.get("mostrar"):
                            contexto += f"Usuario: {msg['mostrar']}\n"
                        else:
                            contexto += f"{'Usuario' if msg['rol']=='user' else 'Asistente'}: {msg['contenido']}\n"
                    if st.session_state.psico_texto_pendiente:
                        contexto += f"\nAntecedentes:\n{st.session_state.psico_texto_pendiente}\n"

                    prompt_borrador = f"""Actua como un psicopedagogo experto redactando un Informe de Evaluacion Psicopedagogica en Chile (Decreto 170).
Analiza la informacion y redacta el informe de forma profesional, formal y detallada en espanol.

Informacion recopilada:
{contexto}

Genera un JSON con las siguientes claves exactas:
{{
  "motivo_evaluacion": "Ingreso" o "Reevaluacion" o "Otro",
  "instrumentos_psico": "lista de instrumentos aplicados",
  "historia_escolar_psico": "antecedentes relevantes de la historia escolar",
  "analisis_cog_fortalezas": "habilidades cognitivas con adecuado desarrollo",
  "analisis_cog_dificultades": "habilidades cognitivas con menor desarrollo",
  "analisis_com_fortalezas": "habilidades comunicativas con adecuado desarrollo",
  "analisis_com_dificultades": "habilidades comunicativas con menor desarrollo",
  "analisis_soc_fortalezas": "habilidades socioemocionales con adecuado desarrollo",
  "analisis_soc_dificultades": "habilidades socioemocionales con menor desarrollo",
  "analisis_apr_fortalezas": "habilidades de aproximacion al aprendizaje fortalezas",
  "analisis_apr_dificultades": "habilidades de aproximacion al aprendizaje dificultades",
  "analisis_mot_fortalezas": "habilidades motoras con adecuado desarrollo",
  "analisis_mot_dificultades": "habilidades motoras con menor desarrollo",
  "analisis_aut_fortalezas": "habilidades de autonomia fortalezas",
  "analisis_aut_dificultades": "habilidades de autonomia dificultades",
  "analisis_sen_fortalezas": "procesamiento sensorial fortalezas",
  "analisis_sen_dificultades": "procesamiento sensorial dificultades",
  "sint_cog_progresos": "progresos y necesidades cognitivas",
  "sint_cog_obstaculos": "obstaculos cognitivos",
  "sint_cog_factores": "factores del entorno cognitivo",
  "sint_cog_estrategias": "estrategias cognitivas que han funcionado",
  "sint_com_necesidades": "necesidades comunicativas",
  "sint_com_obstaculos": "obstaculos comunicativos",
  "sint_soc_fortalezas": "fortalezas socioemocionales",
  "sint_soc_necesidades": "necesidades socioemocionales",
  "sint_soc_obstaculos": "obstaculos socioemocionales",
  "sint_soc_estrategias": "estrategias socioemocionales",
  "sint_apr_fortalezas": "fortalezas de aproximacion al aprendizaje",
  "sint_apr_necesidades": "necesidades de aproximacion al aprendizaje",
  "sint_apr_obstaculos": "obstaculos de aproximacion al aprendizaje",
  "sint_apr_estrategias": "estrategias de aproximacion al aprendizaje",
  "sint_mot_necesidades": "necesidades motoras",
  "sint_mot_obstaculos": "obstaculos motores",
  "sint_mot_estrategias": "estrategias motoras",
  "sint_aut_necesidades": "necesidades de autonomia",
  "sint_aut_obstaculos": "obstaculos de autonomia",
  "sint_aut_estrategias": "estrategias de autonomia",
  "sint_sen_necesidades": "necesidades sensoriales",
  "sint_sen_obstaculos": "obstaculos sensoriales",
  "conclusion_areas": "conclusion por area evaluada",
  "conclusion_general": "conclusion general del informe",
  "sug_establecimiento": "sugerencias al establecimiento educacional",
  "sug_equipo_aula": "sugerencias al equipo de aula",
  "sug_estudiante": "sugerencias al estudiante",
  "sug_familia": "sugerencias a la familia",
  "sug_instituciones": "derivaciones a otras instituciones o redes externas"
}}
Responde UNICAMENTE con el objeto JSON puro. No incluyas texto antes ni despues."""

                    try:
                        respuesta = modelo.invoke(prompt_borrador)
                        match = re.search(r'\{.*\}', respuesta, re.DOTALL)
                        borrador_datos = json.loads(match.group(0))
                        for k in st.session_state.psico_borrador.keys():
                            if k in borrador_datos:
                                st.session_state.psico_borrador[k] = borrador_datos[k]
                        st.session_state.psico_decision_ia = "completado"
                        st.session_state.psico_mostrar_panel = "con_ia"
                        confirmacion = "¡Borrador generado! Revisa y edita los campos en el formulario de abajo."
                        st.markdown(confirmacion)
                        st.session_state.psico_mensajes.append({"rol": "assistant", "contenido": confirmacion, "mostrar": confirmacion})
                    except Exception as e:
                        st.error(f"Error al generar el borrador: {e}")
                        st.session_state.psico_mostrar_panel = "manual"
                        st.session_state.psico_decision_ia = "completado"
                        msg = f"Hubo un error con la IA ({e}). He habilitado el formulario manual."
                        st.markdown(msg)
                        st.session_state.psico_mensajes.append({"rol": "assistant", "contenido": msg, "mostrar": msg})
                else:
                    msg = "Si quieres modificar algo, edita directamente los campos del formulario abajo y genera el documento."
                    st.markdown(msg)

# ==========================================
# PANEL FASE 4 - FORMULARIO
# ==========================================
if st.session_state.psico_etapa == 4 and st.session_state.psico_mostrar_panel is not None:
    st.markdown("---")
    st.header("📝 Fase 4: Contenido del Informe Psicopedagógico")

    if st.button("⬅️ Cambiar opción / Volver", use_container_width=True):
        st.session_state.psico_mostrar_panel = None
        st.session_state.psico_decision_ia = "esperando"
        st.session_state.psico_file_ready = None
        st.rerun()

    if st.session_state.psico_mostrar_panel == "con_ia":
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🪄 Regenerar borrador con IA", type="primary", use_container_width=True):
                st.session_state.psico_decision_ia = "solicitando_info"
                st.rerun()
        with col2:
            if st.button("🧹 Limpiar borrador", use_container_width=True):
                for k in st.session_state.psico_borrador:
                    st.session_state.psico_borrador[k] = ""
                st.session_state.psico_file_ready = None
                st.rerun()

    with st.form("formulario_psico"):

        st.subheader("Identificación y Motivo")
        motivo = st.selectbox(
            "Motivo de Evaluación Psicopedagógica",
            ["Ingreso", "Reevaluación", "Otro"],
            index=["Ingreso", "Reevaluación", "Otro"].index(
                st.session_state.psico_borrador.get("motivo_evaluacion", "Ingreso")
            ) if st.session_state.psico_borrador.get("motivo_evaluacion", "Ingreso") in ["Ingreso", "Reevaluación", "Otro"] else 0
        )
        otro_motivo = st.text_input("Si seleccionó 'Otro', especifique:", value=st.session_state.psico_borrador.get("otro_motivo", ""))
        instrumentos = st.text_area("Instrumentos Aplicados", value=st.session_state.psico_borrador.get("instrumentos_psico", ""))
        historia = st.text_area("Antecedentes Relevantes sobre la Historia Escolar", value=st.session_state.psico_borrador.get("historia_escolar_psico", ""), height=120)

        st.markdown("---")
        st.subheader("🧩 Análisis Cualitativo")

        st.markdown("**a) Habilidades Cognitivas y Comunicativas**")
        cog_fort = st.text_area("Cognitivas — Adecuado desarrollo en:", value=st.session_state.psico_borrador.get("analisis_cog_fortalezas", ""))
        cog_dif = st.text_area("Cognitivas — Menor desarrollo en:", value=st.session_state.psico_borrador.get("analisis_cog_dificultades", ""))
        com_fort = st.text_area("Comunicativas — Adecuado desarrollo en:", value=st.session_state.psico_borrador.get("analisis_com_fortalezas", ""))
        com_dif = st.text_area("Comunicativas — Menor desarrollo en:", value=st.session_state.psico_borrador.get("analisis_com_dificultades", ""))

        st.markdown("**b) Habilidades Personales, Socioemocionales y de Aproximación al Aprendizaje**")
        soc_fort = st.text_area("Socioemocionales — Adecuado desarrollo en:", value=st.session_state.psico_borrador.get("analisis_soc_fortalezas", ""))
        soc_dif = st.text_area("Socioemocionales — Menor desarrollo en:", value=st.session_state.psico_borrador.get("analisis_soc_dificultades", ""))
        apr_fort = st.text_area("Aproximación al Aprendizaje — Adecuado desarrollo en:", value=st.session_state.psico_borrador.get("analisis_apr_fortalezas", ""))
        apr_dif = st.text_area("Aproximación al Aprendizaje — Menor desarrollo en:", value=st.session_state.psico_borrador.get("analisis_apr_dificultades", ""))

        st.markdown("**c) Habilidades Motoras, de Autonomía y Sensoriales**")
        mot_fort = st.text_area("Motoras — Adecuado desarrollo en:", value=st.session_state.psico_borrador.get("analisis_mot_fortalezas", ""))
        mot_dif = st.text_area("Motoras — Menor desarrollo en:", value=st.session_state.psico_borrador.get("analisis_mot_dificultades", ""))
        aut_fort = st.text_area("Autonomía — Adecuado desarrollo en:", value=st.session_state.psico_borrador.get("analisis_aut_fortalezas", ""))
        aut_dif = st.text_area("Autonomía — Menor desarrollo en:", value=st.session_state.psico_borrador.get("analisis_aut_dificultades", ""))
        sen_fort = st.text_area("Sensorial — Adecuado desarrollo en:", value=st.session_state.psico_borrador.get("analisis_sen_fortalezas", ""))
        sen_dif = st.text_area("Sensorial — Menor desarrollo en:", value=st.session_state.psico_borrador.get("analisis_sen_dificultades", ""))

        st.markdown("---")
        st.subheader("📊 Síntesis")

        st.markdown("**a) Cognitivas y Comunicativas**")
        sint_cog_prog = st.text_area("Cognitivas — Progresos/Necesidades:", value=st.session_state.psico_borrador.get("sint_cog_progresos", ""))
        sint_cog_obs = st.text_area("Cognitivas — Obstáculos:", value=st.session_state.psico_borrador.get("sint_cog_obstaculos", ""))
        sint_cog_fac = st.text_area("Cognitivas — Factores del entorno:", value=st.session_state.psico_borrador.get("sint_cog_factores", ""))
        sint_cog_est = st.text_area("Cognitivas — Estrategias:", value=st.session_state.psico_borrador.get("sint_cog_estrategias", ""))
        sint_com_nec = st.text_area("Comunicativas — Necesidades:", value=st.session_state.psico_borrador.get("sint_com_necesidades", ""))
        sint_com_obs = st.text_area("Comunicativas — Obstáculos:", value=st.session_state.psico_borrador.get("sint_com_obstaculos", ""))

        st.markdown("**b) Socioemocionales y Aproximación al Aprendizaje**")
        sint_soc_fort = st.text_area("Socioemocionales — Fortalezas:", value=st.session_state.psico_borrador.get("sint_soc_fortalezas", ""))
        sint_soc_nec = st.text_area("Socioemocionales — Necesidades:", value=st.session_state.psico_borrador.get("sint_soc_necesidades", ""))
        sint_soc_obs = st.text_area("Socioemocionales — Obstáculos:", value=st.session_state.psico_borrador.get("sint_soc_obstaculos", ""))
        sint_soc_est = st.text_area("Socioemocionales — Estrategias:", value=st.session_state.psico_borrador.get("sint_soc_estrategias", ""))
        sint_apr_fort = st.text_area("Aprox. Aprendizaje — Fortalezas:", value=st.session_state.psico_borrador.get("sint_apr_fortalezas", ""))
        sint_apr_nec = st.text_area("Aprox. Aprendizaje — Necesidades:", value=st.session_state.psico_borrador.get("sint_apr_necesidades", ""))
        sint_apr_obs = st.text_area("Aprox. Aprendizaje — Obstáculos:", value=st.session_state.psico_borrador.get("sint_apr_obstaculos", ""))
        sint_apr_est = st.text_area("Aprox. Aprendizaje — Estrategias:", value=st.session_state.psico_borrador.get("sint_apr_estrategias", ""))

        st.markdown("**c) Motoras, Autonomía y Sensorial**")
        sint_mot_nec = st.text_area("Motoras — Necesidades:", value=st.session_state.psico_borrador.get("sint_mot_necesidades", ""))
        sint_mot_obs = st.text_area("Motoras — Obstáculos:", value=st.session_state.psico_borrador.get("sint_mot_obstaculos", ""))
        sint_mot_est = st.text_area("Motoras — Estrategias:", value=st.session_state.psico_borrador.get("sint_mot_estrategias", ""))
        sint_aut_nec = st.text_area("Autonomía — Necesidades:", value=st.session_state.psico_borrador.get("sint_aut_necesidades", ""))
        sint_aut_obs = st.text_area("Autonomía — Obstáculos:", value=st.session_state.psico_borrador.get("sint_aut_obstaculos", ""))
        sint_aut_est = st.text_area("Autonomía — Estrategias:", value=st.session_state.psico_borrador.get("sint_aut_estrategias", ""))
        sint_sen_nec = st.text_area("Sensorial — Necesidades:", value=st.session_state.psico_borrador.get("sint_sen_necesidades", ""))
        sint_sen_obs = st.text_area("Sensorial — Obstáculos:", value=st.session_state.psico_borrador.get("sint_sen_obstaculos", ""))

        st.markdown("---")
        st.subheader("📌 Conclusión")
        conc_areas = st.text_area("Por área evaluada:", value=st.session_state.psico_borrador.get("conclusion_areas", ""), height=120)
        conc_general = st.text_area("General:", value=st.session_state.psico_borrador.get("conclusion_general", ""), height=100)

        st.markdown("---")
        st.subheader("💡 Sugerencias")
        sug_est = st.text_area("Al establecimiento educacional:", value=st.session_state.psico_borrador.get("sug_establecimiento", ""))
        sug_aula = st.text_area("Al equipo de aula:", value=st.session_state.psico_borrador.get("sug_equipo_aula", ""))
        sug_alu = st.text_area("Al estudiante:", value=st.session_state.psico_borrador.get("sug_estudiante", ""))
        sug_fam = st.text_area("A la familia:", value=st.session_state.psico_borrador.get("sug_familia", ""))
        sug_inst = st.text_area("Otras instituciones o redes externas:", value=st.session_state.psico_borrador.get("sug_instituciones", ""))

        submit = st.form_submit_button("💾 Generar Documento Word Final", type="primary", use_container_width=True)

        if submit:
            # Checkboxes de motivo
            check_ingreso = "☒" if motivo == "Ingreso" else "☐"
            check_reevaluacion = "☒" if motivo == "Reevaluación" else "☐"
            check_otro = "☒" if motivo == "Otro" else "☐"

            datos_finales = {
                # Estudiante
                "nombre_est_psico": st.session_state.psico_datos_estudiante.get("nombre", ""),
                "nombre_social_est_psico": st.session_state.psico_datos_estudiante.get("nombre", ""),
                "fecha_nac_psico": st.session_state.psico_datos_estudiante.get("fecha_nacimiento", ""),
                "edad_psico": st.session_state.psico_datos_estudiante.get("edad", ""),
                "establecimiento_psico": st.session_state.psico_datos_estudiante.get("establecimiento", ""),
                "curso_psico": st.session_state.psico_datos_estudiante.get("curso", ""),
                "fecha_evaluacion_psico": st.session_state.psico_datos_estudiante.get("fecha_evaluacion", ""),
                "diagnostico_psico": st.session_state.psico_datos_estudiante.get("diagnostico", ""),
                "fecha_emision_diag_psico": st.session_state.psico_datos_estudiante.get("fecha_emision_diagnostico", ""),
                # Motivo
                "check_ingreso_psico": check_ingreso,
                "check_reevaluacion_psico": check_reevaluacion,
                "check_otro_psico": check_otro,
                # Contenido
                "instrumentos_psico": instrumentos,
                "historia_escolar_psico": historia,
                "analisis_cog_fortalezas": cog_fort,
                "analisis_cog_dificultades": cog_dif,
                "analisis_com_fortalezas": com_fort,
                "analisis_com_dificultades": com_dif,
                "analisis_soc_fortalezas": soc_fort,
                "analisis_soc_dificultades": soc_dif,
                "analisis_apr_fortalezas": apr_fort,
                "analisis_apr_dificultades": apr_dif,
                "analisis_mot_fortalezas": mot_fort,
                "analisis_mot_dificultades": mot_dif,
                "analisis_aut_fortalezas": aut_fort,
                "analisis_aut_dificultades": aut_dif,
                "analisis_sen_fortalezas": sen_fort,
                "analisis_sen_dificultades": sen_dif,
                # Síntesis
                "sint_cog_progresos": sint_cog_prog,
                "sint_cog_obstaculos": sint_cog_obs,
                "sint_cog_factores": sint_cog_fac,
                "sint_cog_estrategias": sint_cog_est,
                "sint_com_necesidades": sint_com_nec,
                "sint_com_obstaculos": sint_com_obs,
                "sint_soc_fortalezas": sint_soc_fort,
                "sint_soc_necesidades": sint_soc_nec,
                "sint_soc_obstaculos": sint_soc_obs,
                "sint_soc_estrategias": sint_soc_est,
                "sint_apr_fortalezas": sint_apr_fort,
                "sint_apr_necesidades": sint_apr_nec,
                "sint_apr_obstaculos": sint_apr_obs,
                "sint_apr_estrategias": sint_apr_est,
                "sint_mot_necesidades": sint_mot_nec,
                "sint_mot_obstaculos": sint_mot_obs,
                "sint_mot_estrategias": sint_mot_est,
                "sint_aut_necesidades": sint_aut_nec,
                "sint_aut_obstaculos": sint_aut_obs,
                "sint_aut_estrategias": sint_aut_est,
                "sint_sen_necesidades": sint_sen_nec,
                "sint_sen_obstaculos": sint_sen_obs,
                # Conclusión
                "conclusion_areas": conc_areas,
                "conclusion_general": conc_general,
                # Sugerencias
                "sug_establecimiento": sug_est,
                "sug_equipo_aula": sug_aula,
                "sug_estudiante": sug_alu,
                "sug_familia": sug_fam,
                "sug_instituciones": sug_inst,
                # Profesional
                "nombre_prof_psico": st.session_state.psico_datos_profesional.get("nombre_prof", ""),
                "rut_prof_psico": st.session_state.psico_datos_profesional.get("rut_prof", ""),
                "profesion_prof_psico": st.session_state.psico_datos_profesional.get("profesion_prof", ""),
                "registro_prof_psico": st.session_state.psico_datos_profesional.get("registro_prof", ""),
                # Docente
                "nombre_docente": st.session_state.psico_datos_docente.get("nombre_docente", ""),
                "rut_docente": st.session_state.psico_datos_docente.get("rut_docente", ""),
                "profesion_docente": st.session_state.psico_datos_docente.get("profesion_docente", ""),
            }

            try:
                doc = DocxTemplate("planillas/plantilla_psicopedagogica.docx")
                doc.render(datos_finales)
                os.makedirs("informes_generados", exist_ok=True)
                nombre_clean = datos_finales["nombre_est_psico"].replace(" ", "_")
                ruta_salida = f"informes_generados/Informe_Psico_{nombre_clean}.docx"
                doc.save(ruta_salida)
                with open(ruta_salida, "rb") as f:
                    byte_data = f.read()
                st.session_state.psico_file_ready = {
                    "data": byte_data,
                    "filename": f"Informe_Psico_{nombre_clean}.docx"
                }
                st.success("¡Informe generado correctamente!")
                st.rerun()
            except Exception as e:
                st.error(f"Error al generar el documento: {e}")

    if st.session_state.psico_file_ready:
        st.download_button(
            label="📥 Descargar Informe Psicopedagógico",
            data=st.session_state.psico_file_ready["data"],
            file_name=st.session_state.psico_file_ready["filename"],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
