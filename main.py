"""
BaseGenspark API v3.0 FINAL
API sécurisée pour agents pédagogiques Genspark
"""

from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from supabase import create_client, Client
import bcrypt
import jwt
import os
import httpx
import uuid

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://iepvmuzfdkklysnqbvwt.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImllcHZtdXpmZGtrbHlzbnFidnd0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg3MTM0NDEsImV4cCI6MjA4NDI4OTQ0MX0.N_veJeUbrCVmW5eHMqCvMvwZb6LD-7cJ9NFa8aCGPIY")
JWT_SECRET = os.getenv("JWT_SECRET", "basegenspark_secret_2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
AGENT_SECRET_TOKEN = os.getenv("AGENT_SECRET_TOKEN", "AGENT_TOKEN_PHOTOMENTOR_2026")
ADMIN_EMAIL = "cyril@alkymya.co"

# Initialisation Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# FastAPI App
app = FastAPI(title="BaseGenspark API", version="3.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class UserRegister(BaseModel):
    email: str
    password: str = Field(min_length=8)
    full_name: str
    role: str = "STUDENT"
    institution: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class SessionCreate(BaseModel):
    session_id: str
    user_id: str
    agent_name: str
    status: str = "in_progress"
    progression_current: int = 0
    progression_total: int = 5
    progression_label: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SessionUpdate(BaseModel):
    status: Optional[str] = None
    progression_current: Optional[int] = None
    progression_label: Optional[str] = None
    resources_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class SessionComplete(BaseModel):
    score: Optional[float] = None
    strengths: Optional[List[str]] = None
    improvements: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class AgentSessionStart(BaseModel):
    student_email: str
    agent_name: str
    progression_total: int = 5
    progression_label: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AgentSessionUpdate(BaseModel):
    progression_current: Optional[int] = None
    progression_label: Optional[str] = None
    resources_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class AgentSessionEnd(BaseModel):
    score: Optional[float] = None
    strengths: Optional[List[str]] = None
    improvements: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

# Security utilities
def hash_password(password: str) -> tuple:
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8'), salt.decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False

def create_jwt_token(user: dict) -> str:
    payload = {
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except:
        raise HTTPException(status_code=401, detail="Token invalide")

async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token manquant")
    scheme, token = authorization.split()
    payload = decode_jwt_token(token)
    response = supabase.table("users").select("*").eq("id", payload["user_id"]).execute()
    if not response.data:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    return response.data[0]

async def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Accès refusé")
    return current_user

async def verify_agent_token(x_agent_token: Optional[str] = Header(None)):
    if not x_agent_token or x_agent_token != AGENT_SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Token agent invalide")
    return True

# Endpoints
@app.get("/")
async def root():
    return {"message": "BaseGenspark API v3.0", "status": "operational"}

@app.get("/health")
async def health():
    try:
        supabase.table("users").select("count").limit(1).execute()
        return {"status": "healthy", "supabase": "connected"}
    except:
        return {"status": "unhealthy", "supabase": "disconnected"}

@app.post("/auth/register")
async def register(user: UserRegister):
    existing = supabase.table("users").select("id").eq("email", user.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    hashed, salt = hash_password(user.password)
    user_data = {
        "email": user.email,
        "password_hash": hashed,
        "salt": salt,
        "full_name": user.full_name,
        "role": user.role,
        "institution": user.institution,
        "created_at": datetime.utcnow().isoformat()
    }
    
    response = supabase.table("users").insert(user_data).execute()
    created_user = response.data[0]
    token = create_jwt_token(created_user)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": created_user["id"],
            "email": created_user["email"],
            "full_name": created_user["full_name"],
            "role": created_user["role"]
        }
    }

@app.post("/auth/login")
async def login(credentials: UserLogin):
    response = supabase.table("users").select("*").eq("email", credentials.email).execute()
    if not response.data:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    user = response.data[0]
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    token = create_jwt_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    }

@app.get("/admin/users")
async def list_users(admin: dict = Depends(require_admin)):
    response = supabase.table("users").select("*").execute()
    return {"users": response.data, "count": len(response.data)}

@app.post("/activity")
async def create_session(session: SessionCreate, user: dict = Depends(get_current_user)):
    session_data = {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "agent_name": session.agent_name,
        "status": session.status,
        "progression_current": session.progression_current,
        "progression_total": session.progression_total,
        "progression_label": session.progression_label,
        "metadata": session.metadata or {},
        "started_at": datetime.utcnow().isoformat()
    }
    response = supabase.table("user_activity").insert(session_data).execute()
    return {"success": True, "session": response.data[0]}

@app.patch("/activity/{session_id}")
async def update_session(session_id: str, update: SessionUpdate, user: dict = Depends(get_current_user)):
    update_data = {k: v for k, v in update.dict(exclude_unset=True).items()}
    update_data["updated_at"] = datetime.utcnow().isoformat()
    response = supabase.table("user_activity").update(update_data).eq("session_id", session_id).execute()
    return {"success": True, "session": response.data[0]}

@app.post("/agent/session/start")
async def agent_start(data: AgentSessionStart, _: bool = Depends(verify_agent_token)):
    # Login admin interne
    admin_pwd = os.getenv("ADMIN_PASSWORD", "CyrilAdmin2026!")
    admin_resp = supabase.table("users").select("*").eq("email", ADMIN_EMAIL).execute()
    admin = admin_resp.data[0]
    
    if not verify_password(admin_pwd, admin["password_hash"]):
        raise HTTPException(status_code=500, detail="Erreur auth admin")
    
    # Trouver ou créer étudiant
    student_resp = supabase.table("users").select("*").eq("email", data.student_email).execute()
    
    if not student_resp.data:
        temp_pwd = f"temp_{uuid.uuid4().hex[:8]}"
        hashed, salt = hash_password(temp_pwd)
        student_data = {
            "email": data.student_email,
            "password_hash": hashed,
            "salt": salt,
            "full_name": data.student_email.split("@")[0].title(),
            "role": "STUDENT",
            "institution": "Club Photo",
            "created_at": datetime.utcnow().isoformat()
        }
        create_resp = supabase.table("users").insert(student_data).execute()
        student = create_resp.data[0]
    else:
        student = student_resp.data[0]
    
    # Générer session_id
    prefix = data.student_email.split("@")[0][:4].upper()
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:4].upper()
    agent_prefix = {"photomentor_pro": "PHOTO", "coach_data": "COACH", "soda_opportunity": "SODA"}.get(data.agent_name, "AGENT")
    session_id = f"{agent_prefix}-{timestamp}-{prefix}-{suffix}"
    
    # Créer session
    session_data = {
        "session_id": session_id,
        "user_id": student["id"],
        "agent_name": data.agent_name,
        "status": "in_progress",
        "progression_current": 0,
        "progression_total": data.progression_total,
        "progression_label": data.progression_label or "Session démarrée",
        "metadata": data.metadata or {},
        "started_at": datetime.utcnow().isoformat()
    }
    supabase.table("user_activity").insert(session_data).execute()
    
    return {"success": True, "session_id": session_id, "user_id": student["id"]}

