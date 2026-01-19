"""
BaseGenspark API v3.0 - FINAL with PLANNING Extension
Pedagogical tracking + Planning Management for AI Agents
"""
import os
import httpx
import bcrypt
import jwt
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, Header, Query
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

app = FastAPI(
    title="BaseGenspark API",
    version="3.0-FINAL",
    description="API complète pour suivi pédagogique et gestion de planning"
)
httpx_client = httpx.Client(timeout=30.0)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# MODELS - AGENTS PÉDAGOGIQUES
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
# MODELS - PLANNING
# ============================================================================
class SessionCreate(BaseModel):
    date: str  # YYYY-MM-DD
    horaire_debut: str  # HH:MM
    horaire_fin: str  # HH:MM
    etablissement_id: Optional[int] = None
    module_id: Optional[int] = None
    promotion_id: Optional[int] = None
    statut_id: int = 3  # PLANIFIE par défaut
    duree_reelle_h: Optional[float] = None
    duree_facturee_h: Optional[float] = None
    tarif_ht_applique: Optional[float] = None
    tva_pct_applique: int = 0
    notes: Optional[str] = None

class SessionUpdate(BaseModel):
    date: Optional[str] = None
    horaire_debut: Optional[str] = None
    horaire_fin: Optional[str] = None
    statut_id: Optional[int] = None
    notes: Optional[str] = None

class ConflictResolve(BaseModel):
    resolution_status: str  # ACKNOWLEDGED, RESOLVED, IGNORED
    resolved_by: str
    resolution_notes: Optional[str] = None

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

def supabase_request(
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None
) -> httpx.Response:
    """Requête générique Supabase REST API"""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    if method == "GET":
        return httpx_client.get(url, headers=headers, params=params)
    elif method == "POST":
        return httpx_client.post(url, headers=headers, json=data)
    elif method == "PATCH":
        return httpx_client.patch(url, headers=headers, json=data, params=params)
    elif method == "DELETE":
        return httpx_client.delete(url, headers=headers, params=params)
    
    raise ValueError(f"Method {method} not supported")

# ============================================================================
# ENDPOINTS - ROOT & HEALTH
# ============================================================================
@app.get("/")
async def root():
    return {
        "message": "BaseGenspark API v3.0-FINAL",
        "status": "operational",
        "features": {
            "agent_endpoints": True,
            "planning_endpoints": True
        },
        "endpoints": {
            "agents": [
                "/agent/session/start",
                "/agent/session/update",
                "/agent/session/end"
            ],
            "planning": [
                "/planning/sessions",
                "/planning/conflicts",
                "/planning/stats/ca",
                "/planning/weekly",
                "/planning/etablissements",
                "/planning/modules"
            ]
        }
    }

