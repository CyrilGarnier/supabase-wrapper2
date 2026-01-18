# 🎓 Guide d'utilisation du Wrapper pour Agents Genspark

## 📍 URL de l'API (une fois déployée)

```
https://votre-url.onrender.com
```

---

## 🤖 Comment utiliser depuis un agent Genspark personnalisé

### Méthode 1 : Avec l'outil `crawler`

Dans les instructions de votre agent, ajoutez :

```python
# Pour lire les logs récents
Use crawler tool to GET https://votre-api.com/logs/recent?limit=10

# Pour créer un log
Use crawler tool to POST https://votre-api.com/logs with JSON body

# Pour lire les logs d'un agent spécifique
Use crawler tool to GET https://votre-api.com/logs/agent/nom_agent
```

### Méthode 2 : Avec Bash (dans sandbox)

```python
# Lire les logs
result = bash("curl -s https://votre-api.com/logs")

# Créer un log
bash("""
curl -X POST https://votre-api.com/logs \
  -H 'Content-Type: application/json' \
  -d '{
    "agent_name": "mon_agent",
    "action": "traitement_termine",
    "details": {"fichiers": 10, "status": "ok"}
  }'
""")
```

---

## 📚 Exemples concrets pour vos agents

### Exemple 1 : Agent qui log son démarrage

**Instructions agent** :
```
Tu es un agent de traitement d'images.

1. Au démarrage, log ton activation :
   POST https://basegenspark-api.com/logs
   Body: {"agent_name": "image_processor", "action": "started", "details": {}}

2. Traite les images

3. À la fin, log les résultats :
   POST https://basegenspark-api.com/logs
   Body: {"agent_name": "image_processor", "action": "completed", "details": {"images_processed": 25}}
```

### Exemple 2 : Agent qui vérifie ce que font les autres

**Instructions agent** :
```
Tu es un agent coordinateur.

1. Vérifie les logs récents :
   GET https://basegenspark-api.com/logs/recent?limit=5

2. Si un agent "data_scraper" a terminé :
   - Lance le traitement suivant
   
3. Log ta décision :
   POST /logs avec tes actions
```

### Exemple 3 : Agent qui partage des données

**Instructions agent** :
```
Tu es un agent qui scrape des données web.

1. Scrape les données
2. Upload dans AI Drive
3. Log l'emplacement :
   POST /logs
   Body: {
     "agent_name": "web_scraper",
     "action": "data_uploaded",
     "details": {
       "url_source": "https://example.com",
       "aidrive_path": "/data/scrape_2026_01_18.csv",
       "rows_count": 1500
     }
   }
   
4. Les autres agents peuvent lire ce log pour savoir où sont les données
```

---

## 🔧 Endpoints disponibles

### Lecture

| Endpoint | Description | Exemple |
|----------|-------------|---------|
| `GET /` | Liste des endpoints | `curl https://api.com/` |
| `GET /health` | Santé de l'API | `curl https://api.com/health` |
| `GET /logs` | Tous les logs | `curl https://api.com/logs` |
| `GET /logs?agent_name=X` | Logs filtrés | `curl https://api.com/logs?agent_name=scraper` |
| `GET /logs/{id}` | Un log | `curl https://api.com/logs/5` |
| `GET /logs/agent/{name}` | Par agent | `curl https://api.com/logs/agent/scraper` |
| `GET /logs/recent?limit=N` | N derniers | `curl https://api.com/logs/recent?limit=5` |
| `GET /stats` | Statistiques | `curl https://api.com/stats` |

### Écriture

| Endpoint | Description | Body JSON |
|----------|-------------|-----------|
| `POST /logs` | Créer un log | `{"agent_name": "...", "action": "...", "details": {...}}` |
| `POST /logs/batch` | Créer plusieurs logs | `[{...}, {...}]` |
| `PUT /logs/{id}` | Mettre à jour | `{"action": "updated"}` |
| `DELETE /logs/{id}` | Supprimer | - |

