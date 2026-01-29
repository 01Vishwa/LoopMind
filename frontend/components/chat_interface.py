import streamlit as st
from utils.api_client import APIClient
from components.visualizer import render_visualizer

def render_chat():
    st.header("💬 Chat with Data")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "plot" in msg:
                render_visualizer(msg["plot"], msg.get("plot_type", "chart"))

    if prompt := st.chat_input("Ask a question..."):
        if "file_id" not in st.session_state:
            st.error("Please upload a file first.")
            return

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = APIClient.analyze(prompt, st.session_state["file_id"])
                
                if "error" in response:
                    st.error(response["error"])
                else:
                    ans = response.get("answer", "")
                    plot = response.get("plot_json")
                    
                    st.markdown(ans)
                    
                    # Store in history
                    msg_data = {"role": "assistant", "content": ans}
                    
                    if plot:
                        # Extract type from plot if possible or assume from backend? 
                        # Backend didn't return type explicitly, but viz worker generated it.
                        # We can guess or just say "generated".
                        # For feedback to work, we need the action name.
                        # The backend currently creates plot but doesn't return the action used clearly 
                        # other than inside the plot logic.
                        # We will assume 'bar' or similar if we could parse, 
                        # OR update backend to return 'action_taken'.
                        # For now, simplistic:
                        msg_data["plot"] = plot
                        msg_data["plot_type"] = "bar" # Placeholder catch-all if not returned.
                        render_visualizer(plot)
                    
                    st.session_state.messages.append(msg_data)
