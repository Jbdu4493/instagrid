# 🔑 Guide : Créer une App Facebook & obtenir un Token Instagram

Ce guide explique **pas à pas** comment obtenir un token Instagram pour utiliser InstaGrid AI.

---

## Prérequis

- Un **compte Instagram Professionnel** (Business ou Creator)
- Une **Page Facebook** liée à ce compte Instagram
- Un **compte Meta for Developers**

> [!IMPORTANT]
> Un compte Instagram **personnel** ne fonctionne PAS avec le Graph API.
> Vous devez passer en compte **Professionnel** (gratuit) dans les paramètres Instagram.

---

## Étape 1 — Passer en compte Instagram Professionnel

Le Graph API **ne fonctionne qu'avec** un compte Instagram **Business** ou **Creator** (pas personnel).

> [!CAUTION]
> Sans compte professionnel, aucune des étapes suivantes ne fonctionnera.
> La conversion est **gratuite** et **réversible** à tout moment.

### Sur mobile (app Instagram)

1. Ouvrir Instagram → cliquer sur votre **photo de profil** (en bas à droite)
2. Cliquer le **menu ☰** (en haut à droite) → **Paramètres et confidentialité**
3. Faire défiler jusqu'à **Type de compte et outils** → **Passer à un compte professionnel**
4. Choisir le type :
   - **Creator** : pour les créateurs de contenu, artistes, influenceurs
   - **Business** : pour les entreprises, boutiques, marques
   - 👉 **Les deux fonctionnent** avec le Graph API, choisissez celui que vous préférez
5. Sélectionner une **catégorie** (ex: "Photographe", "Artiste", "Entrepreneur"...)
6. Choisir d'**afficher ou masquer** la catégorie sur votre profil
7. Vérifier vos **coordonnées** (email, téléphone) — vous pouvez les ignorer
8. Cliquer **Terminé**

### Vérifier que c'est bien activé

Allez sur votre profil → vous devriez voir :
- Un bouton **"Tableau de bord professionnel"** ou **"Outils pro"**
- La mention de votre catégorie sous votre nom

---

## Étape 2 — Créer une Page Facebook (si vous n'en avez pas)

Une **Page Facebook** est **obligatoire** — elle sert de pont entre Instagram et le Graph API.

> [!IMPORTANT]
> Ce n'est pas votre profil Facebook personnel. C'est une **Page** (comme les pages de marques/entreprises).
> Si vous en avez déjà une, passez directement au point suivant.

### Créer une Page Facebook

