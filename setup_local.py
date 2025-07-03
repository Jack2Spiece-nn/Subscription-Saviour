#!/usr/bin/env python3
"""
Local development setup script for Subscription Savor Bot
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9 or higher is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python version {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def setup_virtual_environment():
    """Create and activate virtual environment"""
    if not Path("venv").exists():
        if not run_command("python -m venv venv", "Creating virtual environment"):
            return False
    
    # Check if virtual environment is activated
    if sys.prefix == sys.base_prefix:
        print("⚠️  Virtual environment not activated")
        if os.name == 'nt':  # Windows
            print("To activate: venv\\Scripts\\activate")
        else:  # Unix/MacOS
            print("To activate: source venv/bin/activate")
        return False
    
    print("✅ Virtual environment is active")
    return True

def install_dependencies():
    """Install Python dependencies"""
    return run_command("pip install -r requirements.txt", "Installing dependencies")

def setup_environment_file():
    """Create .env file from template if it doesn't exist"""
    if not Path(".env").exists():
        if Path(".env.example").exists():
            run_command("cp .env.example .env", "Creating .env file from template")
            print("📝 Please edit .env file with your configuration:")
            print("   - TELEGRAM_BOT_TOKEN (from @BotFather)")
            print("   - WEBHOOK_URL (for production)")
            print("   - ADMIN_USER_ID (from @userinfobot)")
        else:
            print("❌ .env.example not found")
            return False
    else:
        print("✅ .env file already exists")
    
    return True

def setup_database():
    """Initialize the database"""
    try:
        from app.database import init_db
        init_db()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def run_tests():
    """Run the test suite"""
    return run_command("python -m pytest tests/ -v", "Running tests")

def main():
    """Main setup function"""
    print("🚀 Setting up Subscription Savor Bot for local development")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Setup virtual environment
    if not setup_virtual_environment():
        print("\n⚠️  Please activate your virtual environment and run this script again")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Setup environment file
    if not setup_environment_file():
        sys.exit(1)
    
    # Initialize database
    if not setup_database():
        print("⚠️  Database setup failed. Make sure to configure DATABASE_URL in .env")
    
    # Run tests
    print("\n🧪 Running tests to verify setup...")
    if run_tests():
        print("✅ All tests passed!")
    else:
        print("⚠️  Some tests failed. Check your configuration.")
    
    print("\n" + "=" * 60)
    print("🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Edit .env file with your bot token and configuration")
    print("2. Start the bot: python main.py")
    print("3. In another terminal, start the worker: python worker.py")
    print("\nFor production deployment, use the 'Deploy to Render' button in README.md")

if __name__ == "__main__":
    main()