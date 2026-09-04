import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "governx-ai-demo-secret-key")
    DATABASE = os.path.join(os.path.dirname(__file__), "database.db")
