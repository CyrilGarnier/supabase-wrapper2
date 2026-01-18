"""
Wrapper API pour BaseGenspark Supabase
Permet aux agents Genspark d'interagir avec la base de données
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
from supabase import create_client, Client
import uvicorn

# Configuration
SUPABASE_URL = "https://iepvmuzfdkklysnqbvwt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImllcHZtdXpmZGtrbHlzbnFidnd0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg3MTM0NDEsImV4cCI6MjA4NDI4OTQ0MX0.N_veJeUbrCVmW5eHMqCvMvwZb6LD-7cJ9NFa8aCGPIY"

# Initialisation
app = FastAPI(
    title="BaseGenspark Wrapper API",
    description="API wrapper pour agents Genspark → Supabase",
    version="1.0.0"
)

# CORS pour permettre les appels depuis n'importe où
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Client Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Modèles Pydantic
class AgentLog(BaseModel):
    agent_name: str = Field(..., description="Nom de l'agent")
    action: str = Field(..., description="Action effectuée")
    details: Optional[Dict[str, Any]] = Field(None, description="Détails JSON")

class AgentLogUpdate(BaseModel):
    agent_name: Optional[str] = None
    action: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

# Routes
@app.get("/")
async def root():
    """Page d'accueil avec documentation"""
    return {
        "service": "BaseGenspark Wrapper API",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "logs": "/logs - Lire tous les logs",
            "create": "POST /logs - Créer un log",
            "read": "GET /logs/{id} - Lire un log",
            "update": "PUT /logs/{id} - Mettre à jour",
            "delete": "DELETE /logs/{id} - Supprimer",
            "by_agent": "GET /logs/agent/{agent_name} - Logs par agent",
            "recent": "GET /logs/recent - Derniers logs"
        },
        "docs": "/docs - Documentation interactive"
    }

@app.get("/health")
async def health_check():
    """Vérification de santé de l'API"""
    try:
        # Test connexion Supabase
        result = supabase.table('agent_logs').select("id").limit(1).execute()
        return {
            "status": "healthy",
            "supabase": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/logs")
async def get_all_logs(
    limit: int = Query(100, description="Nombre maximum de résultats"),
    offset: int = Query(0, description="Offset pour pagination"),
    agent_name: Optional[str] = Query(None, description="Filtrer par agent")
):
    """Récupère tous les logs avec pagination et filtres"""
    try:
        query = supabase.table('agent_logs').select("*")
        
        if agent_name:
            query = query.eq('agent_name', agent_name)
        
        query = query.order('timestamp', desc=True).range(offset, offset + limit - 1)
        
        result = query.execute()
        
        return {
            "success": True,
            "count": len(result.data),
            "data": result.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/{log_id}")
async def get_log(log_id: int):
    """Récupère un log spécifique par ID"""
    try:
        result = supabase.table('agent_logs').select("*").eq('id', log_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Log non trouvé")
        
        return {
            "success": True,
            "data": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/logs")
async def create_log(log: AgentLog):
    """Crée un nouveau log"""
    try:
        result = supabase.table('agent_logs').insert({
            "agent_name": log.agent_name,
            "action": log.action,
            "details": log.details or {}
        }).execute()
        
        return {
            "success": True,
            "message": "Log créé avec succès",
            "data": result.data[0]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/logs/batch")
async def create_logs_batch(logs: List[AgentLog]):
    """Crée plusieurs logs en une seule requête"""
    try:
        logs_data = [
            {
                "agent_name": log.agent_name,
                "action": log.action,
                "details": log.details or {}
            }
            for log in logs
        ]
        
        result = supabase.table('agent_logs').insert(logs_data).execute()
        
        return {
            "success": True,
            "message": f"{len(result.data)} logs créés avec succès",
            "data": result.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/logs/{log_id}")
async def update_log(log_id: int, log: AgentLogUpdate):
    """Met à jour un log existant"""
    try:
        update_data = {}
        if log.agent_name is not None:
            update_data["agent_name"] = log.agent_name
        if log.action is not None:
            update_data["action"] = log.action
        if log.details is not None:
            update_data["details"] = log.details
        
        if not update_data:
            raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")
        
        result = supabase.table('agent_logs').update(update_data).eq('id', log_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Log non trouvé")
        
        return {
            "success": True,
            "message": "Log mis à jour avec succès",
            "data": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/logs/{log_id}")
async def delete_log(log_id: int):
    """Supprime un log"""
    try:
        result = supabase.table('agent_logs').delete().eq('id', log_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Log non trouvé")
        
        return {
            "success": True,
            "message": "Log supprimé avec succès",
            "data": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/agent/{agent_name}")
async def get_logs_by_agent(
    agent_name: str,
    limit: int = Query(100, description="Nombre maximum de résultats")
):
    """Récupère tous les logs d'un agent spécifique"""
    try:
        result = supabase.table('agent_logs')\
            .select("*")\
            .eq('agent_name', agent_name)\
            .order('timestamp', desc=True)\
            .limit(limit)\
            .execute()
        
        return {
            "success": True,
            "agent": agent_name,
            "count": len(result.data),
            "data": result.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/recent")
async def get_recent_logs(limit: int = Query(10, description="Nombre de logs à récupérer")):
    """Récupère les N logs les plus récents"""
    try:
        result = supabase.table('agent_logs')\
            .select("*")\
            .order('timestamp', desc=True)\
            .limit(limit)\
            .execute()
        
        return {
            "success": True,
            "count": len(result.data),
            "data": result.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Statistiques globales sur les logs"""
    try:
        # Total logs
        all_logs = supabase.table('agent_logs').select("agent_name").execute()
        
        # Comptage par agent
        agent_counts = {}
        for log in all_logs.data:
            agent = log['agent_name']
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
        
        return {
            "success": True,
            "total_logs": len(all_logs.data),
            "agents": agent_counts,
            "unique_agents": len(agent_counts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
