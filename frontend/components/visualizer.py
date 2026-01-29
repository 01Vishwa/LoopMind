import streamlit as st
import plotly.io as pio
from utils.api_client import APIClient

def render_visualizer(plot_json: dict, plot_type: str = "unknown"):
    if not plot_json:
        return

    st.subheader("📊 Visualization")
    # Plotly assumes valid JSON
    try:
        fig = pio.from_json(str(plot_json).replace("'", '"')) # Simple quote fix if needed
        # Better: if backend returns dict, just pass it to st.plotly_chart or convert to fig
        # pio.from_json takes string. 
        # If plot_json is a dict, we can use graph_objects or just pass to st.plotly_chart directly if it supports dict (it usually expects Figure).
        # Safe way:
        import plotly.graph_objs as go
        if "data" in plot_json and "layout" in plot_json:
             fig = go.Figure(data=plot_json["data"], layout=plot_json.get("layout"))
             st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Could not render chart: {e}")
        return

    st.write("Was this chart useful?")
    col1, col2 = st.columns(2)
    
    # Context gathering (mock)
    context = {
        "row_count": 100,
        "dtype": "mixed"
    }

    with col1:
        if st.button("👍 Good", key=f"good_{plot_type}"):
            APIClient.send_feedback(plot_type, 1.0, context)
            st.toast("Feedback recorded!")
    
    with col2:
        if st.button("👎 Bad", key=f"bad_{plot_type}"):
            APIClient.send_feedback(plot_type, -1.0, context)
            st.toast("Feedback recorded!")
