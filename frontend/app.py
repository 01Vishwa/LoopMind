import streamlit as st
from components.sidebar import render_sidebar
from components.chat_interface import render_chat

st.set_page_config(page_title="AutoGraph", page_icon="📈", layout="wide")

st.title("AutoGraph 📈")
st.markdown("### Autonomous Data Analyst with RL-driven Visualization")

render_sidebar()
render_chat()
