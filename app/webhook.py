import logging
import asyncio
import threading
from flask import Flask, request, Response
from telegram import Update
from app.config import Config
from app.bot_handlers import bot_instance
from app.database import init_db
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Initialize database
init_db()

# Thread-safe application initialization
_application_initialized = False
_initialization_lock = threading.Lock()
# New: global shared event loop infrastructure
_event_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None

# Helper to start the event loop in a dedicated background thread

def _start_event_loop(loop: asyncio.AbstractEventLoop):
    """Run *loop* forever inside its own OS thread."""
    asyncio.set_event_loop(loop)
    loop.run_forever()

def initialize_application_sync():
    """Initialize the bot application synchronously (thread-safe)"""
    global _application_initialized
    
    # Double-checked locking pattern for thread safety
    if not _application_initialized:
        with _initialization_lock:
            # Check again inside the lock to avoid race condition
            if not _application_initialized:
                try:
                    # New: create (or reuse) the global event loop running in a background thread
                    global _event_loop, _loop_thread
                    if _event_loop is None:
                        _event_loop = asyncio.new_event_loop()
                        _loop_thread = threading.Thread(target=_start_event_loop, args=(_event_loop,), daemon=True)
                        _loop_thread.start()

                    # At this point, _event_loop is guaranteed to be initialized
                    assert _event_loop is not None

                    application = bot_instance.get_application()

                    # Run the asynchronous initialization in the background event loop
                    future = asyncio.run_coroutine_threadsafe(application.initialize(), _event_loop)
                    future.result()  # Wait until initialization completes

                    _application_initialized = True
                    logger.info("Bot application initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize bot application: {str(e)}")
                    raise

def ensure_application_ready():
    """Ensure the bot application is ready to handle requests"""
    if not _application_initialized:
        initialize_application_sync()

    # Static type safety – _event_loop is set by ensure_application_ready
    assert _event_loop is not None

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Subscription Savor Bot"}

@app.route(Config.WEBHOOK_PATH, methods=['POST'])
def telegram_webhook():
    """Handle incoming Telegram webhook updates"""
    try:
        # Get update from request
        update_data = request.get_json()
        logger.info("Received webhook update")
        
        if not update_data:
            logger.warning("Received empty update")
            return Response(status=200)
        
        # Create Update object
        application = bot_instance.get_application()
        update = Update.de_json(update_data, application.bot)
        
        if not update:
            logger.warning("Failed to parse update")
            return Response(status=200)
        
        logger.info(f"Processing update for user: {update.effective_user.id if update.effective_user else 'unknown'}")
        
        # Ensure the application and shared event loop are ready
        ensure_application_ready()

        # Type-narrow the global _event_loop for static analysers
        loop = _event_loop
        assert loop is not None  # noqa: S101 – narrow Optional to concrete loop

        try:
            # Submit processing of the update to the shared event loop and wait for completion
            future = asyncio.run_coroutine_threadsafe(application.process_update(update), loop)
            future.result()
            logger.info("Update processed successfully")
        except Exception as e:
            logger.error(f"Error processing update: {str(e)}", exc_info=True)
        
        return Response(status=200)
        
    except Exception as e:
        logger.error(f"Error in webhook handler: {str(e)}", exc_info=True)
        return Response(status=500)

@app.route('/set_webhook', methods=['POST'])
def set_webhook():
    """Set the webhook URL (for admin use)"""
    try:
        webhook_url = f"{Config.WEBHOOK_URL}{Config.WEBHOOK_PATH}"
        
        # Use synchronous approach for webhook setup
        import requests
        
        telegram_api_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/setWebhook"
        
        response = requests.post(telegram_api_url, json={
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query"]
        })
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                logger.info(f"Webhook set successfully to {webhook_url}")
                return {"success": True, "webhook_url": webhook_url}
            else:
                logger.error(f"Failed to set webhook: {result}")
                return {"success": False, "error": result.get("description")}
        else:
            logger.error(f"HTTP error setting webhook: {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Error setting webhook: {str(e)}")
        return {"success": False, "error": str(e)}

@app.route('/webhook_info', methods=['GET'])
def webhook_info():
    """Get current webhook information"""
    try:
        import requests
        
        telegram_api_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/getWebhookInfo"
        response = requests.get(telegram_api_url)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Error getting webhook info: {str(e)}")
        return {"error": str(e)}

@app.route('/stats', methods=['GET'])
def bot_stats():
    """Get bot statistics (for monitoring)"""
    try:
        from app.database import get_db, User, Subscription, PlanType
        
        with get_db() as db:
            total_users = db.query(User).count()
            pro_users = db.query(User).filter(User.plan_type == PlanType.PRO).count()
            active_subscriptions = db.query(Subscription).filter(Subscription.is_active == True).count()
            
            return {
                "total_users": total_users,
                "pro_users": pro_users,
                "active_subscriptions": active_subscriptions,
                "conversion_rate": round((pro_users / total_users * 100), 2) if total_users > 0 else 0
            }
            
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return {"error": str(e)}

# Auto-setup webhook on startup
def setup_webhook():
    """Setup webhook on application startup"""
    try:
        import requests
        import time
        import asyncio
        
        # Wait a bit for the service to be ready
        time.sleep(2)
        
        # Initialize the bot application
        initialize_application_sync()
        
        webhook_url = f"{Config.WEBHOOK_URL}{Config.WEBHOOK_PATH}"
        telegram_api_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/setWebhook"
        
        response = requests.post(telegram_api_url, json={
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query"]
        }, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                logger.info(f"✅ Webhook set successfully to {webhook_url}")
            else:
                logger.error(f"❌ Failed to set webhook: {result}")
        else:
            logger.error(f"❌ HTTP error setting webhook: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Error setting up webhook: {str(e)}")

# Initialize application on Flask startup
def create_app():
    """Application factory pattern for proper initialization"""
    try:
        initialize_application_sync()
    except Exception as e:
        logger.error(f"Failed to initialize application on startup: {str(e)}")
        # Don't raise here to allow Flask to start, but log the error
    return app

# For production servers like Gunicorn, initialize immediately
try:
    initialize_application_sync()
except Exception as e:
    logger.error(f"Failed to initialize application: {str(e)}")

if __name__ == '__main__':
    # Setup webhook when running directly
    setup_webhook()
    
    # Run Flask app
    port = Config.PORT
    app.run(host='0.0.0.0', port=port, debug=False)