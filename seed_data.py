"""
Seed script to populate the database with test data.
Run: python seed_data.py
"""
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from bson import ObjectId

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['surveyor_marketplace']

# Clear existing data
print("Clearing existing data...")
db.users.drop()
db.listings.drop()
db.contact_unlocks.drop()
db.reviews.drop()

# ===== USERS =====
print("Creating users...")

customer1_id = ObjectId()
customer2_id = ObjectId()
surveyor1_id = ObjectId()
surveyor2_id = ObjectId()

users = [
    {
        '_id': customer1_id,
        'name': 'Rajesh Sharma',
        'email': 'rajesh@example.com',
        'phone': '9876543210',
        'role': 'customer',
        'password_hash': generate_password_hash('password123'),
        'subscription_active': True,
        'profile': {}
    },
    {
        '_id': customer2_id,
        'name': 'Gayatri B',
        'email': 'gayatri@example.com',
        'phone': '9876543211',
        'role': 'customer',
        'password_hash': generate_password_hash('password123'),
        'subscription_active': True,
        'profile': {}
    },
    {
        '_id': surveyor1_id,
        'name': 'Amit Kulkarni',
        'email': 'amit@surveyors.com',
        'phone': '9765432100',
        'role': 'surveyor',
        'password_hash': generate_password_hash('password123'),
        'subscription_active': True,
        'profile': {
            'company': 'Kulkarni Survey Associates',
            'experience': '12 years',
            'specializations': ['Land Survey', 'GPS Survey', 'Topographic Survey']
        }
    },
    {
        '_id': surveyor2_id,
        'name': 'Sunita Joshi',
        'email': 'sunita@geodata.com',
        'phone': '9765432101',
        'role': 'surveyor',
        'password_hash': generate_password_hash('password123'),
        'subscription_active': True,
        'profile': {
            'company': 'GeoData Solutions',
            'experience': '8 years',
            'specializations': ['Building Survey', 'Boundary Survey']
        }
    }
]

db.users.insert_many(users)
print(f"  Created {len(users)} users")

# ===== LISTINGS =====
print("Creating listings...")

listing1_id = ObjectId()
listing2_id = ObjectId()
listing3_id = ObjectId()

listings = [
    {
        '_id': listing1_id,
        'customer_id': customer1_id,
        'customer_name': 'Rajesh Sharma',
        'survey_type': 'Land Survey',
        'area': 'Hinjewadi, Pune',
        'address': 'Plot 45, Phase 2, Hinjewadi IT Park, Pune - 411057',
        'date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
        'time': '09:00',
        'description': 'Need land survey for 2 acre plot. Access road dispute with neighbour. Need boundary markers.',
        'phone': '9876543210',
        'status': 'open',
        'created_at': datetime.utcnow() - timedelta(days=2)
    },
    {
        '_id': listing2_id,
        'customer_id': customer1_id,
        'customer_name': 'Rajesh Sharma',
        'survey_type': 'Building Survey',
        'area': 'Kothrud, Pune',
        'address': 'Building 7B, Kothrud Housing Society, Pune - 411038',
        'date': (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
        'time': '11:00',
        'description': 'Pre-purchase building structural survey required for 3 BHK flat. 12th floor unit.',
        'phone': '9876543210',
        'status': 'open',
        'created_at': datetime.utcnow() - timedelta(days=1)
    },
    {
        '_id': listing3_id,
        'customer_id': customer2_id,
        'customer_name': 'Priya Patel',
        'survey_type': 'GPS Survey',
        'area': 'Baner, Pune',
        'address': 'Agricultural land near Baner Road, Pune - 411045',
        'date': (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
        'time': '08:30',
        'description': 'GPS coordinates needed for 5 acre farm land for legal documentation purpose.',
        'phone': '9876543211',
        'status': 'open',
        'created_at': datetime.utcnow()
    }
]

db.listings.insert_many(listings)
print(f"  Created {len(listings)} listings")

# ===== CONTACT UNLOCKS =====
print("Creating contact unlocks...")

unlock1_id = ObjectId()
unlock2_id = ObjectId()

unlocks = [
    {
        '_id': unlock1_id,
        'listing_id': listing1_id,
        'surveyor_id': surveyor1_id,
        'customer_id': customer1_id,
        'status': 'contacted',
        'unlocked_at': datetime.utcnow() - timedelta(hours=12),
        'contacted_at': datetime.utcnow() - timedelta(hours=6)
    },
    {
        '_id': unlock2_id,
        'listing_id': listing2_id,
        'surveyor_id': surveyor2_id,
        'customer_id': customer1_id,
        'status': 'pending',
        'unlocked_at': datetime.utcnow() - timedelta(hours=3)
    }
]

db.contact_unlocks.insert_many(unlocks)
print(f"  Created {len(unlocks)} contact unlocks")

# ===== REVIEWS =====
print("Creating reviews...")

reviews = [
    {
        'listing_id': listing1_id,
        'surveyor_id': surveyor1_id,
        'customer_id': customer1_id,
        'unlock_id': unlock1_id,
        'rating': 5,
        'review_text': 'Excellent work by Amit! Very professional, arrived on time, and provided detailed survey report within 2 days. Highly recommended.',
        'created_at': datetime.utcnow() - timedelta(hours=2)
    }
]

db.reviews.insert_many(reviews)
print(f"  Created {len(reviews)} reviews")

# Create indexes
print("Creating indexes...")
db.users.create_index('email', unique=True, sparse=True)
db.users.create_index('phone', unique=True, sparse=True)
db.listings.create_index('customer_id')
db.contact_unlocks.create_index([('listing_id', 1), ('surveyor_id', 1)], unique=True)

print("\n✅ Seed data created successfully!")
print("\n📋 Test Accounts:")
print("=" * 50)
print("CUSTOMERS:")
print("  Email: rajesh@example.com | Phone: 9876543210 | Pass: password123")
print("  Email: priya@example.com  | Phone: 9876543211 | Pass: password123")
print("\nSURVEYORS:")
print("  Email: amit@surveyors.com  | Phone: 9765432100 | Pass: password123")
print("  Email: sunita@geodata.com  | Phone: 9765432101 | Pass: password123")
print("=" * 50)
