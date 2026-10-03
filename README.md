# AI-Powered Resume Screening & Candidate-Job Matching System

An intelligent, bias-mitigated talent acquisition platform designed to automate resume screening, evaluate candidate qualifications against job descriptions, and deliver explainable AI (XAI) candidate insights.

---

## 📌 Executive Summary

Modern recruitment workflows suffer from manual overhead and rigid keyword-matching Applicant Tracking Systems (ATS) that fail to recognize semantic equivalencies (e.g., matching *GCP* skills to an *AWS* requirement). Additionally, manual evaluations can introduce unconscious bias based on candidate names, demographics, or alma maters.

This system addresses these challenges with:
- **LLM-Driven Semantic Matching**: Evaluates candidates beyond exact keywords using semantic similarity and LLM reasoning.
- **Explainable AI (XAI)**: Provides explicit matching vs. missing skill breakdowns, score justification, and candidate summaries.
- **Bias Mitigation**: Automatically scrubs Personally Identifiable Information (PII) and demographic data before LLM evaluation, supporting a toggleable **Blind Review Mode**.
- **Multi-Factor Scoring**: Evaluates candidate fit across configurable weights for **Skills**, **Years of Experience (YOE)**, and **Education/Certifications**.
- **Fault-Tolerant File Ingestion**: Gracefully isolates corrupt, unreadable, or encrypted files into an "Unprocessable Files" queue without breaking batch runs.

---

## 🛠️ Architecture & Technology Stack

```
[ Frontend: React 19 + Vite ] ◄--- HTTP/JSON ---► [ Backend: FastAPI + Uvicorn ]
                                                        │
                                   ┌────────────────────┼────────────────────┐
                                   ▼                    ▼                    ▼
                           [ LangGraph Engine ]  [ MongoDB Store ]  [ LM Studio / LLM ]
```

### Core Technologies
- **Backend**: Python 3.10+, [FastAPI](https://fastapi.tiangolo.com/), Uvicorn, [LangGraph](https://github.com/langchain-ai/langgraph), [LangChain](https://github.com/langchain-ai/langchain), PyMuPDF / PyPDF, Python-docx, RapidFuzz, DataSketch, PyMongo
- **Frontend**: [React 19](https://react.dev/), [Vite](https://vitejs.dev/), Lucide React Icons, Vanilla CSS
- **Database & Services**: [MongoDB 7.0](https://www.mongodb.com/), [LM Studio](https://lmstudio.ai/) (OpenAI-compatible local LLM server, e.g. `nvidia/nemotron-3-nano-4b`)
- **Containerization**: Docker, Docker Compose

---

## 🚀 Key Features

1. **Batch Resume Upload & Processing**
   - Supports dragging and dropping up to 50 resumes simultaneously (`.pdf`, `.docx`, `.txt`).
   - Automatically parses job descriptions from text or uploaded documents.

2. **Demographic Data Scrubbing & Blind Review**
   - Strips PII (Names, Emails, Phone Numbers, Addresses, Gender/Pronouns, Graduation Years, Institution Names) prior to model evaluation.
   - Assigns anonymized Candidate IDs (e.g., `Candidate #104`) with a blind mode switch in the frontend UI.

3. **LangGraph Processing Pipeline**
   - **Node 1: Structured Parsing & Extraction**: Extracts candidate skills, YOE, certifications, and work history.
   - **Node 2: Multi-Factor Scoring Engine**: Computes weighted scores across skills, experience, and credentials.
   - **Node 3: LLM Explanation Generator**: Generates transparent, human-readable scoring rationale.

4. **Interactive Candidate Dashboard**
   - Ranks candidates by overall match percentage.
   - Displays mandatory vs. preferred skill matches, missing requirements, and experience fit.
   - Allows dynamically adjusting feature weights to recalculate scores in real-time.

5. **Unprocessable File Handling**
   - Catches corrupted or password-protected files and places them into a dedicated user feedback section.

---

## 📂 Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── agent/          # LangGraph workflow & node definitions
│   │   ├── db/             # MongoDB client & database models
│   │   ├── services/       # Parsing, PII scrubbing, scoring & LLM integrations
│   │   ├── config.py       # Application configurations & environment variables
│   │   ├── main.py         # FastAPI application routes & entrypoint
│   │   └── schemas.py      # Pydantic data schemas
│   ├── requirements.txt    # Python dependencies
│   ├── test_pipeline.py    # Pipeline test suite
│   └── venv/               # Python virtual environment (local)
├── frontend/
│   ├── src/                # React components & UI logic
│   ├── index.html          # Frontend HTML root
│   ├── package.json        # NPM dependencies & scripts
│   └── vite.config.js      # Vite build configuration
├── docker-compose.yml      # Multi-container orchestration (FastAPI + MongoDB)
├── Dockerfile              # Container definition for FastAPI backend
├── prd.md                  # Detailed Product Requirement Document
├── technical_doc.md        # Technical Architecture & Implementation Documentation
├── run_all.py              # Cross-platform Python runner script
├── start.bat               # Windows batch launcher
└── start.ps1               # Windows PowerShell launcher
```

---

## ⚙️ Quick Start Guide

### Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: v18 or higher (with `npm`)
- **LM Studio** (Optional for local LLM inference): Running on `http://localhost:1234/v1` with an OpenAI-compatible endpoint.
- **Docker & Docker Compose** (Optional, for containerized run)

---

### Option A: One-Click Launcher (Recommended for Windows / Local)

Run the automated helper script to launch both Backend and Frontend concurrently:

**Via Python (Cross-Platform):**
```bash
python run_all.py
```

**Via Windows Launcher:**
Double-click `start.bat` or run:
```powershell
.\start.ps1
```

Access the applications at:
- 🌐 **Frontend Dashboard**: [http://localhost:5173](http://localhost:5173)
- ⚡ **Backend API**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- 📖 **API Docs (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### Option B: Manual Setup

#### 1. Setup Backend
```bash
cd backend
python -m venv venv

# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Setup Frontend
```bash
cd frontend
npm install
npm run dev
```

---

### Option C: Running with Docker Compose

To spin up the entire application stack along with MongoDB containerized:

```bash
docker-compose up --build
```

---

## 🧪 Testing

Run backend pipeline tests to verify PII scrubbing, scoring, and parsing functions:

```bash
cd backend
python test_pipeline.py
```

---

## 📄 Documentation Links
- [Product Requirement Document (PRD)](file:///c:/Users/debarghaya/Projects/TCS-Hackathon-Resurrection/prd.md)
- [Technical Architecture Documentation](file:///c:/Users/debarghaya/Projects/TCS-Hackathon-Resurrection/technical_doc.md)

---

## 📜 License
This project is developed for talent acquisition research and hackathon demonstration purposes.
