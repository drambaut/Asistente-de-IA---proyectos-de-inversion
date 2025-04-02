import os
from typing import List
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
import chromadb
from chromadb.config import Settings

class PDFProcessor:
    def __init__(self, pdf_directory: str = "pdfs"):
        self.pdf_directory = pdf_directory
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        self.client = chromadb.Client(Settings(
            persist_directory="db",
            is_persistent=True
        ))
        self.collection = self.client.create_collection(
            name="pdf_documents",
            metadata={"hnsw:space": "cosine"}
        )

    def process_pdfs(self) -> None:
        """Procesa todos los PDFs en el directorio especificado."""
        if not os.path.exists(self.pdf_directory):
            os.makedirs(self.pdf_directory)
            print(f"Directorio {self.pdf_directory} creado. Por favor, añade tus PDFs.")
            return

        pdf_files = [f for f in os.listdir(self.pdf_directory) if f.endswith('.pdf')]
        
        if not pdf_files:
            print("No se encontraron archivos PDF en el directorio.")
            return

        for pdf_file in pdf_files:
            print(f"Procesando {pdf_file}...")
            self._process_single_pdf(pdf_file)

    def _process_single_pdf(self, pdf_file: str) -> None:
        """Procesa un archivo PDF individual."""
        file_path = os.path.join(self.pdf_directory, pdf_file)
        reader = PdfReader(file_path)
        
        text = ""
        for page in reader.pages:
            text += page.extract_text()

        # Dividir el texto en chunks
        chunks = self.text_splitter.split_text(text)
        
        # Crear embeddings y almacenar en ChromaDB
        embeddings = self.embeddings.embed_documents(chunks)
        
        # Almacenar en la base de datos
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            self.collection.add(
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"source": pdf_file, "chunk": i}],
                ids=[f"{pdf_file}_{i}"]
            )

    def search_similar_chunks(self, query: str, n_results: int = 3) -> List[str]:
        """Busca chunks similares a una consulta."""
        query_embedding = self.embeddings.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        return results['documents'][0] 