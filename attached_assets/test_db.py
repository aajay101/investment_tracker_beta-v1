import os
import logging
from app import app, db
from models import User, PortfolioItem, WatchlistItem, PortfolioHistory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test database connection and model creation
with app.app_context():
    try:
        # Try to create tables
        db.create_all()
        logger.info("Database tables created successfully")
        
        # Count existing users
        user_count = User.query.count()
        logger.info(f"Number of users in database: {user_count}")
        
        print("✅ Database connectivity test passed!")
        print("✅ Models created successfully!")
    except Exception as e:
        logger.error(f"Error testing database: {str(e)}")
        print(f"❌ Error: {str(e)}") 