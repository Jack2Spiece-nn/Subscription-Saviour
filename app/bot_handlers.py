import logging
from datetime import datetime, timedelta
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from app.database import get_db, get_user_by_telegram_id, update_user_interaction, Subscription, User, PlanType, SubscriptionType, ReminderType, can_add_subscription, get_active_subscriptions_count
from app.keyboards import *
from app.config import Config

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

class SubscriptionBot:
    def __init__(self):
        Config.validate()
        
        # User session storage for multi-step operations
        self.user_sessions = {}
        
        # Initialize the application once
        self._application = None
        self._initialize_application()
    
    def _initialize_application(self):
        """Initialize the bot application with handlers"""
        # Create the application
        self._application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        
        # Command handlers
        self._application.add_handler(CommandHandler("start", self.start_command))
        self._application.add_handler(CommandHandler("help", self.help_command))
        self._application.add_handler(CommandHandler("list", self.list_subscriptions))
        self._application.add_handler(CommandHandler("add", self.add_subscription_flow))
        self._application.add_handler(CommandHandler("stats", self.stats_command))
        
        # Admin commands
        self._application.add_handler(CommandHandler("admin", self.admin_panel))
        self._application.add_handler(CommandHandler("admin_stats", self.admin_stats))
        self._application.add_handler(CommandHandler("broadcast", self.admin_broadcast))
        self._application.add_handler(CommandHandler("grant_pro", self.admin_grant_pro))
        
        # Message handlers (for persistent keyboard)
        self._application.add_handler(MessageHandler(filters.Regex("^📝 Add Subscription$"), self.add_subscription_flow))
        self._application.add_handler(MessageHandler(filters.Regex("^📋 My Subscriptions$"), self.list_subscriptions))
        self._application.add_handler(MessageHandler(filters.Regex("^⭐ Upgrade to Pro$"), self.upgrade_flow))
        self._application.add_handler(MessageHandler(filters.Regex("^📊 My Stats$"), self.stats_command))
        self._application.add_handler(MessageHandler(filters.Regex("^⚙️ Settings$"), self.settings_command))
        
        # Callback query handler for inline keyboards
        self._application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Text message handler for multi-step flows
        self._application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_input))
    
    def get_application(self) -> Application:
        """Get the initialized bot application"""
        return self._application
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        with get_db() as db:
            db_user = get_user_by_telegram_id(db, user.id)
            db_user.username = user.username
            db_user.first_name = user.first_name
            update_user_interaction(db, user.id)
            db.commit()
            
            # Send welcome message with inline keyboard
            welcome_text = f"""
🎉 Welcome to Subscription Savor, {user.first_name or 'there'}!

Never miss a subscription cancellation deadline again! 

🆓 **Free Plan**: Track up to 3 subscriptions with 2-day reminders
⭐ **Pro Plan**: Unlimited subscriptions, custom reminders, savings tracker & more!

Ready to start saving money?
"""
            
            await update.message.reply_text(
                welcome_text,
                reply_markup=get_welcome_keyboard()
            )
            
            # Set the main persistent keyboard
            await update.message.reply_text(
                "Use the menu below to navigate:",
                reply_markup=get_main_keyboard(db_user.plan_type)
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 **Subscription Savor Help**

**Main Commands:**
• 📝 Add Subscription - Add a new subscription to track
• 📋 My Subscriptions - View all your tracked subscriptions  
• ⭐ Upgrade to Pro - Unlock premium features

**Pro Features:**
• Unlimited subscriptions
• Custom reminder timing (1, 3, or 7 days)
• Recurring subscription tracking
• Personal notes for each subscription
• Savings tracker

**How it works:**
1. Add your free trials and subscriptions
2. Get reminded before they expire
3. Cancel in time to avoid charges
4. Save money! 💰

Need help? Just type your question!
"""
        await update.message.reply_text(help_text)
    
    async def add_subscription_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the add subscription flow"""
        user_id = update.effective_user.id
        
        with get_db() as db:
            if not can_add_subscription(db, user_id):
                await update.message.reply_text(
                    "🚫 You've reached the free plan limit (3 subscriptions).\n\n"
                    "Upgrade to Pro for unlimited subscriptions!",
                    reply_markup=get_upgrade_keyboard()
                )
                return
            
            update_user_interaction(db, user_id)
        
        # Start the flow
        self.user_sessions[user_id] = {"step": "awaiting_service_name"}
        
        await update.message.reply_text(
            "🆕 **Adding New Subscription**\n\n"
            "What's the name of the service? (e.g., Netflix, Spotify, Adobe)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_add")]])
        )
    
    async def list_subscriptions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List user's subscriptions"""
        user_id = update.effective_user.id
        
        with get_db() as db:
            update_user_interaction(db, user_id)
            user = get_user_by_telegram_id(db, user_id)
            
            subscriptions = db.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.is_active == True
            ).order_by(Subscription.end_date).all()
            
            if not subscriptions:
                await update.message.reply_text(
                    "📭 No active subscriptions yet!\n\n"
                    "Tap 'Add Subscription' to get started.",
                    reply_markup=get_welcome_keyboard()
                )
                return
            
            response = f"📋 **Your Subscriptions** ({len(subscriptions)}/{'∞' if user.plan_type == PlanType.PRO else '3'})\n\n"
            
            for sub in subscriptions:
                days_left = (sub.end_date - datetime.utcnow()).days
                status_emoji = "🔴" if days_left <= 2 else "🟡" if days_left <= 7 else "🟢"
                
                response += f"{status_emoji} **{sub.service_name}**\n"
                response += f"   📅 Expires: {sub.end_date.strftime('%Y-%m-%d')}\n"
                response += f"   ⏰ Days left: {days_left}\n"
                
                if sub.cost:
                    response += f"   💰 Cost: {sub.cost}\n"
                
                if user.plan_type == PlanType.PRO and sub.notes:
                    response += f"   📝 Notes: {sub.notes}\n"
                
                response += "\n"
            
            # Add inline keyboards for each subscription
            keyboard = []
            for sub in subscriptions:
                keyboard.append([InlineKeyboardButton(
                    f"🗑️ Delete {sub.service_name}",
                    callback_data=f"delete_{sub.id}"
                )])
            
            if keyboard:
                reply_markup = InlineKeyboardMarkup(keyboard)
            else:
                reply_markup = None
            
            await update.message.reply_text(response, reply_markup=reply_markup)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user stats (Pro feature)"""
        user_id = update.effective_user.id
        
        with get_db() as db:
            user = get_user_by_telegram_id(db, user_id)
            update_user_interaction(db, user_id)
            
            if user.plan_type != PlanType.PRO:
                await update.message.reply_text(
                    "📊 **Stats are a Pro feature!**\n\n"
                    "Upgrade to Pro to see:\n"
                    "• Money saved from canceled subscriptions\n"
                    "• Subscription trends\n"
                    "• Detailed analytics",
                    reply_markup=get_upgrade_keyboard()
                )
                return
            
            # Calculate stats for Pro users
            from app.database import calculate_savings
            savings_data = calculate_savings(db, user_id)
            active_count = get_active_subscriptions_count(db, user_id)
            
            stats_text = f"""
