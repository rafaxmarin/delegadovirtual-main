import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    VERSION: str = "2.1.0"
    APP_NAME: str = "Delegado Virtual"
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    ACTIVE_AI_PROVIDER: str = os.getenv('ACTIVE_AI_PROVIDER', 'gemini')
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL: str = os.getenv('GEMINI_MODEL', 'gemini-flash-latest')
    DEEPSEEK_API_KEY: str = os.getenv('DEEPSEEK_API_KEY', '')
    DEEPSEEK_MODEL: str = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    PROFESOR_PASSWORD: str = os.getenv('PROFESOR_PASSWORD', '')
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', 'delegado_virtual.db')
    DB_TYPE: str = os.getenv('DB_TYPE', 'sqlite').lower()
    FIREBASE_CREDENTIALS_PATH: str = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')
    FIREBASE_CREDENTIALS_JSON: str = os.getenv('FIREBASE_CREDENTIALS_JSON', '')

    @classmethod
    def _update_env_file(cls, key_name: str, value: str):
        """Actualiza o agrega una variable en el archivo .env"""
        env_file = '.env'
        lines = []
        key_found = False
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines):
                if line.startswith(f"{key_name}="):
                    lines[i] = f"{key_name}={value}\n"
                    key_found = True
                    break
        
        if not key_found:
            lines.append(f"{key_name}={value}\n")

        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    @classmethod
    def set_active_ai_provider(cls, provider: str) -> bool:
        provider_clean = provider.lower().strip()
        if provider_clean in ['gemini', 'deepseek']:
            cls.ACTIVE_AI_PROVIDER = provider_clean
            os.environ['ACTIVE_AI_PROVIDER'] = provider_clean
            cls._update_env_file('ACTIVE_AI_PROVIDER', provider_clean)
            return True
        return False

    @classmethod
    def set_gemini_api_key(cls, key: str) -> bool:
        """Actualiza la clave API de Gemini en memoria y la persiste en .env"""
        cls.GEMINI_API_KEY = key
        os.environ['GEMINI_API_KEY'] = key
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
        except Exception:
            pass
        cls._update_env_file('GEMINI_API_KEY', key)
        return True

    @classmethod
    def set_gemini_model(cls, model_name: str) -> bool:
        """Actualiza el modelo de Gemini"""
        cls.GEMINI_MODEL = model_name
        os.environ['GEMINI_MODEL'] = model_name
        cls._update_env_file('GEMINI_MODEL', model_name)
        return True

    @classmethod
    def set_deepseek_api_key(cls, key: str) -> bool:
        """Actualiza la clave API de DeepSeek"""
        cls.DEEPSEEK_API_KEY = key
        os.environ['DEEPSEEK_API_KEY'] = key
        cls._update_env_file('DEEPSEEK_API_KEY', key)
        return True

    @classmethod
    def set_deepseek_model(cls, model_name: str) -> bool:
        """Actualiza el modelo de DeepSeek"""
        cls.DEEPSEEK_MODEL = model_name
        os.environ['DEEPSEEK_MODEL'] = model_name
        cls._update_env_file('DEEPSEEK_MODEL', model_name)
        return True

    @classmethod
    def validate(cls):
        missing = []
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append('TELEGRAM_BOT_TOKEN')
        if missing:
            print(f"⚠️ ADVERTENCIA: Variables de entorno faltantes: {', '.join(missing)}")


