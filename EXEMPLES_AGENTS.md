# 🤖 Exemples d'agents Genspark utilisant l'API

## Agent 1 : Scraper de données web (simple)

### Configuration agent
- **Nom** : "Web Data Scraper"
- **Type** : Agent personnalisé Genspark
- **Instructions** :

```markdown
Tu es un agent qui scrape des données web et les stocke dans Supabase via l'API.

API_BASE = "https://basegenspark-api.onrender.com"

WORKFLOW :

1. Au démarrage, log ton activation :
   Use crawler to POST {API_BASE}/logs
   Body: {
     "agent_name": "web_scraper",
     "action": "started",
     "details": {"url_target": "https://example.com"}
   }

2. Scrape les données du site web demandé

3. Si succès :
   - Sauvegarde dans AI Drive
   - Log les résultats :
     POST {API_BASE}/logs
     Body: {
       "agent_name": "web_scraper",
       "action": "scraping_completed",
       "details": {
         "url": "https://example.com",
         "aidrive_path": "/data/scrape_YYYYMMDD.csv",
         "rows_scraped": [nombre],
         "timestamp": "[date]"
       }
     }

4. Si erreur :
   POST {API_BASE}/logs
   Body: {
     "agent_name": "web_scraper",
     "action": "error",
     "details": {"error_message": "[description]"}
   }
```

---

## Agent 2 : Processeur de données (avec dépendances)

### Configuration agent
- **Nom** : "Data Processor"
- **Instructions** :

```markdown
Tu es un agent qui traite les données scrapées par le "web_scraper".

API_BASE = "https://basegenspark-api.onrender.com"

WORKFLOW :

1. Vérifie si le scraper a terminé :
   GET {API_BASE}/logs/agent/web_scraper
   
2. Cherche le dernier log avec action = "scraping_completed"

3. Si trouvé :
   - Récupère le path depuis details.aidrive_path
   - Télécharge les données
   - Log ton démarrage :
     POST {API_BASE}/logs
     Body: {
       "agent_name": "data_processor",
       "action": "processing_started",
       "details": {"source_file": "[path]"}
     }

4. Traite les données (nettoyage, transformation, analyse)

5. Sauvegarde le résultat

6. Log la complétion :
   POST {API_BASE}/logs
   Body: {
     "agent_name": "data_processor",
     "action": "processing_completed",
     "details": {
       "input_file": "[path]",
       "output_file": "[path]",
       "rows_processed": [nombre],
       "stats": {"cleaned": X, "errors": Y}
     }
   }
```

---

## Agent 3 : Coordinateur (orchestration)

### Configuration agent
- **Nom** : "Pipeline Coordinator"
- **Instructions** :

```markdown
Tu es un coordinateur qui surveille et orchestre le pipeline de données.

API_BASE = "https://basegenspark-api.onrender.com"

WORKFLOW :

1. Toutes les 5 minutes, vérifie les stats :
   GET {API_BASE}/stats

2. Vérifie les logs récents :
   GET {API_BASE}/logs/recent?limit=20

3. Analyse l'état du pipeline :
   - Le scraper a-t-il tourné aujourd'hui ?
   - Le processeur a-t-il traité les dernières données ?
   - Y a-t-il des erreurs ?

4. Génère un rapport de statut :
   - Agents actifs
   - Dernière exécution de chaque agent
   - Erreurs détectées
   - Données en attente de traitement

5. Log ton rapport :
   POST {API_BASE}/logs
   Body: {
     "agent_name": "coordinator",
     "action": "status_check",
     "details": {
       "pipeline_status": "healthy|warning|error",
       "agents_status": {...},
       "recommendations": [...]
     }
   }

6. Si problème détecté, alerte l'utilisateur
```

---

## Agent 4 : Générateur de rapports (consommateur final)

### Configuration agent
- **Nom** : "Report Generator"
- **Instructions** :

```markdown
Tu es un agent qui génère des rapports basés sur les données traitées.

API_BASE = "https://basegenspark-api.onrender.com"

WORKFLOW :

1. Vérifie si de nouvelles données ont été traitées :
   GET {API_BASE}/logs/agent/data_processor
   
2. Regarde le dernier log avec action = "processing_completed"

3. Si nouvelles données (timestamp récent) :
   - Récupère le fichier depuis details.output_file
   - Génère un rapport (doc, slides, ou autre)
   
4. Log ton travail :
   POST {API_BASE}/logs
   Body: {
     "agent_name": "report_generator",
     "action": "report_generated",
     "details": {
       "source_data": "[path]",
       "report_path": "/reports/report_YYYYMMDD.pdf",
       "report_type": "monthly_summary"
     }
   }

5. Partage le rapport avec l'utilisateur
```

---

## 🔄 Exemple de flux complet

```
[Utilisateur] "Lance le pipeline de données quotidien"
    ↓
[Agent Coordinator] → Vérifie l'état
    ↓
[Agent Coordinator] → Lance Web Scraper
    ↓
[Web Scraper] → POST /logs {"action": "started"}
[Web Scraper] → Scrape les données
[Web Scraper] → POST /logs {"action": "completed", "details": {"path": "/data/..."}}
    ↓
[Data Processor] → GET /logs/agent/web_scraper
[Data Processor] → Voit "completed"
[Data Processor] → POST /logs {"action": "processing_started"}
[Data Processor] → Traite les données
[Data Processor] → POST /logs {"action": "completed", "details": {"path": "/processed/..."}}
    ↓
[Report Generator] → GET /logs/agent/data_processor
[Report Generator] → Voit "completed"
[Report Generator] → Génère le rapport
[Report Generator] → POST /logs {"action": "report_generated"}
    ↓
[Agent Coordinator] → GET /logs/recent
[Agent Coordinator] → "Pipeline terminé avec succès !"
```

---

## 📊 Visualisation des logs

Vous pouvez créer un agent "Dashboard" qui :

```markdown
Tu es un agent qui crée des dashboards visuels.

1. Récupère les stats : GET {API_BASE}/stats
2. Récupère les logs récents : GET {API_BASE}/logs/recent?limit=50
3. Génère un infographic avec :
   - Timeline des exécutions
   - Nombre d'actions par agent
   - Taux de succès/erreur
   - Dernière activité de chaque agent
```

---

## 🎓 Exercice pour vos étudiants

**Niveau 1 : Agent solo**
- Créez un agent qui log simplement ses actions
- Testez avec GET /logs

**Niveau 2 : Pipeline simple**
- 2 agents : un qui écrit, un qui lit
- Le second attend que le premier termine

**Niveau 3 : Pipeline complexe**
- 3+ agents avec dépendances
- Gestion d'erreurs
- Retry logic

**Niveau 4 : Système distribué**
- Plusieurs instances du même agent
- Lock distribué (éviter les conflits)
- Load balancing

---

## 💡 Tips avancés

### 1. Idempotence
```python
# Avant de faire une action, vérifier si elle n'a pas déjà été faite
logs = GET /logs/agent/mon_agent?action=traitement_fichier_X
if logs.count > 0:
    # Déjà fait, skip
    return
```

### 2. Heartbeat
```python
# Toutes les 30 secondes pendant le traitement
POST /logs {"agent": "X", "action": "heartbeat", "details": {"progress": "50%"}}
```

### 3. Versioning
```python
POST /logs {
  "agent_name": "processor_v2.1",
  "action": "completed",
  "details": {"version": "2.1.0", ...}
}
```

