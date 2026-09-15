from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid
import subprocess
import os
import re
import urllib.parse
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

import models
from database import engine, get_db
from rag_engine import generate_answer, get_vectorstore_stats

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="BIS AI Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def translate_text(text: str, source_lang: str = "auto", target_lang: str = "en") -> str:
    if source_lang == target_lang or not text:
        return text
    if GoogleTranslator is None:
        return text
    try:
        return GoogleTranslator(source=source_lang, target=target_lang).translate(text)
    except Exception as e:
        print(f"Translation error ({source_lang}->{target_lang}): {e}")
        return text

class ChatRequest(BaseModel):
    message: str
    language: str = "en"
    session_id: Optional[str] = None

class FeedbackRequest(BaseModel):
    message_id: int
    is_positive: bool
    comment: Optional[str] = None

class SimplifyTextRequest(BaseModel):
    text: str
    language: str = "en"

@app.post("/simplify")
async def simplify_text_endpoint(req: SimplifyTextRequest):
    """
    Takes improper/informal/raw text input, understands intent, 
    and returns a simplified, proper, clean version.
    """
    raw_text = req.text
    if not raw_text or not raw_text.strip():
        return {"original": raw_text, "proper_text": ""}
        
    # Standard cleanup & translation if needed
    clean_text = raw_text.strip()
    return {
        "original": raw_text,
        "proper_text": clean_text,
        "status": "processed"
    }

@app.post("/chat")
async def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    session_id = req.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        db_session = models.Session(id=session_id)
        db.add(db_session)
        db.commit()
    else:
        db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
        if not db_session:
            db_session = models.Session(id=session_id)
            db.add(db_session)
            db.commit()

    user_message_text = req.message
    
    # Translate to English if needed
    if req.language != "en":
        user_message_text = translate_text(user_message_text, source_lang=req.language, target_lang="en")

    # Fetch history
    history = db.query(models.Message).filter(models.Message.session_id == session_id).order_by(models.Message.created_at).all()
    history_list = [{"role": msg.role, "content": msg.content} for msg in history[-5:]] # Keep last 5 for context
    
    # Save user message
    user_msg = models.Message(session_id=session_id, role="user", content=user_message_text)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Generate answer
    rag_result = generate_answer(user_message_text, history_list)
    answer_text = rag_result["answer"]

    # Translate back to user language if needed
    if req.language != "en":
        answer_text = translate_text(str(answer_text), source_lang="en", target_lang=req.language)

    # Save assistant message
    # We save the English text in history to keep context in English for the LLM
    assistant_msg = models.Message(session_id=session_id, role="assistant", content=rag_result["answer"])
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return {
        "session_id": session_id,
        "message_id": assistant_msg.id,
        "answer": answer_text,
        "citations": rag_result["citations"],
        "confidence": rag_result["confidence"]
    }

