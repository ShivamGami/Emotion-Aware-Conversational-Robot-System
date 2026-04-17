# Emotion-Aware Conversational Robot System (Hack60 PS9)

## 🚀 Overview

This project is being developed as part of **Hack60 – AI Samarthya (HCLTech × IIT Mandi)**.
The goal is to build an **emotion-aware conversational robot** that can:

* Detect user emotions (face + voice)
* Maintain **long-term conversational memory**
* Provide **personalized responses**
* Authenticate users with profiles
* Respond using **text-to-speech (TTS)**
* Visualize interactions in a **3D environment**

The system integrates **AI, backend services, frontend UI, and 3D visualization** into a unified experience.

---

## 🧠 System Architecture

The project is divided into four major components:

* **AI & Memory (Team 1)**
  Face emotion detection, memory system, LLM-based chat, context graph

* **Voice & Authentication (Team 2)**
  Voice emotion detection, database, JWT authentication, TTS, multimodal fusion

* **Frontend & UX (Team 3)**
  React-based UI, chat interface, dashboards, webcam integration

* **3D World (Team 4)**
  Robot model, environment, animations, context visualization

---

## 🏗️ Project Structure

```
emotion-robot-system/
├── backend/
│   ├── app/
│   │   ├── auth/
│   │   ├── database/
│   │   ├── emotion_detection/
│   │   │   ├── voice/
│   │   │   └── face/
│   │   ├── memory/
│   │   ├── llm/
│   │   ├── api/
│   │   ├── core/
│   │   └── main.py
│   ├── training/
│   ├── models/
│   ├── alembic/
│   └── requirements.txt
├── frontend/
├── docs/
├── scripts/
├── .gitignore
└── README.md

---

## ⚙️ Tech Stack

### Backend

* FastAPI
* SQLAlchemy
* JWT Authentication
* Librosa (audio processing)
* PyTorch / Transformers (LLM & ML models)

### Frontend

* React (TypeScript)
* TailwindCSS
* Zustand (state management)

### AI / ML

* Face Emotion → DeepFace / CNN
* Voice Emotion → MFCC + ML models (RAVDESS)
* Memory → Vector DB (ChromaDB)
* LLM → Phi-3 mini / local model

### 3D Visualization

* React Three Fiber
* Three.js

---

## 👥 Team Responsibilities

| Team   | Role          |
| ------ | ------------- |
| Team 1 | AI + Memory   |
| Team 2 | Voice + Auth  |
| Team 3 | Frontend + UX |
| Team 4 | 3D Worlds     |

---

## 📌 Current Progress

* [x] Repository structure setup
* [ ] Backend setup (FastAPI)
* [ ] Voice Emotion Detection (Task 2.1)
* [ ] Database & Authentication
* [ ] Frontend UI
* [ ] 3D Environment

---

## 🛠️ Setup Instructions (Basic)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm start
```

---

## 📅 Hackathon Timeline

* Phase 1 → Foundation (Core modules setup)
* Phase 2 → Core Build
* Phase 3 → Integration
* Phase 4 → Enhancement
* Phase 5 → Demo

---

## 🎯 Goal

Build a **fully interactive, personalized, emotion-aware robot system** that delivers a strong demo with:

* Memory
* Voice interaction
* Emotion detection
* 3D visualization

---

## ⚠️ Note

This is a **work-in-progress hackathon project**.
Code structure and features will evolve rapidly.

---

## 🧑‍💻 Contributors


---
