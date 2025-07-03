#!/usr/bin/env python3
"""
Subscription Savor - Background Worker
Celery worker for handling background tasks like sending reminders
"""

import logging
from app.config import Config
from app.scheduler import celery_app

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Start the Celery worker"""
    try:
        # Validate configuration
        Config.validate()
        logger.info("✅ Configuration validated for worker")
        
        # Initialize database
        from app.database import init_db
        init_db()
        logger.info("✅ Database initialized for worker")
        
        logger.info("🔧 Starting Celery worker for background tasks...")
        
        # Start the worker
        celery_app.worker_main([
            'worker',
            '--loglevel=info',
            '--concurrency=2',
            '--beat'  # Include beat scheduler
        ])
        
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        exit(1)
        
    except Exception as e:
        logger.error(f"❌ Worker error: {e}")
        exit(1)

if __name__ == '__main__':
    main()