from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
from enum import Enum
import pytz
from app.config import Config

# Database setup
engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Enums
class PlanType(Enum):
    FREE = "free"
    PRO = "pro"

class SubscriptionType(Enum):
    TRIAL = "trial"
    RECURRING = "recurring"

class ReminderType(Enum):
    SEVEN_DAYS = "7_days"
    THREE_DAYS = "3_days"
    ONE_DAY = "1_day"
    TWO_DAYS = "2_days"  # Default for free users

# Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    plan_type = Column(SQLEnum(PlanType), default=PlanType.FREE)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_interaction = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)  # References users.telegram_id
    service_name = Column(String, nullable=False)
    subscription_type = Column(SQLEnum(SubscriptionType), default=SubscriptionType.TRIAL)
    cost = Column(String, nullable=True)  # Store as string for flexibility
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    reminder_type = Column(SQLEnum(ReminderType), default=ReminderType.TWO_DAYS)
    notes = Column(Text, nullable=True)  # Pro feature
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reminded_at = Column(DateTime, nullable=True)

class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    reminder_date = Column(DateTime, nullable=False)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)

class BotStats(Base):
    __tablename__ = "bot_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    total_users = Column(Integer, default=0)
    pro_users = Column(Integer, default=0)
    active_subscriptions = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)

# Database utility functions
def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_user_by_telegram_id(db: Session, telegram_id: int) -> User:
    """Get or create user by Telegram ID"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def update_user_interaction(db: Session, telegram_id: int):
    """Update user's last interaction time"""
    user = get_user_by_telegram_id(db, telegram_id)
    user.last_interaction = datetime.utcnow()
    db.commit()

def get_active_subscriptions_count(db: Session, user_id: int) -> int:
    """Get count of active subscriptions for a user"""
    return db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.is_active == True
    ).count()

def can_add_subscription(db: Session, user_id: int) -> bool:
    """Check if user can add more subscriptions based on their plan"""
    user = get_user_by_telegram_id(db, user_id)
    if user.plan_type == PlanType.PRO:
        return True
    
    active_count = get_active_subscriptions_count(db, user_id)
    return active_count < 3  # Free plan limit

def upgrade_user_to_pro(db: Session, telegram_id: int):
    """Upgrade user to Pro plan"""
    user = get_user_by_telegram_id(db, telegram_id)
    user.plan_type = PlanType.PRO
    db.commit()

def calculate_savings(db: Session, user_id: int) -> dict:
    """Calculate potential savings for Pro users"""
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.is_active == False  # Canceled subscriptions
    ).all()
    
    # This is a simplified calculation
    # In a real app, you'd parse the cost field and calculate based on subscription periods
    total_saved = len(subscriptions) * 10  # Assume $10 average savings per canceled subscription
    
    return {
        "canceled_subscriptions": len(subscriptions),
        "estimated_savings": f"${total_saved}",
        "avg_savings_per_sub": "$10"
    }