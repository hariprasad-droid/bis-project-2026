from fpdf import FPDF
import os

class PDFReport(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 10)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, "BIS AI Assistant - Comprehensive Project Report", 0, 1, "R")

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

    def add_title_page(self):
        self.add_page()
        self.set_y(100)
        self.set_font("helvetica", "B", 24)
        self.set_text_color(0, 0, 0)
        self.cell(0, 20, "PROJECT REPORT", 0, 1, "C")
        self.set_font("helvetica", "B", 18)
        self.cell(0, 15, "BIS AI Assistant", 0, 1, "C")
        self.set_font("helvetica", "I", 14)
        self.cell(0, 15, "An Intelligent Conversational AI for the Bureau of Indian Standards", 0, 1, "C")
        self.add_page()

    def chapter_title(self, num, title):
        self.set_font("helvetica", "B", 16)
        self.set_text_color(41, 128, 185)
        self.cell(0, 10, f"{num}. {title}", 0, 1, "L")
        self.ln(4)

    def sub_chapter_title(self, title):
        self.set_font("helvetica", "B", 13)
        self.set_text_color(44, 62, 80)
        self.cell(0, 8, title, 0, 1, "L")
        self.ln(2)

    def body_text(self, text):
        self.set_font("helvetica", "", 11)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 6, text)
        self.ln(4)
        
    def bullet_point(self, text):
        self.set_font("helvetica", "", 11)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 6, f"  -  {text}")
        self.ln(2)

pdf = PDFReport()
pdf.add_title_page()

# Abstract
pdf.chapter_title(1, "Abstract")
pdf.body_text("The Bureau of Indian Standards (BIS) serves as the National Standards Body of India, providing critical guidelines for product quality, consumer safety, and regulatory compliance. However, navigating the vast repository of BIS standards, Quality Control Orders (QCOs), and certification schemes can be challenging for average citizens and businesses due to technical jargon, language barriers, and the sheer volume of documents.")
pdf.body_text("This project introduces the 'BIS AI Assistant,' an intelligent, multilingual, and voice-enabled conversational AI system. Built using a modern Retrieval-Augmented Generation (RAG) pipeline, the assistant accurately retrieves information exclusively from official BIS documents, ensuring zero hallucinations and high reliability. The system features a responsive React frontend, a high-performance FastAPI backend, a vector database for semantic search, and an integrated real-time data scraper portal to keep the knowledge base up-to-date.")

# Introduction
pdf.chapter_title(2, "Introduction")
pdf.sub_chapter_title("2.1 Problem Statement")
pdf.body_text("Citizens and manufacturers require access to Indian Standards (IS), Conformity Assessment Schemes, and Hallmarking regulations. The current process involves manually searching through thousands of PDF documents and web pages. Key challenges include:")
pdf.bullet_point("Information Overload: Data is scattered across multiple portals.")
pdf.bullet_point("Language Barriers: Essential documents are often available only in English or complex technical language.")
pdf.bullet_point("Accessibility: Lack of intuitive search mechanisms for users unfamiliar with standard numbering.")

pdf.sub_chapter_title("2.2 Proposed Solution")
pdf.body_text("The BIS AI Assistant bridges this gap by acting as a 24/7 intelligent guide. By leveraging Large Language Models (LLMs) and Vector Embeddings, the system understands natural language queries (even if colloquial or misspelled), retrieves the exact official paragraphs, and formulates a precise, easy-to-understand answer with citations.")

# System Architecture
pdf.chapter_title(3, "System Architecture")
pdf.body_text("The architecture is designed for scalability, low latency, and high accuracy. It follows a decoupled client-server model.")
pdf.sub_chapter_title("3.1 Frontend (User Interface)")
pdf.bullet_point("Framework: React.js powered by Vite for rapid development and optimized builds.")
pdf.bullet_point("Styling: Tailwind CSS / Custom CSS for a modern, responsive, and accessible interface.")
pdf.bullet_point("Features: Real-time chat interface with markdown rendering, Voice-to-Text and Text-to-Speech integration, Multilingual support, and a dedicated Scraper Portal for administrators.")

