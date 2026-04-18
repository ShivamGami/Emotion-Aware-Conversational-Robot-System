import sys
import os

def check_dependencies():
    print("--- Emotion Robot Backend Dependency Check ---")
    
    deps = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("sqlalchemy", "SQLAlchemy"),
        ("deepface", "DeepFace"),
        ("torch", "PyTorch"),
        ("sentence_transformers", "Sentence-Transformers"),
        ("chromadb", "ChromaDB"),
    ]
    
    missing = []
    found = []
    
    for module_name, display_name in deps:
        try:
            __import__(module_name)
            found.append(display_name)
            print(f"[OK] {display_name} is installed.")
        except ImportError:
            missing.append(display_name)
            print(f"[ERROR] {display_name} is NOT installed.")
            
    if missing:
        print("\n[!] Possible issues detected. Please install missing dependencies:")
        print(f"pip install {' '.join([m.lower() for m in missing])}")
    else:
        print("\nAll core dependencies are present.")
        
    # Check for model files
    print("\n--- Model File Verification ---")
    models = [
        "voice_model.pth",
        "sql_app.db"
    ]
    for model in models:
        if os.path.exists(model):
            print(f"✅ {model} found.")
        else:
            print(f"❌ {model} NOT found.")

if __name__ == "__main__":
    check_dependencies()
