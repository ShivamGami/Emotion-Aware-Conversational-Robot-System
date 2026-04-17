# Emotion-Aware-Conversational-Robot-System

emotion-robot-system/
│
├── backend/                # FastAPI + ML + DB (Team 1 & 2)
│   ├── app/
│   │   ├── auth/           # JWT, password, routes
│   │   ├── database/       # DB models, session
│   │   ├── emotion_detection/
│   │   │   ├── face/       # Team 1
│   │   │   └── voice/      # Team 2 (YOU)
│   │   ├── memory/         # vector DB (Team 1)
│   │   ├── llm/            # chat engine (Team 1)
│   │   ├── api/            # route handlers
│   │   ├── core/           # config, settings
│   │   └── main.py         # FastAPI entry
│   │
│   ├── training/           # ML training scripts
│   ├── models/             # saved ML models
│   ├── alembic/            # DB migrations
│   ├── requirements.txt
│   └── .env
│
├── frontend/               # React (Team 3)
│   ├── public/
│   │   └── models/         # 3D assets (Team 4)
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── store/
│   │   └── App.tsx
│   └── package.json
│
├── docs/                   # API docs, notes
├── scripts/                # helper scripts
├── .gitignore
└── README.md
