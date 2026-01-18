# BaseGenspark Wrapper API

API wrapper pour permettre aux agents Genspark d'interagir avec Supabase.

## 🚀 Déploiement

### Option 1 : Render.com (Recommandé - Gratuit)

1. Allez sur [render.com](https://render.com)
2. Créez un compte (gratuit)
3. Cliquez sur "New +" → "Web Service"
4. Connectez votre repo GitHub (ou uploadez ce dossier)
5. Configuration :
   - **Name** : `basegenspark-api`
   - **Runtime** : Python 3
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Déployez !

Votre API sera disponible sur : `https://basegenspark-api.onrender.com`

### Option 2 : Railway.app

1. [railway.app](https://railway.app)
2. "New Project" → "Deploy from GitHub"
3. Sélectionnez ce repo
4. Railway détecte automatiquement Python
5. Déployé en 2 minutes !

### Option 3 : Fly.io

```bash
# Installer Fly CLI
curl -L https://fly.io/install.sh | sh

# Se connecter
fly auth login

# Déployer
fly launch
fly deploy
```

### Option 4 : Local (pour tests)

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur
python main.py

# Accessible sur http://localhost:8000
```

## 📚 Documentation

Une fois déployé, accédez à :
- **Documentation interactive** : `https://votre-url.com/docs`
- **Documentation alternative** : `https://votre-url.com/redoc`

## 🔧 Endpoints disponibles

### Lecture

- `GET /` - Page d'accueil avec liste des endpoints
- `GET /health` - Health check
- `GET /logs` - Tous les logs (avec pagination)
- `GET /logs/{id}` - Un log spécifique
- `GET /logs/agent/{agent_name}` - Logs d'un agent
- `GET /logs/recent?limit=10` - N derniers logs
- `GET /stats` - Statistiques globales

### Écriture

- `POST /logs` - Créer un log
- `POST /logs/batch` - Créer plusieurs logs
- `PUT /logs/{id}` - Mettre à jour un log
- `DELETE /logs/{id}` - Supprimer un log

## 📖 Exemples d'utilisation

### Depuis un agent Genspark (avec crawler)

```python
# Lire les logs récents
result = crawler.get("https://votre-api.com/logs/recent?limit=5")

# Créer un log
import requests
response = requests.post(
    "https://votre-api.com/logs",
    json={
        "agent_name": "mon_agent",
        "action": "traitement_image",
        "details": {"image_count": 10, "status": "success"}
    }
)
```

### Depuis curl

```bash
# Lire tous les logs
curl https://votre-api.com/logs

# Créer un log
curl -X POST https://votre-api.com/logs \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "test_agent",
    "action": "test_action",
    "details": {"key": "value"}
  }'
```

## 🔒 Sécurité (à ajouter en production)

Pour l'instant l'API est publique. Pour la production, ajoutez :

1. **API Key authentication**
2. **Rate limiting**
3. **HTTPS uniquement**
4. **Variables d'environnement** pour les secrets

## 📝 Notes

- L'API est actuellement configurée avec vos credentials Supabase
- En production, utilisez des variables d'environnement
- Le free tier de Render redémarre après 15 min d'inactivité (premier appel plus lent)
