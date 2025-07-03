import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, User, Subscription, PlanType, SubscriptionType, ReminderType
from app.database import get_user_by_telegram_id, can_add_subscription, calculate_savings

# Test database setup
@pytest.fixture
def test_db():
    """Create a test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def test_user_creation(test_db):
    """Test user creation and retrieval"""
    telegram_id = 123456789
    
    # Test user creation
    user = get_user_by_telegram_id(test_db, telegram_id)
    assert user.telegram_id == telegram_id
    assert user.plan_type == PlanType.FREE
    assert user.is_active == True
    
    # Test user retrieval (should not create duplicate)
    user2 = get_user_by_telegram_id(test_db, telegram_id)
    assert user.id == user2.id

def test_subscription_limits(test_db):
    """Test subscription limits for free vs pro users"""
    telegram_id = 123456789
    user = get_user_by_telegram_id(test_db, telegram_id)
    
    # Free user should be able to add 3 subscriptions
    assert can_add_subscription(test_db, telegram_id) == True
    
    # Add 3 subscriptions
    for i in range(3):
        sub = Subscription(
            user_id=telegram_id,
            service_name=f"Service {i+1}",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30)
        )
        test_db.add(sub)
    test_db.commit()
    
    # Should not be able to add 4th subscription
    assert can_add_subscription(test_db, telegram_id) == False
    
    # Upgrade to Pro
    user.plan_type = PlanType.PRO
    test_db.commit()
    
    # Pro user should be able to add unlimited subscriptions
    assert can_add_subscription(test_db, telegram_id) == True

def test_savings_calculation(test_db):
    """Test savings calculation"""
    telegram_id = 123456789
    
    # Add some canceled subscriptions
    for i in range(2):
        sub = Subscription(
            user_id=telegram_id,
            service_name=f"Canceled Service {i+1}",
            start_date=datetime.utcnow() - timedelta(days=60),
            end_date=datetime.utcnow() - timedelta(days=30),
            is_active=False
        )
        test_db.add(sub)
    test_db.commit()
    
    savings = calculate_savings(test_db, telegram_id)
    assert savings["canceled_subscriptions"] == 2
    assert savings["estimated_savings"] == "$20"

def test_subscription_creation(test_db):
    """Test subscription creation with different types"""
    telegram_id = 123456789
    
    # Test trial subscription
    trial_sub = Subscription(
        user_id=telegram_id,
        service_name="Netflix Trial",
        subscription_type=SubscriptionType.TRIAL,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=7),
        reminder_type=ReminderType.TWO_DAYS
    )
    test_db.add(trial_sub)
    test_db.commit()
    
    assert trial_sub.id is not None
    assert trial_sub.subscription_type == SubscriptionType.TRIAL
    assert trial_sub.is_active == True
    
    # Test recurring subscription
    recurring_sub = Subscription(
        user_id=telegram_id,
        service_name="Spotify Premium",
        subscription_type=SubscriptionType.RECURRING,
        cost="$9.99/month",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=30),
        reminder_type=ReminderType.THREE_DAYS
    )
    test_db.add(recurring_sub)
    test_db.commit()
    
    assert recurring_sub.id is not None
    assert recurring_sub.cost == "$9.99/month"