import streamlit as st
import json
import os
import re
from docxtpl import DocxTemplate
from langchain_ollama import OllamaLLM
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader

# ==========================================
# 1. CONFIGURACIÓN INICIAL Y MODELO
# ==========================================
st.set_page_config(page_title="Asistente PIE", page_icon="📝", layout="centered")

st.title("🤖 Asistente de Informes PIE")
st.write("Sube los antecedentes o conversemos para generar el documento oficial.")

@st.cache_resource
def cargar_modelo():
    return OllamaLLM(model="llama3.2") 

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
    except Exception as e:
        pass
    return None

# ==========================================
# 2. INICIALIZACIÓN DE LA MEMORIA
# ==========================================
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []
if "texto_pendiente" not in st.session_state:
    st.session_state.texto_pendiente = ""
if "archivo_actual" not in st.session_state:
    st.session_state.archivo_actual = ""
# NUEVA VARIABLE DE ESTADO (ETAPAS)
if "etapa" not in st.session_state:
    st.session_state.etapa = 1 
if "borrador" not in st.session_state:
    st.session_state.borrador = {
        "motivo_evaluacion": "Ingreso",
        "instrumentos_aplicados": "",
        "fecha_evaluacion": "",
        "diagnostico_nee": "",
        "fortalezas_pedagogicas": "",
        "necesidades_pedagogicas": "",
        "fortalezas_sociales": "",
        "necesidades_sociales": "",
        "trabajo_colaborativo": "",
        "apoyos_hogar": "",
        "acuerdos_compromisos": "",
        "fechas_evaluacion": "",
        "nombre_receptor": "",
        "rut_receptor": "",
        "nombre_social_receptor": "",
        "telefono_receptor": "",
        "email_receptor": "",
        "relacion_receptor": "",
        "presencia_receptor": "",
        "tipo_apoderado": "Apoderado/a titular",
        "poder_simple": "No Aplica"
    }
if "datos_estudiante" not in st.session_state:
    st.session_state.datos_estudiante = {}
if "datos_profesional" not in st.session_state:
    st.session_state.datos_profesional = {}
if "file_ready" not in st.session_state:
    st.session_state.file_ready = None
if "mostrar_panel" not in st.session_state:
    st.session_state.mostrar_panel = None
if "decision_ia" not in st.session_state:
    st.session_state.decision_ia = None

# ==========================================
# 3. BARRA LATERAL (LIMPIEZA)
# ==========================================
with st.sidebar:
    st.header("⚙️ Opciones")
    if st.button("🧹 Nuevo Estudiante / Limpiar Chat"):
        st.session_state.mensajes = []
        st.session_state.texto_pendiente = ""
        st.session_state.archivo_actual = ""
        st.session_state.uploader_key += 1
        st.session_state.etapa = 1 # Reiniciamos a la fase 1
        st.session_state.borrador = {
            "motivo_evaluacion": "Ingreso",
            "instrumentos_aplicados": "",
            "fecha_evaluacion": "",
            "diagnostico_nee": "",
            "fortalezas_pedagogicas": "",
            "necesidades_pedagogicas": "",
            "fortalezas_sociales": "",
            "necesidades_sociales": "",
            "trabajo_colaborativo": "",
            "apoyos_hogar": "",
            "acuerdos_compromisos": "",
            "fechas_evaluacion": "",
            "nombre_receptor": "",
            "rut_receptor": "",
            "nombre_social_receptor": "",
            "telefono_receptor": "",
            "email_receptor": "",
            "relacion_receptor": "",
            "presencia_receptor": "",
            "tipo_apoderado": "Apoderado/a titular",
            "poder_simple": "No Aplica"
        }
        st.session_state.datos_estudiante = {}
        st.session_state.datos_profesional = {}
        st.session_state.file_ready = None
        st.session_state.mostrar_panel = None
        st.session_state.decision_ia = None
        st.rerun()

# ==========================================
# 4. CARGA DE ARCHIVOS
# ==========================================
archivo_subido = st.file_uploader("Sube antecedentes (PDF o Word)", type=['pdf', 'docx'], key=st.session_state.uploader_key)

