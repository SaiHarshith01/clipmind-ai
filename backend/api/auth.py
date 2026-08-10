from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.database import get_db
from models.schema import User
from core.security import get_password_hash, verify_password, create_access_token, get_current_user

# 1. Define the Router
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# 2. Schema for Registration
class UserCreate(BaseModel):
    email: str
    password: str

# 3. Register Endpoint (Expects JSON body)
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email is already registered"
        )
    
    # Create new user (Role defaults to LEARNER automatically in database)
    new_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User registered successfully!"}

# 4. Login Endpoint (Expects Form Data for Swagger UI compatibility)
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Look up user (Swagger sends the email in the 'username' field)
    user = db.query(User).filter(User.email == form_data.username).first()
    
    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Generate the JWT Token
    access_token = create_access_token(data={"sub": user.email})
    
    # Return the exact format FastAPI needs for the Swagger Lock button
    return {"access_token": access_token, "token_type": "bearer"}

# 5. Get Profile Endpoint
@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    }