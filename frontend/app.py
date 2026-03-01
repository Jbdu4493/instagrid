import streamlit as st
import requests
import base64
from PIL import Image
import os
import time

# --- Configuration ---
API_URL = os.getenv("API_URL", "http://localhost:8000")
st.set_page_config(page_title="InstaGrid AI", page_icon="favicon.svg", layout="wide")

# --- Security: App Password Gateway ---
if 'app_password' not in st.session_state:
    st.session_state.app_password = None

if not st.session_state.app_password:
    col_s1, col_s2, col_s3 = st.columns([1, 2, 1])
    with col_s2:
        st.markdown("<h2 style='text-align: center;'>🔒 Accès Restreint</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Veuillez saisir le mot de passe de l'application.</p>", unsafe_allow_html=True)
        pwd = st.text_input("Mot de passe", type="password", label_visibility="collapsed", placeholder="••••••••••••")
        if st.button("Déverrouiller", use_container_width=True, type="primary"):
            if pwd:
                with st.spinner("Vérification..."):
                    try:
                        r = requests.get(f"{API_URL}/verify-password", headers={"X-App-Password": pwd})
                        if r.status_code == 200 and r.json().get("valid"):
                            st.session_state.app_password = pwd
                            st.rerun()
                        elif r.status_code == 401:
                            st.error("Mot de passe incorrect.")
                        else:
                            st.error(f"Erreur du serveur d'authentification ({r.status_code})")
                    except Exception as e:
                        st.error(f"Impossible de contacter le serveur : {e}")
    st.stop()

# --- Authenticated HTTP Session ---
def get_api_session():
    if 'api_session' not in st.session_state:
        s = requests.Session()
        s.headers.update({"X-App-Password": st.session_state.app_password})
        st.session_state.api_session = s
    return st.session_state.api_session

api = get_api_session()

# --- Header ---
col1, col2 = st.columns([1, 8])
with col1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=80)
    else:
        st.markdown("## 📸")
with col2:
    st.title("InstaGrid AI")
    st.markdown("### Créez la séquence parfaite de 3 posts Instagram.")

import io

# --- Helper Functions ---
def file_to_base64(file):
    return base64.b64encode(file.getvalue()).decode('utf-8')

