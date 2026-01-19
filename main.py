"""
=====================================================
BaseGenspark API - Version 2.0 avec Authentification
Fusionné : API existante + Sécurité RBAC
=====================================================
"""

import os
import httpx
import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any

# =====================================================
# CONFIGURATION
# =====================================================

SUPABASE_URL = "https://iepvmuzfdkklysnqbvwt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImllcHZtdXpmZGtrbHlzbnFidnd0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg3MTM0NDEsImV4cCI6MjA4NDI4OTQ0MX0.N_veJeUbrCVmW5eHMqCvMvwZb6LD-7cJ9NFa8aCGPIY"

JWT_SECRET = os.getenv("JWT_SECRET", "basegenspark_secret_2026_change_me_in_production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

ADMIN_EMAIL = "cyril@alkymya.co"

# =====================================================
# FASTAPI APP
# =====================================================

app = FastAPI(
    title="BaseGenspark API",
    version="2.0.0",
    description="API sécurisée pour agents Genspark avec authentification RBAC"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Client HTTP global
httpx_client = httpx.AsyncClient(timeout=30.0)

# =====================================================
# SÉCURITÉ : FONCTIONS UTILITAIRES
# =====================================================

def hash_password(password: str) -> tuple[str, str]:
    """Hashe un mot de passe avec bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
    return password_hash.decode('utf-8'), salt.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except:
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
    """Décode et vérifie un JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

async def get_current_user(authorization: Optional[str] = Header(None)):
    """Récupère l'utilisateur authentifié"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    payload = decode_jwt_token(token)
    
    response = await httpx_client.get(
        f"{SUPABASE_URL}/rest/v1/users",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        params={"id": f"eq.{payload['user_id']}"}
    )
    
    users = response.json()
    if not users:
        raise HTTPException(401, "User not found")
    
    user = users[0]
    if not user.get("is_active"):
        raise HTTPException(403, "Account disabled")
    
    return user

def require_role(*allowed_roles: str):
    """Décorateur pour vérifier les rôles"""
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                403,
                f"Insufficient permissions. Required: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

# =====================================================
# ROUTES : PAGE D'ACCUEIL
# =====================================================

@app.get("/")
async def root():
    """Page d'accueil de l'API"""
    return {
        "service": "BaseGenspark API",
        "version": "2.0.0",
        "status": "operational",
        "features": {
            "authentication": "JWT + bcrypt",
            "rbac": "5 roles (ADMIN, INSTRUCTOR, STUDENT, ANALYST, AGENT)",
            "rgpd_compliant": True
        },
        "endpoints": {
            "auth": ["/auth/register", "/auth/login", "/auth/me"],
            "logs": ["/logs", "/logs/{id}", "/logs/agent/{name}", "/logs/recent"],
            "stats": ["/stats"],
            "admin": ["/admin/users", "/admin/users/{id}/role"]
        },
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """Vérification de santé"""
    try:
        response = await httpx_client.get(
            f"{SUPABASE_URL}/rest/v1/users?limit=1",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            }
        )
        supabase_status = "connected" if response.status_code == 200 else "error"
    except:
        supabase_status = "unreachable"
    
    return {
        "status": "healthy",
        "supabase": supabase_status,
        "timestamp": datetime.utcnow().isoformat()
    }

# =====================================================
# ROUTES : AUTHENTIFICATION
# =====================================================

@app.post("/auth/register")
async def register_user(data: dict):
    """
    Inscription d'un nouvel utilisateur
    
    Body:
    {
      "email": "etudiant@example.com",
      "password": "MotDePasse123!",
      "name": "Alice Dupont",
      "role": "STUDENT",
      "promotion": "2025-2026"
    }
    """
    # Vérifier email unique
    check_response = await httpx_client.get(
        f"{SUPABASE_URL}/rest/v1/users",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        params={"email": f"eq.{data['email']}"}
    )
    
    if check_response.json():
        raise HTTPException(400, "Email already registered")
    
    # Hasher le mot de passe
    password_hash, password_salt = hash_password(data["password"])
    
    # Créer l'utilisateur
    user_data = {
        "email": data["email"],
        "password_hash": password_hash,
        "password_salt": password_salt,
        "name": data["name"],
        "role": data.get("role", "STUDENT"),
        "promotion": data.get("promotion"),
        "institution": data.get("institution", "Grande École"),
        "is_active": True,
        "consent_given": False
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
        raise HTTPException(500, "Failed to create user")
    
    new_user = response.json()[0]
    
    return {
        "success": True,
        "user_id": new_user["id"],
        "email": new_user["email"],
        "message": "User created successfully"
    }

@app.post("/auth/login")
async def login(data: dict):
    """
    Connexion utilisateur
    
    Body:
    {
      "email": "cyril@alkymya.co",
      "password": "AdminPass2026!"
    }
    """
    # Récupérer l'utilisateur
    response = await httpx_client.get(
        f"{SUPABASE_URL}/rest/v1/users",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        params={"email": f"eq.{data['email']}"}
    )
    
    users = response.json()
    if not users:
        raise HTTPException(401, "Invalid credentials")
    
    user = users[0]
    
    if not user.get("is_active"):
        raise HTTPException(403, "Account disabled")
    
    # Vérifier le mot de passe
    if not verify_password(data["password"], user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    
    # Mettre à jour last_login_at
    await httpx_client.patch(
        f"{SUPABASE_URL}/rest/v1/users",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        },
        params={"id": f"eq.{user['id']}"},
        json={"last_login_at": datetime.utcnow().isoformat()}
    )
    
    # Créer le JWT
    token = create_jwt_token(user)
    
    # Retourner sans les passwords
    safe_user = {k: v for k, v in user.items() if k not in ["password_hash", "password_salt"]}
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": safe_user
    }

@app.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Récupère les infos de l'utilisateur connecté"""
    safe_user = {k: v for k, v in current_user.items() if k not in ["password_hash", "password_salt"]}
    return safe_user

@app.post("/auth/consent")
async def accept_consent(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Accepter le consentement RGPD"""
    await httpx_client.patch(
        f"{SUPABASE_URL}/rest/v1/users",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        },
        params={"id": f"eq.{current_user['id']}"},
        json={
            "consent_given": True,
            "consent_date": datetime.utcnow().isoformat(),
            "consent_version": data.get("version", "v1.0")
        }
    )
    
    return {"success": True, "message": "Consent recorded"}

# =====================================================
# ROUTES : LOGS (PROTÉGÉES)
# =====================================================

@app.get("/logs")
async def read_logs(
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Lecture des logs (authentification requise)"""
    # STUDENT ne voit que ses propres logs
    params = {"limit": str(limit), "order": "timestamp.desc"}
    if current_user["role"] == "STUDENT":
        params["agent_name"] = f"eq.user:{current_user['id']}"
    
    response = await httpx_client.get(
        f"{SUPABASE_URL}/rest/v1/agent_logs",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        params=params
    )
    
    return {
        "success": True,
        "count": len(response.json()),
        "data": response.json()
    }

@app.post("/logs")
async def create_log(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Créer un log (tous les utilisateurs authentifiés)"""
    log_data = {
        "agent_name": data.get("agent_name"),
        "action": data.get("action"),
        "details": data.get("details", {})
    }
    
    response = await httpx_client.post(
        f"{SUPABASE_URL}/rest/v1/agent_logs",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        },
        json=log_data
    )
    
    if response.status_code == 201:
        return {"success": True, "data": response.json()[0]}
    else:
        raise HTTPException(500, "Failed to create log")

@app.get("/logs/recent")
async def get_recent_logs(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Logs récents"""
    params = {"limit": str(limit), "order": "timestamp.desc"}
    if current_user["role"] == "STUDENT":
        params["agent_name"] = f"eq.user:{current_user['id']}"
    
    response = await httpx_client.get(
        f"{SUPABASE_URL}/rest/v1/agent_logs",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        params=params
    )
    
    return {
        "success": True,
        "count": len(response.json()),
        "data": response.json()
    }

@app.get("/logs/agent/{agent_name}")
async def get_logs_by_agent(
    agent_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Logs d'un agent spécifique"""
    response = await httpx_client.get(
        f"{SUPABASE_URL}/rest/v1/agent_logs",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        params={"agent_name": f"eq.{agent_name}", "order": "timestamp.desc"}
    )
    
    return {
        "success": True,
        "agent_name": agent_name,
        "count": len(response.json()),
        "data": response.json()
    }

@app.get("/stats")
async def get_stats(current_user: dict = Depends(require_role("ADMIN", "INSTRUCTOR", "ANALYST"))):
    """Statistiques globales (ADMIN, INSTRUCTOR, ANALYST uniquement)"""
    response = await httpx_client.get(
        f"{SUPABASE_URL}/rest/v1/agent_logs?select=agent_name",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
    )
    
    logs = response.json()
    agent_counts = {}
    for log in logs:
        agent = log.get("agent_name", "unknown")
        agent_counts[agent] = agent_counts.get(agent, 0) + 1
    
    return {
        "success": True,
        "total_logs": len(logs),
        "unique_agents": len(agent_counts),
        "agents": agent_counts
    }

# =====================================================
# ROUTES : ADMINISTRATION (ADMIN UNIQUEMENT)
# =====================================================

@app.get("/admin/users")
async def list_users(admin: dict = Depends(require_role("ADMIN"))):
    """Liste tous les utilisateurs (ADMIN uniquement)"""
    response = await httpx_client.get(
        f"{SUPABASE_URL}/rest/v1/users",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
    )
    
    users = response.json()
    return [
        {k: v for k, v in user.items() if k not in ["password_hash", "password_salt"]}
        for user in users
    ]

@app.post("/admin/users/{user_id}/role")
async def change_role(
    user_id: str,
    data: dict,
    admin: dict = Depends(require_role("ADMIN"))
):
    """Change le rôle d'un utilisateur (ADMIN uniquement)"""
    new_role = data.get("role")
    if new_role not in ["ADMIN", "INSTRUCTOR", "STUDENT", "ANALYST", "AGENT"]:
        raise HTTPException(400, "Invalid role")
    
    response = await httpx_client.patch(
        f"{SUPABASE_URL}/rest/v1/users",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        },
        params={"id": f"eq.{user_id}"},
        json={"role": new_role}
    )
    
    return {"success": True, "message": f"Role changed to {new_role}"}

# =====================================================
# DÉMARRAGE
# =====================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
