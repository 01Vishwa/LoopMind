import streamlit as st
from utils.api_client import APIClient

def render_sidebar():
    with st.sidebar:
        st.header("📂 Data Source")
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        
        if uploaded_file is not None:
            if "file_id" not in st.session_state:
                with st.spinner("Uploading..."):
                    result = APIClient.upload_file(uploaded_file)
                    if "file_id" in result:
                        st.session_state["file_id"] = result["file_id"]
                        st.session_state["filename"] = result["filename"]
                        st.success(f"Uploaded: {result['filename']}")
                    else:
                        st.error("Upload failed")
        
        if "file_id" in st.session_state:
            st.info(f"Active File: {st.session_state['filename']}")
