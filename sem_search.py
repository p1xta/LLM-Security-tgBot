import os, boto3, tempfile, shutil
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()

s3 = boto3.client('s3', endpoint_url=os.getenv("S3_ENDPOINT"),
                  aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
                  aws_secret_access_key=os.getenv("S3_SECRET_KEY"))

temp_dir = tempfile.mkdtemp()
try:
    all_docs = []
    for obj in s3.list_objects_v2(Bucket=os.getenv("S3_BUCKET"))['Contents']:
        key = obj['Key']
        if key.endswith('/') or not key.lower().endswith(('.pdf', '.txt')):
            continue
            
        local_path = os.path.join(temp_dir, os.path.basename(key))
        s3.download_file(os.getenv("S3_BUCKET"), key, local_path)
        
        loader = PyPDFLoader(local_path) if key.endswith(".pdf") else TextLoader(local_path, encoding="utf-8")
        loaded = loader.load()
        
        valid_docs = [doc for doc in loaded if hasattr(doc, 'page_content') and isinstance(doc.page_content, str) and doc.page_content.strip()]
        all_docs.extend(valid_docs)
    
    chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50, separators=["\n\n", "\n", " ", ""]).split_documents(all_docs)
    
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    FAISS.from_documents(chunks, embeddings).save_local("./vectorstore_faiss")
    print(f"Индекс создан с {len(chunks)} чанками")
    
finally:
    shutil.rmtree(temp_dir)

class SemanticSearchEngine:
    def __init__(self, index_path="./vectorstore_faiss"):
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.index_path = index_path
        self.vectorstore = None
        self.retriever = None
        
    def load_index(self):
        try:
            self.vectorstore = FAISS.load_local(
                self.index_path, 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
            self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
            print("Поисковый индекс загружен")
            return True
        except Exception as e:
            print(f"Ошибка загрузки индекса: {e}")
            return False
    
    def search(self, query):
        if not self.retriever:
            if not self.load_index():
                return "Ошибка: не удалось загрузить поисковый индекс"
        
        try:
            retrieved_docs = self.retriever.invoke(query)
            
            valid_contents = [
                doc.page_content for doc in retrieved_docs 
                if hasattr(doc, 'page_content') and 
                isinstance(doc.page_content, str) and 
                doc.page_content.strip()
            ]
            
            if valid_contents:
                context_chunks = "\n\n".join(valid_contents)
                print(f"RAG: найдено {len(valid_contents)} релевантных фрагментов.")
                return context_chunks
            else:
                print("RAG: релевантные фрагменты не найдены.")
                return "По вашему запросу не найдено информации в документах."
                
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            return "Произошла ошибка при поиске информации."

if __name__ == "__main__":
    search_engine = SemanticSearchEngine()
    if search_engine.load_index():
        test_queries = [
            "Какие требования к доступу?",
            "Как работает система?",
            "Какие есть ограничения?"
        ]
        
        for query in test_queries:
            print(f"\nЗапрос: '{query}'")
            result = search_engine.search(query)
            print(f"Результат: {result[:300]}..." if len(result) > 300 else f"Результат: {result}")
