from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from auth.password import get_password_hash, verify_password
from auth.jwt_handler import create_access_token, decode_access_token
from database.db import get_db
from database.models import User

router = APIRouter()

class UserSignup(BaseModel):
    username: str
    password: str
    email: str

class UserLogin(BaseModel):
    username: str
    password: str

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(user: UserSignup, db: Session = Depends(get_db)):
    db_user = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    hashed_password = get_password_hash(user.password)
    
    # Create actual row in local database
    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        avatar="default.png"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User created successfully", "user": {"id": new_user.id, "username": new_user.username}}

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": str(db_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/profile")
def get_profile(token: str, db: Session = Depends(get_db)):
    decoded = decode_access_token(token)
    if not decoded:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user_id = decoded.get("sub")
    db_user = db.query(User).filter(User.id == int(user_id)).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    return {
        "id": db_user.id,
        "username": db_user.username,
        "email": db_user.email,
        "avatar": db_user.avatar
    }
