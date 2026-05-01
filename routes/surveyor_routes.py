"""
Surveyor Routes - Unlock contacts, view profile
"""
from flask import Blueprint, request, jsonify
from database import get_db
from auth_middleware import token_required, role_required
from bson import ObjectId
from datetime import datetime

surveyor_bp = Blueprint('surveyor', __name__)

@surveyor_bp.route('/unlock-contact', methods=['POST'])
@role_required('surveyor')
def unlock_contact():
    """Surveyor unlocks a customer's contact details for a listing."""
    data = request.get_json()
    
    if not data.get('listing_id'):
        return jsonify({'error': 'listing_id is required'}), 400
    
    db = get_db()
    surveyor_id = ObjectId(request.current_user_id)
    
    # Check subscription
    surveyor = request.current_user
    if not surveyor.get('subscription_active', True):
        return jsonify({'error': 'Active subscription required to unlock contacts'}), 403
    
    # Validate listing exists
    try:
        listing = db.listings.find_one({'_id': ObjectId(data['listing_id'])})
    except Exception:
        return jsonify({'error': 'Invalid listing ID'}), 400
    
    if not listing:
        return jsonify({'error': 'Listing not found'}), 404
    
    # Check if already unlocked
    existing = db.contact_unlocks.find_one({
        'listing_id': listing['_id'],
        'surveyor_id': surveyor_id
    })
    
    if existing:
        # Already unlocked - return the contact details
        customer = db.users.find_one({'_id': listing['customer_id']})
        return jsonify({
            'message': 'Contact already unlocked',
            'already_unlocked': True,
            'contact': {
                'name': listing.get('customer_name', ''),
                'phone': listing.get('phone', ''),
                'address': listing.get('address', '')
            },
            'unlock_id': str(existing['_id']),
            'status': existing.get('status', 'pending')
        }), 200
    
    # Create unlock record
    unlock_doc = {
        'listing_id': listing['_id'],
        'surveyor_id': surveyor_id,
        'customer_id': listing['customer_id'],
        'status': 'pending',  # pending -> contacted / not_contacted
        'unlocked_at': datetime.utcnow()
    }
    
    result = db.contact_unlocks.insert_one(unlock_doc)
    
    # Get customer info to return
    customer = db.users.find_one({'_id': listing['customer_id']})
    
    return jsonify({
        'message': 'Contact unlocked successfully',
        'unlock_id': str(result.inserted_id),
        'contact': {
            'name': listing.get('customer_name', ''),
            'phone': listing.get('phone', ''),
            'address': listing.get('address', '')
        },
        'status': 'pending'
    }), 201


@surveyor_bp.route('/surveyor/profile', methods=['GET'])
@role_required('surveyor')
def get_profile():
    """Get surveyor profile with stats and reviews."""
    db = get_db()
    surveyor_id = ObjectId(request.current_user_id)
    
    # Get reviews for this surveyor
    reviews = list(db.reviews.find({'surveyor_id': surveyor_id}))
    
    # Calculate average rating
    avg_rating = 0
    if reviews:
        avg_rating = sum(r.get('rating', 0) for r in reviews) / len(reviews)
    
    # Format reviews with customer names
    formatted_reviews = []
    for review in reviews:
        customer = db.users.find_one({'_id': review['customer_id']})
        listing = db.listings.find_one({'_id': review['listing_id']})
        formatted_reviews.append({
            'id': str(review['_id']),
            'customer_name': customer['name'] if customer else 'Unknown',
            'survey_type': listing.get('survey_type', '') if listing else '',
            'rating': review.get('rating', 0),
            'review_text': review.get('review_text', ''),
            'created_at': review.get('created_at', '').isoformat() if review.get('created_at') else ''
        })
    
    # Get unlock count (contacts they've accessed)
    unlock_count = db.contact_unlocks.count_documents({'surveyor_id': surveyor_id})
    
    user = request.current_user
    
    return jsonify({
        'surveyor': {
            'id': str(user['_id']),
            'name': user['name'],
            'email': user.get('email', ''),
            'phone': user.get('phone', ''),
            'subscription_active': user.get('subscription_active', True),
            'profile': user.get('profile', {}),
            'stats': {
                'unlocked_contacts': unlock_count,
                'reviews_count': len(reviews),
                'average_rating': round(avg_rating, 1)
            }
        },
        'reviews': formatted_reviews
    }), 200


@surveyor_bp.route('/surveyor/profile', methods=['PUT'])
@role_required('surveyor')
def update_profile():
    """Update surveyor profile."""
    data = request.get_json()
    db = get_db()
    
    update_data = {
        'profile.company': data.get('company', ''),
        'profile.experience': data.get('experience', ''),
        'profile.specializations': data.get('specializations', [])
    }
    
    db.users.update_one(
        {'_id': ObjectId(request.current_user_id)},
        {'$set': update_data}
    )
    
    return jsonify({'message': 'Profile updated successfully'}), 200


@surveyor_bp.route('/surveyor/unlocked-listings', methods=['GET'])
@role_required('surveyor')
def get_unlocked_listings():
    """Get all listings this surveyor has unlocked."""
    db = get_db()
    surveyor_id = ObjectId(request.current_user_id)
    
    unlocks = list(db.contact_unlocks.find({'surveyor_id': surveyor_id}))
    
    result = []
    for unlock in unlocks:
        listing = db.listings.find_one({'_id': unlock['listing_id']})
        if listing:
            result.append({
                'unlock_id': str(unlock['_id']),
                'status': unlock.get('status', 'pending'),
                'unlocked_at': unlock.get('unlocked_at', '').isoformat() if unlock.get('unlocked_at') else '',
                'listing': {
                    'id': str(listing['_id']),
                    'customer_name': listing.get('customer_name', ''),
                    'phone': listing.get('phone', ''),  # Show since unlocked
                    'survey_type': listing.get('survey_type', ''),
                    'area': listing.get('area', ''),
                    'address': listing.get('address', ''),
                    'date': listing.get('date', ''),
                    'time': listing.get('time', ''),
                    'description': listing.get('description', '')
                }
            })
    
    return jsonify({'unlocked_listings': result}), 200
