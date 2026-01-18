"""
Wrapper API pour BaseGenspark Supabase (version ultra-simplifiée)
Sans Pydantic, sans Supabase client - uniquement stdlib + FastAPI
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx

# Configuration Supabase
SUPABASE_URL = "https://iepvmuzfdkklysnqbvwt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImllcHZtdXpmZGtrbHlzbnFidnd0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg3MTM0NDEsImV4cCI6MjA4NDI4OTQ0MX0.N_veJeUbrCVmW5eHMqCvMvwZb6LD-7cJ9NFa8aCGPIY"

# Headers pour Supabase REST API
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Initialisation FastAPI
app = FastAPI(
    title="BaseGenspark Wrapper API",
    description="API wrapper pour agents Genspark → Supabase (ultra-simplifié)",
    version="1.2.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
@app.get("/")
async def root():
    """Page d'accueil avec documentation"""
    return {
        "service": "BaseGenspark Wrapper API",
        "status": "operational",
        "version": "1.2.0",
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
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/agent_logs?select=id&limit=1",
                headers=HEADERS,
                timeout=10.0
            )
            response.raise_for_status()
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
        url = f"{SUPABASE_URL}/rest/v1/agent_logs?select=*&order=timestamp.desc&limit={limit}&offset={offset}"
        
        if agent_name:
            url += f"&agent_name=eq.{agent_name}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=HEADERS, timeout=10.0)
            response.raise_for_status()
            data = response.json()
        
        return {
            "success": True,
            "count": len(data),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/{log_id}")
async def get_log(log_id: int):
    """Récupère un log spécifique par ID"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/agent_logs?id=eq.{log_id}",
                headers=HEADERS,
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
        
        if not data:
            raise HTTPException(status_code=404, detail="Log non trouvé")
        
        return {
            "success": True,
            "data": data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/logs")
async def create_log(log_data: Dict[str, Any]):
    """Crée un nouveau log"""
    try:
        # Validation simple
        if "agent_name" not in log_data or "action" not in log_data:
            raise HTTPException(
                status_code=400, 
                detail="Champs requis: agent_name, action"
            )
        
        payload = {
            "agent_name": log_data["agent_name"],
            "action": log_data["action"],
            "details": log_data.get("details", {})
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/agent_logs",
                headers=HEADERS,
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
        
        return {
            "success": True,
            "message": "Log créé avec succès",
            "data": data[0] if isinstance(data, list) else data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/logs/batch")
async def create_logs_batch(logs_data: List[Dict[str, Any]]):
    """Crée plusieurs logs en une seule requête"""
    try:
        payload = []
        for log in logs_data:
            if "agent_name" not in log or "action" not in log:
                raise HTTPException(
                    status_code=400,
                    detail="Chaque log doit avoir agent_name et action"
                )
            payload.append({
                "agent_name": log["agent_name"],
                "action": log["action"],
                "details": log.get("details", {})
            })
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/agent_logs",
                headers=HEADERS,
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
        
        return {
            "success": True,
            "message": f"{len(data)} logs créés avec succès",
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/logs/{log_id}")
async def update_log(log_id: int, update_data: Dict[str, Any]):
    """Met à jour un log existant"""
    try:
        if not update_data:
            raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{SUPABASE_URL}/rest/v1/agent_logs?id=eq.{log_id}",
                headers=HEADERS,
                json=update_data,
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
        
        if not data:
            raise HTTPException(status_code=404, detail="Log non trouvé")
        
        return {
            "success": True,
            "message": "Log mis à jour avec succès",
            "data": data[0] if isinstance(data, list) else data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/logs/{log_id}")
async def delete_log(log_id: int):
    """Supprime un log"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{SUPABASE_URL}/rest/v1/agent_logs?id=eq.{log_id}",
                headers=HEADERS,
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
        
        if not data:
            raise HTTPException(status_code=404, detail="Log non trouvé")
        
        return {
            "success": True,
            "message": "Log supprimé avec succès",
            "data": data[0] if isinstance(data, list) else data
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
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/agent_logs?agent_name=eq.{agent_name}&order=timestamp.desc&limit={limit}",
                headers=HEADERS,
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
        
        return {
            "success": True,
            "agent": agent_name,
            "count": len(data),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/recent")
async def get_recent_logs(limit: int = Query(10, description="Nombre de logs à récupérer")):
    """Récupère les N logs les plus récents"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/agent_logs?select=*&order=timestamp.desc&limit={limit}",
                headers=HEADERS,
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
        
        return {
            "success": True,
            "count": len(data),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Statistiques globales sur les logs"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/agent_logs?select=agent_name",
                headers=HEADERS,
                timeout=10.0
            )
            response.raise_for_status()
            all_logs = response.json()
        
        # Comptage par agent
        agent_counts = {}
        for log in all_logs:
            agent = log['agent_name']
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
        
        return {
            "success": True,
            "total_logs": len(all_logs),
            "agents": agent_counts,
            "unique_agents": len(agent_counts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
