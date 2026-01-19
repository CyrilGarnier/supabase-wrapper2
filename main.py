"""
=====================================================
BaseGenspark API - Version 2.1 avec Endpoints Agents
Ajout : 3 endpoints sécurisés pour agents pédagogiques
=====================================================
"""

import os
import httpx
import bcrypt
import jwt
import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

# =====================================================
# CONFIGURATION
# =====================================================

SUPABASE_URL = "https://iepvmuzfdkklysnqbvwt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImllcHZtdXpmZGtrbHlzbnFidnd0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg3MTM0NDEsImV4cCI6MjA4NDI4OTQ0MX0.N_veJeUbrCVmW5eHMqCvMvwZb6LD-7cJ9NFa8aCGPIY"

JWT_SECRET = os.getenv("JWT_SECRET", "basegenspark_secret_2026_change_me_in_production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

AGENT_SECRET_TOKEN = os.getenv("AGENT_SECRET_TOKEN", "AGENT_TOKEN_PHOTOMENTOR_2026")

ADMIN_EMAIL = "cyril@alkymya.co"

# HTTP Client
httpx_client = httpx.AsyncClient(timeout=30.0)

# FastAPI
app = FastAPI(
    title="BaseGenspark API",
    version="2.1.0",
    description="API sécurisée avec endpoints agents pédagogiques"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# MODELS PYDANTIC
# =====================================================

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

# =====================================================
# SECURITY UTILITIES
# =====================================================

def hash_password(password: str) -> tuple[str, str]:
    """Hash un mot de passe avec bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    password_bytes = password.encode('utf-8')
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8'), salt.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False

def create_jwt_token(user_data: dict) -> str:
    """Crée un JWT token"""
    payload = {
        "user_id": user_data["id"],
        "email": user_data["email"],
        "role": user_data["role"],
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str) -> dict:
    """Décode et valide un JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expiré")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token invalide")

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Récupère l'utilisateur courant depuis le token JWT"""
    if not authorization:
        raise HTTPException(401, "Token manquant")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(401, "Schéma d'authentification invalide")
        
        payload = decode_jwt_token(token)
        
        response = await httpx_client.get(
            f"{SUPABASE_URL}/rest/v1/users?id=eq.{payload['user_id']}&select=*",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )
        
        if response.status_code != 200 or not response.json():
            raise HTTPException(401, "Utilisateur introuvable")
        
        return response.json()[0]
    
    except ValueError:
        raise HTTPException(401, "Format de token invalide")

async def verify_agent_token(x_agent_token: Optional[str] = Header(None)) -> bool:
    """Vérifie le token agent"""
    if not x_agent_token or x_agent_token != AGENT_SECRET_TOKEN:
        raise HTTPException(401, "Token agent invalide")
    return True

# =====================================================
# ENDPOINTS - ROOT & HEALTH
# =====================================================

@app.get("/")
async def root():
    return {
        "service": "BaseGenspark API",
        "version": "2.1.0",
        "status": "operational",
        "features": {
            "authentication": "JWT + bcrypt",
            "rbac": "5 roles (ADMIN, INSTRUCTOR, STUDENT, ANALYST, AGENT)",
            "agent_endpoints": True,
            "rgpd_compliant": True
        },
        "endpoints": {
            "auth": ["/auth/register", "/auth/login", "/auth/me"],
            "logs": ["/logs", "/logs/{id}", "/logs/agent/{name}", "/logs/recent"],
            "stats": ["/stats"],
            "admin": ["/admin/users", "/admin/users/{id}/role"],
            "agents": ["/agent/session/start", "/agent/session/{id}", "/agent/session/{id}/end"]
        },
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    try:
        response = await httpx_client.get(
            f"{SUPABASE_URL}/rest/v1/users?select=count&limit=1",
            headers={"apikey": SUPABASE_KEY}
        )
        supabase_status = "connected" if response.status_code == 200 else "disconnected"
    except:
        supabase_status = "disconnected"
    
    return {
        "status": "healthy" if supabase_status == "connected" else "unhealthy",
        "supabase": supabase_status,
        "timestamp": datetime.utcnow().isoformat()
    }

# =====================================================
# ENDPOINTS - AUTH (garder l'existant)
# =====================================================

@app.post("/auth/register")
async def register(request: Request):
    data = await request.json()
    
    # Vérifier si l'email existe
    response = await httpx_client.get(
        f"{SUPABASE_URL}/rest/v1/users?email=eq.{data['email']}&select=id",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    )
    
    if response.status_code == 200 and response.json():
        raise HTTPException(400, "Email déjà utilisé")
    
    # Hash password
    hashed_password, salt = hash_password(data["password"])
    
    user_data = {
        "email": data["email"],
        "password_hash": hashed_password,
        "salt": salt,
        "name": data.get("name", data["email"].split("@")[0]),
        "role": data.get("role", "STUDENT"),
        "institution": data.get("institution"),
        "created_at": datetime.utcnow().isoformat()
    }
    
    response = await httpx_client.post(
        f"{SUPABASE_URL}/rest/v1/users",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        },
        json=user_data
    )
    
    if response.status_code != 201:
        raise HTTPException(500, "Erreur lors de la création de l'utilisateur")
    
    created_user = response.json()[0]
    token = create_jwt_token(created_user)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": created_user["id"],
            "email": created_user["email"],
            "name": created_user["name"],
            "role": created_user["role"]
        }
    }

