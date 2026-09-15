# AI-Powered Conversational Assistant for Indian Standards (BIS)

This project is a Retrieval-Augmented Generation (RAG) based web application to answer user queries related to Indian Standards and BIS services, using only freely available BIS content. 

## Structure
- `backend/`: FastAPI application, ingestion pipeline, RAG engine, SQLite database.
- `frontend/`: React application for the chat interface.

## Setup Instructions

### 1. Environment Variables
Copy `.env.example` to `.env` and fill in the required keys (`OLLAMA_API_KEY`):
```bash
cp .env.example .env
```

### 2. Backend
Create a virtual environment and install dependencies:
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # On Windows
pip install -r requirements.txt
```

#### Running the Ingestion Pipeline
Place your raw PDF/HTML documents in `backend/data/raw/`. Then run:
```bash
python ingest.py
```
This will extract text, chunk it, generate embeddings, and store them in ChromaDB (`backend/vectorstore/`).

#### Starting the FastAPI Server
```bash
uvicorn main:app --reload
```

### 3. Frontend
Navigate to the frontend directory, install dependencies, and start the development server:
```bash
cd frontend
npm install
npm run dev
```
