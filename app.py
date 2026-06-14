import streamlit as st

st.set_page_config(
    page_title="Asistente PIE",
    page_icon="📝",
    layout="centered"
)

st.title("📝 Asistente de Documentos PIE")
st.write("Selecciona el tipo de documento que deseas generar desde el menú lateral.")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 📋 Informe a la Familia
    Informe ministerial 2025 según Decreto N° 170/2010.
    Recopila datos del estudiante, profesional y apoderado
    a través del chat para generar el documento oficial.
    """)
    if st.button("Ir a Informe a la Familia →", use_container_width=True):
        st.switch_page("pages/1_Informe_Familia.py")

with col2:
    st.markdown("""
    ### 🧠 Evaluación Psicopedagógica
    Informe de Evaluación Psicopedagógica 2026.
    Incluye análisis cualitativo por áreas cognitiva,
    socioemocional y motora, síntesis y sugerencias.
    """)
    if st.button("Ir a Evaluación Psicopedagógica →", use_container_width=True):
        st.switch_page("pages/2_Evaluacion_Psicopedagogica.py")

st.markdown("---")
st.caption("Sistema de generación de documentos PIE — Modelo: LLaMA 3.1")
