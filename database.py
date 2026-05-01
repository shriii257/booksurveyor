"""
MongoDB Database Connection Setup using PyMongo
"""
from flask import current_app, g
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

_client = None

def init_db(app):
    """Initialize database connection with the Flask app."""
    global _client
    try:
        _client = MongoClient(app.config['MONGO_URI'])
        # Test connection
        _client.admin.command('ping')
        print(f"✅ Connected to MongoDB at {app.config['MONGO_URI']}")
        
        # Create indexes for performance
        db = _client[app.config['DB_NAME']]
        db.users.create_index('email', unique=True, sparse=True)
        db.users.create_index('phone', unique=True, sparse=True)
        db.listings.create_index('customer_id')
        db.contact_unlocks.create_index([('listing_id', 1), ('surveyor_id', 1)], unique=True)
        db.reviews.create_index([('listing_id', 1), ('surveyor_id', 1)], unique=True)
        print("✅ Database indexes created")
    except ConnectionFailure as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("   Make sure MongoDB is running on localhost:27017")

def get_db():
    """Get database instance."""
    from flask import current_app
    if _client is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _client[current_app.config['DB_NAME']]
