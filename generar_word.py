from docxtpl import DocxTemplate

# 1. Cargamos tu plantilla
doc = DocxTemplate("plantilla_informe.docx")

# 2. Los datos exactos que pusiste en tus etiquetas {{ }}
# Llenamos con datos de prueba para ver si funciona
datos_de_prueba = {
    "nombre_estudiante": "Florencia Antonia Torres Pérez",
    "nombre_social_estudiante": "Florencia",
    "rut_estudiante": "23.456.789-0",
    "fecha_nacimiento_estudiante": "15/07/2014",
    "edad_estudiante": "10 años",
    "curso_estudiante": "4° Básico A",
    "establecimiento_estudiante": "Liceo Santa Teresita de Llolleo"
}

# 3. Inyectamos los datos
doc.render(datos_de_prueba)

# 4. Guardamos el resultado
nombre_salida = "Informe_Prueba_Generado.docx"
doc.save(nombre_salida)

print(f"¡Listo! Revisa tu carpeta, se acaba de crear el archivo: {nombre_salida}")