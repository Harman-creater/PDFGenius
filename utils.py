import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from transformers import AutoModelForSeq2SeqLM
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.llms import HuggingFacePipeline
import streamlit as st

import time
import os

# Path to FAISS index
FAISS_INDEX = "vectorstore/"


@st.cache_resource
def create_qa_pipeline():
    """
    Create the Question-Answering pipeline with a free Hugging Face model.
    """
    start_time = time.time()

    if not os.path.exists("vectorstore/index.faiss"):
        raise FileNotFoundError("Vectorstore not found. Please process documents first!")

    # Initialize embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # Load the existing FAISS vector store
    db = FAISS.load_local(
        FAISS_INDEX, 
        embeddings, 
        allow_dangerous_deserialization=True
    )

    # Custom Prompt Template
    custom_prompt = PromptTemplate(
        template="""
        \nAnswer:
        {context}
        """,
        input_variables=["context", "question"]
    )

    # Load a small Hugging Face model
    model_name = "google/flan-t5-base"

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    # Create a Hugging Face pipeline
    pipe = pipeline(
        # "text-generation",
        "text2text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=150,
        device=-1,
        temperature = 0.3,
        do_sample = True
    )

    # Convert the pipeline to a LangChain LLM
    llm = HuggingFacePipeline(pipeline=pipe)

    # Create a Retrieval QA Chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",  # Specify the chain type
        retriever=db.as_retriever(search_kwargs={"k": 3}),  # Adjust 'k' for relevance
        chain_type_kwargs={"prompt": custom_prompt},
        return_source_documents=True  # Include source documents in the response
    )
    elapsed = time.time() - start_time
    print(f"utils.py : QA pipeline loaded in {elapsed:.2f} seconds")

    return qa_chain

@st.cache_resource(show_spinner="Almost ready for you...")
def get_summarizer():
    return pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")