@app.post("/feedback")
async def feedback_endpoint(req: FeedbackRequest, db: Session = Depends(get_db)):
    msg = db.query(models.Message).filter(models.Message.id == req.message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
        
    feedback = db.query(models.Feedback).filter(models.Feedback.message_id == req.message_id).first()
    if feedback:
        feedback.is_positive = req.is_positive
        feedback.comment = req.comment
    else:
        feedback = models.Feedback(
            message_id=req.message_id,
            is_positive=req.is_positive,
            comment=req.comment
        )
        db.add(feedback)
        
    db.commit()
    return {"status": "success"}

def run_ingest_script():
    try:
        import sys
        subprocess.run([sys.executable, "ingest.py"], cwd=str(Path(__file__).parent), check=True)
    except Exception as e:
        print(f"Ingestion failed: {e}")

@app.post("/ingest")
async def ingest_endpoint(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_ingest_script)
    return {"status": "Ingestion started in the background"}

@app.get("/status")
async def status_endpoint():
    """Return vectorstore stats: total chunks, files, size, categories."""
    stats = get_vectorstore_stats()
    return stats

@app.get("/source/{file_path:path}")
async def serve_source_file(file_path: str):
    """Serve original source documents (PDF, HTML, TXT) for citation viewing."""
    data_dir = (Path(__file__).resolve().parent / "data" / "raw").resolve()
    
    decoded_path = urllib.parse.unquote(file_path).replace('\\', '/').strip('/')
    requested = (data_dir / decoded_path).resolve()
    
    if not (str(requested).startswith(str(data_dir)) and requested.is_file()):
        requested = None
        filename = Path(decoded_path).name
        matches = list(data_dir.rglob(filename))
        if matches:
            requested = matches[0]
        else:
            stem_raw = Path(decoded_path).stem
            stem_clean = re.sub(r'[^a-zA-Z0-9]', '', stem_raw).lower()
            for f in data_dir.rglob('*'):
                if f.is_file():
                    f_stem_raw = f.stem
                    f_stem_stripped = re.sub(r'^wp[-_]content[-_]uploads[-_]\d+[-_]\d+[-_]', '', f_stem_raw, flags=re.IGNORECASE)
                    f_clean = re.sub(r'[^a-zA-Z0-9]', '', f_stem_stripped).lower()
                    f_clean_orig = re.sub(r'[^a-zA-Z0-9]', '', f_stem_raw).lower()
                    if stem_clean and (stem_clean == f_clean or stem_clean == f_clean_orig or (len(stem_clean) > 5 and stem_clean in f_clean_orig)):
                        requested = f
                        break
                        
    if not requested or not requested.is_file():
        raise HTTPException(status_code=404, detail="Source file not found")
        
    ext = requested.suffix.lower()
    if ext == ".pdf":
        media_type = "application/pdf"
    elif ext in [".html", ".htm"]:
        media_type = "text/html"
    elif ext == ".csv":
        media_type = "text/csv"
    elif ext == ".json":
        media_type = "application/json"
    else:
        media_type = "text/plain"

    headers = {
        "Content-Disposition": f'inline; filename="{requested.name}"'
    }
    return FileResponse(str(requested), media_type=media_type, headers=headers)

# --- Scraper API Endpoints ---
scraper_process = None
SCRAPER_LOG_FILE = BASE_DIR / "scraper_debug.log"

@app.post("/scraper/start")
async def start_scraper():
    global scraper_process
    if scraper_process and scraper_process.poll() is None:
        return {"status": "error", "message": "Scraper is already running"}
    
    import sys
    log_file = open(SCRAPER_LOG_FILE, "a")
    scraper_process = subprocess.Popen(
        [sys.executable, "bis_scraper.py"],
        cwd=str(BASE_DIR),
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    return {"status": "success", "message": "Scraper started"}

@app.post("/scraper/stop")
async def stop_scraper():
    global scraper_process
    if scraper_process and scraper_process.poll() is None:
        scraper_process.terminate()
        scraper_process = None
        return {"status": "success", "message": "Scraper stopped"}
    return {"status": "error", "message": "Scraper is not running"}

@app.get("/scraper/status")
async def scraper_status():
    global scraper_process
    is_running = scraper_process is not None and scraper_process.poll() is None
    
    logs = []
    if SCRAPER_LOG_FILE.exists():
        try:
            with open(SCRAPER_LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                logs = [line.strip() for line in lines[-50:]]
        except Exception as e:
            logs = [f"Error reading logs: {e}"]
            
    return {
        "is_running": is_running,
        "logs": logs
    }

@app.get("/scraper/manifest")
async def scraper_manifest():
    manifest_path = BASE_DIR / "data" / "sources.json"
    if not manifest_path.exists():
        return []
        
    try:
        import json
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            items = []
            for url, info in data.items():
                items.append({
                    "url": url,
                    "local_path": info.get("local_path"),
                    "fetched_at": info.get("fetched_at"),
                    "is_pdf": info.get("is_pdf", False)
                })
            items.sort(key=lambda x: x.get("fetched_at", ""), reverse=True)
            return items
    except Exception as e:
        return {"error": str(e)}

# Serve frontend static files
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.isdir(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))
else:
    print(f"Warning: Frontend dist directory not found at {frontend_dist}.")
    print("Make sure to build the frontend (npm run build) to serve it from FastAPI.")
