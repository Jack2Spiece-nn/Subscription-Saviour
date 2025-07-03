import logging
import asyncio
from datetime import datetime, timedelta
from typing import List
from celery import Celery
from telegram import Bot
from sqlalchemy.orm import Session
from app.config import Config
from app.database import get_db, Subscription, Reminder, User, ReminderType, PlanType
from app.keyboards import get_reminder_action_keyboard

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery('subscription_savor', broker=Config.REDIS_URL)

class ReminderScheduler:
    def __init__(self):
        self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    
    async def send_reminder(self, subscription: Subscription, user: User) -> bool:
        """Send a reminder message to the user"""
        try:
            days_left = (subscription.end_date - datetime.utcnow()).days
            
            # Create reminder message
            reminder_text = f"""
🚨 **Subscription Reminder**

⚠️ **{subscription.service_name}** expires in {days_left} day{'s' if days_left != 1 else ''}!

📅 **Expiry Date**: {subscription.end_date.strftime('%Y-%m-%d')}
💰 **Cost**: {subscription.cost or 'Not specified'}
"""
            
            if user.plan_type == PlanType.PRO and subscription.notes:
                reminder_text += f"📝 **Your Notes**: {subscription.notes}\n"
            
            reminder_text += f"""
**Don't forget to cancel if you don't want to continue!**

Take action now:
"""
            
            # Send reminder with action buttons
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=reminder_text,
                reply_markup=get_reminder_action_keyboard(subscription.id, user.plan_type),
                parse_mode='Markdown'
            )
            
            # Update subscription reminded status
            with get_db() as db:
                sub = db.query(Subscription).filter(Subscription.id == subscription.id).first()
                if sub:
                    sub.reminded_at = datetime.utcnow()
                    db.commit()
            
            logger.info(f"Reminder sent successfully to user {user.telegram_id} for subscription {subscription.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send reminder to user {user.telegram_id}: {str(e)}")
            return False
    
    def get_reminder_offset_days(self, reminder_type: ReminderType) -> int:
        """Get the number of days before expiry to send reminder"""
        mapping = {
            ReminderType.ONE_DAY: 1,
            ReminderType.TWO_DAYS: 2,
            ReminderType.THREE_DAYS: 3,
            ReminderType.SEVEN_DAYS: 7
        }
        return mapping.get(reminder_type, 2)  # Default to 2 days
    
    async def process_pending_reminders(self):
        """Process all pending reminders"""
        with get_db() as db:
            # Get all active subscriptions that need reminders
            subscriptions = db.query(Subscription).filter(
                Subscription.is_active == True,
                Subscription.reminded_at.is_(None)  # Not yet reminded
            ).all()
            
            reminders_sent = 0
            
            for subscription in subscriptions:
                # Calculate when to send reminder
                reminder_offset = self.get_reminder_offset_days(subscription.reminder_type)
                reminder_date = subscription.end_date - timedelta(days=reminder_offset)
                
                # Check if it's time to send the reminder
                if datetime.utcnow() >= reminder_date:
                    # Get user info
                    user = db.query(User).filter(User.telegram_id == subscription.user_id).first()
                    
                    if user and user.is_active:
                        success = await self.send_reminder(subscription, user)
                        if success:
                            reminders_sent += 1
                        
                        # Add a small delay to avoid rate limiting
                        await asyncio.sleep(0.1)
            
            logger.info(f"Processed reminders: {reminders_sent} sent")
            return reminders_sent
    
    async def cleanup_expired_subscriptions(self):
        """Mark expired subscriptions as inactive"""
        with get_db() as db:
            expired_count = db.query(Subscription).filter(
                Subscription.is_active == True,
                Subscription.end_date < datetime.utcnow()
            ).update({"is_active": False})
            
            db.commit()
            logger.info(f"Marked {expired_count} expired subscriptions as inactive")
            return expired_count

# Celery tasks
@celery_app.task
def send_scheduled_reminders():
    """Celery task to send scheduled reminders"""
    try:
        scheduler = ReminderScheduler()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Process reminders
        reminders_sent = loop.run_until_complete(scheduler.process_pending_reminders())
        
        # Cleanup expired subscriptions
        expired_cleaned = loop.run_until_complete(scheduler.cleanup_expired_subscriptions())
        
        loop.close()
        
        return {
            "reminders_sent": reminders_sent,
            "expired_cleaned": expired_cleaned,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in scheduled reminder task: {str(e)}")
        raise

@celery_app.task
def send_individual_reminder(subscription_id: int):
    """Send a reminder for a specific subscription"""
    try:
        scheduler = ReminderScheduler()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        with get_db() as db:
            subscription = db.query(Subscription).filter(
                Subscription.id == subscription_id,
                Subscription.is_active == True
            ).first()
            
            if subscription:
                user = db.query(User).filter(User.telegram_id == subscription.user_id).first()
                if user:
                    success = loop.run_until_complete(scheduler.send_reminder(subscription, user))
                    loop.close()
                    return {"success": success, "subscription_id": subscription_id}
        
        loop.close()
        return {"success": False, "error": "Subscription or user not found"}
        
    except Exception as e:
        logger.error(f"Error sending individual reminder: {str(e)}")
        raise

# Configure Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'send-reminders-every-hour': {
        'task': 'app.scheduler.send_scheduled_reminders',
        'schedule': 3600.0,  # Every hour
    },
}
celery_app.conf.timezone = 'UTC'

# Helper function to start background tasks
def setup_scheduler():
    """Setup and start the reminder scheduler"""
    logger.info("Reminder scheduler setup complete")
    return celery_app