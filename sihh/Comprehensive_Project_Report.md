# Comprehensive Project Report: BIS AI Assistant

## 1. Abstract
The Bureau of Indian Standards (BIS) serves as the National Standards Body of India, providing critical guidelines for product quality, consumer safety, and regulatory compliance. However, navigating the vast repository of BIS standards, Quality Control Orders (QCOs), and certification schemes can be challenging for average citizens and businesses due to technical jargon, language barriers, and the sheer volume of documents.

This project introduces the "BIS AI Assistant," an intelligent, multilingual, and voice-enabled conversational AI system. Built using a modern Retrieval-Augmented Generation (RAG) pipeline, the assistant accurately retrieves information exclusively from official BIS documents, ensuring zero hallucinations and high reliability. The system features a responsive React frontend, a high-performance FastAPI backend, a vector database for semantic search, and an integrated real-time data scraper portal to keep the knowledge base up-to-date.

## 2. Introduction
### 2.1 Problem Statement
Citizens and manufacturers require access to Indian Standards (IS), Conformity Assessment Schemes, and Hallmarking regulations. The current process involves manually searching through thousands of PDF documents and web pages. Key challenges include:
- **Information Overload:** Data is scattered across multiple portals.
- **Language Barriers:** Essential documents are often available only in English or complex technical language.
- **Accessibility:** Lack of intuitive search mechanisms for users unfamiliar with standard numbering (e.g., IS 10500 for drinking water).

### 2.2 Proposed Solution
The BIS AI Assistant bridges this gap by acting as a 24/7 intelligent guide. By leveraging Large Language Models (LLMs) and Vector Embeddings, the system understands natural language queries (even if colloquial or misspelled), retrieves the exact official paragraphs, and formulates a precise, easy-to-understand answer with citations.

## 3. System Architecture
The architecture is designed for scalability, low latency, and high accuracy. It follows a decoupled client-server model.

### 3.1 Frontend (User Interface)
- **Framework:** React.js powered by Vite for rapid development and optimized builds.
- **Styling:** Tailwind CSS / Custom CSS for a modern, responsive, and accessible interface.
- **Features:** 
  - Real-time chat interface with markdown rendering.
  - Voice-to-Text and Text-to-Speech integration for accessibility.
  - Multilingual support for various Indian languages.
  - Dedicated "Scraper Portal" for administrators to manage document ingestion.

### 3.2 Backend (API & Business Logic)
- **Framework:** FastAPI (Python) for asynchronous, high-throughput request handling.
- **Database:** PostgreSQL (via Supabase) for robust session management and data persistence.
- **Vector Store:** Supabase `pgvector` for storing and retrieving high-dimensional document embeddings.
- **LLM Orchestration:** Custom RAG pipeline capable of routing requests to OpenRouter (cloud models) or falling back to local Ollama instances.

## 4. Technical Implementation Details
### 4.1 Retrieval-Augmented Generation (RAG) Pipeline
The core of the assistant is the RAG engine, which operates in three phases:
1. **Ingestion & Chunking:** Official BIS PDFs and HTML pages are parsed using `PyMuPDF` and `BeautifulSoup`. The text is split into chunks of 1000 characters using `RecursiveCharacterTextSplitter` with an overlap of 250 characters to preserve context.
2. **Embedding:** Each chunk is passed through an Embedding Model (e.g., OpenAI `text-embedding-3-small` or HuggingFace models) to convert semantic meaning into mathematical vectors (dimension 1536). These vectors are stored in Supabase using the `pgvector` extension.
3. **Retrieval & Generation:** When a user asks a question, the query is converted into a vector. The system performs a cosine similarity search in Supabase to find the top 5 most relevant document chunks. These chunks are appended to the system prompt, forcing the LLM to generate answers *only* using the provided context.

### 4.2 Query Normalization & Intent Recognition
Before searching the vector database, the system intercepts the user's query and performs intent normalization. For example:
- If a user asks about "water," the system expands the search terms to include "IS 10500, IS 14543, packaged drinking water, guidelines."
- If a user asks about "gold," it expands to "hallmarking, HUID, AHC, mandatory hallmarking order."
This drastically improves retrieval accuracy for non-technical users.

### 4.3 Web Scraping and Auto-Updating
The system includes `mega_scraper.py` and `bis_scraper.py`, which are asynchronous web crawlers designed specifically for the BIS portal. 
- They monitor the "What's New" sections, circulars, and product manuals.
- When new guidelines are published, the scraper automatically downloads the PDF, extracts the text, generates embeddings, and inserts them into the Supabase database.
- Administrators can trigger this process manually via the React Frontend Scraper Portal.

### 4.4 Multi-Tier LLM Fallback Mechanism
To ensure the system never goes down during high traffic or API outages, it implements a multi-tier fallback:
1. **Primary:** Custom API endpoints (if provided).
2. **Secondary:** OpenRouter API utilizing fast, highly capable models like `google/gemma-4-31b-it`.
3. **Tertiary:** Local `Ollama` instance running `llama3.2-vision` or similar local models to guarantee absolute privacy and offline capabilities.

## 5. Security & Deployment (Vercel + Supabase)
The application has been architected to be completely serverless and cloud-native:
- **Vercel:** Hosts the Vite frontend as static assets and runs the FastAPI backend as Serverless Functions via the `api/index.py` entrypoint.
- **Supabase:** Replaces local SQLite and ChromaDB, providing enterprise-grade PostgreSQL with connection pooling. The `match_documents` RPC function ensures vector searches are computed directly on the database server, minimizing latency.
- **CORS & Environment:** Strict CORS policies ensure only authorized frontend domains can access the FastAPI backend. Sensitive keys (OpenAI, Supabase) are securely injected via environment variables.

## 6. Future Scope
1. **WhatsApp Bot Integration:** Extending the AI assistant to WhatsApp via the Twilio or Meta Graph API to reach citizens who do not use web browsers.
2. **Image Recognition:** Allowing users to upload pictures of ISI marks or HUID codes to instantly verify authenticity using Vision LLMs.
3. **Automated Form Filling:** Assisting manufacturers in filling out complex FMCS (Foreign Manufacturers Certification Scheme) forms dynamically through a conversational interface.

## 7. Conclusion
The BIS AI Assistant successfully demonstrates how modern Generative AI and RAG architectures can be utilized to democratize access to national standards. By transforming static, difficult-to-read PDFs into an interactive, multilingual, and voice-enabled conversational agent, this project significantly enhances the accessibility of the Bureau of Indian Standards for all citizens.
