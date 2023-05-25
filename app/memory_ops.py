#!/usr/bin/env python3

import os
import glob
from typing import List
from dotenv import load_dotenv
from multiprocessing import Pool
from tqdm import tqdm

from langchain.document_loaders import (
    SitemapLoader,
)
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings,HuggingFaceEmbeddings
from langchain.docstore.document import Document
from app.env import (
    EMBEDDINGS_MODEL_NAME,
    MEMORY_DIR,
    BASE_PATH,
    OPENAI_MODEL,
)

from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from chromadb.config import Settings


# Define the folder for storing database
PERSIST_DIRECTORY = os.path.join(MEMORY_DIR, "chromadb")

# Define the Chroma settings
CHROMA_SETTINGS = Settings(
        chroma_db_impl='duckdb+parquet',
        persist_directory=PERSIST_DIRECTORY,
        anonymized_telemetry=False
)

def append_line_to_file(line, folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
    else:
        print("dir already exists")
    # Get current date in YYYY-MM-DD format
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    # Create file if it doesn't exist
    file_path = os.path.join(folder_path, f'{date_str}.txt')
    if not os.path.exists(file_path):
        with open(file_path, 'w'):
            pass
    
    # Append line to file
    with open(file_path, 'a') as f:
        f.write(line + '\n')

def ask_with_memory(line) -> str:
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL_NAME)
    
    #embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

    db = Chroma(persist_directory=PERSIST_DIRECTORY, embedding_function=embeddings, client_settings=CHROMA_SETTINGS)
    retriever = db.as_retriever()

    res = ""
    llm = ChatOpenAI(temperature=0, openai_api_base=BASE_PATH, model_name=OPENAI_MODEL)
    qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, return_source_documents=True)

    # Get the answer from the chain
    res = qa(line)
    answer, docs = res['result'], res['source_documents']
    res = answer
    res = "**Sources**\n"
    # Print the relevant sources used for the answer
    for document in docs:
        res = res + "\n" + document.metadata["source"] + " : "
        res = res + document.page_content
    
    return res

def build_knowledgebase(sitemap):
    # Load environment variables
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL_NAME)
    #embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
    chunk_size = 500 # 500
    chunk_overlap = 50
    sitemap_loader = SitemapLoader(web_path=sitemap)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    texts = text_splitter.split_documents(sitemap_loader.load())
    print(f"Creating embeddings. May take some minutes...")
    db = Chroma.from_documents(texts, embeddings, persist_directory=PERSIST_DIRECTORY, client_settings=CHROMA_SETTINGS)
    db.persist()
    db = None

def update_memory(line):
    append_line_to_file(line, os.path.join(MEMORY_DIR, "dataset"))

    # # This example uses text-davinci-003 by default; feel free to change if desired
    # llm_predictor = LLMPredictor(llm=OpenAI(temperature=0, model_name="gpt-3.5-turbo", openai_api_base=BASE_PATH))

    # # Configure prompt parameters and initialise helper
    # max_input_size = 200
    # num_output = 256
    # max_chunk_overlap = 30
    # d = Document(line)
    # documents = [d]

    # persist_dir = os.path.join(MEMORY_DIR, "memory")
    # prompt_helper = PromptHelper(max_input_size, num_output, max_chunk_overlap)

    # # Load documents from the 'data' directory
    # service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor, prompt_helper=prompt_helper)
    # docstore = os.path.join(persist_dir, "/docstore.json")

    # if not os.path.exists(docstore):
    #     os.makedirs(persist_dir, exist_ok=True)
    #     index = GPTVectorStoreIndex.from_documents( documents, service_context=service_context)
    #     index.storage_context.persist(persist_dir=persist_dir)
    #     return
    # else:
    #     print("docstore already exists")
    # # rebuild storage context
    # storage_context = StorageContext.from_defaults(persist_dir=persist_dir)

    # # store to index
    # index = load_index_from_storage(storage_context,     service_context=service_context,    )
    # index.insert(d)
    # index.storage_context.persist(persist_dir=persist_dir)
