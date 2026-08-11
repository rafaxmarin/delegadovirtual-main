import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    VERSION: str = "2.0.0"
    APP_NAME: str = "Delegado Virtual"
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL: str = os.getenv('GEMINI_MODEL', 'gemini-flash-latest')
    PROFESOR_PASSWORD: str = os.getenv('PROFESOR_PASSWORD', '')
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', 'delegado_virtual.db')

    @classmethod
    def validate(cls):
        missing = []
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append('TELEGRAM_BOT_TOKEN')
        if not cls.GEMINI_API_KEY:
            missing.append('GEMINI_API_KEY')
        if missing:
            print(f"⚠️ ADVERTENCIA: Variables de entorno faltantes: {', '.join(missing)}")
