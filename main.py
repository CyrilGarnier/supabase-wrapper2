"""
BaseGenspark API v2.1 - FIXED with STUDENTS table
Pedagogical tracking with clean separation
"""
import os
import httpx
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ============================================================================
# CONFIGURATION
# ============================================================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://iepvmuzfdkklysnqbvwt.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
AGENT_SECRET_TOKEN = os.getenv("AGENT_SECRET_TOKEN", "AGENT_TOKEN_PHOTOMENTOR_2026")
JWT_SECRET = os.getenv("JWT_SECRET", "basegenspark_secret_2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

app = FastAPI(title="BaseGenspark API", version="2.1-STUDENTS")
httpx_client = httpx.Client()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# MODELS
# ============================================================================
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

# ============================================================================
# AUTH HELPERS
# ============================================================================
def verify_agent_token(
    x_agent_token: Optional[str] = Header(None),
    token: Optional[str] = None
):
    """Vérifier le token agent (header OU query parameter)"""
    provided_token = x_agent_token or token
    if not provided_token or provided_token != AGENT_SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Token agent invalide")
    return True

# ============================================================================
# ENDPOINTS
# ============================================================================
@app.get("/")
async def root():
    return {
        "message": "BaseGenspark API v2.1-STUDENTS",
        "status": "operational",
        "agent_endpoints": True
    }

@app.get("/health")
async def health():
    try:
        response = httpx_client.get(
            f"{SUPABASE_URL}/rest/v1/students?select=count",
            headers={"apikey": SUPABASE_KEY}
        )
        supabase_status = "connected" if response.status_code == 200 else "error"
    except:
        supabase_status = "error"
    
    return {
        "status": "healthy",
        "supabase": supabase_status,
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# AGENT ENDPOINTS
# ============================================================================
@app.post("/agent/session/start")
async def agent_session_start(
    data: AgentSessionStart,
    authenticated: bool = Depends(verify_agent_token)
):
    """Démarrer une session pédagogique"""
    try:
        # 1️⃣ Trouver ou créer l'étudiant dans la table STUDENTS
        response = httpx_client.get(
            f"{SUPABASE_URL}/rest/v1/students?email=eq.{data.student_email}&select=*",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )
        
        if response.status_code == 200 and response.json():
            student = response.json()[0]
            student_id = student["id"]
        else:
            # Créer un nouvel étudiant
            full_name = data.student_email.split("@")[0].replace(".", " ").title()
            new_student = {
                "email": data.student_email,
                "full_name": full_name,
                "institution": "Club Photo",
                "role": "STUDENT"
            }
            
            response = httpx_client.post(
                f"{SUPABASE_URL}/rest/v1/students",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=new_student
            )
            
            if response.status_code not in [200, 201]:
                raise HTTPException(
                    status_code=500,
                    detail=f"Impossible de créer l'étudiant: {response.text}"
                )
            
            student = response.json()[0]
            student_id = student["id"]
        
        # 2️⃣ Générer un session_id unique
        agent_prefix_map = {
            "photomentor_pro": "PHOTO",
            "data_analyst_coach": "COACH",
            "soda_opportunity": "SODA"
        }
        prefix = agent_prefix_map.get(data.agent_name, "AGENT")
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        student_prefix = data.student_email.split("@")[0][:4].upper()
        
        import uuid
        suffix = uuid.uuid4().hex[:4].upper()
        session_id = f"{prefix}-{timestamp}-{student_prefix}-{suffix}"
        
        # 3️⃣ Créer la session dans user_activity
        session_data = {
            "session_id": session_id,
            "student_id": student_id,
            "agent_name": data.agent_name,
            "status": "in_progress",
            "progression_current": 0,
            "progression_total": data.progression_total,
            "progression_label": data.progression_label,
            "metadata": data.metadata or {},
            "started_at": datetime.utcnow().isoformat()
        }
        
        response = httpx_client.post(
            f"{SUPABASE_URL}/rest/v1/user_activity",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            },
            json=session_data
        )
        
        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=500,
                detail=f"Impossible de créer la session: {response.text}"
            )
        
        return {
            "success": True,
            "session_id": session_id,
            "student_id": student_id,
            "student_name": student["full_name"],
            "message": f"Session créée pour {student['full_name']}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/agent/session/{session_id}")
async def agent_session_update(
    session_id: str,
    data: AgentSessionUpdate,
    authenticated: bool = Depends(verify_agent_token)
):
    """Mettre à jour une session"""
    try:
        update_data = {"updated_at": datetime.utcnow().isoformat()}
        
        if data.progression_current is not None:
            update_data["progression_current"] = data.progression_current
        if data.progression_label:
            update_data["progression_label"] = data.progression_label
        if data.resources_count is not None:
            update_data["resources_count"] = data.resources_count
        if data.metadata:
            update_data["metadata"] = data.metadata
        
        response = httpx_client.patch(
            f"{SUPABASE_URL}/rest/v1/user_activity?session_id=eq.{session_id}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            },
            json=update_data
        )
        
        if response.status_code not in [200, 204]:
            raise HTTPException(status_code=500, detail="Échec de la mise à jour")
        
        return {"success": True, "session_id": session_id, "updated": update_data}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/session/{session_id}/end")
async def agent_session_end(
    session_id: str,
    data: AgentSessionEnd,
    authenticated: bool = Depends(verify_agent_token)
):
    """Clôturer une session"""
    try:
        # Récupérer la session
        response = httpx_client.get(
            f"{SUPABASE_URL}/rest/v1/user_activity?session_id=eq.{session_id}&select=*",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )
        
        if response.status_code != 200 or not response.json():
            raise HTTPException(status_code=404, detail="Session introuvable")
        
        session = response.json()[0]
        started_at = datetime.fromisoformat(session["started_at"].replace("Z", "+00:00"))
        from datetime import timezone
        completed_at = datetime.now(timezone.utc)
        duration_minutes = int((completed_at - started_at).total_seconds() / 60)
        
        update_data = {
            "status": "completed",
            "completed_at": completed_at.isoformat(),
            "duration_minutes": duration_minutes,
            "updated_at": completed_at.isoformat()
        }
        
        if data.score is not None:
            update_data["score"] = data.score
        if data.strengths:
            update_data["strengths"] = data.strengths
        if data.improvements:
            update_data["improvements"] = data.improvements
        if data.metadata:
            update_data["metadata"] = data.metadata
        
        response = httpx_client.patch(
            f"{SUPABASE_URL}/rest/v1/user_activity?session_id=eq.{session_id}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            },
            json=update_data
        )
        
        if response.status_code not in [200, 204]:
            raise HTTPException(status_code=500, detail="Échec de clôture")
        
        return {
            "success": True,
            "session_id": session_id,
            "duration_minutes": duration_minutes,
            "completed_at": completed_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ADMIN ENDPOINTS (pour l'Agent Superviseur)
# ============================================================================
@app.get("/admin/students")
async def admin_list_students():
    """Lister tous les étudiants"""
    response = httpx_client.get(
        f"{SUPABASE_URL}/rest/v1/students?select=*&order=created_at.desc",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
    )
    return response.json() if response.status_code == 200 else []

@app.get("/admin/sessions")
async def admin_list_sessions():
    """Lister toutes les sessions"""
    response = httpx_client.get(
        f"{SUPABASE_URL}/rest/v1/user_activity?select=*&order=started_at.desc&limit=100",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
    )
    return response.json() if response.status_code == 200 else []

