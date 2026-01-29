import os
import shutil
import pandas as pd
import uuid

DATA_DIR = "/data"

class FileManager:
    @staticmethod
    def save_upload(file_obj) -> str:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        file_id = str(uuid.uuid4())
        # Preserve extension
        ext = os.path.splitext(file_obj.filename)[1]
        file_path = os.path.join(DATA_DIR, f"{file_id}{ext}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file_obj.file, buffer)
            
        return file_id

    @staticmethod
    def get_file_path(file_id: str) -> str:
        # Simple lookup: find file starting with file_id in data dir
        if not os.path.exists(DATA_DIR):
            return None
        for f in os.listdir(DATA_DIR):
            if f.startswith(file_id):
                return os.path.join(DATA_DIR, f)
        return None

    @staticmethod
    def read_csv(file_id: str) -> pd.DataFrame:
        path = FileManager.get_file_path(file_id)
        if path:
            return pd.read_csv(path)
        raise FileNotFoundError("File not found")