---

## 💡 Patterns utiles

### Pattern 1 : Pipeline d'agents

```
Agent A (scraper)
  ↓ log "data_ready"
Agent B (processor) vérifie les logs
  ↓ voit "data_ready"
  ↓ traite les données
  ↓ log "processing_done"
Agent C (reporter) vérifie les logs
  ↓ voit "processing_done"
  ↓ génère le rapport
```

### Pattern 2 : Lock distribué

```python
# Agent vérifie si un autre agent travaille déjà
logs_recent = GET /logs/recent?limit=1
if logs_recent[0].agent_name == "mon_agent" and logs_recent[0].action == "processing":
    # Un autre instance travaille, on attend
    pass
else:
    # On lock
    POST /logs {"agent_name": "mon_agent", "action": "processing"}
    # Travail
    # On unlock
    POST /logs {"agent_name": "mon_agent", "action": "completed"}
```

### Pattern 3 : Données partagées

```python
# Agent A stocke des données
POST /logs {
  "agent_name": "data_collector",
  "action": "data_collected",
  "details": {
    "cdn_url": "https://cdn.com/data.csv",
    "rows": 1000,
    "columns": ["name", "age", "city"]
  }
}

# Agent B lit les métadonnées
logs = GET /logs/agent/data_collector
data_info = logs[0].details
# Maintenant Agent B sait où sont les données et leur structure
```

---

## 🎯 Template d'instructions pour agents

Copiez-collez ceci dans vos agents personnalisés :

```markdown
Tu es [NOM_AGENT], spécialisé dans [TÂCHE].

API_BASE_URL = "https://votre-api.onrender.com"

WORKFLOW :

1. DÉMARRAGE
   - Log ton activation :
     POST {API_BASE_URL}/logs
     {"agent_name": "[NOM_AGENT]", "action": "started", "details": {"timestamp": "now"}}

2. VÉRIFICATION DES DÉPENDANCES
   - Vérifie si les agents dont tu dépends ont terminé :
     GET {API_BASE_URL}/logs/agent/[AGENT_DEPENDANCE]
   - Si pas prêt : attendre ou alerter

3. TRAITEMENT
   - Fais ton travail
   - Log les étapes importantes

4. RÉSULTATS
   - Stocke tes outputs (AI Drive ou CDN)
   - Log l'emplacement et les métadonnées :
     POST {API_BASE_URL}/logs
     {"agent_name": "[NOM_AGENT]", "action": "completed", "details": {"output_path": "..."}}

5. ERREURS
   - En cas d'erreur :
     POST {API_BASE_URL}/logs
     {"agent_name": "[NOM_AGENT]", "action": "error", "details": {"error": "message"}}
```

---

## 🔐 Sécurité (future)

Pour l'instant l'API est ouverte. En production, on ajoutera :

```python
# Authentification par API key
headers = {
    "X-API-Key": "votre_cle_secrete"
}
curl -H "X-API-Key: xxx" https://api.com/logs
```

---

## 📊 Monitoring

Vous pouvez créer un agent "monitoring" qui :

```python
# Toutes les 5 minutes
stats = GET /logs/stats
if stats.agents["agent_critique"] == 0:
    # Alert : l'agent critique n'a pas tourné
    send_notification()
```

---

## 🎓 Pour vos étudiants

**Exercice pratique** :

1. Créez 3 agents personnalisés qui :
   - Agent A : Scrape des données
   - Agent B : Analyse les données (attend que A finisse)
   - Agent C : Génère un rapport (attend que B finisse)

2. Utilisez l'API pour coordonner le pipeline

3. Visualisez le flux avec `GET /logs`

**Critères de réussite** :
- Les agents ne se lancent que dans le bon ordre
- Chaque agent log son début/fin
- Les données transitent via les logs (métadonnées)

