 1	"""
     2	Module CRM pour BaseGenspark API
     3	================================
     4	
     5	Routes pour gérer:
     6	- Prospects
     7	- Opportunités
     8	- Pipeline commercial
     9	- Stats et alertes
    10	"""
    11	
    12	from fastapi import APIRouter, HTTPException, Depends, Query
    13	from pydantic import BaseModel, Field, EmailStr
    14	from typing import Optional, List, Dict, Any
    15	from datetime import datetime, date
    16	import httpx
    17	import os
    18	
    19	# ========================================
    20	# CONFIGURATION
    21	# ========================================
    22	
    23	SUPABASE_URL = os.getenv("SUPABASE_URL", "https://iepvmuzfdkklysnqbvwt.supabase.co")
    24	SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    25	
    26	# Client HTTP
    27	httpx_client = httpx.Client(timeout=30.0)
    28	
    29	# Headers Supabase
    30	def get_supabase_headers():
    31	    return {
    32	        "apikey": SUPABASE_KEY,
    33	        "Authorization": f"Bearer {SUPABASE_KEY}",
    34	        "Content-Type": "application/json"
    35	    }
    36	
    37	# ========================================
    38	# ROUTER
    39	# ========================================
    40	
    41	router = APIRouter(
    42	    prefix="/crm",
    43	    tags=["CRM"],
    44	    responses={404: {"description": "Not found"}},
    45	)
    46	
    47	# ========================================
    48	# MODÈLES DE DONNÉES
    49	# ========================================
    50	
    51	class ProspectCreate(BaseModel):
    52	    """Créer un nouveau prospect"""
    53	    nom: str
    54	    entreprise: str
    55	    poste: Optional[str] = None
    56	    email: Optional[EmailStr] = None
    57	    telephone: Optional[str] = None
    58	    siren: Optional[str] = None
    59	    siret: Optional[str] = None
    60	    code_naf: Optional[str] = None
    61	    forme_juridique: Optional[str] = None
    62	    effectif: Optional[str] = None
    63	    adresse: Optional[str] = None
    64	    code_postal: Optional[str] = None
    65	    ville: Optional[str] = None
    66	    linkedin_url: Optional[str] = None
    67	    source_contact: Optional[str] = None
    68	    type_contact: Optional[str] = None
    69	    offre_cible: Optional[str] = None
    70	    secteur_activite: Optional[str] = None
    71	    statut: Optional[str] = "Prise de contact"
    72	    prochaine_action: Optional[str] = None
    73	    date_prochaine_action: Optional[date] = None
    74	    probabilite_closing: Optional[int] = Field(50, ge=0, le=100)
    75	    montant_estime: Optional[float] = 0
    76	    notes_internes: Optional[str] = None
    77	    responsable_commercial: Optional[str] = "cyril@alkymya.co"
    78	
    79	class ProspectUpdate(BaseModel):
    80	    """Modifier un prospect"""
    81	    nom: Optional[str] = None
    82	    entreprise: Optional[str] = None
    83	    poste: Optional[str] = None
    84	    email: Optional[EmailStr] = None
    85	    telephone: Optional[str] = None
    86	    statut: Optional[str] = None
    87	    prochaine_action: Optional[str] = None
    88	    date_prochaine_action: Optional[date] = None
    89	    probabilite_closing: Optional[int] = Field(None, ge=0, le=100)
    90	    montant_estime: Optional[float] = None
    91	    notes_internes: Optional[str] = None
    92	
    93	class OpportuniteCreate(BaseModel):
    94	    """Créer une opportunité"""
    95	    prospect_id: str
    96	    nom_opportunite: str
    97	    type_offre: Optional[str] = None
    98	    statut: Optional[str] = "Qualification"
    99	    montant_ht: float
   100	    probabilite_closing: int = Field(50, ge=0, le=100)
   101	    financement_opco: bool = False
   102	    montant_opco: float = 0
   103	    date_cloture_prevue: Optional[date] = None
   104	    prochaine_etape: Optional[str] = None
   105	    notes: Optional[str] = None
   106	
   107	class OpportuniteUpdate(BaseModel):
   108	    """Modifier une opportunité"""
   109	    statut: Optional[str] = None
   110	    montant_ht: Optional[float] = None
   111	    probabilite_closing: Optional[int] = Field(None, ge=0, le=100)
   112	    financement_opco: Optional[bool] = None
   113	    montant_opco: Optional[float] = None
   114	    date_cloture_prevue: Optional[date] = None
   115	    prochaine_etape: Optional[str] = None
   116	    notes: Optional[str] = None
   117	
   118	# ========================================
   119	# ROUTES PROSPECTS
   120	# ========================================
   121	
   122	@router.get("/prospects")
   123	async def list_prospects(
   124	    statut: Optional[str] = Query(None, description="Filtrer par statut"),
   125	    limit: int = Query(100, ge=1, le=500)
   126	):
   127	    """
   128	    Liste tous les prospects actifs
   129	    """
   130	    try:
   131	        url = f"{SUPABASE_URL}/rest/v1/crm_v_prospects_actifs"
   132	        params = {"limit": limit}
   133	        
   134	        if statut:
   135	            params["statut"] = f"eq.{statut}"
   136	        
   137	        response = httpx_client.get(url, headers=get_supabase_headers(), params=params)
   138	        response.raise_for_status()
   139	        data = response.json()
   140	        
   141	        return {
   142	            "success": True,
   143	            "count": len(data),
   144	            "prospects": data
   145	        }
   146	    
   147	    except httpx.HTTPError as e:
   148	        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")
   149	
   150	@router.get("/prospects/search")
   151	async def search_prospects(
   152	    q: str = Query(..., description="Terme de recherche")
   153	):
   154	    """
   155	    Recherche fulltext dans les prospects
   156	    """
   157	    try:
   158	        url = f"{SUPABASE_URL}/rest/v1/rpc/crm_search_prospects"
   159	        payload = {"query_text": q}
   160	        
   161	        response = httpx_client.post(url, headers=get_supabase_headers(), json=payload)
   162	        response.raise_for_status()
   163	        data = response.json()
   164	        
   165	        return {
   166	            "success": True,
   167	            "count": len(data),
   168	            "prospects": data
   169	        }
   170	    
   171	    except httpx.HTTPError as e:
   172	        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")
   173	
   174	@router.get("/prospects/{prospect_id}")
   175	async def get_prospect(prospect_id: str):
   176	    """
   177	    Détails complets d'un prospect (avec opportunités, interactions, RDV)
   178	    """
   179	    try:
   180	        # Récupérer le prospect
   181	        url_prospect = f"{SUPABASE_URL}/rest/v1/crm_prospects"
   182	        params = {"id": f"eq.{prospect_id}"}
   183	        
   184	        response = httpx_client.get(url_prospect, headers=get_supabase_headers(), params=params)
   185	        response.raise_for_status()
   186	        prospects = response.json()
   187	        
   188	        if not prospects:
   189	            raise HTTPException(status_code=404, detail="Prospect non trouvé")
   190	        
   191	        prospect = prospects[0]
   192	        
   193	        # Récupérer les opportunités
   194	        url_opps = f"{SUPABASE_URL}/rest/v1/crm_opportunites"
   195	        params_opps = {"prospect_id": f"eq.{prospect_id}"}
   196	        response_opps = httpx_client.get(url_opps, headers=get_supabase_headers(), params=params_opps)
   197	        opportunites = response_opps.json() if response_opps.status_code == 200 else []
   198	        
   199	        # Récupérer les interactions
   200	        url_inter = f"{SUPABASE_URL}/rest/v1/crm_interactions"
   201	        params_inter = {"prospect_id": f"eq.{prospect_id}", "limit": "10"}
   202	        response_inter = httpx_client.get(url_inter, headers=get_supabase_headers(), params=params_inter)
   203	        interactions = response_inter.json() if response_inter.status_code == 200 else []
   204	        
   205	        # Récupérer les RDV
   206	        url_rdv = f"{SUPABASE_URL}/rest/v1/crm_rendez_vous"
   207	        params_rdv = {"prospect_id": f"eq.{prospect_id}"}
   208	        response_rdv = httpx_client.get(url_rdv, headers=get_supabase_headers(), params=params_rdv)
   209	        rendez_vous = response_rdv.json() if response_rdv.status_code == 200 else []
   210	        
   211	        return {
   212	            "success": True,
   213	            "prospect": {
   214	                **prospect,
   215	                "opportunites": opportunites,
   216	                "interactions": interactions,
   217	                "rendez_vous": rendez_vous
   218	            }
   219	        }
   220	    
   221	    except httpx.HTTPError as e:
   222	        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")
   223	
   224	@router.post("/prospects", status_code=201)
   225	async def create_prospect(prospect: ProspectCreate):
   226	    """
   227	    Créer un nouveau prospect
   228	    """
   229	    try:
   230	        url = f"{SUPABASE_URL}/rest/v1/crm_prospects"
   231	        headers = {**get_supabase_headers(), "Prefer": "return=representation"}
   232	        
   233	        payload = prospect.dict(exclude_none=True)
   234	        payload["date_dernier_echange"] = str(date.today())
   235	        
   236	        response = httpx_client.post(url, headers=headers, json=payload)
   237	        response.raise_for_status()
   238	        data = response.json()
   239	        
   240	        return {
   241	            "success": True,
   242	            "message": "Prospect créé avec succès",
   243	            "prospect": data[0] if isinstance(data, list) else data
   244	        }
   245	    
   246	    except httpx.HTTPError as e:
   247	        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")
   248	
   249	@router.patch("/prospects/{prospect_id}")
   250	async def update_prospect(prospect_id: str, updates: ProspectUpdate):
   251	    """
   252	    Modifier un prospect
   253	    """
   254	    try:
   255	        url = f"{SUPABASE_URL}/rest/v1/crm_prospects"
   256	        params = {"id": f"eq.{prospect_id}"}
   257	        headers = {**get_supabase_headers(), "Prefer": "return=representation"}
   258	        
   259	        payload = updates.dict(exclude_none=True)
   260	        
   261	        # Mise à jour automatique de date_dernier_echange si statut change
   262	        if "statut" in payload:
   263	            payload["date_dernier_echange"] = str(date.today())
   264	        
   265	        response = httpx_client.patch(url, headers=headers, params=params, json=payload)
   266	        response.raise_for_status()
   267	        data = response.json()
   268	        
   269	        if not data:
   270	            raise HTTPException(status_code=404, detail="Prospect non trouvé")
   271	        
   272	        return {
   273	            "success": True,
   274	            "message": "Prospect mis à jour",
   275	            "prospect": data[0] if isinstance(data, list) else data
   276	        }
   277	    
   278	    except httpx.HTTPError as e:
   279	        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")
   280	
   281	# ========================================
   282	# ROUTES OPPORTUNITÉS
   283	# ========================================
   284	
   285	@router.get("/opportunites")
   286	async def list_opportunites(
   287	    statut: Optional[str] = Query(None, description="Filtrer par statut")
   288	):
   289	    """
   290	    Liste toutes les opportunités
   291	    """
   292	    try:
   293	        url = f"{SUPABASE_URL}/rest/v1/crm_v_pipeline_opportunites"
   294	        params = {}
   295	        
   296	        if statut:
   297	            params["statut"] = f"eq.{statut}"
   298	        
   299	        response = httpx_client.get(url, headers=get_supabase_headers(), params=params)
   300	        response.raise_for_status()
   301	        data = response.json()
   302	        
   303	        return {
   304	            "success": True,
   305	            "count": len(data),
   306	            "opportunites": data
   307	        }
   308	    
   309	    except httpx.HTTPError as e:
   310	        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")
   311	
   312	@router.get("/pipeline")
   313	async def get_pipeline():
   314	    """
   315	    Vue pipeline avec stats
   316	    """
   317	    try:
   318	        url = f"{SUPABASE_URL}/rest/v1/crm_v_pipeline_opportunites"
   319	        
   320	        response = httpx_client.get(url, headers=get_supabase_headers())
   321	        response.raise_for_status()
   322	        opportunites = response.json()
   323	        
   324	        # Calculer les stats
   325	        valeur_totale = sum(o.get("montant_ht", 0) for o in opportunites)
   326	        valeur_ponderee = sum(o.get("valeur_ponderee", 0) for o in opportunites)
   327	        taux_moyen = round(sum(o.get("probabilite_closing", 0) for o in opportunites) / len(opportunites)) if opportunites else 0
   328	        
   329	        # Grouper par statut
   330	        par_statut = {}
   331	        for opp in opportunites:
   332	            statut = opp.get("statut", "Non défini")
   333	            if statut not in par_statut:
   334	                par_statut[statut] = {"count": 0, "valeur": 0, "valeur_ponderee": 0}
   335	            par_statut[statut]["count"] += 1
   336	            par_statut[statut]["valeur"] += opp.get("montant_ht", 0)
   337	            par_statut[statut]["valeur_ponderee"] += opp.get("valeur_ponderee", 0)
   338	        
   339	        return {
   340	            "success": True,
   341	            "pipeline": {
   342	                "total_opportunites": len(opportunites),
   343	                "valeur_totale": valeur_totale,
   344	                "valeur_ponderee": valeur_ponderee,
   345	                "taux_conversion_moyen": taux_moyen,
   346	                "par_statut": par_statut,
   347	                "opportunites": opportunites
   348	            }
   349	        }
   350	    
   351	    except httpx.HTTPError as e:
   352	        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")
   353	
   354	@router.post("/opportunites", status_code=201)
   355	async def create_opportunite(opportunite: OpportuniteCreate):
   356	    """
   357	    Créer une opportunité
   358	    """
   359	    try:
   360	        url = f"{SUPABASE_URL}/rest/v1/crm_opportunites"
   361	        headers = {**get_supabase_headers(), "Prefer": "return=representation"}
   362	        
   363	        payload = opportunite.dict(exclude_none=True)
   364	        
   365	        response = httpx_client.post(url, headers=headers, json=payload)
   366	        response.raise_for_status()
   367	        data = response.json()
   368	        
   369	        return {
   370	            "success": True,
   371	            "message": "Opportunité créée",
   372	            "opportunite": data[0] if isinstance(data, list) else data
   373	        }
   374	    
   375	    except httpx.HTTPError as e:
   376	        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")
   377	
   378	@router.patch("/opportunites/{opportunite_id}")
   379	async def update_opportunite(opportunite_id: str, updates: OpportuniteUpdate):
   380	    """
   381	    Modifier une opportunité
   382	    """
   383	    try:
   384	        url = f"{SUPABASE_URL}/rest/v1/crm_opportunites"
   385	        params = {"id": f"eq.{opportunite_id}"}
   386	        headers = {**get_supabase_headers(), "Prefer": "return=representation"}
   387	        
   388	        payload = updates.dict(exclude_none=True)
   389	        
   390	        response = httpx_client.patch(url, headers=headers, params=params, json=payload)
   391	        response.raise_for_status()
   392	        data = response.json()
   393	        
   394	        if not data:
   395	            raise HTTPException(status_code=404, detail="Opportunité non trouvée")
   396	        
   397	        return {
   398	            "success": True,
   399	            "message": "Opportunité mise à jour",
   400	            "opportunite": data[0] if isinstance(data, list) else data
   401	        }
   402	    
   403	    except httpx.HTTPError as e:
   404	        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")
   405	
   406	# ========================================
   407	# ROUTES STATS
   408	# ========================================
   409	
   410	@router.get("/stats")
   411	async def get_stats():
   412	    """
   413	    Tableau de bord global
   414	    """
   415	    try:
   416	        # Stats depuis la vue
   417	        url_tableau = f"{SUPABASE_URL}/rest/v1/crm_v_tableau_bord"
   418	        response_tableau = httpx_client.get(url_tableau, headers=get_supabase_headers())
   419	        response_tableau.raise_for_status()
   420	        tableau = response_tableau.json()[0] if response_tableau.json() else {}
   421	        
   422	        # Compter prospects
   423	        url_prospects = f"{SUPABASE_URL}/rest/v1/crm_prospects?select=id"
   424	        response_prospects = httpx_client.get(url_prospects, headers=get_supabase_headers())
   425	        total_prospects = len(response_prospects.json()) if response_prospects.status_code == 200 else 0
   426	        
   427	        # Stats opportunités
   428	        url_opps = f"{SUPABASE_URL}/rest/v1/crm_opportunites?select=montant_ht,probabilite_closing,statut"
   429	        response_opps = httpx_client.get(url_opps, headers=get_supabase_headers())
   430	        opportunites = response_opps.json() if response_opps.status_code == 200 else []
   431	        
   432	        valeur_totale = sum(o.get("montant_ht", 0) for o in opportunites)
   433	        valeur_ponderee = sum(o.get("montant_ht", 0) * o.get("probabilite_closing", 0) / 100 for o in opportunites)
   434	        en_cours = len([o for o in opportunites if o.get("statut") not in ["Gagné", "Perdu"]])
   435	        
   436	        return {
   437	            "success": True,
   438	            "stats": {
   439	                "prospects": {
   440	                    "total": total_prospects,
   441	                    **tableau
   442	                },
   443	                "opportunites": {
   444	                    "total": len(opportunites),
   445	                    "en_cours": en_cours,
   446	                    "valeur_totale": valeur_totale,
   447	                    "valeur_ponderee": valeur_ponderee
   448	                },
   449	                "alertes": {
   450	                    "relances_urgentes": tableau.get("nb_relances_urgentes", 0)
   451	                }
   452	            }
   453	        }
   454	    
   455	    except httpx.HTTPError as e:
   456	        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")
   457	
   458	@router.get("/alertes")
   459	async def get_alertes():
   460	    """
   461	    Prospects à relancer
   462	    """
   463	    try:
   464	        today = str(date.today())
   465	        
   466	        # Actions en retard
   467	        url_retard = f"{SUPABASE_URL}/rest/v1/crm_prospects"
   468	        params_retard = {
   469	            "date_prochaine_action": f"lt.{today}",
   470	            "statut": f"not.in.(Gagné,Perdu)",
   471	            "select": "id,entreprise,prochaine_action,date_prochaine_action"
   472	        }
   473	        response_retard = httpx_client.get(url_retard, headers=get_supabase_headers(), params=params_retard)
   474	        actions_retard = response_retard.json() if response_retard.status_code == 200 else []
   475	        
   476	        alertes = []
   477	        for p in actions_retard:
   478	            jours_retard = (date.today() - datetime.strptime(p["date_prochaine_action"], "%Y-%m-%d").date()).days
   479	            alertes.append({
   480	                "type": "Action en retard",
   481	                "prospect_id": p["id"],
   482	                "entreprise": p["entreprise"],
   483	                "prochaine_action": p["prochaine_action"],
   484	                "date_prochaine_action": p["date_prochaine_action"],
   485	                "jours_retard": jours_retard,
   486	                "priorite": "Haute"
   487	            })
   488	        
   489	        return {
   490	            "success": True,
   491	            "count": len(alertes),
   492	            "alertes": alertes
   493	        }
   494	    
   495	    except httpx.HTTPError as e:
   496	        raise HTTPException(status_code=500, detail=f"Erreur Supabase: {str(e)}")
