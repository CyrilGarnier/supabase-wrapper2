"""
Module CRM pour BaseGenspark API
================================

Routes pour gérer:
- Prospects
- Opportunités
- Pipeline commercial
- Stats et alertes
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import httpx
import os

# ========================================
# CONFIGURATION
# ========================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://iepvmuzfdkklysnqbvwt.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Client HTTP
httpx_client = httpx.Client(timeout=30.0)

# Headers Supabase
def get_supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

# ========================================
# ROUTER
# ========================================

router = APIRouter(
    prefix="/crm",
    tags=["CRM"],
    responses={404: {"description": "Not found"}},
)

# ========================================
# MODÈLES DE DONNÉES
# ========================================

class ProspectCreate(BaseModel):
    """Créer un nouveau prospect"""
    nom: str
    entreprise: str
    poste: Optional[str] = None
    email: Optional[EmailStr] = None
    telephone: Optional[str] = None
    siren: Optional[str] = None
    siret: Optional[str] = None
    code_naf: Optional[str] = None
    forme_juridique: Optional[str] = None
    effectif: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    linkedin_url: Optional[str] = None
    source_contact: Optional[str] = None
    type_contact: Optional[str] = None
    offre_cible: Optional[str] = None
    secteur_activite: Optional[str] = None
    statut: Optional[str] = "Prise de contact"
    prochaine_action: Optional[str] = None
    date_prochaine_action: Optional[date] = None
    probabilite_closing: Optional[int] = Field(50, ge=0, le=100)
    montant_estime: Optional[float] = 0
    notes_internes: Optional[str] = None
    responsable_commercial: Optional[str] = "cyril@alkymya.co"

class ProspectUpdate(BaseModel):
    """Modifier un prospect"""
    nom: Optional[str] = None
    entreprise: Optional[str] = None
    poste: Optional[str] = None
    email: Optional[EmailStr] = None
    telephone: Optional[str] = None
    statut: Optional[str] = None
    prochaine_action: Optional[str] = None
    date_prochaine_action: Optional[date] = None
    probabilite_closing: Optional[int] = Field(None, ge=0, le=100)
    montant_estime: Optional[float] = None
    notes_internes: Optional[str] = None

class OpportuniteCreate(BaseModel):
    """Créer une opportunité"""
    prospect_id: str
    nom_opportunite: str
    type_offre: Optional[str] = None
    statut: Optional[str] = "Qualification"
    montant_ht: float
    probabilite_closing: int = Field(50, ge=0, le=100)
    financement_opco: bool = False
    montant_opco: float = 0
    date_cloture_prevue: Optional[date] = None
    prochaine_etape: Optional[str] = None
    notes: Optional[str] = None

class OpportuniteUpdate(BaseModel):
    """Modifier une opportunité"""
    statut: Optional[str] = None
    montant_ht: Optional[float] = None
    probabilite_closing: Optional[int] = Field(None, ge=0, le=100)
    financement_opco: Optional[bool] = None
    montant_opco: Optional[float] = None
    date_cloture_prevue: Optional[date] = None
    prochaine_etape: Optional[str] = None
    notes: Optional[str] = None

# ========================================
# ROUTES PROSPECTS
# ========================================

@router.get("/prospects")
async def list_prospects(
    statut: Optional[str] = Query(None, description="Filtrer par statut"),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Liste tous les prospects actifs
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/crm_v_prospects_actifs"
        params = {"limit": limit}
        
        if statut:
            params["statut"] = f"eq.{statut}"
        
        response = httpx_client.get(url, headers=get_supabase_headers(), params=params)
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "count": len(data),
            "prospects": data
        }
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")

@router.get("/prospects/search")
async def search_prospects(
    q: str = Query(..., description="Terme de recherche")
):
    """
    Recherche fulltext dans les prospects
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/rpc/crm_search_prospects"
        payload = {"query_text": q}
        
        response = httpx_client.post(url, headers=get_supabase_headers(), json=payload)
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "count": len(data),
            "prospects": data
        }
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")