1. Aller sur **[facebook.com/pages/create](https://www.facebook.com/pages/create)**
2. Remplir :
   - **Nom de la Page** : ce que vous voulez (ex: votre nom, votre marque)
   - **Catégorie** : taper un mot-clé et sélectionner (ex: "Photographe")
   - **Bio** : optionnel, quelques mots suffisent
3. Cliquer **Créer une Page**
4. Vous pouvez ignorer les étapes de personnalisation (photo, couverture...)

### Passer la Page en mode Business (important !)

1. Sur votre nouvelle Page, cliquer **Paramètres** (en bas à gauche ou ⚙️)
2. Aller dans **Paramètres de la Page** → **Modèles et onglets** ou **Page info**
3. Vérifiez que la page est de type **Business** ou **Entreprise**
   - Si elle ne l'est pas, allez dans **Paramètres** → **Général** → **Type** et changez en "Entreprise locale" ou "Marque"

> [!TIP]
> En général, une Page créée en 2024+ est automatiquement compatible.
> Si vous avez un doute, c'est très probablement bon.

---

## Étape 3 — Lier le compte Instagram à la Page Facebook

C'est l'étape la plus importante : sans cette liaison, le Graph API ne peut pas accéder à votre compte Instagram.

### Méthode A — Depuis Instagram (recommandée)

1. Ouvrir Instagram → **menu ☰** → **Paramètres et confidentialité**
2. Aller dans **Espace Comptes** (ou "Centre de comptes Meta")
3. Cliquer **Comptes** → **Ajouter un compte** → **Ajouter un compte Facebook**
4. Se connecter avec votre compte Facebook
5. Votre Page Facebook devrait apparaître automatiquement

### Méthode B — Depuis Facebook

1. Aller sur votre **Page Facebook**
2. Cliquer **Paramètres** → **Instagram** (dans le menu de gauche)
3. Cliquer **Connecter un compte Instagram**
4. Entrer vos identifiants Instagram
5. Confirmer la liaison

### Méthode C — Depuis Meta Business Suite

1. Aller sur **[business.facebook.com](https://business.facebook.com/)**
2. Sélectionner votre Page
3. Menu de gauche → **Paramètres** → **Comptes Instagram**
4. Cliquer **Ajouter un compte Instagram**
5. Se connecter avec vos identifiants Instagram

### Vérifier que la liaison fonctionne

Pour confirmer que tout est bien lié :

1. Aller sur **[Graph API Explorer](https://developers.facebook.com/tools/explorer/)**
2. Générer un token avec la permission `pages_show_list`
3. Faire la requête : `me/accounts?fields=name,instagram_business_account`
4. Si vous voyez un objet `instagram_business_account` avec un `id`, **c'est lié !** ✅
5. Si le champ est vide ou absent, la liaison n'est pas faite → recommencez l'étape 3

> [!WARNING]
> Il faut parfois **attendre quelques minutes** après la liaison pour que le Graph API la détecte.
> Si ça ne marche pas immédiatement, attendez 5-10 minutes et réessayez.

---

## Étape 4 — Créer une App Facebook

1. Aller sur **[developers.facebook.com](https://developers.facebook.com/)**
2. Cliquer **Mon app** → **Créer une app**
3. Choisir le type **Business** (ou "Autre" si Business n'est pas proposé)
4. Remplir :
   - **Nom de l'app** : `InstaGrid` (ou ce que vous voulez)
   - **E-mail de contact** : votre email
5. Cliquer **Créer l'app**

---

## Étape 5 — Ajouter le produit "Instagram Graph API"

1. Dans le **Dashboard** de votre app, section **Ajouter des produits**
2. Chercher **Instagram Graph API** → cliquer **Configurer**
3. C'est tout — le produit est activé

---

## Étape 6 — Récupérer l'App ID et App Secret

1. Aller dans **Paramètres** → **Base** (dans le menu de gauche)
2. Copier :
   - **Identifiant d'app** → c'est votre `FB_APP_ID`
   - **Clé secrète** → cliquer "Afficher" → c'est votre `FB_APP_SECRET`
3. Les mettre dans votre `.env` :

```env
FB_APP_ID=926109429872957
FB_APP_SECRET=votre_cle_secrete
```

---

## Étape 7 — Générer un Token depuis le Graph API Explorer

1. Aller sur **[Graph API Explorer](https://developers.facebook.com/tools/explorer/)**
2. En haut à droite, sélectionner **votre app** (InstaGrid)
3. Cliquer **Générer un token d'accès**
4. Accorder les **permissions** suivantes :
   - `pages_show_list`
   - `pages_read_engagement`
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_manage_posts` (parfois requis)
5. Cliquer **Générer** puis **Continuer** dans le popup Facebook
6. Copier le token affiché

> [!WARNING]
> Ce token est **court** (expire en ~1-2 heures). Utilisez le bouton **Étendre** dans InstaGrid pour le convertir en token permanent.

---

## Étape 8 — Trouver votre Instagram User ID

1. Toujours dans le **Graph API Explorer**
2. Dans le champ de requête, taper : `me/accounts`
3. Cliquer **Envoyer**
4. Vous verrez vos Pages Facebook. Copier l'`id` de la page liée à Instagram
5. Faire une nouvelle requête : `VOTRE_PAGE_ID?fields=instagram_business_account`
6. L'`id` retourné est votre **Instagram User ID** (`IG_USER_ID`)

Ou plus simple — utiliser cette requête directe :
```
me/accounts?fields=name,instagram_business_account
```

Le champ `instagram_business_account.id` = votre `IG_USER_ID`

---

## Étape 9 — Étendre le Token (dans InstaGrid)

1. Collez le token court dans le champ **Access Token** sur `http://localhost:3000`
2. Cliquez le bouton **🔄 Étendre**
3. Le backend échange automatiquement :

```
Token court (1-2h) → Token long (60 jours) → Token permanent (∞)
```

4. Le token permanent est sauvegardé dans `backend/data/token.json`
5. Il survit aux redémarrages du container ✅

---

## Récap des variables `.env`

```env
# Obligatoire
IG_USER_ID=17841401830960721
IG_ACCESS_TOKEN=EAAB...  # sera remplacé automatiquement par le token permanent

# Pour l'extension de token (recommandé)
FB_APP_ID=926109429872957
FB_APP_SECRET=xxxxxxxxxxxxx

# Optionnel (sinon tmpfiles.org est utilisé)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=...
AWS_S3_REGION=eu-west-3
```

---

## Résumé visuel

```
Instagram Pro ──► Page Facebook ──► App Facebook ──► Graph API Explorer
                                         │                    │
                                    App ID + Secret     Token court
                                         │                    │
                                         └──── Étendre ───────┘
                                                    │
                                            Token PERMANENT ♾️
                                                    │
                                          backend/data/token.json
```

---

## FAQ

**Q: Mon token a expiré, que faire ?**
R: Regénérez un token court sur le Graph API Explorer, collez-le dans InstaGrid, et cliquez Étendre.

**Q: J'ai l'erreur "Invalid OAuth access token" ?**
R: Le token est expiré. Suivez l'étape 6 pour en générer un nouveau.

**Q: Je ne vois pas `instagram_content_publish` dans les permissions ?**
R: Votre app doit avoir le produit "Instagram Graph API" activé (étape 4).

**Q: Mon compte IG est personnel, ça marche ?**
R: Non. Passez en compte Professionnel (étape 1), c'est gratuit et réversible.
