"""
BaseGenspark API v3.0 CORRECT
Architecture : users = suivi pédagogique, agents = token only
"""
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from supabase import create_client, Client
from passlib.context import CryptContext
import os
import uuid

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
AGENT_SECRET_TOKEN = os.getenv("AGENT_SECRET_TOKEN")
ADMIN_EMAIL = "cyril@alkymya.co"

# Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Password context (juste pour créer les users avec password temporaire)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# App
app = FastAPI(title="BaseGenspark API", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Models
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

# Security
def verify_agent_token(x_agent_token: Optional[str] = Header(None)):
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
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/agent/session/start")
async def agent_start(data: AgentSessionStart, _: bool = Depends(verify_agent_token)):
    """
    Créer une session pour un agent pédagogique.
    ✅ Token agent vérifié = authentification suffisante
    ✅ Pas besoin de vérifier le mot de passe admin
    """
    try:
        # Trouver ou créer l'étudiant
        student_resp = supabase.table("users").select("*").eq("email", data.student_email).execute()
        
        if not student_resp.data:
            # Créer l'étudiant avec un password temporaire (jamais utilisé)
            temp_pwd = f"temp_{uuid.uuid4().hex[:8]}"
            hashed = pwd_context.hash(temp_pwd)
            
            student_data = {
                "email": data.student_email,
                "password_hash": hashed,
                "salt": "auto",
                "full_name": data.student_email.split("@")[0].title(),
                "role": "STUDENT",
                "institution": "Club Photo / Grande École",
                "created_at": datetime.utcnow().isoformat()
            }
            
            create_resp = supabase.table("users").insert(student_data).execute()
            
            if not create_resp.data:
                raise HTTPException(status_code=500, detail="Impossible de créer l'étudiant")
            
            student = create_resp.data[0]
        else:
            student = student_resp.data[0]
        
        # Générer session_id unique
        prefix = data.student_email.split("@")[0][:4].upper()
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        suffix = uuid.uuid4().hex[:4].upper()
        
        agent_prefix_map = {
            "photomentor_pro": "PHOTO",
            "coach_data": "COACH",
            "soda_opportunity": "SODA"
        }
        agent_prefix = agent_prefix_map.get(data.agent_name, "AGENT")
        session_id = f"{agent_prefix}-{timestamp}-{prefix}-{suffix}"
        
        # Créer la session dans user_activity
        session_data = {
            "session_id": session_id,
            "user_id": student["id"],  # 🎯 user_id de l'étudiant
            "agent_name": data.agent_name,
            "status": "in_progress",
            "progression_current": 0,
            "progression_total": data.progression_total,
            "progression_label": data.progression_label or "Session démarrée",
            "metadata": data.metadata or {},
            "started_at": datetime.utcnow().isoformat()
        }
        
        activity_resp = supabase.table("user_activity").insert(session_data).execute()
        
        if not activity_resp.data:
            raise HTTPException(status_code=500, detail="Impossible de créer la session")
        
        return {
            "success": True,
            "session_id": session_id,
            "user_id": student["id"],
            "student_name": student["full_name"],
            "message": f"Session créée pour {student['full_name']}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.patch("/agent/session/{session_id}")
async def agent_update(session_id: str, data: AgentSessionUpdate, _: bool = Depends(verify_agent_token)):
    """Mettre à jour une session en cours"""
    try:
        update_data = {k: v for k, v in data.dict(exclude_unset=True).items()}
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("user_activity").update(update_data).eq("session_id", session_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Session introuvable")
        
        return {"success": True, "session": response.data[0]}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.post("/agent/session/{session_id}/end")
async def agent_end(session_id: str, data: AgentSessionEnd, _: bool = Depends(verify_agent_token)):
    """Clôturer une session avec score et feedback"""
    try:
        # Récupérer la session pour calculer la durée
        session_resp = supabase.table("user_activity").select("started_at").eq("session_id", session_id).execute()
        
        if not session_resp.data:
            raise HTTPException(status_code=404, detail="Session introuvable")
        
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
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Session introuvable")
        
        return {
            "success": True,
            "session": response.data[0],
            "duration_minutes": duration
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/admin/users")
async def list_users():
    """Lister tous les users (pour l'Agent Superviseur)"""
    try:
        response = supabase.table("users").select("id, email, full_name, role, institution, created_at").execute()
        return {"users": response.data, "count": len(response.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/admin/sessions")
async def list_sessions(limit: int = 50):
    """Lister les dernières sessions (pour l'Agent Superviseur)"""
    try:
        response = supabase.table("user_activity").select("""
            session_id, user_id, agent_name, status, progression_current, 
            progression_total, progression_label, score, started_at, completed_at,
            duration_minutes, users!inner(email, full_name)
        """).order("created_at", desc=True).limit(limit).execute()
        
        return {"sessions": response.data, "count": len(response.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

