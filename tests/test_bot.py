import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.bot_handlers import SubscriptionBot
from app.database import User, PlanType
from app.config import Config

# Mock configuration for testing
@pytest.fixture
def mock_config():
    with patch.object(Config, 'TELEGRAM_BOT_TOKEN', 'test_token'):
        with patch.object(Config, 'WEBHOOK_URL', 'https://test.com'):
            with patch.object(Config, 'ADMIN_USER_ID', 123456789):
                yield Config

@pytest.fixture
def bot_instance(mock_config):
    """Create a bot instance for testing"""
    with patch('app.bot_handlers.Config') as mock_config_class:
        mock_config_class.return_value = mock_config
        mock_config_class.validate = Mock()
        bot = SubscriptionBot()
        return bot

@pytest.mark.asyncio
async def test_start_command(bot_instance):
    """Test the /start command"""
    # Mock update and context
    update = Mock()
    context = Mock()
    user = Mock()
    user.id = 123456789
    user.username = "testuser"
    user.first_name = "Test"
    update.effective_user = user
    update.message = Mock()
    update.message.reply_text = AsyncMock()
    
    # Mock database operations
    with patch('app.bot_handlers.get_db') as mock_get_db:
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        mock_user = Mock()
        mock_user.plan_type = PlanType.FREE
        
        with patch('app.bot_handlers.get_user_by_telegram_id', return_value=mock_user):
            with patch('app.bot_handlers.update_user_interaction'):
                with patch('app.bot_handlers.get_welcome_keyboard') as mock_keyboard:
                    with patch('app.bot_handlers.get_main_keyboard') as mock_main_keyboard:
                        await bot_instance.start_command(update, context)
                        
                        # Verify welcome message was sent
                        assert update.message.reply_text.call_count == 2
                        mock_keyboard.assert_called_once()
                        mock_main_keyboard.assert_called_once_with(PlanType.FREE)

@pytest.mark.asyncio
async def test_add_subscription_limit(bot_instance):
    """Test adding subscription when limit is reached"""
    update = Mock()
    context = Mock()
    user = Mock()
    user.id = 123456789
    update.effective_user = user
    update.message = Mock()
    update.message.reply_text = AsyncMock()
    
    # Mock database to return False for can_add_subscription
    with patch('app.bot_handlers.get_db') as mock_get_db:
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        with patch('app.bot_handlers.can_add_subscription', return_value=False):
            with patch('app.bot_handlers.update_user_interaction'):
                with patch('app.bot_handlers.get_upgrade_keyboard') as mock_keyboard:
                    await bot_instance.add_subscription_flow(update, context)
                    
                    # Verify limit message was sent
                    update.message.reply_text.assert_called_once()
                    call_args = update.message.reply_text.call_args[0][0]
                    assert "reached the free plan limit" in call_args
                    mock_keyboard.assert_called_once()

@pytest.mark.asyncio 
async def test_list_empty_subscriptions(bot_instance):
    """Test listing subscriptions when user has none"""
    update = Mock()
    context = Mock()
    user = Mock()
    user.id = 123456789
    update.effective_user = user
    update.message = Mock()
    update.message.reply_text = AsyncMock()
    
    with patch('app.bot_handlers.get_db') as mock_get_db:
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        mock_user = Mock()
        mock_user.plan_type = PlanType.FREE
        
        with patch('app.bot_handlers.get_user_by_telegram_id', return_value=mock_user):
            with patch('app.bot_handlers.update_user_interaction'):
                with patch('app.bot_handlers.get_welcome_keyboard') as mock_keyboard:
                    await bot_instance.list_subscriptions(update, context)
                    
                    # Verify empty message was sent
                    update.message.reply_text.assert_called_once()
                    call_args = update.message.reply_text.call_args[0][0]
                    assert "No active subscriptions yet" in call_args
                    mock_keyboard.assert_called_once()

@pytest.mark.asyncio
async def test_admin_access_denied(bot_instance):
    """Test admin command access for non-admin user"""
    update = Mock()
    context = Mock()
    user = Mock()
    user.id = 987654321  # Different from ADMIN_USER_ID
    update.effective_user = user
    update.message = Mock()
    update.message.reply_text = AsyncMock()
    
    await bot_instance.admin_panel(update, context)
    
    # Verify access denied message
    update.message.reply_text.assert_called_once_with("❌ Access denied.")

def test_user_session_management(bot_instance):
    """Test user session storage for multi-step flows"""
    user_id = 123456789
    
    # Test session creation
    bot_instance.user_sessions[user_id] = {"step": "awaiting_service_name"}
    assert user_id in bot_instance.user_sessions
    assert bot_instance.user_sessions[user_id]["step"] == "awaiting_service_name"
    
    # Test session cleanup
    del bot_instance.user_sessions[user_id]
    assert user_id not in bot_instance.user_sessions