import re
from langchain.llms import OpenAI, OpenAIChat
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Milvus
from langchain.document_loaders import TextLoader
from langchain.chains import ConversationalRetrievalChain
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.document_loaders import UnstructuredExcelLoader
from langchain.document_loaders import UnstructuredWordDocumentLoader
from langchain.document_loaders import UnstructuredPowerPointLoader
from langchain.document_loaders import UnstructuredEPubLoader
from langchain.document_loaders.image import UnstructuredImageLoader
from langchain.document_loaders import AsyncHtmlLoader
from langchain.document_loaders import YoutubeLoader

from app.utils.utils import replace_hyphens_with_underscores


def get_loader(filepath, extention):
        if extention == '.csv':
                return CSVLoader(file_path=filepath)
        if extention == '.pdf':
                return TextLoader(file_path=filepath)
        if extention == '.xls':
                return UnstructuredExcelLoader(file_path=filepath)
        if extention == '.xlsx':
                return UnstructuredExcelLoader(file_path=filepath)
        if extention == '.docx':
                return UnstructuredWordDocumentLoader(file_path=filepath)
        if extention == '.ppt':
                return UnstructuredPowerPointLoader(file_path=filepath)
        if extention == '.pptx':
                return UnstructuredPowerPointLoader(file_path=filepath)
        if extention == '.epub':
                return UnstructuredEPubLoader(file_path=filepath)
        if extention == '.jpg':
                return UnstructuredImageLoader(file_path=filepath)
        if extention == '.jpeg':
                return UnstructuredImageLoader(file_path=filepath)
        if extention == '.png':
                return UnstructuredImageLoader(file_path=filepath)
        if extention == '.txt':
                return TextLoader(file_path=filepath)
        if extention == '.md':
                return TextLoader(file_path=filepath)  # Markdown files use TextLoader
        if extention == '.html':
                return AsyncHtmlLoader([filepath])
        if extention == '.youtube':
                return YoutubeLoader.from_youtube_url(filepath, add_video_info=True)
        # Default to TextLoader for unknown extensions
        return TextLoader(file_path=filepath)


def ingest_file_to_vector_db(filepath, uuid_filename, extention):
        print(f'[RAG-DEBUG] ===== FILE INGESTION START =====')
        print(f'[RAG-DEBUG] Filepath: {filepath}')
        print(f'[RAG-DEBUG] UUID filename (assistant_id): {uuid_filename}')
        print(f'[RAG-DEBUG] Extension: {extention}')
        
        try:
            print(f'[RAG-DEBUG] Getting loader for extension: {extention}')
            loader = get_loader(filepath=filepath, extention=extention)
            print(f'[RAG-DEBUG] Loader obtained: {type(loader).__name__}')
            
            print(f'[RAG-DEBUG] Loading documents...')
            documents = loader.load()
            print(f'[RAG-DEBUG] Loaded {len(documents)} document(s)')
            
            print(f'[RAG-DEBUG] Splitting documents into chunks...')
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
            docs = text_splitter.split_documents(documents)
            print(f'[RAG-DEBUG] Split into {len(docs)} chunk(s)')
            for i, doc in enumerate(docs[:3]):  # Show first 3 chunks
                print(f'[RAG-DEBUG]   Chunk {i+1}: {len(doc.page_content)} chars')
            
            print(f'[RAG-DEBUG] Initializing embeddings...')
            embeddings = OpenAIEmbeddings()
            print(f'[RAG-DEBUG] Embeddings initialized')
            
            collection_name = replace_hyphens_with_underscores(uuid_filename)
            print(f'[RAG-DEBUG] Collection name: {collection_name}')
            print(f'[RAG-DEBUG] Original UUID: {uuid_filename}')
            print(f'[RAG-DEBUG] Connecting to Milvus at 127.0.0.1:19530...')
            
            print(f'[RAG-DEBUG] Ingesting documents into Milvus...')
            Milvus.from_documents(
                    docs,
                    embeddings,
                    collection_name=collection_name,
                    connection_args={"host": "127.0.0.1", "port": "19530"}
            )
            print(f'[RAG-DEBUG] ✓ Successfully ingested into collection: {collection_name}')
            print(f'[RAG-DEBUG] ===== FILE INGESTION SUCCESS =====')
            return collection_name
        except Exception as e:
            print(f'[RAG-DEBUG] ✗ ERROR during ingestion: {e}')
            import traceback
            traceback.print_exc()
            print(f'[RAG-DEBUG] ===== FILE INGESTION FAILED =====')
            raise


def make_chain(vector_store):
        api = OpenAIChat(model='gpt-3.5-turbo')
        print(f'Here is in chain 1')
        chain = ConversationalRetrievalChain.from_llm(
                llm=api,
                retriever=vector_store.as_retriever(),
                verbose=True
        )
        print(f'Here is in chain 2 {chain}')
        return chain


async def chat_with_doc(uuid, question, history):
        print(f'chat_with_doc uuid {uuid}')
        print(f'chat_with_doc question {question}')
        vector_db_collection_name = replace_hyphens_with_underscores(uuid)
        print(f'chat_with_doc vector_db_collection_name {vector_db_collection_name}')
        # Sanitize the question
        sanitized_question = re.sub(r'\n', ' ', question.strip())
        print(f'chat_with_doc sanitized_question {sanitized_question}')
        # Initialize Milvus vector store
        vector_store = Milvus(embedding_function=OpenAIEmbeddings(), collection_name=vector_db_collection_name)
        # vector_store = Milvus._load(collection_name=collection_name)
        chain = make_chain(vector_store)
        print(f'Make chain Done {chain}')
        response = await chain.acall({
                'question': sanitized_question,
                'chat_history': "",
        })
        print(f'response from chat_with_doc {response}')
        return response