def crop_image_for_ai(file, ratio_str, position):
    if ratio_str == "original":
        return file_to_base64(file)
    
    img = Image.open(file)
    RATIOS = {'1:1': 1, '4:5': 4/5, '16:9': 16/9}
    target_ratio = RATIOS.get(ratio_str)
    if not target_ratio: 
        return file_to_base64(file)
    
    img_ratio = img.width / img.height
    posX = position.get("x", 50) / 100.0
    posY = position.get("y", 50) / 100.0
    
    if img_ratio > target_ratio:
        new_w = int(img.height * target_ratio)
        offset_x = int((img.width - new_w) * posX)
        box = (offset_x, 0, offset_x + new_w, img.height)
    else:
        new_h = int(img.width / target_ratio)
        offset_y = int((img.height - new_h) * posY)
        box = (0, offset_y, img.width, offset_y + new_h)
        
    cropped = img.crop(box)
    buf = io.BytesIO()
    if cropped.mode in ("RGBA", "P"):
        cropped = cropped.convert("RGB")
    cropped.save(buf, format="JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def fetch_config(password):
    try:
        r = requests.get(f"{API_URL}/config", headers={"X-App-Password": password})
        if r.status_code == 200:
            return r.json()
    except Exception:
        return {}
    return {}

config_data = fetch_config(st.session_state.app_password)

# --- Session State Management ---
if 'ig_user_id' not in st.session_state:
    st.session_state.ig_user_id = config_data.get("ig_user_id", "")
if 'access_token' not in st.session_state:
    st.session_state.access_token = config_data.get("ig_access_token", "")
if 'posts' not in st.session_state:
    st.session_state.posts = []
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None

# Constants
CROP_OPTIONS = {"Original": "original", "Carré (1:1)": "1:1", "Portrait (4:5)": "4:5", "Paysage (16:9)": "16:9"}

# --- Layout: TABS ---
tab_create, tab_drafts, tab_settings = st.tabs(["✨ Création", "📄 Brouillons", "⚙️ Paramètres"])

# ==========================================
# TAB 3: PARAMÈTRES (Token Management)
# ==========================================
with tab_settings:
    st.subheader("🔑 Token Instagram & Configuration")
    
    new_user_id = st.text_input("Instagram User ID", value=st.session_state.ig_user_id, placeholder="ex: 1784140...")
    new_token = st.text_input("Access Token", value=st.session_state.access_token, type="password")
    
    if st.button("💾 Sauvegarder Localement"):
        st.session_state.ig_user_id = new_user_id
        st.session_state.access_token = new_token
        st.success("Paramètres enregistrés dans la session courante.")
        
    st.markdown("---")
    st.markdown("### Étendre le Token (Token Permanent)")
    if st.button("🔄 Échanger le Short-Lived Token"):
        if not st.session_state.access_token:
            st.warning("Veuillez d'abord renseigner un token court.")
        else:
            with st.spinner("Échange en cours avec Facebook Graph API..."):
                try:
                    res = api.post(f"{API_URL}/exchange-token", json={"short_lived_token": st.session_state.access_token})
                    if res.status_code == 200:
                        data = res.json()
                        st.success(data.get("message", "Token étendu avec succès !"))
                        if data.get("access_token"):
                            st.session_state.access_token = data["access_token"]
                    else:
                        st.error(f"Erreur d'échange: {res.text}")
                except Exception as e:
                    st.error(f"Impossible de contacter le serveur : {e}")

# ==========================================
# TAB 2: BROUILLONS
# ==========================================
with tab_drafts:
    st.subheader("📄 Brouillons Sauvegardés")
    if st.button("🔄 Rafraîchir les brouillons"):
        st.rerun()
        
    try:
        drafts_res = api.get(f"{API_URL}/drafts")
        if drafts_res.status_code == 200:
            drafts = drafts_res.json().get("drafts", [])
            if not drafts:
                st.info("Aucun brouillon trouvé.")
            else:
                for d in drafts:
                    with st.expander(f"Brouillon #{d['id']} - {d['created_at'].split('T')[0]}"):
                        cols = st.columns(3)
                        for idx, p in enumerate(d['posts']):
                            with cols[idx]:
                                img_url = p.get('image_url', '')
                                if not img_url.startswith("http"):
                                    img_url = f"{API_URL}{img_url}" if img_url.startswith('/') else f"{API_URL}/{img_url}"
                                st.image(img_url, use_container_width=True)
                                
                                c_arrow_ld, c_arrow_rd = st.columns(2)
                                with c_arrow_ld:
                                    if idx > 0 and st.button("◀️ Déplacer", key=f"d_left_{d['id']}_{idx}"):
                                        order = [0, 1, 2]
                                        order[idx], order[idx-1] = order[idx-1], order[idx]
                                        api.put(f"{API_URL}/drafts/{d['id']}", json={"post_order": order})
                                        st.rerun()
                                with c_arrow_rd:
                                    if idx < 2 and st.button("Déplacer ▶️", key=f"d_right_{d['id']}_{idx}"):
                                        order = [0, 1, 2]
                                        order[idx], order[idx+1] = order[idx+1], order[idx]
                                        api.put(f"{API_URL}/drafts/{d['id']}", json={"post_order": order})
                                        st.rerun()
                                        
                                new_cap = st.text_area("Légende", p.get('caption', ''), key=f"draft_{d['id']}_cap_{idx}", height=100)
                                p['new_caption'] = new_cap
                                
                                if st.button("🔄 Régénérer", key=f"d_regen_{d['id']}_{idx}"):
                                    with st.spinner("Régénération..."):
                                        try:
                                            # Fetch image bytes to send base64
                                            img_res = api.get(img_url if img_url.startswith("http") else f"http://localhost:8000/drafts/image/{p.get('image_key').split('/')[-1]}")
                                            img_b64 = base64.b64encode(img_res.content).decode('utf-8')
                                            payload = {
                                                "image_base64": img_b64,
                                                "captions_history": [p.get('caption', '')]
                                            }
                                            reg_res = api.post(f"{API_URL}/regenerate_caption", json=payload)
                                            if reg_res.status_code == 200:
                                                new_text = reg_res.json()["caption"]
                                                # Save immediately to draft
                                                current_captions = [pt.get('caption', '') for pt in d['posts']]
                                                current_captions[idx] = new_text
                                                requests.put(f"{API_URL}/drafts/{d['id']}", json={"captions": current_captions})
                                                api.put(f"{API_URL}/drafts/{d['id']}", json={"captions": current_captions})
                                                st.success("Régénéré !")
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error("Erreur de régénération.")
                                        except Exception as e:
                                            st.error(f"Erreur : {e}")
                        
                        _, col_action0, col_action1, col_action2 = st.columns([5, 1.5, 2.5, 1.5])
                        with col_action0:
                            if st.button("💾 Mettre à jour", key=f"update_{d['id']}"):
                                new_captions = [p.get('new_caption', p.get('caption', '')) for p in d['posts']]
                                update_res = api.put(f"{API_URL}/drafts/{d['id']}", json={"captions": new_captions})
                                if update_res.status_code == 200:
                                    st.success("Modifications enregistrées.")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Erreur de sauvegarde")
                        with col_action1:
                            if st.button("🚀 Publier sur Instagram", key=f"pub_{d['id']}", type="primary"):
                                if not st.session_state.ig_user_id or not st.session_state.access_token:
                                    st.error("Renseignez l'ID Utilisateur et le Token dans les Paramètres.")
                                else:
                                    with st.spinner("Publication du brouillon..."):
                                        post_res = api.post(f"{API_URL}/drafts/{d['id']}/post", json={
                                            "access_token": st.session_state.access_token,
                                            "ig_user_id": st.session_state.ig_user_id,
                                            "force": False
                                        })
                                        if post_res.status_code == 200:
                                            st.success("✅ Brouillon publié sur Instagram !")
                                        else:
                                            st.error(f"Erreur : {post_res.text}")
                        with col_action2:
                            if st.button("🗑️ Supprimer", key=f"del_{d['id']}"):
                                del_res = api.delete(f"{API_URL}/drafts/{d['id']}")
                                if del_res.status_code == 200:
                                    st.warning("Brouillon supprimé.")
                                    st.rerun()
        else:
            st.error("Erreur lors de la récupération des brouillons.")
    except Exception as e:
        st.error(f"Erreur API Brouillons : {e}")

# ==========================================
# TAB 1: CRÉATION (Upload, Analyse, Edition)
# ==========================================
with tab_create:
    # --- 0. GRILLE ACTUELLE ---
    if st.session_state.ig_user_id and st.session_state.access_token:
        with st.expander("👁️ Afficher la Grille Instagram Actuelle"):
            try:
                res = api.get(f"{API_URL}/ig-posts?ig_user_id={st.session_state.ig_user_id}&access_token={st.session_state.access_token}")
                if res.status_code == 200:
                    recent_posts = res.json().get("posts", [])
                    if recent_posts:
                        st.markdown("---")
                        
                        # Afficher les images par rangée de 3
                        for i in range(0, min(9, len(recent_posts)), 3):
                            cols = st.columns(3)
                            row_posts = recent_posts[i:i+3]
                            for j, post in enumerate(row_posts):
                                with cols[j]:
                                    if post.get('media_type') == 'VIDEO':
                                        st.image(post.get('thumbnail_url', post.get('media_url')), use_container_width=True)
                                    else:
                                        st.image(post.get('media_url'), use_container_width=True)
                                    st.caption(f"❤️ {post.get('like_count', 0)}  💬 {post.get('comments_count', 0)}")
                    else:
                        st.info("Aucun post récent trouvé sur ce compte.")
            except Exception as e:
                st.warning(f"Impossible de charger la grille actuelle: {e}")

    # --- 1. UPLOAD ---
    st.subheader("1. Charger les 3 Photos")
    upload_cols = st.columns(3)
    uploaded_files = [None, None, None]
    
    contexts = ["", "", ""]
    crop_selections = ["original", "original", "original"]
    crop_x = [50, 50, 50]
    crop_y = [50, 50, 50]

    for i, col in enumerate(upload_cols):
        with col:
            st.markdown(f"**Photo {i+1}**" + (" (Gauche)" if i==0 else " (Milieu)" if i==1 else " (Droite)"))
            uploaded_files[i] = st.file_uploader(f"Uploader Image {i+1}", type=['jpg', 'png', 'jpeg'], key=f"file_{i}")
            
            if uploaded_files[i]:
                img_placeholder = st.empty()
                contexts[i] = st.text_area(f"Contexte {i+1}", key=f"context_{i}", height=70, placeholder="Décrivez cette image...")
                
                # Crop options UI
                crop_label = st.selectbox(f"Format", options=list(CROP_OPTIONS.keys()), key=f"crop_{i}")
                crop_selections[i] = CROP_OPTIONS[crop_label]
                if crop_selections[i] != "original":
                    sx, sy = st.columns(2)
                    crop_x[i] = sx.slider("Focus Horizontal %", 0, 100, 50, key=f"cx_{i}")
                    crop_y[i] = sy.slider("Focus Vertical %", 0, 100, 50, key=f"cy_{i}")

                # Live Preview
                try:
                    cropped_b64 = crop_image_for_ai(
                        uploaded_files[i], 
                        crop_selections[i], 
                        {"x": crop_x[i], "y": crop_y[i]}
                    )
                    cropped_bytes = base64.b64decode(cropped_b64)
                    img_placeholder.image(cropped_bytes, use_container_width=True)
                except Exception as e:
                    img_placeholder.image(uploaded_files[i], use_container_width=True)

                st.caption("✅ Prêt")
            else:
                st.info("En attente...")

    st.markdown("---")
    user_context = st.text_input("Fil Rouge (Optionnel)", placeholder="Décrivez le lien ou l'histoire globale entre ces images...")
    all_uploaded = all(f is not None for f in uploaded_files)

    if all_uploaded and not st.session_state.analysis_done:
        if st.button("✨ Analyser la Grille & Générer les Légendes", type="primary"):
            st.session_state.posts = []
            for idx, file in enumerate(uploaded_files):
                 file.seek(0)
                 st.session_state.posts.append({
                     'id': idx,
                     'file': file,
                     'caption': '',
                     'base64': crop_image_for_ai(file, crop_selections[idx], {"x": crop_x[idx], "y": crop_y[idx]}),
                     'crop_ratio': crop_selections[idx],
                     'crop_pos': {"x": crop_x[idx], "y": crop_y[idx]}
                 })

            with st.spinner("Analyse du flux visuel en cours..."):
                try:
                    files_for_api = [("files", post['file']) for post in st.session_state.posts]
                    for post in st.session_state.posts:
                        post['file'].seek(0)
                        
                    data = {
                        "user_context": user_context,
                        "context_0": contexts[0],
                        "context_1": contexts[1],
                        "context_2": contexts[2]
                    }
                    
                    response = api.post(f"{API_URL}/analyze", files=files_for_api, data=data)
                    
                    if response.status_code == 200:
                        res = response.json()
                        st.session_state.analysis_result = res
                        st.session_state.analysis_done = True
                        
                        suggested_order = res['suggested_order']
                        new_posts_list = []
                        for idx in suggested_order:
                            original_post = st.session_state.posts[idx]
                            original_post['caption'] = res['captions'][idx]
                            original_post['history'] = [res['captions'][idx]]
                            original_post['hist_idx'] = 0
                            new_posts_list.append(original_post)
                            
                        st.session_state.posts = new_posts_list
                        st.success("Analyse terminée ! L'ordre a été optimisé.")
                        st.rerun()
                    else:
                        st.error(f"Erreur d'analyse: {response.text}")
                except Exception as e:
                    st.error(f"Échec de connexion API: {e}")

    elif not all_uploaded:
        st.warning("Veuillez charger 3 images pour commencer.")

    # --- 2. ÉDITEUR ---
    if st.session_state.analysis_done:
        st.markdown("---")
        st.subheader("2. Grid Editor (Flow & Légendes)")
        
        cols = st.columns(3)
        for idx, col in enumerate(cols):
            post = st.session_state.posts[idx]
            with col:
                st.image(post['file'], use_container_width=True)
                st.caption(f"Position {idx + 1} ({['Gauche', 'Milieu', 'Droite'][idx]})")
                
                c_arrow_l, c_arrow_r = st.columns(2)
                with c_arrow_l:
                    if idx > 0 and st.button("◀️ Déplacer", key=f"left_{post['id']}"):
                        st.session_state.posts[idx], st.session_state.posts[idx-1] = st.session_state.posts[idx-1], st.session_state.posts[idx]
                        st.rerun()
                with c_arrow_r:
                    if idx < 2 and st.button("Déplacer ▶️", key=f"right_{post['id']}"):
                        st.session_state.posts[idx], st.session_state.posts[idx+1] = st.session_state.posts[idx+1], st.session_state.posts[idx]
                        st.rerun()
                
                # Légende text_area
                new_caption = st.text_area("Légende", value=post['caption'], height=150, key=f"caption_edit_{post['id']}")
                post['caption'] = new_caption
                
                # Regenerate Caption Action
                if st.button("🔄 Régénérer Légende", key=f"regen_{post['id']}"):
                    with st.spinner("Régénération..."):
                        try:
                            # Use analysis state threading details if available
                            th_fr = st.session_state.analysis_result.get('common_thread_fr', '')
                            th_en = st.session_state.analysis_result.get('common_thread_en', '')
                            payload = {
                                "image_base64": post['base64'],
                                "common_context": user_context,
                                "individual_context": contexts[post['id']],
                                "captions_history": post['history'],
                                "common_thread_fr": th_fr,
                                "common_thread_en": th_en
                            }
                            reg_res = api.post(f"{API_URL}/regenerate_caption", json=payload)
                            if reg_res.status_code == 200:
                                new_text = reg_res.json()["caption"]
                                post["history"].append(new_text)
                                post["hist_idx"] = len(post["history"]) - 1
                                post["caption"] = new_text
                                st.rerun()
                            else:
                                st.error("Erreur de régénération.")
                        except Exception as e:
                            st.error(f"Erreur: {e}")

        # Metrics & Strategy
        res = st.session_state.analysis_result
        if res:
            st.markdown("---")
            st.subheader("3. Stratégie & Hashtags")
            score = res.get('coherence_score', 80)
            st.markdown(f"**Score de Cohérence** : {score}/100")
            st.progress(score / 100)
            st.caption(res.get('coherence_reasoning', ''))
            
            hashtags_list = res.get('hashtags', [])
            if not isinstance(hashtags_list, list): hashtags_list = [hashtags_list]*3
            
            if st.button("➕ Ajouter les Hashtags aux Légendes"):
                for idx, post in enumerate(st.session_state.posts):
                    if idx < len(hashtags_list):
                        ladder = hashtags_list[idx]
                        all_tags = "\n\n" + " ".join([f"#{t}" for t in ladder.get('broad',[]) + ladder.get('niche',[]) + ladder.get('specific',[])])
                        post['caption'] += all_tags
                        post['history'].append(post['caption'])
                        post['hist_idx'] = len(post['history']) - 1
                st.rerun()

        # --- ACTIONS DE FIN ---
        st.markdown("---")
        st.subheader("4. Action Finale")
        c_reset, c_save, c_post = st.columns(3)
        
        with c_reset:
            if st.button("🗑️ Réinitialiser le Projet"):
                st.session_state.posts = []
                st.session_state.analysis_done = False
                st.session_state.analysis_result = None
                st.rerun()
                
        with c_save:
            if st.button("💾 Sauvegarder en Brouillon", type="secondary"):
                post_payload_list = [{"image_base64": p['base64'], "caption": p['caption']} for p in st.session_state.posts]
                ratios = [p['crop_ratio'] for p in st.session_state.posts]
                positions = [p['crop_pos'] for p in st.session_state.posts]
                
                try:
                    save_res = api.post(f"{API_URL}/drafts", json={
                        "posts": post_payload_list,
                        "crop_ratios": ratios,
                        "crop_positions": positions
                    })
                    if save_res.status_code == 200:
                        st.success("✅ Brouillon sauvegardé avec succès.")
                    else:
                        st.error(f"Erreur de sauvegarde: {save_res.text}")
                except Exception as e:
                    st.error(f"Erreur : {e}")
                    
        with c_post:
            if st.button("🚀 Publier sur Instagram", type="primary"):
                if not st.session_state.ig_user_id or not st.session_state.access_token:
                    st.error("Allez dans l'onglet Paramètres pour renseigner l'utilisateur et le token.")
                else:
                    with st.spinner("Envoi à Facebook Graph API... Cela peut prendre jusqu'à une minute."):
                        try:
                            # Note: The stream interface currently sends crop logic via Draft routes, 
                            # but direct post endpoint expects PostRequest.
                            post_payload_list = [{"image_base64": p['base64'], "caption": p['caption']} for p in st.session_state.posts]
                            req_body = {
                                "ig_user_id": st.session_state.ig_user_id,
                                "access_token": st.session_state.access_token,
                                "posts": post_payload_list
                            }
                            post_res = api.post(f"{API_URL}/post", json=req_body)
                            if post_res.status_code == 200:
                                st.balloons()
                                data = post_res.json()
                                st.success("✅ " + data.get('message', 'Publié !'))
                            else:
                                st.error(f"Erreur de publication: {post_res.text}")
                        except Exception as e:
                            st.error(f"Erreur inattendue : {e}")