@app.patch("/agent/session/{session_id}")
async def agent_update(session_id: str, data: AgentSessionUpdate, _: bool = Depends(verify_agent_token)):
    update_data = {k: v for k, v in data.dict(exclude_unset=True).items()}
    update_data["updated_at"] = datetime.utcnow().isoformat()
    response = supabase.table("user_activity").update(update_data).eq("session_id", session_id).execute()
    return {"success": True, "session": response.data[0]}

@app.post("/agent/session/{session_id}/end")
async def agent_end(session_id: str, data: AgentSessionEnd, _: bool = Depends(verify_agent_token)):
    session_resp = supabase.table("user_activity").select("started_at").eq("session_id", session_id).execute()
    started = datetime.fromisoformat(session_resp.data[0]["started_at"].replace('Z', '+00:00'))
    completed = datetime.utcnow()
    duration = int((completed - started).total_seconds() / 60)
    
    completion_data = {
        "status": "completed",
        "completed_at": completed.isoformat(),
        "duration_minutes": duration,
        "updated_at": completed.isoformat()
    }
    
    if data.score is not None:
        completion_data["score"] = data.score
    if data.strengths:
        completion_data["strengths"] = data.strengths
    if data.improvements:
        completion_data["improvements"] = data.improvements
    if data.metadata:
        completion_data["metadata"] = data.metadata
    
    response = supabase.table("user_activity").update(completion_data).eq("session_id", session_id).execute()
    return {"success": True, "session": response.data[0], "duration_minutes": duration}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