if archivo_subido is not None:
    if st.session_state.archivo_actual != archivo_subido.name:
        with st.spinner("Adjuntando archivo de forma invisible..."):
            os.makedirs("temp", exist_ok=True)
            ruta_temp = os.path.join("temp", archivo_subido.name)
            with open(ruta_temp, "wb") as f:
                f.write(archivo_subido.getbuffer())
            
            texto_extraido = ""
            try:
                if archivo_subido.name.endswith('.pdf'):
                    loader = PyPDFLoader(ruta_temp)
                    docs = loader.load()
                    texto_extraido = "\n".join([doc.page_content for doc in docs])
                elif archivo_subido.name.endswith('.docx'):
                    loader = Docx2txtLoader(ruta_temp)
                    docs = loader.load()
                    texto_extraido = "\n".join([doc.page_content for doc in docs])
                
                st.session_state.texto_pendiente = f"--- INICIO DEL DOCUMENTO '{archivo_subido.name}' ---\n{texto_extraido}\n--- FIN DEL DOCUMENTO ---"
                st.session_state.archivo_actual = archivo_subido.name
                st.success(f"📎 Archivo '{archivo_subido.name}' adjuntado. Escribe algo en el chat para procesarlo.")
            except Exception as e:
                st.error(f"Error al leer el documento: {e}")

# ==========================================
# 5. INTERFAZ DEL CHAT (ARQUITECTURA DE SUPERVISOR)
# ==========================================
# Dibujar mensajes previos en pantalla
for mensaje in st.session_state.mensajes:
    if mensaje.get("mostrar", "") != "":
        with st.chat_message(mensaje["rol"]):
            st.markdown(mensaje.get("mostrar", mensaje["contenido"]))

prompt = st.chat_input("Ej: Hola, el alumno se llama...")

