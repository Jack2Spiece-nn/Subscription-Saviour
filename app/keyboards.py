from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
from app.database import PlanType

# Main Menu Keyboard (Persistent)
def get_main_keyboard(user_plan: PlanType) -> ReplyKeyboardMarkup:
    """Get the main persistent keyboard based on user plan"""
    keyboard = [
        [KeyboardButton("📝 Add Subscription"), KeyboardButton("📋 My Subscriptions")],
    ]
    
    if user_plan == PlanType.FREE:
        keyboard.append([KeyboardButton("⭐ Upgrade to Pro")])
    else:
        keyboard.append([KeyboardButton("📊 My Stats"), KeyboardButton("⚙️ Settings")])
    
    return ReplyKeyboardMarkup(
        keyboard, 
        resize_keyboard=True, 
        persistent=True,
        one_time_keyboard=False
    )

# Inline Keyboards
def get_welcome_keyboard() -> InlineKeyboardMarkup:
    """Welcome message keyboard for new users"""
    keyboard = [
        [InlineKeyboardButton("🚀 Let's Add Your First Trial!", callback_data="add_first_subscription")],
        [InlineKeyboardButton("📖 How It Works", callback_data="how_it_works")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_subscription_type_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting subscription type"""
    keyboard = [
        [InlineKeyboardButton("🆓 Free Trial", callback_data="type_trial")],
        [InlineKeyboardButton("🔄 Recurring Subscription", callback_data="type_recurring")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_add")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_reminder_settings_keyboard(user_plan: PlanType) -> InlineKeyboardMarkup:
    """Keyboard for reminder settings based on user plan"""
    keyboard = []
    
    if user_plan == PlanType.PRO:
        keyboard.extend([
            [InlineKeyboardButton("📅 7 Days Before", callback_data="reminder_7_days")],
            [InlineKeyboardButton("📅 3 Days Before", callback_data="reminder_3_days")],
            [InlineKeyboardButton("📅 1 Day Before", callback_data="reminder_1_day")]
        ])
    else:
        keyboard.append([InlineKeyboardButton("📅 2 Days Before (Free)", callback_data="reminder_2_days")])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_add")])
    return InlineKeyboardMarkup(keyboard)

def get_subscription_actions_keyboard(subscription_id: int, user_plan: PlanType) -> InlineKeyboardMarkup:
    """Keyboard for individual subscription actions"""
    keyboard = [
        [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{subscription_id}")],
    ]
    
    if user_plan == PlanType.PRO:
        keyboard.append([InlineKeyboardButton("📝 Edit Notes", callback_data=f"edit_notes_{subscription_id}")])
        keyboard.append([InlineKeyboardButton("⚙️ Change Reminder", callback_data=f"change_reminder_{subscription_id}")])
    
    return InlineKeyboardMarkup(keyboard)

def get_reminder_action_keyboard(subscription_id: int, user_plan: PlanType) -> InlineKeyboardMarkup:
    """Keyboard for reminder message actions"""
    keyboard = [
        [InlineKeyboardButton("✅ Mark as Canceled", callback_data=f"cancel_sub_{subscription_id}")],
    ]
    
    if user_plan == PlanType.PRO:
        keyboard.append([InlineKeyboardButton("⏰ Snooze 1 Day", callback_data=f"snooze_{subscription_id}")])
    
    return InlineKeyboardMarkup(keyboard)

def get_confirmation_keyboard(action: str, item_id: int) -> InlineKeyboardMarkup:
    """Generic confirmation keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data=f"confirm_{action}_{item_id}"),
            InlineKeyboardButton("❌ No", callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_upgrade_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for Pro upgrade options"""
    keyboard = [
        [InlineKeyboardButton("⭐ Upgrade to Pro", callback_data="upgrade_to_pro")],
        [InlineKeyboardButton("📋 Free Plan Limits", callback_data="free_limits")],
        [InlineKeyboardButton("❌ Not Now", callback_data="cancel_upgrade")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Admin panel keyboard"""
    keyboard = [
        [InlineKeyboardButton("📊 Bot Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⭐ Grant Pro Access", callback_data="admin_grant_pro")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Helper functions
def remove_keyboard() -> ReplyKeyboardMarkup:
    """Remove custom keyboard"""
    return ReplyKeyboardMarkup([[]], resize_keyboard=True, one_time_keyboard=True)

def get_back_keyboard() -> InlineKeyboardMarkup:
    """Simple back button"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]])