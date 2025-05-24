import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import streamlit as st

# Dataset and Index Paths
DATASET = "dataset/"
FAISS_INDEX = "vectorstore/"

def embed_documents():
    """
    Embed all PDF documents in the dataset directory
    """
    # Ensure the index directory exists
    os.makedirs(FAISS_INDEX, exist_ok=True)

    # Create the document loader
    loader = DirectoryLoader(DATASET, glob="*.pdf", loader_cls=PyPDFLoader)

    # Load the documents
    documents = loader.load()

    # Check if any documents were loaded
    if not documents:
        # print(f"No documents found in {DATASET}. Please check your PDF files.")
        st.error(f"No documents found in '{DATASET}'. Please upload PDFs first.")
        return

    # Create the text splitter
    # splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)


    # Split the documents into chunks
    chunks = splitter.split_documents(documents)

    # Initialize Hugging Face Embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # Create the vector store
    vector_store = FAISS.from_documents(chunks, embeddings)

    # Save the vector store
    vector_store.save_local(FAISS_INDEX)

    print(f"Embedded {len(chunks)} chunks from {len(documents)} documents")

if __name__ == "__main__":
    embed_documents()