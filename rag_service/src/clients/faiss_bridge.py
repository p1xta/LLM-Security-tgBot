from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from pathlib import Path

from log.logger import logger


class FAISSbridge:
    def __init__(self, store_filepath: str = "./vectorstore_faiss"):
        self.embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vector_search_init(store_filepath)
        
    def store_doc_vectors(self, docs):
        chunks = self.docs_to_chunks(docs)
        self.vectorstore = FAISS.from_documents(chunks, self.embedder)
        self.vectorstore.save_local(self.store_filepath)
        self.vector_search_init(self.store_filepath)
        
    def vector_search_init(self, store_filepath, top_k: int = 3):
        self.store_filepath = store_filepath
        if Path(store_filepath).exists:
            self.vectorstore = FAISS.load_local(store_filepath, self.embedder, allow_dangerous_deserialization=True)
            self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": top_k})
        else:
            self.vectorstore = None
        
    def find_relevant_data(self, user_input: str):
        retrieved_docs = self.retriever.invoke(user_input)
        logger.info(f"Найдено {len(retrieved_docs)} подходящих докуметов.")
        return retrieved_docs

    @staticmethod
    def docs_to_chunks(docs):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = text_splitter.split_documents(docs)
        logger.info(f"FAISS нашел {len(chunks)} подходящих чанков.")
        return chunks
    
    