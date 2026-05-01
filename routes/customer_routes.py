"""
Customer Routes - Mark contacted status
"""
from flask import Blueprint, request, jsonify
from database import get_db
from auth_middleware import role_required
from bson import ObjectId
from datetime import datetime

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/mark-contacted', methods=['POST'])
@role_required('customer')
def mark_contacted():
    """Customer marks a surveyor as 'contacted'."""
    data = request.get_json()
    
    if not data.get('unlock_id'):
        return jsonify({'error': 'unlock_id is required'}), 400
    
    db = get_db()
    
    try:
        unlock = db.contact_unlocks.find_one({'_id': ObjectId(data['unlock_id'])})
    except Exception:
        return jsonify({'error': 'Invalid unlock ID'}), 400
    
    if not unlock:
        return jsonify({'error': 'Unlock record not found'}), 404
    
    # Verify this customer owns the listing
    listing = db.listings.find_one({'_id': unlock['listing_id']})
    if not listing or str(listing['customer_id']) != request.current_user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Update status to contacted
    db.contact_unlocks.update_one(
        {'_id': unlock['_id']},
        {'$set': {'status': 'contacted', 'contacted_at': datetime.utcnow()}}
    )
    
    return jsonify({'message': 'Marked as contacted', 'status': 'contacted'}), 200


@customer_bp.route('/mark-not-contacted', methods=['POST'])
@role_required('customer')
def mark_not_contacted():
    """Customer marks a surveyor as 'not contacted'."""
    data = request.get_json()
    
    if not data.get('unlock_id'):
        return jsonify({'error': 'unlock_id is required'}), 400
    
    db = get_db()
    
    try:
        unlock = db.contact_unlocks.find_one({'_id': ObjectId(data['unlock_id'])})
    except Exception:
        return jsonify({'error': 'Invalid unlock ID'}), 400
    
    if not unlock:
        return jsonify({'error': 'Unlock record not found'}), 404
    
    # Verify this customer owns the listing
    listing = db.listings.find_one({'_id': unlock['listing_id']})
    if not listing or str(listing['customer_id']) != request.current_user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Update status
    db.contact_unlocks.update_one(
        {'_id': unlock['_id']},
        {'$set': {'status': 'not_contacted', 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({'message': 'Marked as not contacted', 'status': 'not_contacted'}), 200


@customer_bp.route('/customer/dashboard', methods=['GET'])
@role_required('customer')
def customer_dashboard():
    """Get customer dashboard data."""
    db = get_db()
    customer_id = ObjectId(request.current_user_id)
    
    # Get all listings by this customer
    listings = list(db.listings.find({'customer_id': customer_id}).sort('created_at', -1))
    
    total_unlocks = 0
    contacted_count = 0
    
    result = []
    for listing in listings:
        unlocks = list(db.contact_unlocks.find({'listing_id': listing['_id']}))
        total_unlocks += len(unlocks)
        contacted = sum(1 for u in unlocks if u.get('status') == 'contacted')
        contacted_count += contacted
        
        unlock_data = []
        for unlock in unlocks:
            surveyor = db.users.find_one({'_id': unlock['surveyor_id']})
            has_review = db.reviews.find_one({
                'listing_id': listing['_id'],
                'surveyor_id': unlock['surveyor_id']
            }) is not None
            unlock_data.append({
                'unlock_id': str(unlock['_id']),
                'surveyor_id': str(unlock['surveyor_id']),
                'surveyor_name': surveyor['name'] if surveyor else 'Unknown',
                'status': unlock.get('status', 'pending'),
                'has_review': has_review
            })
        
        result.append({
            'id': str(listing['_id']),
            'survey_type': listing['survey_type'],
            'area': listing['area'],
            'address': listing['address'],
            'date': listing['date'],
            'time': listing['time'],
            'description': listing.get('description', ''),
            'phone': listing.get('phone', ''),
            'status': listing.get('status', 'open'),
            'created_at': listing.get('created_at', '').isoformat() if listing.get('created_at') else '',
            'unlocks': unlock_data
        })
    
    return jsonify({
        'listings': result,
        'stats': {
            'total_listings': len(listings),
            'total_unlocks': total_unlocks,
            'contacted': contacted_count
        }
    }), 200
