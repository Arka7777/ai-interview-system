# 🧑‍💼 AI Interview Preparation & Mock Interview System

An AI-powered mock interview platform that conducts job-specific technical interviews, evaluates candidate answers, generates adaptive follow-up questions, and provides a detailed performance report.

The project uses **LangGraph** for the interview workflow, **Groq** as the LLM provider, **FastAPI** for the backend, and **Streamlit** for the frontend.

---

## 🚀 Live Demo

### 🎨 Frontend — Streamlit

👉 https://ai-interview-system-slu2fqzh5fdmpe4h82hs4x.streamlit.app/

### ⚙️ Backend — FastAPI

👉 https://ai-interview-system-backend-0hoo.onrender.com

### 📚 API Documentation — Swagger

👉 https://ai-interview-system-backend-0hoo.onrender.com/docs

---

## ✨ Features

- 🎯 Job-role specific mock interviews
- 📄 Optional Job Description analysis
- 🧠 AI-generated interview questions
- 🔍 Automatic skill extraction
- 🛠️ Tool and framework identification
- 📊 AI-based answer evaluation
- ⭐ Answer scoring from 0–10
- 🔄 Adaptive follow-up questions
- 📝 Interview history
- 📈 Final performance report
- 💪 Strength identification
- ⚠️ Weak-area identification
- 📚 Recommended topics for improvement
- ⏸️ Real LangGraph interrupt/resume workflow
- 🌐 Deployed FastAPI backend
- 🎨 Streamlit web interface

---

# 🏗️ System Architecture

```text
                         ┌──────────────────────┐
                         │        User          │
                         │ Candidate / Student  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      Streamlit       │
                         │       Frontend       │
                         └──────────┬───────────┘
                                    │
                              HTTP Requests
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       FastAPI        │
                         │       Backend        │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      LangGraph       │
                         │   Interview Engine   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │        Groq          │
                         │         LLM          │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   interviews.json    │
                         │ Human-readable copy  │
                         └──────────────────────┘

## 📁 Project Structure

```text
ai-interview-system/
│
├── .venv/
│
├── backend/
│   ├── backend.py
│   ├── .env
│   ├── requirements.txt
│   └── interviews.json
│
├── frontend/
│   └── app.py
│
├── .gitignore
└── README.md


## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **Backend:** FastAPI, Uvicorn, Pydantic
- **AI/LLM:** LangChain, LangGraph, Groq
- **Model:** GPT-OSS
- **Storage:** JSON (`interviews.json`), LangGraph `MemorySaver`
- **Deployment:** Streamlit Community Cloud, Render
- **Programming Language:** Python
- **Version Control:** Git, GitHub

---

## 👨‍💻 Author

**Arkapravo Biswas**

B.Tech in Information Technology  
Kalyani Government Engineering College

---
