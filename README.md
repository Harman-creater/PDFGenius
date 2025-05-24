# PDFGenius💡 – AI-Powered Academic Assistant

PDFGenius is a web-based academic assistant that allows users to upload PDF documents and interact with them through natural language questions. The system provides intelligent answers, summarizations, and voice-based responses. It is built using modern NLP technologies including LangChain, Hugging Face Transformers, and FAISS, with a user-friendly interface powered by Streamlit and secure authentication managed through Flask.

## Features

- User authentication system (sign up, login, password reset via email)
- Upload and manage multiple academic PDFs (max 3, up to 5MB each)
- Context-aware question answering using Hugging Face `flan-t5-base`
- Semantic search and retrieval powered by FAISS vector store
- Text-to-speech responses using gTTS
- Chat interface with conversation history

## Project Structure

.
├── app.txt                 # Streamlit frontend
├── auth.txt                # Flask backend for auth
├── ingest.txt              # Embeds PDFs and stores vectors in FAISS
├── utils.txt               # Utility functions (QA chain, summarizer)
├── requirements.txt        # Python dependencies
├── dataset/                # Uploaded PDFs
├── vectorstore/            # FAISS index storage
├── auth.db                 # SQLite DB for user data

## Usage Instructions  

- Run the Flast Auth Server `python auth.py`
- Run the Streamlit App `streamlit run app.py`