@router.get("/prospects/{prospect_id}")
async def get_prospect(prospect_id: str):
    """
    Détails complets d'un prospect (avec opportunités, interactions, RDV)
    """
    try:
        # Récupérer le prospect
        url_prospect = f"{SUPABASE_URL}/rest/v1/crm_prospects"
        params = {"id": f"eq.{prospect_id}"}
        
        response = httpx_client.get(url_prospect, headers=get_supabase_headers(), params=params)
        response.raise_for_status()
        prospects = response.json()
        
        if not prospects:
            raise HTTPException(status_code=404, detail="Prospect non trouvé")
        
        prospect = prospects[0]
        
        # Récupérer les opportunités
        url_opps = f"{SUPABASE_URL}/rest/v1/crm_opportunites"
        params_opps = {"prospect_id": f"eq.{prospect_id}"}
        response_opps = httpx_client.get(url_opps, headers=get_supabase_headers(), params=params_opps)
        opportunites = response_opps.json() if response_opps.status_code == 200 else []
        
        # Récupérer les interactions
        url_inter = f"{SUPABASE_URL}/rest/v1/crm_interactions"
        params_inter = {"prospect_id": f"eq.{prospect_id}", "limit": "10"}
        response_inter = httpx_client.get(url_inter, headers=get_supabase_headers(), params=params_inter)
        interactions = response_inter.json() if response_inter.status_code == 200 else []
        
        # Récupérer les RDV
        url_rdv = f"{SUPABASE_URL}/rest/v1/crm_rendez_vous"
        params_rdv = {"prospect_id": f"eq.{prospect_id}"}
        response_rdv = httpx_client.get(url_rdv, headers=get_supabase_headers(), params=params_rdv)
        rendez_vous = response_rdv.json() if response_rdv.status_code == 200 else []
        
        return {
            "success": True,
            "prospect": {
                **prospect,
                "opportunites": opportunites,
                "interactions": interactions,
                "rendez_vous": rendez_vous
            }
        }
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")

@router.post("/prospects", status_code=201)
async def create_prospect(prospect: ProspectCreate):
    """
    Créer un nouveau prospect
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/crm_prospects"
        headers = {**get_supabase_headers(), "Prefer": "return=representation"}
        
        payload = prospect.dict(exclude_none=True)
        payload["date_dernier_echange"] = str(date.today())
        
        response = httpx_client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "message": "Prospect créé avec succès",
            "prospect": data[0] if isinstance(data, list) else data
        }
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")

@router.patch("/prospects/{prospect_id}")
async def update_prospect(prospect_id: str, updates: ProspectUpdate):
    """
    Modifier un prospect
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/crm_prospects"
        params = {"id": f"eq.{prospect_id}"}
        headers = {**get_supabase_headers(), "Prefer": "return=representation"}
        
        payload = updates.dict(exclude_none=True)
        
        # Mise à jour automatique de date_dernier_echange si statut change
        if "statut" in payload:
            payload["date_dernier_echange"] = str(date.today())
        
        response = httpx_client.patch(url, headers=headers, params=params, json=payload)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            raise HTTPException(status_code=404, detail="Prospect non trouvé")
        
        return {
            "success": True,
            "message": "Prospect mis à jour",
            "prospect": data[0] if isinstance(data, list) else data
        }
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")

# ========================================
# ROUTES OPPORTUNITÉS
# ========================================

@router.get("/opportunites")
async def list_opportunites(
    statut: Optional[str] = Query(None, description="Filtrer par statut")
):
    """
    Liste toutes les opportunités
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/crm_v_pipeline_opportunites"
        params = {}
        
        if statut:
            params["statut"] = f"eq.{statut}"
        
        response = httpx_client.get(url, headers=get_supabase_headers(), params=params)
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "count": len(data),
            "opportunites": data
        }
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")

@router.get("/pipeline")
async def get_pipeline():
    """
    Vue pipeline avec stats
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/crm_v_pipeline_opportunites"
        
        response = httpx_client.get(url, headers=get_supabase_headers())
        response.raise_for_status()
        opportunites = response.json()
        
        # Calculer les stats
        valeur_totale = sum(o.get("montant_ht", 0) for o in opportunites)
        valeur_ponderee = sum(o.get("valeur_ponderee", 0) for o in opportunites)
        taux_moyen = round(sum(o.get("probabilite_closing", 0) for o in opportunites) / len(opportunites)) if opportunites else 0
        
        # Grouper par statut
        par_statut = {}
        for opp in opportunites:
            statut = opp.get("statut", "Non défini")
            if statut not in par_statut:
                par_statut[statut] = {"count": 0, "valeur": 0, "valeur_ponderee": 0}
            par_statut[statut]["count"] += 1
            par_statut[statut]["valeur"] += opp.get("montant_ht", 0)
            par_statut[statut]["valeur_ponderee"] += opp.get("valeur_ponderee", 0)
        
        return {
            "success": True,
            "pipeline": {
                "total_opportunites": len(opportunites),
                "valeur_totale": valeur_totale,
                "valeur_ponderee": valeur_ponderee,
                "taux_conversion_moyen": taux_moyen,
                "par_statut": par_statut,
                "opportunites": opportunites
            }
        }
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")

