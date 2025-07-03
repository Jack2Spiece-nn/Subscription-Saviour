# 🤖 Subscription Savor - Telegram Bot

Never miss a subscription cancellation deadline again! Subscription Savor is a smart Telegram bot that tracks your free trials and paid subscriptions, sending you timely reminders before they auto-renew.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## ✨ Features

### 🆓 Free Plan
- Track up to **3 active subscriptions**
- **2-day advance reminders** before expiration
- Easy subscription management with inline keyboards
- Modern, intuitive Telegram interface

### ⭐ Pro Plan ($4.99/month)
- **Unlimited subscriptions** tracking
- **Custom reminder timing** (1, 3, or 7 days before)
- **Recurring subscription** tracking (monthly/yearly bills)
- **Personal notes** for each subscription
- **Savings tracker** - see how much money you've saved
- **Snooze reminders** for flexible management
- Priority support

### 🛠️ Admin Features
- Bot usage statistics
- Broadcast messages to all users
- Manual Pro plan upgrades
- Real-time monitoring dashboard

## 🚀 Quick Start

### Deploy to Render (Recommended)

1. **Click the Deploy button above** [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

2. **Set required environment variables:**
   - `TELEGRAM_BOT_TOKEN` - Get from [@BotFather](https://t.me/BotFather)
   - `WEBHOOK_URL` - Your Render app URL (will be provided after deployment)
   - `ADMIN_USER_ID` - Your Telegram user ID ([Get it here](https://t.me/userinfobot))

3. **Deploy!** Render will automatically:
   - Set up PostgreSQL database
   - Configure Redis for background tasks
   - Deploy web service and worker
   - Set up the webhook

### Manual Setup

#### Prerequisites
- Python 3.9+
- PostgreSQL database
- Redis server
- Telegram Bot Token

#### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd subscription-savor-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize database**
   ```bash
   python -c "from app.database import init_db; init_db()"
   ```

5. **Start the services**
   
   **Web service (in one terminal):**
   ```bash
   python main.py
   ```
   
   **Background worker (in another terminal):**
   ```bash
   python worker.py
   ```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | ✅ | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `WEBHOOK_URL` | Your app's public URL | ✅ | `https://mybot.onrender.com` |
| `ADMIN_USER_ID` | Admin's Telegram user ID | ✅ | `123456789` |
| `DATABASE_URL` | PostgreSQL connection string | ✅ | `postgresql://user:pass@host/db` |
| `REDIS_URL` | Redis connection string | ✅ | `redis://localhost:6379/0` |
| `SECRET_KEY` | Flask secret key | ⚠️ | Auto-generated on Render |
| `PRO_PLAN_PRICE` | Pro plan pricing display | ❌ | `$4.99/month` |
| `PORT` | Server port | ❌ | `5000` |

### Getting Your Bot Token

1. Start a chat with [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` command
3. Choose a name and username for your bot
4. Copy the token provided

### Getting Your Telegram User ID

1. Start a chat with [@userinfobot](https://t.me/userinfobot) on Telegram
2. Send any message
3. Copy your user ID from the response

## 🎯 How to Use

### For Users

1. **Start the bot** - Send `/start` to your deployed bot
2. **Add subscriptions** - Use the "📝 Add Subscription" button
3. **View your list** - Tap "📋 My Subscriptions" to see all active subscriptions
4. **Get reminders** - Receive automatic notifications before expiration
5. **Take action** - Use inline buttons to mark as canceled or snooze (Pro)

### Bot Commands

- `/start` - Welcome message and setup
- `/help` - Show available commands and features
- `/list` - View all your subscriptions
- `/add` - Add a new subscription
- `/stats` - View your savings (Pro only)

### Admin Commands

- `/admin` - Access admin panel
- `/admin_stats` - View bot statistics
- `/broadcast <message>` - Send message to all users
- `/grant_pro <user_id>` - Upgrade a user to Pro

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram API  │◄──►│   Web Service   │◄──►│   PostgreSQL    │
└─────────────────┘    │   (Flask)       │    │   Database      │
                       └─────────────────┘    └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Background      │◄──►│     Redis       │
                       │ Worker (Celery) │    │     Queue       │
                       └─────────────────┘    └─────────────────┘
```

### Components

- **Web Service**: Handles Telegram webhooks and user interactions
- **Background Worker**: Processes scheduled reminders and maintenance tasks
- **PostgreSQL**: Stores user data, subscriptions, and statistics
- **Redis**: Manages background task queue and caching

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run specific test file
pytest tests/test_database.py

# Run with coverage
pytest --cov=app tests/
```

## 📊 Monitoring

### Health Checks

- **Web Service**: `GET /` - Returns service status
- **Webhook Info**: `GET /webhook_info` - Current webhook configuration
- **Bot Stats**: `GET /stats` - Usage statistics

### Logs

The application provides structured logging for monitoring:

- **INFO**: Normal operations, reminders sent
- **WARNING**: Non-critical issues, failed webhook attempts
- **ERROR**: Critical errors, failed database operations

## 🔒 Security

- **Environment Variables**: Sensitive data stored securely
- **Admin Protection**: Admin commands restricted by user ID
- **Input Validation**: All user inputs sanitized
- **Database**: Parameterized queries prevent SQL injection
- **Rate Limiting**: Built-in Telegram API rate limiting

## 🚀 Deployment Guide

### Render Deployment (Recommended)

1. **Fork this repository** to your GitHub account

2. **Click Deploy to Render** button above

3. **Configure environment variables** in Render dashboard:
   - Get your bot token from @BotFather
   - Get your user ID from @userinfobot
   - Set webhook URL to your Render app URL

4. **Deploy and test** - Your bot should be live!

### Alternative Deployment Options

- **Heroku**: Use the provided Procfile (not included, but can be created)
- **Digital Ocean**: Deploy using Docker
- **AWS**: Use Elastic Beanstalk or ECS
- **VPS**: Direct deployment with systemd services

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add docstrings to all functions
- Write tests for new features
- Update README if needed

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [Create an issue](../../issues) for bugs or feature requests
- **Documentation**: Check this README for common questions
- **Community**: Join our [Telegram support group](https://t.me/subscription_savor_support) (if available)

## 📈 Roadmap

- [ ] Payment integration for Pro upgrades
- [ ] Mobile app companion
- [ ] Integration with popular services APIs
- [ ] Advanced analytics and insights
- [ ] Team/family subscription sharing
- [ ] Browser extension for auto-detection

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Excellent Telegram Bot API wrapper
- [Flask](https://flask.palletsprojects.com/) - Lightweight web framework
- [Celery](https://docs.celeryproject.org/) - Distributed task queue
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit and ORM
- [Render](https://render.com/) - Cloud platform for deployment

---

**Made with ❤️ for people who forget to cancel subscriptions** 

*Save money, reduce stress, never miss a deadline again!*