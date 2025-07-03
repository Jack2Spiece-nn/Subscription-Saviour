import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    WEBHOOK_PATH = f"/bot/{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else None
    
    # Admin Settings
    ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))
    
    # Database Settings
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///subscriptions.db')
    
    # Redis Settings (for Celery)
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Flask Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Pro Plan Settings
    PRO_PLAN_PRICE = os.getenv('PRO_PLAN_PRICE', '$4.99/month')
    
    # Render Settings
    PORT = int(os.getenv('PORT', 5000))
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not cls.WEBHOOK_URL:
            raise ValueError("WEBHOOK_URL is required")
        if not cls.ADMIN_USER_ID:
            raise ValueError("ADMIN_USER_ID is required")