@router.post("/opportunites", status_code=201)
async def create_opportunite(opportunite: OpportuniteCreate):
    """
    Créer une opportunité
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/crm_opportunites"
        headers = {**get_supabase_headers(), "Prefer": "return=representation"}
        
        payload = opportunite.dict(exclude_none=True)
        
        response = httpx_client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "message": "Opportunité créée",
            "opportunite": data[0] if isinstance(data, list) else data
        }
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")

@router.patch("/opportunites/{opportunite_id}")
async def update_opportunite(opportunite_id: str, updates: OpportuniteUpdate):
    """
    Modifier une opportunité
    """
    try:
        url = f"{SUPABASE_URL}/rest/v1/crm_opportunites"
        params = {"id": f"eq.{opportunite_id}"}
        headers = {**get_supabase_headers(), "Prefer": "return=representation"}
        
        payload = updates.dict(exclude_none=True)
        
        response = httpx_client.patch(url, headers=headers, params=params, json=payload)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            raise HTTPException(status_code=404, detail="Opportunité non trouvée")
        
        return {
            "success": True,
            "message": "Opportunité mise à jour",
            "opportunite": data[0] if isinstance(data, list) else data
        }
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")

# ========================================
# ROUTES STATS
# ========================================

@router.get("/stats")
async def get_stats():
    """
    Tableau de bord global
    """
    try:
        # Stats depuis la vue
        url_tableau = f"{SUPABASE_URL}/rest/v1/crm_v_tableau_bord"
        response_tableau = httpx_client.get(url_tableau, headers=get_supabase_headers())
        response_tableau.raise_for_status()
        tableau = response_tableau.json()[0] if response_tableau.json() else {}
        
        # Compter prospects
        url_prospects = f"{SUPABASE_URL}/rest/v1/crm_prospects?select=id"
        response_prospects = httpx_client.get(url_prospects, headers=get_supabase_headers())
        total_prospects = len(response_prospects.json()) if response_prospects.status_code == 200 else 0
        
        # Stats opportunités
        url_opps = f"{SUPABASE_URL}/rest/v1/crm_opportunites?select=montant_ht,probabilite_closing,statut"
        response_opps = httpx_client.get(url_opps, headers=get_supabase_headers())
        opportunites = response_opps.json() if response_opps.status_code == 200 else []
        
        valeur_totale = sum(o.get("montant_ht", 0) for o in opportunites)
        valeur_ponderee = sum(o.get("montant_ht", 0) * o.get("probabilite_closing", 0) / 100 for o in opportunites)
        en_cours = len([o for o in opportunites if o.get("statut") not in ["Gagné", "Perdu"]])
        
        return {
            "success": True,
            "stats": {
                "prospects": {
                    "total": total_prospects,
                    **tableau
                },
                "opportunites": {
                    "total": len(opportunites),
                    "en_cours": en_cours,
                    "valeur_totale": valeur_totale,
                    "valeur_ponderee": valeur_ponderee
                },
                "alertes": {
                    "relances_urgentes": tableau.get("nb_relances_urgentes", 0)
                }
            }
        }
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")

@router.get("/alertes")
async def get_alertes():
    """
    Prospects à relancer
    """
    try:
        today = str(date.today())
        
        # Actions en retard
        url_retard = f"{SUPABASE_URL}/rest/v1/crm_prospects"
        params_retard = {
            "date_prochaine_action": f"lt.{today}",
            "statut": f"not.in.(Gagné,Perdu)",
            "select": "id,entreprise,prochaine_action,date_prochaine_action"
        }
        response_retard = httpx_client.get(url_retard, headers=get_supabase_headers(), params=params_retard)
        actions_retard = response_retard.json() if response_retard.status_code == 200 else []
        
        alertes = []
        for p in actions_retard:
            jours_retard = (date.today() - datetime.strptime(p["date_prochaine_action"], "%Y-%m-%d").date()).days
            alertes.append({
                "type": "Action en retard",
                "prospect_id": p["id"],
                "entreprise": p["entreprise"],
                "prochaine_action": p["prochaine_action"],
                "date_prochaine_action": p["date_prochaine_action"],
                "jours_retard": jours_retard,
                "priorite": "Haute"
            })
        
        return {
            "success": True,
            "count": len(alertes),
            "alertes": alertes
        }
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")
