from langchain_ollama import OllamaLLM

# Conectamos Python con el modelo que descargaste (asegúrate de poner el nombre exacto)
# Si bajaste phi3 o gemma:2b, cámbialo aquí.
modelo = OllamaLLM(model="llama3.2") 

print("Pensando...")

# Le mandamos una instrucción directa
respuesta = modelo.invoke("Hola, actúa como un experto en educación especial en Chile y preséntate en un párrafo corto.")

print("\nRespuesta del modelo:")
print(respuesta)