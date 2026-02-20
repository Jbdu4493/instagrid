import streamlit as st
import requests
import base64
from PIL import Image
import io
import os

# API URL
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="InstaGrid AI", page_icon="favicon.svg", layout="wide")

# --- Styles ---
st.markdown("""
<style>
    .reportview-container {
        background: #0e1117;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em; 
        font-weight: bold;
    }
    .metric-card {
        background-color: #262730;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #41424b;
        text-align: center;
    }
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #ec4899, #a855f7, #6366f1);
    }
    .upload-slot {
        border: 2px dashed #41424b;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
col1, col2 = st.columns([1, 8])
with col1:
    st.image("logo.png", width=80)
with col2:
    st.title("InstaGrid AI")
    st.markdown("### Create the perfect 3-post grid sequence.")

# --- Session State Initialization ---
if 'posts' not in st.session_state:
    # Structure: [{'id': 0, 'file': file_obj, 'caption': '', 'base64': ''}, ...]
    st.session_state.posts = []
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None

# --- Helper: Convert File to Base64 ---
def file_to_base64(file):
    return base64.b64encode(file.getvalue()).decode('utf-8')

# --- 1. UPLOAD SECTION (3 Slots) ---
st.subheader("1. Upload Your 3 Grid Photos")

upload_cols = st.columns(3)
uploaded_files = [None, None, None]

for i, col in enumerate(upload_cols):
    with col:
        st.markdown(f"**Slot {i+1}**" + (" (Left)" if i==0 else " (Middle)" if i==1 else " (Right)"))
        uploaded_files[i] = st.file_uploader(f"Upload Image {i+1}", type=['jpg', 'png', 'jpeg'], key=f"file_{i}")
        
        if uploaded_files[i]:
            st.image(uploaded_files[i], use_container_width=True)
            st.text_area(f"Context {i+1}", key=f"context_{i}", height=70, placeholder="Describe this specific photo...")
            st.caption("✅ Ready")
        else:
            st.info("Waiting for upload...")

st.markdown("---")
user_context = st.text_input("Common Thread / Fil Rouge (Optional)", placeholder="Describe the overall theme or connection between images...")

# Check if all files are uploaded
all_uploaded = all(f is not None for f in uploaded_files)

# --- ACTION: GENERATE STRATEGY ---
if all_uploaded and not st.session_state.analysis_done:
    if st.button("✨ Generate Strategy & Captions", type="primary"):
        
        # Initialize Session State with these files
        st.session_state.posts = []
        for idx, file in enumerate(uploaded_files):
             # Save file pointer position just in case
             file.seek(0)
             st.session_state.posts.append({
                 'id': idx,
                 'file': file,
                 'caption': '',
                 'base64': file_to_base64(file)
             })

        with st.spinner("Analyzing Visual Flow & Generating Captions..."):
            try:
                # Prepare files for API
                files_for_api = [("files", post['file']) for post in st.session_state.posts]
                # Reset file pointers
                for post in st.session_state.posts:
                    post['file'].seek(0)
                    
                    
                # Prepare data for API
                data = {
                    "user_context": user_context,
                    "context_0": st.session_state.context_0,
                    "context_1": st.session_state.context_1,
                    "context_2": st.session_state.context_2
                }
                
                response = requests.post(f"{API_URL}/analyze", files=files_for_api, data=data)
                
                if response.status_code == 200:
                    res = response.json()
                    st.session_state.analysis_result = res
                    st.session_state.analysis_done = True
                    
                    # Apply Suggested Order logic
                    suggested_order = res['suggested_order']
                    
                    new_posts_list = []
                    for idx in suggested_order:
                        # Find the post that was originally at this index
                        original_post = st.session_state.posts[idx]
                        # Update caption from API (List access)
                        original_post['caption'] = res['captions'][idx]
                        new_posts_list.append(original_post)
                        
                    st.session_state.posts = new_posts_list
                    
                    st.success("Analysis Complete & Order Optimized!")
                    st.rerun()
                else:
                    st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"Connection Failed: {e}")

elif not all_uploaded:
    st.warning("Please upload images to all 3 slots to proceed.")


# --- 2. EDITOR & ANALYSIS ---
if st.session_state.analysis_done:
    
    st.markdown("---")
    st.subheader("2. Grid Editor (Visual Flow & Captions)")
    st.info("Review the AI-suggested order and captions. You can reorder if needed.")

    # Reordering Control
    current_ids = [p['id'] for p in st.session_state.posts]
    
    with st.expander("🔄 Reorder Grid", expanded=False):
        col_order, col_info = st.columns([3, 1])
        with col_order:
             new_order_str = st.text_input(
                "Set Order by ID (e.g. 2,0,1)", 
                value=",".join(map(str, current_ids)),
                help="ID 0 = Slot 1 Upload, ID 1 = Slot 2 Upload, etc."
            )
        with col_info:
            if st.button("Update Order"):
                 try:
                    new_indices = [int(x.strip()) for x in new_order_str.split(",")]
                    # Validate
                    if sorted(new_indices) != sorted(current_ids):
                         st.error("Invalid IDs. Must match current images.")
                    else:
                        # Rebuild list in new order
                        reordered_posts = []
                        for new_idx in new_indices:
                             post = next(p for p in st.session_state.posts if p['id'] == new_idx)
                             reordered_posts.append(post)
                        st.session_state.posts = reordered_posts
                        st.rerun()
                 except Exception as e:
                     st.error(f"Invalid format: {e}")

    # Display Columns (Left - Middle - Right)
    cols = st.columns(3)
    
    for idx, col in enumerate(cols):
        post = st.session_state.posts[idx]
        with col:
            st.image(post['file'], use_container_width=True)
            st.caption(f"Position {idx + 1} ({['Left', 'Middle', 'Right'][idx]}) - ID: {post['id']}")
            
            # Editable Caption
            new_caption = st.text_area(
                f"Caption", 
                value=post['caption'], 
                height=150,
                key=f"caption_{post['id']}" 
            )
            post['caption'] = new_caption


    # Metrics & Strategy
    if st.session_state.analysis_result:
        res = st.session_state.analysis_result
        st.markdown("---")
        st.subheader("3. Strategy & Coherence")
        
        # Coherence
        score = res['coherence_score']
        st.markdown(f"**Visual Coherence Score**: {score}/100")
        st.progress(score / 100)
        st.caption(res['coherence_reasoning'])
        
        # Hashtags (Per Image)
        st.markdown("#### Hashtags Strategy")
        
        # Ensure hashtags is a list (backward compat)
        hashtags_list = res['hashtags'] if isinstance(res['hashtags'], list) else [res['hashtags']]*3
        
        cols_ladders = st.columns(3)
        
        for idx, col in enumerate(cols_ladders):
            with col:
                st.markdown(f"**Image {idx+1} Hashtags**")
                ladder = hashtags_list[idx]
                
                with st.expander("🌍 Broad", expanded=True):
                    st.code(" ".join([f"#{t}" for t in ladder['broad']]), language="markdown")
                with st.expander("🎯 Niche", expanded=True):
                    st.code(" ".join([f"#{t}" for t in ladder['niche']]), language="markdown")
                with st.expander("💎 Specific", expanded=True):
                    st.code(" ".join([f"#{t}" for t in ladder['specific']]), language="markdown")

        if st.button("Append Hashtags to Captions"):
            for idx, post in enumerate(st.session_state.posts):
                ladder = hashtags_list[idx]
                all_tags = "\n\n" + " ".join([f"#{t}" for t in ladder['broad'] + ladder['niche'] + ladder['specific']])
                post['caption'] += all_tags
            st.rerun()

    # --- 3. PUBLICATION ---
    st.markdown("---")
    st.subheader("4. Publication (Graph API)")
    
    with st.form("instagram_graph"):
        col_id, col_token = st.columns(2)
        with col_id:
            ig_user_id = st.text_input("Instagram User ID", value=os.getenv("IG_USER_ID", ""))
        with col_token:
            access_token = st.text_input("Access Token", type="password", value=os.getenv("IG_ACCESS_TOKEN", ""))
        
        submit_post = st.form_submit_button("🚀 Post to Instagram Grid")
        
    if submit_post:
        if not ig_user_id or not access_token:
            st.error("Veuillez renseigner l'Instagram User ID et l'Access Token.")
        else:
            with st.spinner("Publication via Graph API en cours..."):
                try:
                    post_payload_list = []
                    for post in st.session_state.posts:
                        post_payload_list.append({
                            "image_base64": post['base64'],
                            "caption": post['caption']
                        })
                    
                    req_body = {
                        "ig_user_id": ig_user_id,
                        "access_token": access_token,
                        "posts": post_payload_list
                    }
                    
                    post_res = requests.post(f"{API_URL}/post", json=req_body)
                    
                    if post_res.status_code == 200:
                        data = post_res.json()
                        st.balloons()
                        st.success("✅ " + data['message'])
                        st.write("Execution Log:")
                        st.json(data['logs'])
                    else:
                        st.error(f"Posting Failed: {post_res.text}")
                        
                except Exception as e:
                    st.error(f"Error: {e}")
