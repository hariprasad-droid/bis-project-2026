from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 16)
        self.set_text_color(44, 62, 80)
        self.cell(0, 10, "BIS AI Assistant - Project Explanation & YouTube Script", 0, 1, "C") # type: ignore
        self.ln(5)

    def chapter_title(self, title):
        self.set_font("helvetica", "B", 14)
        self.set_text_color(41, 128, 185)
        self.cell(0, 10, title, 0, 1, "L") # type: ignore
        self.ln(2)

    def visual_cue(self, text):
        self.set_font("helvetica", "B", 11)
        self.set_text_color(52, 152, 219)
        self.multi_cell(0, 8, text)
        self.ln(2)

    def script_text(self, text):
        self.set_font("helvetica", "I", 12)
        self.set_text_color(51, 51, 51)
        self.multi_cell(0, 8, text)
        self.ln(5)

pdf = PDF()
pdf.add_page()

# Section 1
pdf.chapter_title("1. Hook & Introduction (0:00 - 0:45)")
pdf.visual_cue("Visual: Screen recording of the BIS AI Assistant interface, showing a user asking a question in Hindi and getting a precise answer.")
pdf.script_text('"Have you ever tried navigating complex government standards or finding specific information on the Bureau of Indian Standards (BIS) website? It can be overwhelming. Today, I\'m excited to present our solution: The BIS AI Assistant. It\'s an intelligent, multilingual, and voice-enabled conversational AI designed specifically to make BIS services and Indian Standards instantly accessible to everyone."')

# Section 2
pdf.chapter_title("2. The Problem It Solves (0:45 - 1:30)")
pdf.visual_cue("Visual: Graphics showing scattered PDF documents, a complicated website, and people speaking different languages.")
pdf.script_text('"The Bureau of Indian Standards offers a wealth of crucial information, but citizens often face three major hurdles:\n1. Information Overload: Data is scattered across thousands of PDFs and web pages.\n2. Language Barriers: Essential standards are often only available in English or technical jargon.\n3. Accessibility: Not everyone is comfortable typing complex queries.\nOur AI Assistant bridges this gap by acting as a 24/7 knowledgeable guide."')

# Section 3
pdf.chapter_title("3. Key Features (1:30 - 3:00)")
pdf.visual_cue("Visual: Quick montage of the UI features as they are mentioned.")
pdf.script_text('"Let\'s look at what makes this assistant powerful:\n- Retrieval-Augmented Generation (RAG): It doesn\'t just guess; it fetches exact paragraphs from official BIS documents before answering, eliminating hallucinations.\n- Multilingual Support & Voice: Users can speak their questions in multiple Indian languages, and the AI will reply back with text and voice.\n- Built-in Text Simplifier: A dedicated tool to convert formal, complex jargon into simple, everyday language.\n- Live Data Scraper Portal: An admin interface that can scrape new updates directly from the BIS website and integrate them into the AI\'s brain in real-time."')

# Section 4
pdf.chapter_title("4. Architecture & Tech Stack (3:00 - 4:15)")
pdf.visual_cue("Visual: A clean architecture diagram showing Frontend -> Backend -> Vector DB & LLM.")
pdf.script_text('"Under the hood, we\'ve built a robust and scalable architecture:\n- Frontend: Built with React and Vite, utilizing Tailwind/CSS for a responsive, modern UI.\n- Backend: Powered by FastAPI in Python, ensuring high performance.\n- Vector Database: We use ChromaDB to store document embeddings securely.\n- AI Engine: We utilize Sentence Transformers for embeddings and dynamically switch between OpenRouter models and a local Ollama instance for text generation, ensuring high availability and privacy."')

# Section 5
pdf.chapter_title("5. How It Works (The RAG Pipeline) (4:15 - 5:30)")
pdf.visual_cue("Visual: Animation of a document being chunked, converted to embeddings, and then retrieved when a user asks a question.")
pdf.script_text('"How does it actually know the answers?\n1. Ingestion: We extract text from BIS PDFs and HTML pages, chunk them into smaller pieces, and convert them into mathematical vectors (embeddings).\n2. Retrieval: When a user asks a question, the system converts the query into a vector and finds the most relevant document chunks in ChromaDB.\n3. Generation: The retrieved context, along with the user\'s question, is sent to the LLM (Large Language Model) to generate a highly accurate, context-aware answer."')

# Section 6
pdf.chapter_title("6. Live Demo (5:30 - 7:00)")
pdf.visual_cue("Visual: Live walkthrough of the application.")
pdf.script_text('"Let\'s see it in action.\n[Action: Type \'What are the standards for drinking water?\']\nNotice how it provides a precise answer and cites the source document.\n[Action: Use the microphone to ask a question in Hindi]\nThe AI understands the language, translates the intent, retrieves the context, and responds back perfectly.\n[Action: Open the Scraper Portal]\nAnd here is the Scraper Portal, where admins can fetch the latest notifications from the BIS website with a single click, keeping the AI\'s knowledge completely up-to-date."')

# Section 7
pdf.chapter_title("7. Conclusion & Future Scope (7:00 - 7:45)")
pdf.visual_cue("Visual: Final slide with contact info or GitHub repository link.")
pdf.script_text('"The BIS AI Assistant is more than just a chatbot; it\'s a step towards democratizing access to national standards and regulations. In the future, we plan to integrate WhatsApp support and real-time document parsing.\nThank you for watching! Check out the GitHub link in the description to explore the code."')

output_path = r"c:\bis\sihh\YouTube_Video_Script.pdf"
pdf.output(output_path)
print(f"PDF successfully generated at: {output_path}")
