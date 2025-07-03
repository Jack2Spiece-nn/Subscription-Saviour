#!/usr/bin/env python3
"""
Subscription Savor - Telegram Bot
Main application entry point
"""

import os
import sys
import logging
from app.config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    try:
        # Validate configuration
        Config.validate()
        logger.info("✅ Configuration validated successfully")
        
        # Initialize database
        from app.database import init_db
        init_db()
        logger.info("✅ Database initialized")
        
        # Start the webhook server
        from app.webhook import app, setup_webhook
        
        # Setup webhook
        setup_webhook()
        
        # Run the Flask app
        port = Config.PORT
        logger.info(f"🚀 Starting Subscription Savor Bot on port {port}")
        
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
        
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.error("Please check your environment variables:")
        logger.error("- TELEGRAM_BOT_TOKEN")
        logger.error("- WEBHOOK_URL") 
        logger.error("- ADMIN_USER_ID")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Application error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()