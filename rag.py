from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaLLM, OllamaEmbeddings

print("1. Extrayendo la información del Word...")
# Cargamos el documento Word
loader = Docx2txtLoader("Informe a la Familia ministerial 2025.docx")
documentos = loader.load()

print("2. Transformando el texto (creando fragmentos)...")
# Cortamos el texto en pedazos de 500 caracteres para no saturar la memoria
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
fragmentos = text_splitter.split_documents(documentos)

print("3. Cargando a la Base de Datos Vectorial (ChromaDB)...")
# Convertimos el texto a matemática usando el modelo ligero que acabas de descargar
embeddings = OllamaEmbeddings(model="nomic-embed-text")
vectorstore = Chroma.from_documents(documents=fragmentos, embedding=embeddings)

print("4. Buscando la información relevante...")
# Aquí pones lo que quieres saber del documento
pregunta = "¿De qué trata este documento y cuáles son los puntos clave?"

# La base de datos busca los fragmentos que más se parecen a tu pregunta
resultados = vectorstore.similarity_search(pregunta, k=2) 
contexto = resultados[0].page_content + "\n" + resultados[1].page_content

print("5. Generando la respuesta final con Llama 3.2...\n")
# Instanciamos el cerebro principal
llm = OllamaLLM(model="llama3.2")

# Le inyectamos tu PDF directamente en las instrucciones
prompt = f"""Basándote EXCLUSIVAMENTE en esta información oficial: 
{contexto}

Por favor, responde a esta pregunta: {pregunta}"""

respuesta = llm.invoke(prompt)

print("--- RESPUESTA DE LA IA ---")
print(respuesta)