@app.post("/auth/login")
async def login(request: Request):
    data = await request.json()
    
    response = await httpx_client.get(
        f"{SUPABASE_URL}/rest/v1/users?email=eq.{data['email']}&select=*",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    )
    
    if response.status_code != 200 or not response.json():
        raise HTTPException(401, "Email ou mot de passe incorrect")
    
    user = response.json()[0]
    
    if not verify_password(data["password"], user["password_hash"]):
        raise HTTPException(401, "Email ou mot de passe incorrect")
    
    # Enregistrer login
    await httpx_client.post(
        f"{SUPABASE_URL}/rest/v1/login_history",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "user_id": user["id"],
            "login_at": datetime.utcnow().isoformat()
        }
    )
    
    token = create_jwt_token(user)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "consent_given": user.get("consent_given"),
            "consent_date": user.get("consent_date"),
            "consent_version": user.get("consent_version"),
            "promotion": user.get("promotion"),
            "institution": user.get("institution"),
            "country": user.get("country"),
            "metadata": user.get("metadata", {}),
            "created_at": user.get("created_at"),
            "updated_at": user.get("updated_at"),
            "last_activity_at": user.get("last_activity_at"),
            "last_login_at": user.get("last_login_at"),
            "deleted_at": user.get("deleted_at"),
            "is_active": user.get("is_active", True)
        }
    }

# =====================================================
# ENDPOINTS - AGENTS PÉDAGOGIQUES (NOUVEAUX)
# =====================================================

