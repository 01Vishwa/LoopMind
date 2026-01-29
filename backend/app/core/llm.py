import os
from langchain_openai import ChatOpenAI

def get_llm():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    return ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=api_key)
