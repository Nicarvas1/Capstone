class ConversationSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.etapa = 1
        self.mensajes = []
        self.datos_estudiante = {}
        self.datos_profesional = {}
        self.borrador = {
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
            "poder_simple": "No Aplica",
        }
        self.decision_ia = None  # None | "esperando" | "solicitando_info" | "completado"
        self.word_filename = None
