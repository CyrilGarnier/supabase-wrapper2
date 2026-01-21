"""
BaseGenspark API v4.0 - Version BÉTON
======================================

Date: 20 janvier 2026
Auteur: Cyril (Alkymya)

Fonctionnalités:
- Agents pédagogiques (création auto étudiant)
- Agent Superviseur (lecture + création étudiants)
- Planning (10 endpoints)
- Utilitaires (health, calendar)
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from routers import crm
import httpx
import os
from uuid import uuid4

# ========================================
# 📌 CONFIGURATION
# ========================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://iepvmuzfdkklysnqbvwt.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
AGENT_SECRET_TOKEN = os.getenv("AGENT_SECRET_TOKEN", "AGENT_TOKEN_PHOTOMENTOR_2026")

# JWT (pas encore utilisé mais prévu)
JWT_SECRET = os.getenv("JWT_SECRET", "basegenspark_secret_2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Client HTTP réutilisable
httpx_client = httpx.Client(timeout=30.0)

# ========================================
# 🚀 INITIALISATION FASTAPI
# ========================================

app = FastAPI(
    title="BaseGenspark API",
    version="4.0-BÉTON",
    description="API complète pour agents pédagogiques, superviseur et planning"
)

# CORS (pour accès frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Module CRM
app.include_router(crm.router)

# ========================================
# 🔐 SÉCURITÉ : Vérification token
# ========================================

def verify_agent_token(
    x_agent_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
) -> bool:
    """
    Vérifie le token d'authentification (header ou query param)
    """
    provided_token = x_agent_token or token
    if not provided_token or provided_token != AGENT_SECRET_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Token invalide ou manquant"
        )
    return True

# ========================================
# 📊 MODÈLES DE DONNÉES
# ========================================

# --- Agents pédagogiques ---

class AgentSessionStart(BaseModel):
    """Démarrer une session agent"""
    student_email: str = Field(..., description="Email de l'étudiant")
    student_name: Optional[str] = Field(None, description="Nom complet (créé auto si absent)")
    institution: str = Field("Alkymya", description="Établissement de l'étudiant")
    agent_name: str = Field(..., description="Nom de l'agent (PHOTOMENTOR, COACH_RH, etc.)")
    progression_total: int = Field(5, description="Nombre total d'étapes")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class AgentSessionUpdate(BaseModel):
    """Mettre à jour une session"""
    progression_current: Optional[int] = None
    progression_label: Optional[str] = None
    resources_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class AgentSessionEnd(BaseModel):
    """Terminer une session"""
    score: Optional[float] = Field(None, ge=0, le=100)
    strengths: Optional[List[str]] = None
    improvements: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

# --- Admin / Superviseur ---

class StudentCreate(BaseModel):
    """Créer un étudiant manuellement"""
    email: str
    full_name: str
    institution: str = "Club Photo"
    country: Optional[str] = None
    role: str = "STUDENT"

# --- Planning (modèles existants) ---

class SessionCreate(BaseModel):
    """Créer une session planning"""
    date: str
    horaire_debut: str
    horaire_fin: str
    etablissement_id: int
    module_id: int
    promotion_id: Optional[int] = None
    statut_id: int
    duree_reelle_h: Optional[float] = None
    duree_facturee_h: float
    tarif_ht_applique: float
    tva_pct_applique: int = 0
    ca_ht: float
    ca_ttc: float
    numero_session: Optional[str] = None
    annee_scolaire: Optional[str] = None
    notes: Optional[str] = None

class SessionUpdate(BaseModel):
    """Modifier une session planning"""
    date: Optional[str] = None
    horaire_debut: Optional[str] = None
    horaire_fin: Optional[str] = None
    etablissement_id: Optional[int] = None
    module_id: Optional[int] = None
    promotion_id: Optional[int] = None
    statut_id: Optional[int] = None
    duree_reelle_h: Optional[float] = None
    duree_facturee_h: Optional[float] = None
    tarif_ht_applique: Optional[float] = None
    tva_pct_applique: Optional[int] = None
    ca_ht: Optional[float] = None
    ca_ttc: Optional[float] = None
    numero_session: Optional[str] = None
    annee_scolaire: Optional[str] = None
    notes: Optional[str] = None

class ConflictResolve(BaseModel):
    """Résoudre un conflit"""
    resolution: str
    resolved_by: str


# ========================================
# 🏠 ENDPOINTS UTILITAIRES
# ========================================

@app.get("/")
def root():
    """Informations API + liste des endpoints"""
    return {
        "message": "BaseGenspark API v4.0-BÉTON",
        "status": "operational",
        "features": {
            "agent_endpoints": True,
            "admin_endpoints": True,
            "planning_endpoints": True,
            "calendar_view": True
        },
        "endpoints": {
            "agents": [
                "POST /agent/session/start",
                "PATCH /agent/session/{session_id}",
                "POST /agent/session/{session_id}/end"
            ],
            "admin": [
                "GET /admin/students",
                "POST /admin/students",
                "GET /admin/sessions"
            ],
            "planning": [
                "GET /planning/sessions",
                "POST /planning/sessions",
                "PATCH /planning/sessions/{id}",
                "DELETE /planning/sessions/{id}",
                "GET /planning/conflicts",
                "PATCH /planning/conflicts/{id}",
                "GET /planning/stats/ca",
                "GET /planning/weekly",
                "GET /planning/etablissements",
                "GET /planning/modules"
            ],
            "utils": [
                "GET /health",
                "GET /planning/calendar"
            ]
        }
    }

@app.get("/health")
def health_check():
    """Vérifier la connexion Supabase"""
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        response = httpx_client.get(
            f"{SUPABASE_URL}/rest/v1/users?select=count&limit=1",
            headers=headers
        )
        if response.status_code == 200:
            return {
                "status": "healthy",
                "supabase": "connected",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "unhealthy",
                "supabase": "error",
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "supabase": f"error: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


# ========================================
# 🤖 ENDPOINTS AGENTS PÉDAGOGIQUES
# ========================================

@app.post("/agent/session/start")
def agent_session_start(
    data: AgentSessionStart,
    _: bool = Depends(verify_agent_token)
):
    """
    Démarrer une session agent (PhotoMentor, Coach RH, etc.)
    
    FONCTIONNALITÉS :
    1. Vérifier si l'étudiant existe dans `students`
    2. SI NON → Créer automatiquement l'étudiant
    3. Créer la session dans `user_activity`
    
    Exemple :
    POST /agent/session/start?token=AGENT_TOKEN...
    {
        "student_email": "marie@example.com",
        "student_name": "Marie Dupont",
        "agent_name": "PHOTOMENTOR",
        "progression_total": 5
    }
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        # ========================================
        # ÉTAPE 1 : Vérifier si l'étudiant existe
        # ========================================
        
        students_response = httpx_client.get(
            f"{SUPABASE_URL}/rest/v1/students?email=eq.{data.student_email}",
            headers=headers
        )
        
        students = students_response.json()
        
        # ========================================
        # ÉTAPE 2 : Créer l'étudiant s'il n'existe pas
        # ========================================
        
        if not students:
            print(f"[INFO] Étudiant {data.student_email} non trouvé → Création automatique")
            
            new_student = {
                "email": data.student_email,
                "full_name": data.student_name or data.student_email.split('@')[0],
                "institution": data.institution,
                "role": "STUDENT",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            create_response = httpx_client.post(
                f"{SUPABASE_URL}/rest/v1/students",
                headers=headers,
                json=new_student
            )
            
            if create_response.status_code not in [200, 201]:
                raise HTTPException(
                    status_code=500,
                    detail=f"Erreur création étudiant : {create_response.text}"
                )
            
            # Récupérer l'étudiant créé
            students = create_response.json()
            if isinstance(students, list):
                student = students[0]
            else:
                student = students
            
            print(f"[SUCCESS] Étudiant créé : {student}")
        else:
            student = students[0]
            print(f"[INFO] Étudiant trouvé : {student['email']}")
        
        # ========================================
        # ÉTAPE 3 : Créer la session dans user_activity
        # ========================================
        
        # Générer session_id
        prefix = {
            "PHOTOMENTOR": "PHOTO",
            "COACH_RH": "COACH",
            "SODA_OPPORTUNITY": "SODA"
        }.get(data.agent_name.upper(), "AGENT")
        
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        student_prefix = data.student_email[:4].upper()
        unique_suffix = uuid4().hex[:4].upper()
        
        session_id = f"{prefix}-{timestamp}-{student_prefix}-{unique_suffix}"
        
        # Créer l'activité
        activity_data = {
            "session_id": session_id,
            "student_id": student["id"],
            "agent_name": data.agent_name,
            "status": "in_progress",
            "progression_current": 0,
            "progression_total": data.progression_total,
            "progression_label": "Démarrage...",
            "metadata": data.metadata or {},
            "started_at": datetime.utcnow().isoformat()
        }
        
        activity_response = httpx_client.post(
            f"{SUPABASE_URL}/rest/v1/user_activity",
            headers=headers,
            json=activity_data
        )
        
        if activity_response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur création session : {activity_response.text}"
            )
        
        activity = activity_response.json()
        if isinstance(activity, list):
            activity = activity[0]
        
        return {
            "success": True,
            "message": "Session démarrée avec succès",
            "session_id": session_id,
            "student": {
                "id": student["id"],
                "email": student["email"],
                "name": student.get("full_name", student["email"])
            },
            "agent_name": data.agent_name,
            "activity_id": activity.get("id")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/agent/session/{session_id}")
def agent_session_update(
    session_id: str,
    data: AgentSessionUpdate,
    _: bool = Depends(verify_agent_token)
):
    """
    Mettre à jour la progression d'une session
    
    Exemple :
    PATCH /agent/session/PHOTO-20260120-MARI-A3F2?token=AGENT_TOKEN...
    {
        "progression_current": 3,
        "progression_label": "Analyse de composition",
        "resources_count": 5
    }
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        # Préparer les données à mettre à jour
        update_data = {
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if data.progression_current is not None:
            update_data["progression_current"] = data.progression_current
        if data.progression_label is not None:
            update_data["progression_label"] = data.progression_label
        if data.resources_count is not None:
            update_data["resources_count"] = data.resources_count
        if data.metadata is not None:
            update_data["metadata"] = data.metadata
        
        # Mettre à jour dans Supabase
        response = httpx_client.patch(
            f"{SUPABASE_URL}/rest/v1/user_activity?session_id=eq.{session_id}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur mise à jour session : {response.text}"
            )
        
        return {
            "success": True,
            "message": "Session mise à jour",
            "session_id": session_id,
            "updated_fields": list(update_data.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/session/{session_id}/end")
def agent_session_end(
    session_id: str,
    data: AgentSessionEnd,
    _: bool = Depends(verify_agent_token)
):
    """
    Terminer une session agent
    
    Exemple :
    POST /agent/session/PHOTO-20260120-MARI-A3F2/end?token=AGENT_TOKEN...
    {
        "score": 85.5,
        "strengths": ["Bonne maîtrise de la composition", "Créativité"],
        "improvements": ["Gestion de la lumière"],
        "metadata": {"photos_analyzed": 12}
    }
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        # Récupérer la session pour calculer la durée
        get_response = httpx_client.get(
            f"{SUPABASE_URL}/rest/v1/user_activity?session_id=eq.{session_id}",
            headers=headers
        )
        
        sessions = get_response.json()
        if not sessions:
            raise HTTPException(status_code=404, detail="Session non trouvée")
        
        session = sessions[0]
        
        # Calculer la durée
        started_at = datetime.fromisoformat(session["started_at"].replace('Z', '+00:00'))
        completed_at = datetime.utcnow()
        duration_minutes = int((completed_at - started_at).total_seconds() / 60)
        
        # Préparer les données de fin
        end_data = {
            "status": "completed",
            "completed_at": completed_at.isoformat(),
            "duration_minutes": duration_minutes,
            "updated_at": completed_at.isoformat()
        }
        
        if data.score is not None:
            end_data["score"] = data.score
        if data.strengths is not None:
            end_data["strengths"] = data.strengths
        if data.improvements is not None:
            end_data["improvements"] = data.improvements
        if data.metadata is not None:
            # Fusionner avec metadata existant
            existing_metadata = session.get("metadata", {})
            end_data["metadata"] = {**existing_metadata, **data.metadata}
        
        # Mettre à jour dans Supabase
        response = httpx_client.patch(
            f"{SUPABASE_URL}/rest/v1/user_activity?session_id=eq.{session_id}",
            headers=headers,
            json=end_data
        )
        
        if response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur fin de session : {response.text}"
            )
        
        return {
            "success": True,
            "message": "Session terminée",
            "session_id": session_id,
            "duration_minutes": duration_minutes,
            "score": data.score,
            "completed_at": completed_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# 👨‍💼 ENDPOINTS ADMIN / SUPERVISEUR
# ========================================

@app.get("/admin/students")
def admin_list_students(
    limit: int = Query(100, description="Nombre max d'étudiants"),
    offset: int = Query(0, description="Décalage pour pagination"),
    _: bool = Depends(verify_agent_token)
):
    """
    Lister tous les étudiants
    
    Exemple :
    GET /admin/students?limit=50&token=AGENT_TOKEN...
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        
        response = httpx_client.get(
            f"{SUPABASE_URL}/rest/v1/students?select=*&order=created_at.desc&limit={limit}&offset={offset}",
            headers=headers
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur récupération étudiants : {response.text}"
            )
        
        students = response.json()
        
        return {
            "success": True,
            "count": len(students),
            "limit": limit,
            "offset": offset,
            "students": students
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/students")
def admin_create_student(
    data: StudentCreate,
    _: bool = Depends(verify_agent_token)
):
    """
    Créer un étudiant manuellement (Agent Superviseur)
    
    Exemple :
    POST /admin/students?token=AGENT_TOKEN...
    {
        "email": "nouveau@example.com",
        "full_name": "Nouveau Étudiant",
        "institution": "ISCOM Paris",
        "country": "FR"
    }
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        # Vérifier si l'email existe déjà
        check_response = httpx_client.get(
            f"{SUPABASE_URL}/rest/v1/students?email=eq.{data.email}",
            headers=headers
        )
        
        existing = check_response.json()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Un étudiant avec l'email {data.email} existe déjà"
            )
        
        # Créer l'étudiant
        new_student = {
            "email": data.email,
            "full_name": data.full_name,
            "institution": data.institution,
            "country": data.country,
            "role": data.role,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = httpx_client.post(
            f"{SUPABASE_URL}/rest/v1/students",
            headers=headers,
            json=new_student
        )
        
        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur création étudiant : {response.text}"
            )
        
        created = response.json()
        if isinstance(created, list):
            created = created[0]
        
        return {
            "success": True,
            "message": "Étudiant créé avec succès",
            "student": created
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/sessions")
def admin_list_sessions(
    limit: int = Query(100, description="Nombre max de sessions"),
    offset: int = Query(0, description="Décalage pour pagination"),
    status: Optional[str] = Query(None, description="Filtrer par statut (in_progress, completed, abandoned)"),
    agent_name: Optional[str] = Query(None, description="Filtrer par agent (PHOTOMENTOR, COACH_RH, etc.)"),
    _: bool = Depends(verify_agent_token)
):
    """
    Lister toutes les sessions pédagogiques
    
    Exemple :
    GET /admin/sessions?status=completed&limit=50&token=AGENT_TOKEN...
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        
        # Construire la requête avec filtres
        query = f"{SUPABASE_URL}/rest/v1/user_activity?select=*&order=started_at.desc&limit={limit}&offset={offset}"
        
        if status:
            query += f"&status=eq.{status}"
        if agent_name:
            query += f"&agent_name=eq.{agent_name}"
        
        response = httpx_client.get(query, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur récupération sessions : {response.text}"
            )
        
        sessions = response.json()
        
        return {
            "success": True,
            "count": len(sessions),
            "limit": limit,
            "offset": offset,
            "filters": {
                "status": status,
                "agent_name": agent_name
            },
            "sessions": sessions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# 📅 ENDPOINTS PLANNING
# ========================================

# --- 1. SESSIONS ---

@app.get("/planning/sessions")
def get_planning_sessions(
    date_start: str = Query(..., description="Date début (YYYY-MM-DD)"),
    date_end: str = Query(..., description="Date fin (YYYY-MM-DD)"),
    etablissement_id: Optional[int] = None,
    _: bool = Depends(verify_agent_token)
):
    """
    Récupérer sessions dans une plage de dates
    
    GET /planning/sessions?date_start=2026-01-19&date_end=2026-01-31&token=xxx
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        
        query = f"{SUPABASE_URL}/rest/v1/planning_sessions?date=gte.{date_start}&date=lte.{date_end}&select=*&order=date.asc,horaire_debut.asc"
        
        if etablissement_id:
            query += f"&etablissement_id=eq.{etablissement_id}"
        
        response = httpx_client.get(query, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur Supabase: {response.text}"
            )
        
        sessions = response.json()
        
        return {
            "success": True,
            "date_start": date_start,
            "date_end": date_end,
            "count": len(sessions),
            "sessions": sessions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/planning/sessions")
def create_planning_session(
    session: SessionCreate,
    _: bool = Depends(verify_agent_token)
):
    """
    Créer une nouvelle session planning
    
    POST /planning/sessions?token=xxx
    {
        "date": "2026-01-25",
        "horaire_debut": "09:00:00",
        "horaire_fin": "12:30:00",
        "etablissement_id": 1,
        "module_id": 1,
        ...
    }
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        response = httpx_client.post(
            f"{SUPABASE_URL}/rest/v1/planning_sessions",
            headers=headers,
            json=session.dict(exclude_none=True)
        )
        
        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur création: {response.text}"
            )
        
        created = response.json()
        if isinstance(created, list):
            created = created[0]
        
        return {
            "success": True,
            "message": "Session créée",
            "session": created
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/planning/sessions/{session_id}")
def update_planning_session(
    session_id: int,
    session: SessionUpdate,
    _: bool = Depends(verify_agent_token)
):
    """
    Mettre à jour une session planning
    
    PATCH /planning/sessions/123?token=xxx
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        response = httpx_client.patch(
            f"{SUPABASE_URL}/rest/v1/planning_sessions?id=eq.{session_id}",
            headers=headers,
            json=session.dict(exclude_none=True)
        )
        
        if response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur mise à jour: {response.text}"
            )
        
        return {
            "success": True,
            "message": "Session mise à jour"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/planning/sessions/{session_id}")
def delete_planning_session(
    session_id: int,
    _: bool = Depends(verify_agent_token)
):
    """
    Supprimer une session planning
    
    DELETE /planning/sessions/123?token=xxx
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        
        response = httpx_client.delete(
            f"{SUPABASE_URL}/rest/v1/planning_sessions?id=eq.{session_id}",
            headers=headers
        )
        
        if response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur suppression: {response.text}"
            )
        
        return {
            "success": True,
            "message": "Session supprimée"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 2. CONFLICTS ---

@app.get("/planning/conflicts")
def get_planning_conflicts(
    resolved: Optional[bool] = False,
    _: bool = Depends(verify_agent_token)
):
    """
    Récupérer les conflits de planning
    
    GET /planning/conflicts?resolved=false&token=xxx
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        
        query = f"{SUPABASE_URL}/rest/v1/planning_conflicts?select=*&order=detected_at.desc"
        
        if resolved is not None:
            query += f"&resolved=eq.{str(resolved).lower()}"
        
        response = httpx_client.get(query, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur Supabase: {response.text}"
            )
        
        conflicts = response.json()
        
        return {
            "success": True,
            "count": len(conflicts),
            "conflicts": conflicts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/planning/conflicts/{conflict_id}")
def resolve_planning_conflict(
    conflict_id: int,
    data: ConflictResolve,
    _: bool = Depends(verify_agent_token)
):
    """
    Résoudre un conflit de planning
    
    PATCH /planning/conflicts/5?token=xxx
    {
        "resolution": "Session décalée",
        "resolved_by": "cyril@alkymya.co"
    }
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        update_data = {
            "resolved": True,
            "resolution": data.resolution,
            "resolved_by": data.resolved_by,
            "resolved_at": datetime.utcnow().isoformat()
        }
        
        response = httpx_client.patch(
            f"{SUPABASE_URL}/rest/v1/planning_conflicts?id=eq.{conflict_id}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur résolution: {response.text}"
            )
        
        return {
            "success": True,
            "message": "Conflit résolu",
            "conflict_id": conflict_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 3. STATS & ANALYTICS ---

@app.get("/planning/stats/ca")
def get_ca_stats(
    month: Optional[str] = Query(None, description="Mois (YYYY-MM)"),
    year: Optional[int] = Query(None, description="Année (YYYY)"),
    _: bool = Depends(verify_agent_token)
):
    """
    Statistiques de chiffre d'affaires
    
    GET /planning/stats/ca?month=2026-01&token=xxx
    GET /planning/stats/ca?year=2026&token=xxx
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        
        query = f"{SUPABASE_URL}/rest/v1/planning_sessions?select=ca_ht,ca_ttc,date"
        
        if month:
            year_val, month_val = month.split("-")
            query += f"&date=gte.{year_val}-{month_val}-01"
            next_month = int(month_val) + 1 if int(month_val) < 12 else 1
            next_year = year_val if int(month_val) < 12 else str(int(year_val) + 1)
            query += f"&date=lt.{next_year}-{next_month:02d}-01"
        elif year:
            query += f"&date=gte.{year}-01-01&date=lt.{year+1}-01-01"
        
        response = httpx_client.get(query, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur Supabase: {response.text}"
            )
        
        sessions = response.json()
        
        ca_ht_total = sum(float(s.get("ca_ht", 0) or 0) for s in sessions)
        ca_ttc_total = sum(float(s.get("ca_ttc", 0) or 0) for s in sessions)
        
        return {
            "success": True,
            "period": month or str(year),
            "sessions_count": len(sessions),
            "ca_ht": round(ca_ht_total, 2),
            "ca_ttc": round(ca_ttc_total, 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/planning/weekly")
def get_weekly_planning(
    date: str = Query(..., description="Date de référence (YYYY-MM-DD)"),
    _: bool = Depends(verify_agent_token)
):
    """
    Planning hebdomadaire (semaine contenant la date fournie)
    
    GET /planning/weekly?date=2026-01-20&token=xxx
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        
        # Calculer début et fin de semaine
        ref_date = datetime.strptime(date, "%Y-%m-%d").date()
        week_start = ref_date - timedelta(days=ref_date.weekday())
        week_end = week_start + timedelta(days=6)
        
        query = f"{SUPABASE_URL}/rest/v1/planning_sessions?date=gte.{week_start.isoformat()}&date=lte.{week_end.isoformat()}&select=*&order=date.asc,horaire_debut.asc"
        
        response = httpx_client.get(query, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur Supabase: {response.text}"
            )
        
        sessions = response.json()
        
        return {
            "success": True,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "sessions_count": len(sessions),
            "sessions": sessions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 4. RÉFÉRENTIELS ---

@app.get("/planning/etablissements")
def get_etablissements(
    actif: Optional[bool] = True,
    _: bool = Depends(verify_agent_token)
):
    """
    Liste des établissements
    
    GET /planning/etablissements?actif=true&token=xxx
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        
        query = f"{SUPABASE_URL}/rest/v1/planning_etablissements?select=*&order=nom.asc"
        
        if actif is not None:
            query += f"&actif=eq.{str(actif).lower()}"
        
        response = httpx_client.get(query, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur Supabase: {response.text}"
            )
        
        etablissements = response.json()
        
        return {
            "success": True,
            "count": len(etablissements),
            "etablissements": etablissements
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/planning/modules")
def get_modules(
    etablissement_id: Optional[int] = None,
    actif: Optional[bool] = True,
    _: bool = Depends(verify_agent_token)
):
    """
    Liste des modules de formation
    
    GET /planning/modules?etablissement_id=1&actif=true&token=xxx
    """
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        
        query = f"{SUPABASE_URL}/rest/v1/planning_modules?select=*&order=nom.asc"
        
        if etablissement_id:
            query += f"&etablissement_id=eq.{etablissement_id}"
        
        if actif is not None:
            query += f"&actif=eq.{str(actif).lower()}"
        
        response = httpx_client.get(query, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur Supabase: {response.text}"
            )
        
        modules = response.json()
        
        return {
            "success": True,
            "count": len(modules),
            "modules": modules
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# 📆 ENDPOINT CALENDAR (Vue HTML)
# ========================================

@app.get("/planning/calendar", response_class=HTMLResponse)
def get_planning_calendar(
    date: Optional[str] = Query(default=None, description="Date de référence (YYYY-MM-DD)"),
    _: bool = Depends(verify_agent_token)
):
    """
    Afficher le calendrier planning en HTML
    
    GET /planning/calendar?date=2026-01-20&token=xxx
    """
    template_path = "templates/planning_calendar_view.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>404 - Template non trouvé</h1><p>Le fichier planning_calendar_view.html est introuvable.</p>",
            status_code=404
        )

# ========================================
# 🚀 RUN
# ========================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