📊 **Your Subscription Stats**

💰 **Money Saved**: {savings_data['estimated_savings']}
📋 **Active Subscriptions**: {active_count}
❌ **Canceled Subscriptions**: {savings_data['canceled_subscriptions']}
📈 **Average Savings per Cancel**: {savings_data['avg_savings_per_sub']}

Keep up the great work! 🎉
"""
            
            await update.message.reply_text(stats_text)
    
    async def upgrade_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Pro upgrade flow"""
        upgrade_text = f"""
⭐ **Upgrade to Savor Pro** ⭐

**Free Plan:**
• ✅ Up to 3 subscriptions
• ✅ 2-day reminders
• ✅ Basic tracking

**Pro Plan** - {Config.PRO_PLAN_PRICE}:
• ✅ Unlimited subscriptions
• ✅ Custom reminders (1, 3, 7 days)
• ✅ Recurring subscription tracking
• ✅ Personal notes
• ✅ Savings tracker & analytics
• ✅ Snooze reminders

Ready to unlock the full potential?
"""
        
        await update.message.reply_text(
            upgrade_text,
            reply_markup=get_upgrade_keyboard()
        )
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle settings (Pro feature)"""
        user_id = update.effective_user.id
        
        with get_db() as db:
            user = get_user_by_telegram_id(db, user_id)
            update_user_interaction(db, user_id)
            
            settings_text = f"""
