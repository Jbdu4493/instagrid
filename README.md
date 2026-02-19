# 🎨 InstaGrid AI

Application d’**intelligence artificielle** qui automatise la publication de **grilles de 3 posts** sur Instagram.

---

## 📱 C'est quoi une grille de 3 ?

Sur Instagram, le profil affiche les posts en **lignes de 3**. Un tryptique (3 images publiées dans le bon ordre) crée une **ligne visuelle cohérente** sur votre profil — c'est une technique utilisée par les créateurs et les marques pour donner un aspect professionnel et soigné à leur feed.

InstaGrid AI automatise tout le processus :

1. **Vous uploadez 3 images** dans l’interface
2. **L’IA analyse** les images (couleurs, composition, ambiance) et détermine l’**ordre optimal** pour un flux visuel harmonieux
3. **L’IA génère des captions** bilingues (FR/EN) avec un fil conducteur commun entre les 3 posts
4. **L’IA propose des hashtags** stratégiques par pyramide (broad → niche → spécifique)
5. **L’app publie automatiquement** les 3 posts dans le bon ordre sur Instagram via le Graph API

Résultat : une ligne de 3 photos parfaitement agencées sur votre profil, avec des captions optimisées pour l’engagement.

---

## ✨ Fonctionnalités

- **Analyse visuelle IA** — Détecte le meilleur ordre de publication pour un flux visuel cohérent
- **Captions bilingues FR/EN** — Générées par GPT-4o, avec fil conducteur commun
- **Hashtags stratégiques** — Pyramide broad → niche → spécifique
- **Publication auto** — Poste les 3 images directement sur Instagram dans le bon ordre
- **Token permanent** — Échange automatique du token (1h → ∞)
- **Double hébergement** — AWS S3 (recommandé) ou tmpfiles.org (fallback)

---

## 🚀 Démarrage rapide

### 1. Cloner et configurer

```bash
git clone https://github.com/Jbdu4493/instagrid.git
cd instagrid
cp .env.example .env
```

Éditer `.env` avec vos clés :

```env
OPENAI_API_KEY=sk-proj-...
IG_USER_ID=17841401830960721
IG_ACCESS_TOKEN=EAAB...
FB_APP_ID=926109429872957
FB_APP_SECRET=xxxxx
```

> 📖 Pas encore de token Instagram ? Suivez le guide **[SETUP_FACEBOOK_APP.md](SETUP_FACEBOOK_APP.md)**

### 2. Lancer

```bash
docker-compose up -d --build
```

### 3. Utiliser

| Service | URL |
|---------|-----|
| **React UI** | [http://localhost:3000](http://localhost:3000) |
| **API Backend** | [http://localhost:8001](http://localhost:8001) |
| **Streamlit** (legacy) | [http://localhost:8503](http://localhost:8503) |

---

## 📋 Workflow

```
1. Upload     → Glisser 3 images dans l'interface
2. Contexte   → Ajouter du contexte (optionnel)
3. Analyse    → L'IA détermine l'ordre optimal + génère les captions
4. Édition    → Réordonner, regénérer les captions, ajouter des hashtags
5. Publier    → Post automatique sur Instagram
```

---

## 🏗️ Architecture

```
┌──────────────────┐     ┌──────────────────┐
│   React Frontend │────▶│  FastAPI Backend  │
│   (port 3000)    │     │   (port 8001)     │
└──────────────────┘     └────────┬─────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼              ▼
              ┌──────────┐ ┌──────────┐  ┌────────────┐
              │ OpenAI   │ │  AWS S3  │  │ Instagram  │
              │ GPT-4o   │ │ (ou tmp) │  │ Graph API  │
              └──────────┘ └──────────┘  └────────────┘
```

---

## 📁 Structure

```
├── backend/
│   ├── main.py              # API FastAPI
│   ├── prompts.yaml          # Prompts OpenAI
│   ├── requirements.txt
│   ├── Dockerfile
│   └── data/token.json       # Token persisté (auto-généré)
├── frontend-react/
│   ├── src/App.jsx           # Interface principale
│   ├── src/components/       # GridEditor, StrategyPanel, UploadSection
│   └── Dockerfile
├── frontend/                 # Streamlit (legacy)
├── docker-compose.yml
├── .env.example              # Template de configuration
├── .gitignore
├── SETUP_FACEBOOK_APP.md     # Guide complet token Facebook/Instagram
└── README.md
```

---

## 🔑 Configuration des tokens

| Variable | Requis | Description |
|----------|--------|-------------|
| `OPENAI_API_KEY` | ✅ | Clé API OpenAI (GPT-4o) |
| `IG_USER_ID` | ✅ | ID du compte Instagram Business |
| `IG_ACCESS_TOKEN` | ✅ | Token d'accès Instagram |
| `FB_APP_ID` | 📌 | ID de l'App Facebook (pour token permanent) |
| `FB_APP_SECRET` | 📌 | Secret de l'App Facebook |
| `AWS_ACCESS_KEY_ID` | ⚠️ | Clé AWS (fortement recommandé) |
| `AWS_SECRET_ACCESS_KEY` | ⚠️ | Secret AWS |
| `AWS_S3_BUCKET` | ⚠️ | Nom du bucket S3 |
| `AWS_S3_REGION` | ⚠️ | Région AWS (défaut: `eu-west-3`) |

> [!WARNING]
> **Il est fortement recommandé d’utiliser AWS S3** pour l’hébergement des images. Le fallback `tmpfiles.org` fonctionne mais est un service tiers gratuit sans garantie de disponibilité ni de fiabilité. Pour un usage en production, S3 est bien plus stable et rapide.

---

## 🔄 Extension de token

Le bouton **Étendre** dans l'UI convertit votre token court en permanent :

```
Token court (1-2h) → Token long (60j) → Token permanent (∞)
```

Le token permanent est sauvegardé dans `backend/data/token.json` et rechargé automatiquement au redémarrage.

---

## 📖 Documentation

- **[SETUP_FACEBOOK_APP.md](SETUP_FACEBOOK_APP.md)** — Guide pas à pas pour créer une App Facebook et obtenir un token Instagram

---

## 🛠️ Stack technique

- **Backend** : Python, FastAPI, OpenAI, boto3, Pillow
- **Frontend** : React, Vite, TailwindCSS, Lucide Icons
- **Infra** : Docker, Nginx, AWS S3
- **APIs** : Instagram Graph API, OpenAI GPT-4o
