import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from app.scheduler import ReminderScheduler, send_scheduled_reminders
from app.database import Subscription, User, ReminderType, PlanType

@pytest.fixture
def mock_scheduler():
    """Create a mock scheduler for testing"""
    with patch('app.scheduler.Config') as mock_config:
        mock_config.TELEGRAM_BOT_TOKEN = 'test_token'
        scheduler = ReminderScheduler()
        scheduler.bot = Mock()
        scheduler.bot.send_message = AsyncMock()
        return scheduler

@pytest.mark.asyncio
async def test_send_reminder_success(mock_scheduler):
    """Test successful reminder sending"""
    # Create mock subscription and user
    subscription = Mock()
    subscription.id = 1
    subscription.service_name = "Netflix"
    subscription.end_date = datetime.utcnow() + timedelta(days=2)
    subscription.cost = "$9.99/month"
    subscription.notes = None
    
    user = Mock()
    user.telegram_id = 123456789
    user.plan_type = PlanType.FREE
    
    # Mock database update
    with patch('app.scheduler.get_db') as mock_get_db:
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = subscription
        
        result = await mock_scheduler.send_reminder(subscription, user)
        
        # Verify reminder was sent
        assert result == True
        mock_scheduler.bot.send_message.assert_called_once()
        
        # Check message content
        call_args = mock_scheduler.bot.send_message.call_args
        assert call_args[1]['chat_id'] == user.telegram_id
        assert "Netflix" in call_args[1]['text']
        assert "expires in 2 days" in call_args[1]['text']

@pytest.mark.asyncio
async def test_send_reminder_with_notes(mock_scheduler):
    """Test reminder sending with Pro user notes"""
    subscription = Mock()
    subscription.id = 1
    subscription.service_name = "Adobe Creative Suite"
    subscription.end_date = datetime.utcnow() + timedelta(days=1)
    subscription.cost = "$52.99/month"
    subscription.notes = "Remember to export all projects first!"
    
    user = Mock()
    user.telegram_id = 123456789
    user.plan_type = PlanType.PRO
    
    with patch('app.scheduler.get_db') as mock_get_db:
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = subscription
        
        result = await mock_scheduler.send_reminder(subscription, user)
        
        assert result == True
        call_args = mock_scheduler.bot.send_message.call_args
        assert "Your Notes" in call_args[1]['text']
        assert "Remember to export all projects first!" in call_args[1]['text']

def test_reminder_offset_calculation(mock_scheduler):
    """Test reminder offset day calculation"""
    assert mock_scheduler.get_reminder_offset_days(ReminderType.ONE_DAY) == 1
    assert mock_scheduler.get_reminder_offset_days(ReminderType.TWO_DAYS) == 2
    assert mock_scheduler.get_reminder_offset_days(ReminderType.THREE_DAYS) == 3
    assert mock_scheduler.get_reminder_offset_days(ReminderType.SEVEN_DAYS) == 7

@pytest.mark.asyncio
async def test_process_pending_reminders(mock_scheduler):
    """Test processing multiple pending reminders"""
    # Create mock subscriptions
    now = datetime.utcnow()
    
    subscription1 = Mock()
    subscription1.id = 1
    subscription1.service_name = "Netflix"
    subscription1.end_date = now + timedelta(days=2)
    subscription1.reminder_type = ReminderType.TWO_DAYS
    subscription1.user_id = 123456789
    
    subscription2 = Mock()
    subscription2.id = 2
    subscription2.service_name = "Spotify"
    subscription2.end_date = now + timedelta(days=3)
    subscription2.reminder_type = ReminderType.THREE_DAYS
    subscription2.user_id = 987654321
    
    user1 = Mock()
    user1.telegram_id = 123456789
    user1.is_active = True
    user1.plan_type = PlanType.FREE
    
    user2 = Mock()
    user2.telegram_id = 987654321
    user2.is_active = True
    user2.plan_type = PlanType.PRO
    
    with patch('app.scheduler.get_db') as mock_get_db:
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        # Mock subscriptions query
        mock_db.query.return_value.filter.return_value.all.return_value = [subscription1, subscription2]
        
        # Mock user queries
        def mock_user_query(model):
            if model == User:
                user_query = Mock()
                def filter_func(condition):
                    # Return appropriate user based on telegram_id
                    result = Mock()
                    if hasattr(condition, 'left') and hasattr(condition.left, 'key'):
                        if '123456789' in str(condition):
                            result.first.return_value = user1
                        else:
                            result.first.return_value = user2
                    else:
                        result.first.return_value = user1
                    return result
                user_query.filter = filter_func
                return user_query
            return mock_db.query.return_value
        
        mock_db.query.side_effect = mock_user_query
        
        # Mock successful reminder sending
        with patch.object(mock_scheduler, 'send_reminder', return_value=True) as mock_send:
            result = await mock_scheduler.process_pending_reminders()
            
            # Should process both subscriptions
            assert mock_send.call_count == 2
            assert result == 2

@pytest.mark.asyncio 
async def test_cleanup_expired_subscriptions(mock_scheduler):
    """Test cleanup of expired subscriptions"""
    with patch('app.scheduler.get_db') as mock_get_db:
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        # Mock query to return 3 expired subscriptions
        mock_db.query.return_value.filter.return_value.update.return_value = 3
        
        result = await mock_scheduler.cleanup_expired_subscriptions()
        
        assert result == 3
        mock_db.commit.assert_called_once()

def test_celery_task_configuration():
    """Test Celery task is properly configured"""
    from app.scheduler import celery_app
    
    # Check if beat schedule is configured
    assert 'send-reminders-every-hour' in celery_app.conf.beat_schedule
    
    # Check schedule interval (should be 1 hour = 3600 seconds)
    schedule = celery_app.conf.beat_schedule['send-reminders-every-hour']
    assert schedule['schedule'] == 3600.0
    assert schedule['task'] == 'app.scheduler.send_scheduled_reminders'