pdf.sub_chapter_title("3.2 Backend (API & Business Logic)")
pdf.bullet_point("Framework: FastAPI (Python) for asynchronous, high-throughput request handling.")
pdf.bullet_point("Database: PostgreSQL (via Supabase) for robust session management and data persistence.")
pdf.bullet_point("Vector Store: Supabase pgvector for storing and retrieving high-dimensional document embeddings.")
pdf.bullet_point("LLM Orchestration: Custom RAG pipeline capable of routing requests to OpenRouter or falling back to local Ollama instances.")

# Implementation
pdf.chapter_title(4, "Technical Implementation Details")
pdf.sub_chapter_title("4.1 Retrieval-Augmented Generation (RAG) Pipeline")
pdf.body_text("The core of the assistant is the RAG engine, which operates in three phases:")
pdf.bullet_point("Ingestion & Chunking: Official BIS PDFs and HTML pages are parsed using PyMuPDF and BeautifulSoup. The text is split into chunks of 1000 characters using RecursiveCharacterTextSplitter.")
pdf.bullet_point("Embedding: Each chunk is passed through an Embedding Model (e.g., OpenAI text-embedding-3-small) to convert semantic meaning into mathematical vectors. These vectors are stored in Supabase.")
pdf.bullet_point("Retrieval & Generation: When a user asks a question, the query is converted into a vector. The system performs a cosine similarity search to find the top 5 most relevant document chunks. These chunks are appended to the system prompt, forcing the LLM to generate answers *only* using the provided context.")

pdf.sub_chapter_title("4.2 Query Normalization & Intent Recognition")
pdf.body_text("Before searching the vector database, the system intercepts the user's query and performs intent normalization. For example, if a user asks about 'water,' the system expands the search terms to include 'IS 10500, IS 14543, packaged drinking water.' This drastically improves retrieval accuracy for non-technical users.")

pdf.sub_chapter_title("4.3 Multi-Tier LLM Fallback Mechanism")
pdf.body_text("To ensure the system never goes down during high traffic or API outages, it implements a multi-tier fallback:")
pdf.bullet_point("Primary: Custom API endpoints.")
pdf.bullet_point("Secondary: OpenRouter API utilizing highly capable models like google/gemma-4-31b-it.")
pdf.bullet_point("Tertiary: Local Ollama instances running local models to guarantee privacy.")

# Security & Deployment
pdf.chapter_title(5, "Security & Deployment")
pdf.body_text("The application has been architected to be completely serverless and cloud-native:")
pdf.bullet_point("Vercel: Hosts the Vite frontend as static assets and runs the FastAPI backend as Serverless Functions via the api/index.py entrypoint.")
pdf.bullet_point("Supabase: Replaces local SQLite and ChromaDB, providing enterprise-grade PostgreSQL. The match_documents RPC function ensures vector searches are computed directly on the database server.")

# Future Scope & Conclusion
pdf.chapter_title(6, "Future Scope")
pdf.bullet_point("WhatsApp Bot Integration: Extending the AI assistant to WhatsApp via the Meta Graph API to reach citizens who do not use web browsers.")
pdf.bullet_point("Image Recognition: Allowing users to upload pictures of ISI marks or HUID codes to instantly verify authenticity using Vision LLMs.")

pdf.chapter_title(7, "Conclusion")
pdf.body_text("The BIS AI Assistant successfully demonstrates how modern Generative AI and RAG architectures can be utilized to democratize access to national standards. By transforming static, difficult-to-read PDFs into an interactive, multilingual, and voice-enabled conversational agent, this project significantly enhances the accessibility of the Bureau of Indian Standards for all citizens.")

output_path = r"c:\bis\sihh\Comprehensive_Project_Report.pdf"
pdf.output(output_path)
print(f"PDF successfully generated at: {output_path}")
