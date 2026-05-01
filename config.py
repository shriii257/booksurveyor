"""
Configuration settings for Surveyor Marketplace
"""
import os
from datetime import timedelta

class Config:
    # Secret key for JWT tokens
    SECRET_KEY = os.environ.get('SECRET_KEY', 'surveyor-marketplace-secret-key-2024')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-surveyor-2024')
    JWT_EXPIRATION_HOURS = 24
    
    # MongoDB connection
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
    DB_NAME = os.environ.get('DB_NAME', 'surveyor_marketplace')
    
    # Subscription cost (in demo mode, unlock is free)
    SUBSCRIPTION_ACTIVE_DEFAULT = True  # For MVP, all surveyors can unlock