⚙️ **Your Settings**

**Plan**: {user.plan_type.value.title()}
**Member Since**: {user.created_at.strftime('%Y-%m-%d')}
**Active Subscriptions**: {get_active_subscriptions_count(db, user_id)}
"""
            
            if user.plan_type == PlanType.PRO:
                settings_text += "\n✨ **Pro Features Enabled**"
            
            await update.message.reply_text(settings_text)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        with get_db() as db:
            update_user_interaction(db, user_id)
        
        # Route to appropriate handler based on callback data
        if data == "add_first_subscription":
            await self._handle_add_subscription_callback(query, context)
        elif data.startswith("delete_"):
            await self._handle_delete_subscription(query, context)
        elif data.startswith("confirm_delete_"):
            await self._handle_confirm_delete(query, context)
        elif data == "upgrade_to_pro":
            await self._handle_upgrade_callback(query, context)
        elif data.startswith("type_"):
            await self._handle_subscription_type(query, context)
        elif data.startswith("reminder_"):
            await self._handle_reminder_setting(query, context)
        elif data == "skip_cost":
            await self._handle_skip_cost(query, context)
        elif data == "cancel_add" or data == "cancel_action":
            await self._handle_cancel(query, context)
        # Add more callback handlers as needed
    
    async def _handle_add_subscription_callback(self, query, context):
        """Handle adding subscription from inline button"""
        user_id = query.from_user.id
        
        with get_db() as db:
            if not can_add_subscription(db, user_id):
                await query.edit_message_text(
                    "🚫 You've reached the free plan limit (3 subscriptions).\n\n"
                    "Upgrade to Pro for unlimited subscriptions!",
                    reply_markup=get_upgrade_keyboard()
                )
                return
        
        self.user_sessions[user_id] = {"step": "awaiting_service_name"}
        
        await query.edit_message_text(
            "🆕 **Adding New Subscription**\n\n"
            "What's the name of the service? (e.g., Netflix, Spotify, Adobe)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_add")]])
        )
    
    async def _handle_delete_subscription(self, query, context):
        """Handle subscription deletion"""
        subscription_id = int(query.data.split("_")[1])
        
        with get_db() as db:
            subscription = db.query(Subscription).filter(
                Subscription.id == subscription_id,
                Subscription.user_id == query.from_user.id
            ).first()
            
            if not subscription:
                await query.edit_message_text("❌ Subscription not found.")
                return
            
            await query.edit_message_text(
                f"🗑️ **Delete Subscription**\n\n"
                f"Are you sure you want to delete '{subscription.service_name}'?\n\n"
                f"This action cannot be undone.",
                reply_markup=get_confirmation_keyboard("delete", subscription_id)
            )
    
    async def _handle_confirm_delete(self, query, context):
        """Handle confirmed deletion"""
        subscription_id = int(query.data.split("_")[2])
        
        with get_db() as db:
            subscription = db.query(Subscription).filter(
                Subscription.id == subscription_id,
                Subscription.user_id == query.from_user.id
            ).first()
            
            if subscription:
                subscription.is_active = False
                db.commit()
                
                await query.edit_message_text(
                    f"✅ **Deleted Successfully**\n\n"
                    f"'{subscription.service_name}' has been removed from your list."
                )
            else:
                await query.edit_message_text("❌ Subscription not found.")
    
    async def _handle_upgrade_callback(self, query, context):
        """Handle Pro upgrade callback"""
        await query.edit_message_text(
            "⭐ **Pro Upgrade**\n\n"
            "To upgrade to Pro, please contact our support team.\n\n"
            "🔜 Payment integration coming soon!\n\n"
            "For now, admin can manually upgrade accounts."
        )
    
    async def _handle_skip_cost(self, query, context):
        """Handle skipping cost input"""
        user_id = query.from_user.id
        
        if user_id not in self.user_sessions:
            await query.edit_message_text("❌ Session expired. Please start over.")
            return
        
        # Skip cost and move to end date
        self.user_sessions[user_id]["cost"] = None
        self.user_sessions[user_id]["step"] = "awaiting_end_date"
        
        await query.edit_message_text(
            f"📅 **End Date**\n\n"
            f"When does this subscription expire?\n"
            f"Please enter the date in format: YYYY-MM-DD\n"
            f"(e.g., 2024-02-15)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_add")]])
        )
    
    async def _handle_cancel(self, query, context):
        """Handle cancellation"""
        user_id = query.from_user.id
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        
        await query.edit_message_text("❌ Operation canceled.")
    
    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text input for multi-step flows"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            # No active session, ignore
            return
        
        session = self.user_sessions[user_id]
        step = session.get("step")
        
        if step == "awaiting_service_name":
            await self._handle_service_name_input(update, context)
        elif step == "awaiting_cost":
            await self._handle_cost_input(update, context)
        elif step == "awaiting_end_date":
            await self._handle_end_date_input(update, context)
        # Add more steps as needed
    
    async def _handle_service_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle service name input"""
        user_id = update.effective_user.id
        service_name = update.message.text.strip()
        
        if len(service_name) > 50:
            await update.message.reply_text("❌ Service name is too long. Please keep it under 50 characters.")
            return
        
        self.user_sessions[user_id]["service_name"] = service_name
        self.user_sessions[user_id]["step"] = "awaiting_cost"
        
        await update.message.reply_text(
            f"💰 **Cost (Optional)**\n\n"
            f"What's the cost of {service_name}? (e.g., $9.99/month)\n\n"
            f"Or send 'skip' to continue without cost.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭️ Skip", callback_data="skip_cost")]])
        )
    
    async def _handle_cost_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle cost input"""
        user_id = update.effective_user.id
        cost_text = update.message.text.strip()
        
        if cost_text.lower() == 'skip':
            self.user_sessions[user_id]["cost"] = None
        else:
            self.user_sessions[user_id]["cost"] = cost_text
        
        self.user_sessions[user_id]["step"] = "awaiting_end_date"
        
        await update.message.reply_text(
            f"📅 **End Date**\n\n"
            f"When does this subscription expire?\n"
            f"Please enter the date in format: YYYY-MM-DD\n"
            f"(e.g., 2024-02-15)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_add")]])
        )
    
    async def _handle_end_date_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle end date input"""
        user_id = update.effective_user.id
        date_text = update.message.text.strip()
        
        try:
            from datetime import datetime
            end_date = datetime.strptime(date_text, '%Y-%m-%d')
            
            if end_date <= datetime.now():
                await update.message.reply_text("❌ End date must be in the future. Please try again.")
                return
            
            # Save the subscription
            session = self.user_sessions[user_id]
            
            with get_db() as db:
                user = get_user_by_telegram_id(db, user_id)
                
                subscription = Subscription(
                    user_id=user_id,
                    service_name=session["service_name"],
                    cost=session.get("cost"),
                    start_date=datetime.utcnow(),
                    end_date=end_date,
                    subscription_type=SubscriptionType.TRIAL,
                    reminder_type=ReminderType.TWO_DAYS if user.plan_type == PlanType.FREE else ReminderType.THREE_DAYS
                )
                
                db.add(subscription)
                db.commit()
                db.refresh(subscription)
                
                # Clean up session
                del self.user_sessions[user_id]
                
                # Send confirmation
                days_until = (end_date - datetime.utcnow()).days
                confirmation_text = f"""
✅ **Subscription Added!**

🔔 **{subscription.service_name}**
📅 Expires: {end_date.strftime('%Y-%m-%d')}
⏰ Days left: {days_until}
💰 Cost: {subscription.cost or 'Not specified'}

I'll remind you {2 if user.plan_type == PlanType.FREE else 3} days before it expires!
"""
                
                await update.message.reply_text(confirmation_text)
                
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid date format. Please use YYYY-MM-DD format (e.g., 2024-02-15)"
            )
    
    async def _handle_subscription_type(self, query, context):
        """Handle subscription type selection"""
        user_id = query.from_user.id
        subscription_type = query.data.split("_")[1]  # trial or recurring
        
        if user_id not in self.user_sessions:
            await query.edit_message_text("❌ Session expired. Please start over.")
            return
        
        self.user_sessions[user_id]["subscription_type"] = subscription_type
        
        with get_db() as db:
            user = get_user_by_telegram_id(db, user_id)
            
            await query.edit_message_text(
                f"⏰ **Reminder Settings**\n\n"
                f"When would you like to be reminded?",
                reply_markup=get_reminder_settings_keyboard(user.plan_type)
            )
    
    async def _handle_reminder_setting(self, query, context):
        """Handle reminder setting selection"""
        user_id = query.from_user.id
        reminder_setting = query.data.split("_")[1]  # days
        
        if user_id not in self.user_sessions:
            await query.edit_message_text("❌ Session expired. Please start over.")
            return
        
        # Map reminder settings
        reminder_map = {
            "7": ReminderType.SEVEN_DAYS,
            "3": ReminderType.THREE_DAYS,
            "1": ReminderType.ONE_DAY,
            "2": ReminderType.TWO_DAYS
        }
        
        self.user_sessions[user_id]["reminder_type"] = reminder_map.get(reminder_setting, ReminderType.TWO_DAYS)
        
        await query.edit_message_text(
            f"✅ **Settings Saved**\n\n"
            f"Reminder set for {reminder_setting} day(s) before expiration.\n\n"
            f"Your subscription has been added successfully!"
        )
    
    # Admin handlers
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin panel access"""
        if update.effective_user.id != Config.ADMIN_USER_ID:
            await update.message.reply_text("❌ Access denied.")
            return
        
        await update.message.reply_text(
            "👑 **Admin Panel**\n\nSelect an action:",
            reply_markup=get_admin_keyboard()
        )
    
    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin statistics"""
        if update.effective_user.id != Config.ADMIN_USER_ID:
            await update.message.reply_text("❌ Access denied.")
            return
        
        with get_db() as db:
            total_users = db.query(User).count()
            pro_users = db.query(User).filter(User.plan_type == PlanType.PRO).count()
            active_subscriptions = db.query(Subscription).filter(Subscription.is_active == True).count()
            
            stats_text = f"""
📊 **Bot Statistics**

👥 **Total Users**: {total_users}
⭐ **Pro Users**: {pro_users}
📋 **Active Subscriptions**: {active_subscriptions}
📈 **Pro Conversion Rate**: {(pro_users/total_users*100):.1f}% if total_users > 0 else 0%

Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
"""
            
            await update.message.reply_text(stats_text)
    
    async def admin_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin broadcast message"""
        if update.effective_user.id != Config.ADMIN_USER_ID:
            await update.message.reply_text("❌ Access denied.")
            return
        
        # Implementation for broadcast
        await update.message.reply_text(
            "📢 **Broadcast Message**\n\n"
            "Send the message you want to broadcast to all users.\n"
            "Use /cancel to abort."
        )
    
    async def admin_grant_pro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Grant Pro access to a user"""
        if update.effective_user.id != Config.ADMIN_USER_ID:
            await update.message.reply_text("❌ Access denied.")
            return
        
        # Parse command arguments
        args = context.args
        if not args:
            await update.message.reply_text(
                "Usage: /grant_pro <user_id>\n\n"
                "Example: /grant_pro 123456789"
            )
            return
        
        try:
            target_user_id = int(args[0])
            
            with get_db() as db:
                from app.database import upgrade_user_to_pro
                upgrade_user_to_pro(db, target_user_id)
                
                await update.message.reply_text(
                    f"✅ Successfully upgraded user {target_user_id} to Pro!"
                )
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID format.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

# Global bot instance
bot_instance = SubscriptionBot()