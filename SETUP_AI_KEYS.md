# 🔑 Guide: Obtenir vos Clés API d'Intelligence Artificielle

L'application **InstaGrid AI** a besoin de se connecter à des moteurs d'intelligence artificielle ("cerveaux") pour analyser vos photos et rédiger vos légendes Instagram de manière intelligente. 

L'application supporte le concept de **Multi-IA**, vous pouvez donc utiliser **OpenAI (ChatGPT)**, **Google Gemini**, ou même configurer les deux !

Ce guide vous explique pas-à-pas comment obtenir les clés API pour ces plateformes afin de les copier dans votre fichier `.env`.

---

## Sommaire
1. [Obtenir une clé API OpenAI (ChatGPT)](#1-obtenir-une-clé-api-openai-chatgpt)
2. [Obtenir une clé API Google Gemini](#2-obtenir-une-clé-api-google-gemini)
3. [Configurer votre application InstaGrid](#3-configurer-votre-application-instagrid)

---

## 1. Obtenir une clé API OpenAI (ChatGPT)

OpenAI propose le modèle GPT-4o-mini qui excelle dans la rédaction de contenu engageant. 

1. **Créer un compte** :
   - Allez sur la plateforme développeur d'OpenAI : [https://platform.openai.com/](https://platform.openai.com/)
   - Cliquez sur **Sign Up** si vous n'avez pas de compte, ou **Log In**.

2. **Ajouter un moyen de paiement (Requis)** :
   *Note : L'API d'OpenAI n'est pas gratuite, mais coûte des fractions de centime par analyse. Vous ne payez qu'à l'usage.*
   - Dans le menu de gauche, allez dans l'icône **Settings** (Roue crantée) > **Billing**.
   - Ajoutez une carte bancaire (`Add payment details`).
   - Ajoutez au moins 5$ de crédit sur votre compte.

3. **Générer la clé API** :
   - Toujours dans le menu de gauche, allez dans **API Keys** (ou cliquez sur ce lien : [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)).
   - Cliquez sur le bouton vert **"Create new secret key"**.
   - Donnez-lui un nom clair, par exemple : `InstaGrid-App`.
   - Cliquez sur **Create secret key**.

4. **Copier la clé** :
   - ⚠️ **Très important** : Un pop-up va s'afficher avec votre clé (elle commence par `sk-proj-...`). Vous ne pourrez la voir qu'une seule fois ! Cliquez sur le bouton pour la **copier**.
   - Collez-la temporairement dans un bloc-notes.

---

## 2. Obtenir une clé API Google Gemini

Google Gemini offre un excellent modèle visuel (`gemini-flash`). La génération d'une clé API est généralement gratuite dans les limites d'usage standard via Google AI Studio.

1. **Créer un compte Google / Se connecter** :
   - Allez sur Google AI Studio : [https://aistudio.google.com/](https://aistudio.google.com/)
   - Connectez-vous avec votre adresse compte Gmail/Google.
   - Acceptez les conditions d'utilisation si c'est votre première connexion.

2. **Générer la clé API** :
   - En haut à gauche, cliquez sur le bouton **"Get API key"**.
   - Cliquez sur le gros bouton bleu **"Create API key"**.
   - Google va vous demander de sélectionner ou de créer un "Google Cloud project" (Projet cloud).
   - Choisissez **"Create API key in a new project"** (Créer la clé dans un nouveau projet).

3. **Copier la clé** :
   - Un pop-up s'affichera avec votre nouvelle clé API générée (une longue suite de lettres et de chiffres).
   - Cliquez sur le bouton "Copier" ou copiez le texte vous-même.
   - Collez-la temporairement dans votre bloc-notes.

---

## 3. Configurer votre application InstaGrid

Maintenant que vous avez copié vos (ou votre) clés, nous devons dire à InstaGrid de les utiliser.

1. **Ouvrir le fichier `.env`**
   - À la racine du dossier de votre projet `instagrid`, trouvez le fichier nommé `.env`. S'il n'existe pas, faites une copie de `.env.example` et renommez-la en `.env`.
   - Ouvrez ce fichier avec un éditeur de texte (Bloc-notes, VSCode, TextEdit, etc.).

2. **Copier les clés**
   - Remplissez les champs correspondants :
   
   ```env
   # --- AI Providers ---
   OPENAI_API_KEY=sk-proj-VOtre-CLEF-OPEN-AI-ICI
   GEMINI_API_KEY=AIzaSyB-votre-Clef-Gemini-Ici
   ```

   *(Note : Vous n'êtes pas obligé de remplir les deux. Remplir uniquement celle du moteur que vous préférez est suffisant).*

3. **Redémarrer l'application**
   - Si votre application tourne déjà via Docker, vous devez redémarrer le serveur pour qu'il prenne en compte les nouvelles clés. Dans votre terminal, lancez :
   ```bash
   docker compose restart backend
   ```

C'est terminé ! Retournez sur l'application InstaGrid (React ou Streamlit). Le bouton ou le menu déroulant *"Moteur IA"* détectera automatiquement vos clés et vous autorisera à générer vos grilles. ✨