if prompt:
    # 1. Mostrar el mensaje del usuario
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 2. Guardar en memoria (con o sin documento adjunto)
    if "texto_pendiente" in st.session_state and st.session_state.texto_pendiente != "":
        st.session_state.mensajes.append({
            "rol": "user", 
            "contenido": f"Contexto del documento:\n{st.session_state.texto_pendiente}\n\nInstrucción: {prompt}", 
            "mostrar": prompt
        })
        st.session_state.texto_pendiente = "" 
    else:
        st.session_state.mensajes.append({
            "rol": "user", 
            "contenido": prompt, 
            "mostrar": prompt
        })

    # 3. Construir un historial limpio para la IA
    historial_texto = ""
    for m in st.session_state.mensajes:
        rol = "Usuario" if m["rol"] == "user" else "Asistente"
        historial_texto += f"{rol}: {m['contenido']}\n"

    # 4. LÓGICA DE CONTROL (PYTHON ES EL JEFE)
    with st.chat_message("assistant"):
        with st.spinner("Procesando información..."):
            
            # ---------------------------------------------------------
            # ETAPA 1: DATOS DEL ESTUDIANTE
            # ---------------------------------------------------------
            if st.session_state.etapa == 1:
                
                # A. Extracción silenciosa de validación
                prompt_check = f"""Analiza el historial y extrae los datos del estudiante en un objeto JSON puro.
Usa estrictamente la siguiente plantilla JSON con las llaves indicadas:
{{
  "nombre": "nombre completo del alumno o 'FALTA'",
  "rut": "RUT del alumno o 'FALTA'",
  "fecha_nacimiento": "fecha de nacimiento o 'FALTA'",
  "edad": "edad (ej: 11 años) o 'FALTA'",
  "curso": "curso y letra (ej: 5° Básico B) o 'FALTA'",
  "establecimiento": "colegio o 'FALTA'"
}}
Si un dato no se menciona en la conversación, pon 'FALTA'. No inventes información.

Historial:
{historial_texto}

Responde ÚNICAMENTE con el objeto JSON:"""
                check_json = modelo.invoke(prompt_check)
                
                # B. Python evalúa (no la IA)
                datos = extraer_json(check_json)
                if datos is not None:
                    try:
                        # Asegurar que todas las llaves existan
                        for key in ["nombre", "rut", "fecha_nacimiento", "edad", "curso", "establecimiento"]:
                            if key not in datos:
                                datos[key] = "FALTA"
                        # Buscamos cuáles claves dicen "FALTA" o están vacías
                        faltantes = [k for k, v in datos.items() if "FALTA" in str(v).upper() or v == ""]
                    except:
                        faltantes = ["los datos básicos del estudiante que aún no me hayas dado (Nombre, RUT, Fecha de Nacimiento, Edad, Curso, Establecimiento)"]
                else:
                    faltantes = ["los datos básicos del estudiante que aún no me hayas dado (Nombre, RUT, Fecha de Nacimiento, Edad, Curso, Establecimiento)"]
                
                # C. Toma de decisión
                if len(faltantes) == 0:
                    st.session_state.datos_estudiante = datos
                    st.session_state.etapa = 2
                    st.info("✅ Datos del estudiante completos. Pasando a la Fase 2: Datos del Profesional...")
                    mensaje_transicion = "¡Excelente! Ya tengo los datos del estudiante. Para terminar, indícame los datos del profesional a cargo (Tu Nombre, RUT, Rol/Cargo, Teléfono, E-mail y Fecha de entrega)."
                    st.session_state.mensajes.append({"rol": "assistant", "contenido": mensaje_transicion, "mostrar": mensaje_transicion})
                    st.rerun() # Recarga para mostrar la nueva fase
                
                else:
                    # Le pedimos a la IA que genere una respuesta natural pidiendo SOLO lo que falta
                    prompt_hablar = f"""Eres un asistente amable ayudando a un PROFESIONAL DE EDUCACIÓN (Profesor/Psicólogo). NO estás hablando con el estudiante.
Según el historial, faltan estos datos del estudiante: {', '.join(faltantes)}.
Dirígete al profesional y hazle UNA sola pregunta natural pidiendo estrictamente esos datos faltantes.
Historial:
{historial_texto}"""
                    respuesta_ia = modelo.invoke(prompt_hablar)
                    st.markdown(respuesta_ia)
                    st.session_state.mensajes.append({"rol": "assistant", "contenido": respuesta_ia, "mostrar": respuesta_ia})

            # ---------------------------------------------------------
            # ETAPA 2: DATOS DEL PROFESIONAL
            # ---------------------------------------------------------
            elif st.session_state.etapa == 2:
                
                # A. Extracción silenciosa
                prompt_check = f"""Analiza el historial y extrae los datos del profesional en un objeto JSON puro.
Usa estrictamente la siguiente plantilla JSON con las llaves indicadas:
{{
  "nombre_prof": "nombre completo o 'FALTA'",
  "rut_prof": "RUT o 'FALTA'",
  "rol": "cargo/rol profesional o 'FALTA'",
  "telefono": "teléfono o 'FALTA'",
  "email": "email o 'FALTA'",
  "fecha_entrega_informe": "fecha en que se entrega o redacta el informe (NO es tu cumpleaños ni tu nacimiento) o 'FALTA'"
}}
Si un dato no se menciona en la conversación, pon 'FALTA'. No inventes información.

Historial:
{historial_texto}

Responde ÚNICAMENTE con el objeto JSON:"""
                check_json = modelo.invoke(prompt_check)
                
                datos = extraer_json(check_json)
                if datos is not None:
                    try:
                        # Asegurar que todas las llaves existan
                        for key in ["nombre_prof", "rut_prof", "rol", "telefono", "email", "fecha_entrega_informe"]:
                            if key not in datos:
                                datos[key] = "FALTA"
                        faltantes = [k for k, v in datos.items() if "FALTA" in str(v).upper() or v == ""]
                    except:
                        faltantes = ["los datos de tu perfil profesional que falten (Nombre, RUT, Rol, Teléfono, Email, Fecha de entrega del informe)"]
                else:
                    faltantes = ["los datos de tu perfil profesional que falten (Nombre, RUT, Rol, Teléfono, Email, Fecha de entrega del informe)"]

                # B. Toma de decisión final
                if len(faltantes) == 0:
                    st.session_state.datos_profesional = datos
                    
                    st.session_state.etapa = 3
                    st.info("✅ Datos del profesional recolectados. Pasando a la Fase 3: Datos del Receptor (Apoderado)...")
                    mensaje_transicion = "¡Excelente! Ya tengo tus datos profesionales. Ahora, por favor indícame los datos de la persona que recibe la información (Nombre, RUT, Nombre social, Teléfono, E-mail, Relación con el estudiante y quiénes están presentes en la reunión)."
                    st.session_state.mensajes.append({"rol": "assistant", "contenido": mensaje_transicion, "mostrar": mensaje_transicion})
                    st.rerun()
                
                else:
                    # Dar contexto a la IA sobre qué significa cada campo para evitar alucinaciones
                    prompt_hablar = f"""Eres un asistente amable. Estás hablando con el PROFESIONAL que redactará el informe.
Faltan estos datos del propio profesional: {', '.join(faltantes)}.
(Nota: 'fecha_entrega_informe' es la fecha de entrega del informe, NO preguntes por su fecha de nacimiento).
Dirígete a él de forma natural y hazle UNA sola pregunta para conseguir sus propios datos faltantes.
Historial:
{historial_texto}"""
                    respuesta_ia = modelo.invoke(prompt_hablar)
                    st.markdown(respuesta_ia)
                    st.session_state.mensajes.append({"rol": "assistant", "contenido": respuesta_ia, "mostrar": respuesta_ia})

            # ---------------------------------------------------------
            # ETAPA 3: DATOS DEL RECEPTOR (APODERADO)
            # ---------------------------------------------------------
            elif st.session_state.etapa == 3:
                # A. Extracción silenciosa
                prompt_check = f"""Analiza el historial y extrae los datos del receptor (apoderado) en un objeto JSON puro.
Usa estrictamente la siguiente plantilla JSON con las llaves indicadas:
{{
  "nombre_rec": "nombre completo o 'FALTA'",
  "rut_rec": "RUT o 'FALTA'",
  "nombre_social_rec": "nombre social o 'FALTA'",
  "telefono_rec": "teléfono o 'FALTA'",
  "email_rec": "email o 'FALTA'",
  "relacion_rec": "relación (ej: madre, padre, abuela, tutor) o 'FALTA'",
  "presencia_rec": "personas presentes (ej: madre y psicóloga) o 'FALTA'"
}}
Si un dato no se menciona en la conversación, pon 'FALTA'. No inventes información.

Historial:
{historial_texto}

Responde ÚNICAMENTE con el objeto JSON:"""
                check_json = modelo.invoke(prompt_check)
                
                try:
                    datos = extraer_json(check_json)
                    # Asegurar que todas las llaves existan
                    for key in ["nombre_rec", "rut_rec", "nombre_social_rec", "telefono_rec", "email_rec", "relacion_rec", "presencia_rec"]:
                        if datos is None or key not in datos:
                            if datos is None: datos = {}
                            datos[key] = "FALTA"
                    faltantes = [k for k, v in datos.items() if "FALTA" in str(v).upper() or v == ""]
                except:
                    faltantes = ["los datos de la persona que recibe la información (Nombre, RUT, Nombre social, Teléfono, Email, Relación con el estudiante, Presencia)"]

                # B. Toma de decisión final
                if len(faltantes) == 0:
                    st.session_state.borrador["nombre_receptor"] = datos.get("nombre_rec", "")
                    st.session_state.borrador["rut_receptor"] = datos.get("rut_rec", "")
                    st.session_state.borrador["nombre_social_receptor"] = datos.get("nombre_social_rec", "")
                    st.session_state.borrador["telefono_receptor"] = datos.get("telefono_rec", "")
                    st.session_state.borrador["email_receptor"] = datos.get("email_rec", "")
                    st.session_state.borrador["relacion_receptor"] = datos.get("relacion_rec", "")
                    st.session_state.borrador["presencia_receptor"] = datos.get("presencia_rec", "")
                    
                    st.session_state.etapa = 4
                    st.session_state.decision_ia = "esperando"
                    st.info("✅ Datos del receptor recolectados. Pasando a la Fase 4...")
                    mensaje_transicion = "¡Perfecto! Hemos recopilado todos los datos de identificación.\n\n¿Deseas agregar antecedentes o información adicional sobre el estudiante para que la IA redacte un borrador de los resultados (responde **Sí**), o prefieres rellenar y generar la plantilla editable directamente (responde **No**)?"
                    st.session_state.mensajes.append({"rol": "assistant", "contenido": mensaje_transicion, "mostrar": mensaje_transicion})
                    st.rerun()
                
                else:
                    prompt_hablar = f"""Eres un asistente amable ayudando a un PROFESIONAL DE EDUCACIÓN.
Faltan estos datos de la persona que recibe la información (apoderado): {', '.join(faltantes)}.
Dirígete al profesional y hazle UNA sola pregunta de forma natural para conseguir los datos del receptor faltantes.
Historial:
{historial_texto}"""
                    respuesta_ia = modelo.invoke(prompt_hablar)
                    st.markdown(respuesta_ia)
                    st.session_state.mensajes.append({"rol": "assistant", "contenido": respuesta_ia, "mostrar": respuesta_ia})

            # ---------------------------------------------------------
            # ETAPA 4: BORRADOR DE EVALUACIÓN
            # ---------------------------------------------------------
            elif st.session_state.etapa == 4:
                user_reply = prompt.strip().lower()
                
                if st.session_state.decision_ia == "esperando":
                    user_reply_clean = re.sub(r'[^\w\s]', '', user_reply)
                    palabras = user_reply_clean.split()
                    
                    afirmaciones = ["si", "sí", "yes", "agregar", "añadir", "redactar", "ia", "s"]
                    negaciones = ["no", "directamente", "n", "manual"]
                    
                    es_si = any(p in afirmaciones for p in palabras) or "si" in user_reply_clean
                    es_no = any(p in negaciones for p in palabras) or "no" in user_reply_clean
                    
                    if es_si and not es_no:
                        st.session_state.decision_ia = "solicitando_info"
                        respuesta_ia = "¡Excelente! Por favor, escribe aquí la información adicional del alumno o sube un archivo (PDF/DOCX) con sus antecedentes. Una vez que me envíes este texto, yo me encargaré de redactar el borrador con la IA y mostrarte el formulario editado."
                        st.markdown(respuesta_ia)
                        st.session_state.mensajes.append({"rol": "assistant", "contenido": respuesta_ia, "mostrar": respuesta_ia})
                    elif es_no:
                        st.session_state.decision_ia = "no"
                        st.session_state.mostrar_panel = "sin_ia"
                        respuesta_ia = "Entendido. He habilitado la plantilla editable en la parte inferior de la pantalla para que la completes de manera manual."
                        st.markdown(respuesta_ia)
                        st.session_state.mensajes.append({"rol": "assistant", "contenido": respuesta_ia, "mostrar": respuesta_ia})
                    else:
                        respuesta_ia = "Disculpa, no me quedó claro. ¿Deseas agregar más información para redactar con IA? Por favor responde **Sí** o **No**."
                        st.markdown(respuesta_ia)
                        st.session_state.mensajes.append({"rol": "assistant", "contenido": respuesta_ia, "mostrar": respuesta_ia})
                        
                elif st.session_state.decision_ia == "solicitando_info":
                    respuesta_ia_espera = "Recibido. Estoy analizando la información y redactando la propuesta técnica para el informe. Un momento por favor..."
                    st.markdown(respuesta_ia_espera)
                    
                    contexto_completo = ""
                    for msg in st.session_state.mensajes:
                        if msg.get("mostrar", ""):
                            contexto_completo += f"Usuario: {msg['mostrar']}\n"
                        else:
                            contexto_completo += f"{'Usuario' if msg['rol']=='user' else 'Asistente'}: {msg['contenido']}\n"
            
                    if st.session_state.texto_pendiente:
                        contexto_completo += f"\nTexto de antecedentes cargados:\n{st.session_state.texto_pendiente}\n"
            
                    prompt_borrador = f"""Actúa como un experto psicopedagogo y redactor de informes PIE en Chile (Decreto 170).
Analiza la conversación e información adjunta para redactar el informe técnico del estudiante de forma muy profesional, formal y detallada.

Información recopilada:
{contexto_completo}

Genera un JSON con las siguientes claves exactas en español:
{{
  "motivo_evaluacion": "Ingreso" o "Reevaluacion" (sugiere basado en los datos),
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
Responde ÚNICAMENTE con el objeto JSON puro entre llaves. No incluyas explicaciones antes o después."""
            
                    try:
                        respuesta = modelo.invoke(prompt_borrador)
                        match = re.search(r'\{.*\}', respuesta, re.DOTALL)
                        borrador_datos = json.loads(match.group(0))
                
                        for k in st.session_state.borrador.keys():
                            if k in borrador_datos:
                                st.session_state.borrador[k] = borrador_datos[k]
                        
                        st.session_state.decision_ia = "completado"
                        st.session_state.mostrar_panel = "con_ia"
                        
                        confirmacion = "¡Borrador generado con éxito! He completado la propuesta técnica en el panel de abajo. Puedes editar los campos y descargar el documento final."
                        st.markdown(confirmacion)
                        st.session_state.mensajes.append({"rol": "assistant", "contenido": confirmacion, "mostrar": confirmacion})
                    except Exception as e:
                        st.error(f"Error al generar el borrador con la IA: {e}")
                        st.session_state.mostrar_panel = "con_ia"
                        st.session_state.decision_ia = "completado"
                        error_msg = f"Hubo un detalle al procesar con la IA ({e}). He habilitado el formulario abajo para que lo completes de manera manual."
                        st.markdown(error_msg)
                        st.session_state.mensajes.append({"rol": "assistant", "contenido": error_msg, "mostrar": error_msg})
                else:
                    respuesta_ia = "Si deseas modificar algún dato del informe, puedes editarlo directamente en los campos del formulario de abajo y luego presionar 'Generar Documento Word Final'."
                    st.markdown(respuesta_ia)
          # ==========================================