@app.get("/health")
async def health():
    try:
        response = httpx_client.get(
            f"{SUPABASE_URL}/rest/v1/users?select=count",
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
# ENDPOINTS - AGENTS PÉDAGOGIQUES
# ============================================================================
@app.post("/agent/session/start")
async def agent_session_start(
    data: AgentSessionStart,
    _: bool = Depends(verify_agent_token)
):
    """
    Démarrer une session agent pour un étudiant
    """
    try:
        # Vérifier si l'étudiant existe
        user_response = supabase_request(
            "GET",
            "users",
            params={"email": f"eq.{data.student_email}", "select": "id,email,full_name"}
        )
        
        users = user_response.json()
        if not users:
            raise HTTPException(status_code=404, detail="Étudiant non trouvé")
        
        user = users[0]
        user_id = user["id"]
        
        # Générer session_id
        session_id = f"{data.agent_name.upper()}-{datetime.utcnow().strftime('%Y%m%d')}-{user_id[:8].upper()}"
        
        # Créer session dans user_activity
        activity_data = {
            "session_id": session_id,
            "user_id": user_id,
            "agent_name": data.agent_name,
            "started_at": datetime.utcnow().isoformat(),
            "status": "in_progress",
            "progression_total": data.progression_total,
            "progression_current": 0,
            "progression_label": data.progression_label or "Démarrage...",
            "metadata": data.metadata or {}
        }
        
        response = supabase_request("POST", "user_activity", data=activity_data)
        
        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur création session: {response.text}"
            )
        
        created_session = response.json()[0] if isinstance(response.json(), list) else response.json()
        
        return {
            "success": True,
            "session_id": session_id,
            "student": {
                "id": user_id,
                "email": user["email"],
                "name": user["full_name"]
            },
            "agent_name": data.agent_name,
            "activity_id": created_session.get("id")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/agent/session/update")
async def agent_session_update(
    session_id: str,
    data: AgentSessionUpdate,
    _: bool = Depends(verify_agent_token)
):
    """
    Mettre à jour une session agent en cours
    """
    try:
        update_data = {}
        
        if data.progression_current is not None:
            update_data["progression_current"] = data.progression_current
        
        if data.progression_label:
            update_data["progression_label"] = data.progression_label
        
        if data.resources_count is not None:
            update_data["resources_count"] = data.resources_count
        
        if data.metadata:
            update_data["metadata"] = data.metadata
        
        if not update_data:
            raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")
        
        response = supabase_request(
            "PATCH",
            "user_activity",
            data=update_data,
            params={"session_id": f"eq.{session_id}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur mise à jour: {response.text}"
            )
        
        return {
            "success": True,
            "session_id": session_id,
            "updated": update_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/session/end")
async def agent_session_end(
    session_id: str,
    data: AgentSessionEnd,
    _: bool = Depends(verify_agent_token)
):
    """
    Terminer une session agent
    """
    try:
        update_data = {
            "completed_at": datetime.utcnow().isoformat(),
            "status": "completed"
        }
        
        if data.score is not None:
            update_data["score"] = data.score
            update_data["completion_rate"] = min(data.score / 100, 1.0)
        
        if data.strengths:
            update_data["strengths"] = data.strengths
        
        if data.improvements:
            update_data["improvements"] = data.improvements
        
        if data.metadata:
            update_data["metadata"] = data.metadata
        
        response = supabase_request(
            "PATCH",
            "user_activity",
            data=update_data,
            params={"session_id": f"eq.{session_id}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur finalisation: {response.text}"
            )
        
        return {
            "success": True,
            "session_id": session_id,
            "status": "completed",
            "score": data.score
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINTS - PLANNING
# ============================================================================

# --- 1. SESSIONS ---
@app.get("/planning/sessions")
async def get_planning_sessions(
    date_start: str = Query(..., description="Date début (YYYY-MM-DD)"),
    date_end: str = Query(..., description="Date fin (YYYY-MM-DD)"),
    etablissement_id: Optional[int] = None,
    statut_code: Optional[str] = None,
    _: bool = Depends(verify_agent_token)
):
    """
    Récupérer sessions dans une plage de dates
    
    GET /planning/sessions?date_start=2026-01-19&date_end=2026-01-31&token=xxx
    """
    try:
        # Construction des filtres
        params = {
            "date": f"gte.{date_start}",
            "date": f"lte.{date_end}",
            "select": "*",
            "order": "date.asc,horaire_debut.asc"
        }
        
        if etablissement_id:
            params["etablissement_id"] = f"eq.{etablissement_id}"
        
        response = supabase_request("GET", "planning_sessions", params=params)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
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
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/planning/sessions")
async def create_planning_session(
    session: SessionCreate,
    _: bool = Depends(verify_agent_token)
):
    """
    Créer une nouvelle session
    
    POST /planning/sessions
    {
        "date": "2026-01-25",
        "horaire_debut": "09:00",
        "horaire_fin": "12:30",
        "etablissement_id": 1,
        "module_id": 1,
        "promotion_id": 1,
        "duree_facturee_h": 3.5,
        "tarif_ht_applique": 75.00
    }
    """
    try:
        response = supabase_request(
            "POST",
            "planning_sessions",
            data=session.dict(exclude_none=True)
        )
        
        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur création: {response.text}"
            )
        
        created_session = response.json()[0] if isinstance(response.json(), list) else response.json()
        
        return {
            "success": True,
            "message": "Session créée avec succès",
            "session": created_session
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/planning/sessions/{session_id}")
async def update_planning_session(
    session_id: int,
    session: SessionUpdate,
    _: bool = Depends(verify_agent_token)
):
    """
    Mettre à jour une session
    
    PATCH /planning/sessions/{session_id}
    """
    try:
        response = supabase_request(
            "PATCH",
            "planning_sessions",
            data=session.dict(exclude_none=True),
            params={"id": f"eq.{session_id}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur mise à jour: {response.text}"
            )
        
        updated_session = response.json()[0] if response.json() else {}
        
        return {
            "success": True,
            "message": "Session mise à jour",
            "session": updated_session
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/planning/sessions/{session_id}")
async def delete_planning_session(
    session_id: int,
    _: bool = Depends(verify_agent_token)
):
    """
    Supprimer une session
    
    DELETE /planning/sessions/{session_id}
    """
    try:
        response = supabase_request(
            "DELETE",
            "planning_sessions",
            params={"id": f"eq.{session_id}"}
        )
        
        if response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur suppression: {response.text}"
            )
        
        return {
            "success": True,
            "message": "Session supprimée"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 2. CONFLICTS ---
@app.get("/planning/conflicts")
async def get_planning_conflicts(
    resolved: Optional[bool] = False,
    _: bool = Depends(verify_agent_token)
):
    """
    Récupérer les conflits de planning
    
    GET /planning/conflicts?resolved=false&token=xxx
    """
    try:
        params = {
            "select": "*",
            "order": "detected_at.desc"
        }
        
        if resolved is not None:
            if resolved:
                params["resolved_at"] = "not.is.null"
            else:
                params["resolved_at"] = "is.null"
        
        response = supabase_request("GET", "planning_conflicts", params=params)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Supabase: {response.text}"
            )
        
        conflicts = response.json()
        
        return {
            "success": True,
            "count": len(conflicts),
            "conflicts": conflicts
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/planning/conflicts/{conflict_id}")
async def resolve_planning_conflict(
    conflict_id: int,
    data: ConflictResolve,
    _: bool = Depends(verify_agent_token)
):
    """
    Résoudre un conflit de planning
    
    PATCH /planning/conflicts/{conflict_id}
    {
        "resolution_status": "RESOLVED",
        "resolved_by": "cyril@alkymya.co",
        "resolution_notes": "Session HETIC décalée à 14h"
    }
    """
    try:
        update_data = {
            "resolution_status": data.resolution_status,
            "resolved_by": data.resolved_by,
            "resolved_at": datetime.utcnow().isoformat(),
            "resolution_notes": data.resolution_notes
        }
        
        response = supabase_request(
            "PATCH",
            "planning_conflicts",
            data=update_data,
            params={"id": f"eq.{conflict_id}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur résolution: {response.text}"
            )
        
        return {
            "success": True,
            "message": "Conflit résolu",
            "conflict_id": conflict_id
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 3. STATS & ANALYTICS ---
@app.get("/planning/stats/ca")
async def get_ca_stats(
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
        params = {"select": "ca_ht,ca_ttc,date"}
        
        if month:
            # Format: 2026-01
            year_month = month.split("-")
            params["date"] = f"gte.{year_month[0]}-{year_month[1]}-01"
            params["date"] = f"lt.{year_month[0]}-{int(year_month[1])+1:02d}-01"
        elif year:
            params["date"] = f"gte.{year}-01-01"
            params["date"] = f"lt.{year+1}-01-01"
        
        response = supabase_request("GET", "planning_sessions", params=params)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
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
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/planning/weekly")
async def get_weekly_planning(
    date: str = Query(..., description="Date de référence (YYYY-MM-DD)"),
    _: bool = Depends(verify_agent_token)
):
    """
    Planning hebdomadaire (semaine contenant la date fournie)
    
    GET /planning/weekly?date=2026-01-20&token=xxx
    """
    try:
        # Calculer début et fin de semaine
        ref_date = datetime.strptime(date, "%Y-%m-%d").date()
        week_start = ref_date - timedelta(days=ref_date.weekday())
        week_end = week_start + timedelta(days=6)
        
        params = {
            "date": f"gte.{week_start.isoformat()}",
            "date": f"lte.{week_end.isoformat()}",
            "select": "*",
            "order": "date.asc,horaire_debut.asc"
        }
        
        response = supabase_request("GET", "planning_sessions", params=params)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
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
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 4. RÉFÉRENTIELS ---
@app.get("/planning/etablissements")
async def get_etablissements(
    actif: Optional[bool] = True,
    _: bool = Depends(verify_agent_token)
):
    """
    Liste des établissements
    
    GET /planning/etablissements?actif=true&token=xxx
    """
    try:
        params = {"select": "*", "order": "nom.asc"}
        
        if actif is not None:
            params["actif"] = f"eq.{str(actif).lower()}"
        
        response = supabase_request("GET", "planning_etablissements", params=params)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Supabase: {response.text}"
            )
        
        etablissements = response.json()
        
        return {
            "success": True,
            "count": len(etablissements),
            "etablissements": etablissements
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/planning/modules")
async def get_modules(
    etablissement_id: Optional[int] = None,
    actif: Optional[bool] = True,
    _: bool = Depends(verify_agent_token)
):
    """
    Liste des modules de formation
    
    GET /planning/modules?etablissement_id=1&actif=true&token=xxx
    """
    try:
        params = {"select": "*", "order": "nom.asc"}
        
        if etablissement_id:
            params["etablissement_id"] = f"eq.{etablissement_id}"
        
        if actif is not None:
            params["actif"] = f"eq.{str(actif).lower()}"
        
        response = supabase_request("GET", "planning_modules", params=params)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur Supabase: {response.text}"
            )
        
        modules = response.json()
        
        return {
            "success": True,
            "count": len(modules),
            "modules": modules
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# RUN
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