@app.post("/agent/session/start")
async def agent_session_start(
    data: AgentSessionStart,
    _: bool = Depends(verify_agent_token)
):
    """
    Démarrer une nouvelle session pour un agent pédagogique
    Authentification : X-Agent-Token header
    """
    try:
        # 1. Trouver ou créer l'étudiant
        response = await httpx_client.get(
            f"{SUPABASE_URL}/rest/v1/users?email=eq.{data.student_email}&select=*",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        )
        
        if response.status_code == 200 and response.json():
            student = response.json()[0]
        else:
            # Créer l'étudiant
            temp_pwd = f"temp_{uuid.uuid4().hex[:8]}"
            hashed, salt = hash_password(temp_pwd)
            
            student_data = {
                "email": data.student_email,
                "password_hash": hashed,
                "salt": salt,
                "name": data.student_email.split("@")[0].title(),
                "role": "STUDENT",
                "institution": "Club Photo / Grande École",
                "created_at": datetime.utcnow().isoformat()
            }
            
            create_resp = await httpx_client.post(
                f"{SUPABASE_URL}/rest/v1/users",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=student_data
            )
            
            if create_resp.status_code != 201:
                raise HTTPException(500, "Impossible de créer l'étudiant")
            
            student = create_resp.json()[0]
        
        # 2. Générer session_id
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
        
        # 3. Créer la session dans user_activity
        session_data = {
            "session_id": session_id,
            "user_id": student["id"],
            "agent_name": data.agent_name,
            "status": "in_progress",
            "progression_current": 0,
            "progression_total": data.progression_total,
            "progression_label": data.progression_label or "Session démarrée",
            "metadata": data.metadata or {},
            "started_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        activity_resp = await httpx_client.post(
            f"{SUPABASE_URL}/rest/v1/user_activity",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            },
            json=session_data
        )
        
        if activity_resp.status_code != 201:
            raise HTTPException(500, "Impossible de créer la session")
        
        return {
            "success": True,
            "session_id": session_id,
            "user_id": student["id"],
            "student_name": student["name"],
            "message": f"Session créée pour {student['name']}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur: {str(e)}")

@app.patch("/agent/session/{session_id}")
async def agent_session_update(
    session_id: str,
    data: AgentSessionUpdate,
    _: bool = Depends(verify_agent_token)
):
    """
    Mettre à jour une session en cours
    Authentification : X-Agent-Token header
    """
    try:
        update_data = {}
        
        if data.progression_current is not None:
            update_data["progression_current"] = data.progression_current
        if data.progression_label is not None:
            update_data["progression_label"] = data.progression_label
        if data.resources_count is not None:
            update_data["resources_count"] = data.resources_count
        if data.metadata is not None:
            update_data["metadata"] = data.metadata
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        response = await httpx_client.patch(
            f"{SUPABASE_URL}/rest/v1/user_activity?session_id=eq.{session_id}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            },
            json=update_data
        )
        
        if response.status_code != 200 or not response.json():
            raise HTTPException(404, "Session introuvable")
        
        return {
            "success": True,
            "session": response.json()[0]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur: {str(e)}")

@app.post("/agent/session/{session_id}/end")
async def agent_session_end(
    session_id: str,
    data: AgentSessionEnd,
    _: bool = Depends(verify_agent_token)
):
    """
    Clôturer une session avec score et feedback
    Authentification : X-Agent-Token header
    """
    try:
        # Récupérer la session pour calculer la durée
        response = await httpx_client.get(
            f"{SUPABASE_URL}/rest/v1/user_activity?session_id=eq.{session_id}&select=started_at",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        )
        
        if response.status_code != 200 or not response.json():
            raise HTTPException(404, "Session introuvable")
        
        started_str = response.json()[0]["started_at"]
        started = datetime.fromisoformat(started_str.replace('Z', '+00:00').replace('+00:00', ''))
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
        
        update_resp = await httpx_client.patch(
            f"{SUPABASE_URL}/rest/v1/user_activity?session_id=eq.{session_id}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            },
            json=completion_data
        )
        
        if update_resp.status_code != 200 or not update_resp.json():
            raise HTTPException(404, "Session introuvable")
        
        return {
            "success": True,
            "session": update_resp.json()[0],
            "duration_minutes": duration
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur: {str(e)}")

# =====================================================
# STARTUP/SHUTDOWN
# =====================================================

@app.on_event("startup")
async def startup():
    print("🚀 BaseGenspark API v2.1 démarrée")
    print(f"📊 Supabase: {SUPABASE_URL}")
    print(f"🔐 JWT expiration: {JWT_EXPIRATION_HOURS}h")
    print(f"🤖 Agent endpoints: ACTIVÉS")

@app.on_event("shutdown")
async def shutdown():
    await httpx_client.aclose()
    print("🛑 BaseGenspark API v2.1 arrêtée")

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