# 6. PANEL DE CONTROL FASE 4 (RESULTADOS DE EVALUACIÓN)
# ==========================================
if st.session_state.etapa == 4 and st.session_state.mostrar_panel is not None:
    st.markdown("---")
    st.header("📝 Fase 4: Resultados de la Evaluación y Borrador de Informe")
    
    # Botón para volver atrás
    if st.button("⬅️ Cambiar opción / Volver", use_container_width=True):
        st.session_state.mostrar_panel = None
        st.session_state.decision_ia = "esperando"
        st.session_state.file_ready = None
        st.rerun()
        
    if st.session_state.mostrar_panel == "con_ia":
        st.write("A continuación puedes generar un borrador automático usando la IA a partir de los documentos subidos o de la conversación, o rellenar el informe manualmente.")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🪄 Generar propuesta borrador con IA", type="primary", use_container_width=True):
                with st.spinner("La IA está analizando la información y redactando el informe..."):
                    # Compilar contexto completo
                    contexto_completo = ""
                    for msg in st.session_state.mensajes:
                        if msg.get("mostrar", ""):
                            contexto_completo += f"Usuario: {msg['mostrar']}\n"
                        else:
                            contexto_completo += f"{'Usuario' if msg['rol']=='user' else 'Asistente'}: {msg['contenido']}\n"
            
                    if st.session_state.texto_pendiente:
                        contexto_completo += f"\nTexto de antecedentes cargados:\n{st.session_state.texto_pendiente}\n"
            
                    prompt_borrador = f"""Actúa como un experto psicopedagogo y redactor de informes PIE en Chile (Decreto 170).
    Analiza la conversación e información adjunta para redactar el informe técnico del estudiante de forma muy profesional, formal y detallada.

    Información recopilada:
    {contexto_completo}

    Genera un JSON con las siguientes claves exactas en español:
    {{
      "motivo_evaluacion": "Ingreso" o "Reevaluacion" (sugiere basado en los datos),
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
      "fechas_evaluacion": "...",
      "nombre_receptor": "nombre completo del apoderado o receptor si se menciona en el historial, sino ''",
      "rut_receptor": "RUT del receptor si se menciona, sino ''",
      "nombre_social_receptor": "nombre social del receptor si se menciona, sino ''",
      "telefono_receptor": "teléfono del receptor si se menciona, sino ''",
      "email_receptor": "email del receptor si se menciona, sino ''",
      "relacion_receptor": "relación (madre, padre, abuelo, tutor, etc.) si se menciona, sino ''",
      "presencia_receptor": "otras personas presentes si se mencionan, sino ''",
      "tipo_apoderado": "Apoderado/a titular" o "Apoderado/a suplente",
      "poder_simple": "No Aplica" o "Sí" o "No"
    }}
    Responde ÚNICAMENTE con el objeto JSON puro entre llaves. No incluyas explicaciones antes o después."""
            
                    try:
                        respuesta = modelo.invoke(prompt_borrador)
                        match = re.search(r'\{.*\}', respuesta, re.DOTALL)
                        borrador_datos = json.loads(match.group(0))
                
                        # Actualizar st.session_state.borrador
                        for k in st.session_state.borrador.keys():
                            if k in borrador_datos:
                                st.session_state.borrador[k] = borrador_datos[k]
                        st.success("¡Propuesta de borrador generada exitosamente! Revisa los campos abajo.")
                    except Exception as e:
                        st.error(f"Error al generar el borrador con la IA: {e}")
                        st.code(respuesta if 'respuesta' in locals() else "")
                
        with col2:
            if st.button("🧹 Limpiar Borrador", use_container_width=True):
                for k in st.session_state.borrador.keys():
                    st.session_state.borrador[k] = ""
                st.session_state.file_ready = None
                st.rerun()

    # Formulario para editar el borrador
    with st.form("formulario_borrador"):
        st.subheader("Editar Contenido del Informe")
    
        motivo = st.selectbox(
            "Motivo de la Evaluación",
            ["Ingreso", "Reevaluación"],
            index=0 if st.session_state.borrador.get("motivo_evaluacion", "Ingreso") == "Ingreso" else 1
        )
        instrumentos = st.text_area(
            "Instrumentos Aplicados (nombre de test, pautas, etc.)",
            value=st.session_state.borrador.get("instrumentos_aplicados", "")
        )
        fecha_eval = st.text_input(
            "Fecha de la Evaluación (o fecha del informe psicopedagógico)",
            value=st.session_state.borrador.get("fecha_evaluacion", "")
        )
        diagnostico = st.text_area(
            "Diagnóstico asociado a NEE (sin siglas)",
            value=st.session_state.borrador.get("diagnostico_nee", "")
        )
    
        st.markdown("**Ámbito Pedagógico**")
        fort_ped = st.text_area("Fortalezas – Logros – Talentos", value=st.session_state.borrador.get("fortalezas_pedagogicas", ""))
        nec_ped = st.text_area("Necesidades de Apoyo Pedagógico", value=st.session_state.borrador.get("necesidades_pedagogicas", ""))
    
        st.markdown("**Ámbito Social / Afectivo**")
        fort_soc = st.text_area("Fortalezas – Logros – Talentos (Socioafectivo)", value=st.session_state.borrador.get("fortalezas_sociales", ""))
        nec_soc = st.text_area("Necesidades de Apoyo (Socioafectivo)", value=st.session_state.borrador.get("necesidades_sociales", ""))
    
        trabajo_colab = st.text_area("Trabajo Colaborativo y Apoyos Educativos para la Inclusión", value=st.session_state.borrador.get("trabajo_colaborativo", ""))
        apoyos_hogar = st.text_area("Apoyos que requiere en el hogar", value=st.session_state.borrador.get("apoyos_hogar", ""))
        acuerdos = st.text_area("Acuerdos y Compromisos Escuela - Familia", value=st.session_state.borrador.get("acuerdos_compromisos", ""))
        fechas_avance = st.text_input("Fechas en que se evaluarán los avances", value=st.session_state.borrador.get("fechas_evaluacion", ""))
    
        st.markdown("**Identificación del Receptor (Apoderado / Persona que recibe la información)**")
    
        tipo_apoderado = st.selectbox(
            "Tipo de Apoderado",
            ["Apoderado/a titular", "Apoderado/a suplente"],
            index=0 if st.session_state.borrador.get("tipo_apoderado", "Apoderado/a titular") == "Apoderado/a titular" else 1
        )
        poder_simple = st.selectbox(
            "¿Apoderado suplente presenta Poder Simple?",
            ["No Aplica", "Sí", "No"],
            index=0 if st.session_state.borrador.get("poder_simple", "No Aplica") == "No Aplica" else (1 if st.session_state.borrador.get("poder_simple") == "Sí" else 2)
        )
    
        submit_generar = st.form_submit_button("💾 Generar Documento Word Final", type="primary", use_container_width=True)
    
        if submit_generar:
            # Guardar valores del formulario en el estado por si acaso
            st.session_state.borrador.update({
                "motivo_evaluacion": motivo,
                "instrumentos_aplicados": instrumentos,
                "fecha_evaluacion": fecha_eval,
                "diagnostico_nee": diagnostico,
                "fortalezas_pedagogicas": fort_ped,
                "necesidades_pedagogicas": nec_ped,
                "fortalezas_sociales": fort_soc,
                "necesidades_sociales": nec_soc,
                "trabajo_colaborativo": trabajo_colab,
                "apoyos_hogar": apoyos_hogar,
                "acuerdos_compromisos": acuerdos,
                "fechas_evaluacion": fechas_avance,
                "tipo_apoderado": tipo_apoderado,
                "poder_simple": poder_simple
            })
        
            # Preparar todos los datos para la plantilla
            datos_finales = {}
        
            # Mapear datos del estudiante
            datos_finales["nombre_estudiante"] = st.session_state.datos_estudiante.get("nombre", "No especificado")
            datos_finales["nombre_social_estudiante"] = st.session_state.datos_estudiante.get("nombre_social", st.session_state.datos_estudiante.get("nombre", "No especificado"))
            datos_finales["rut_estudiante"] = st.session_state.datos_estudiante.get("rut", "No especificado")
            datos_finales["fecha_nacimiento_estudiante"] = st.session_state.datos_estudiante.get("fecha_nacimiento", "No especificado")
            datos_finales["edad_estudiante"] = st.session_state.datos_estudiante.get("edad", "No especificado")
            datos_finales["curso_estudiante"] = st.session_state.datos_estudiante.get("curso", "No especificado")
            datos_finales["establecimiento_estudiante"] = st.session_state.datos_estudiante.get("establecimiento", "No especificado")
        
            # Mapear datos del profesional
            datos_finales["nombre_profesional"] = st.session_state.datos_profesional.get("nombre_prof", "No especificado")
            datos_finales["nombre_social_profesional"] = st.session_state.datos_profesional.get("nombre_prof", "No especificado")
            datos_finales["rut_profesional"] = st.session_state.datos_profesional.get("rut_prof", "No especificado")
            datos_finales["rol_profesional"] = st.session_state.datos_profesional.get("rol", "No especificado")
            datos_finales["telefono_profesional"] = st.session_state.datos_profesional.get("telefono", "No especificado")
            datos_finales["email_profesional"] = st.session_state.datos_profesional.get("email", "No especificado")
            datos_finales["fecha_informe"] = st.session_state.datos_profesional.get("fecha_informe", "No especificado")
        
            # Mapear datos de la evaluación
            datos_finales["instrumentos_aplicados"] = instrumentos
            datos_finales["fecha_evaluacion"] = fecha_eval
            datos_finales["diagnostico_nee"] = diagnostico
            datos_finales["fortalezas_pedagogicas"] = fort_ped
            datos_finales["necesidades_pedagogicas"] = nec_ped
            datos_finales["fortalezas_sociales"] = fort_soc
            datos_finales["necesidades_sociales"] = nec_soc
            datos_finales["trabajo_colaborativo"] = trabajo_colab
            datos_finales["apoyos_hogar"] = apoyos_hogar
            datos_finales["acuerdos_compromisos"] = acuerdos
            datos_finales["fechas_evaluacion"] = fechas_avance
        
            # Mapear datos del receptor
            datos_finales["nombre_receptor"] = st.session_state.borrador.get("nombre_receptor", "No especificado")
            datos_finales["rut_receptor"] = st.session_state.borrador.get("rut_receptor", "No especificado")
            datos_finales["nombre_social_receptor"] = st.session_state.borrador.get("nombre_social_receptor", "No especificado")
            datos_finales["telefono_receptor"] = st.session_state.borrador.get("telefono_receptor", "No especificado")
            datos_finales["email_receptor"] = st.session_state.borrador.get("email_receptor", "No especificado")
            datos_finales["relacion_receptor"] = st.session_state.borrador.get("relacion_receptor", "No especificado")
            datos_finales["presencia_receptor"] = st.session_state.borrador.get("presencia_receptor", "No especificado")
        
            # Checkbox de motivo
            if motivo == "Ingreso":
                datos_finales["check_ingreso"] = "☒"
                datos_finales["check_reevaluacion"] = "☐"
            else:
                datos_finales["check_ingreso"] = "☐"
                datos_finales["check_reevaluacion"] = "☒"
            
            # Checkbox de tipo apoderado
            if tipo_apoderado == "Apoderado/a titular":
                datos_finales["check_titular"] = "☒"
                datos_finales["check_suplente"] = "☐"
            else:
                datos_finales["check_titular"] = "☐"
                datos_finales["check_suplente"] = "☒"
            
            # Checkbox de poder simple
            if poder_simple == "Sí":
                datos_finales["check_poder_si"] = "☒"
                datos_finales["check_poder_no"] = "☐"
            elif poder_simple == "No":
                datos_finales["check_poder_si"] = "☐"
                datos_finales["check_poder_no"] = "☒"
            else:
                datos_finales["check_poder_si"] = "☐"
                datos_finales["check_poder_no"] = "☐"
            
            try:
                # Priorizar plantilla con etiquetas (temp) si existe, de lo contrario usar la original
                ruta_plantilla = "planillas/plantilla_informe_temp.docx" if os.path.exists("planillas/plantilla_informe_temp.docx") else "planillas/plantilla_informe.docx"
            
                doc = DocxTemplate(ruta_plantilla)
                doc.render(datos_finales)
            
                os.makedirs("informes_generados", exist_ok=True)
                nombre_alumno_clean = datos_finales["nombre_estudiante"].replace(" ", "_")
                ruta_salida = f"informes_generados/Informe_Generado_{nombre_alumno_clean}.docx"
                doc.save(ruta_salida)
            
                with open(ruta_salida, "rb") as f:
                    byte_data = f.read()
                
                st.session_state.file_ready = {
                    "data": byte_data,
                    "filename": f"Informe_Generado_{nombre_alumno_clean}.docx"
                }
                st.success("¡Informe generado correctamente! Haz clic en el botón de abajo para descargarlo.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al generar el documento Word: {e}")

    if "file_ready" in st.session_state and st.session_state.file_ready:
        st.download_button(
            label="📥 Descargar Informe Word Generado",
            data=st.session_state.file_ready["data"],
            file_name=st.session_state.file_ready["filename"],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )
