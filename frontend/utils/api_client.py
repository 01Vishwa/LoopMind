import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

class APIClient:
    @staticmethod
    def upload_file(file):
        files = {"file": (file.name, file, file.type)}
        try:
            response = requests.post(f"{BACKEND_URL}/upload", files=files)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def analyze(query: str, file_id: str):
        payload = {"query": query, "file_id": file_id}
        try:
            response = requests.post(f"{BACKEND_URL}/analyze", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def send_feedback(action: str, reward: float, context: dict):
        payload = {"action": action, "reward": reward, "context": context}
        try:
            requests.post(f"{BACKEND_URL}/feedback", json=payload)
        except:
            pass
