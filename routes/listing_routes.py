"""
Listing Routes - Create and view survey listings
"""
from flask import Blueprint, request, jsonify
from database import get_db
from auth_middleware import token_required, role_required
from bson import ObjectId
from datetime import datetime

listing_bp = Blueprint('listings', __name__)

SURVEY_TYPES = [
    'Land Survey', 'Building Survey', 'GPS Survey',
    'Topographic Survey', 'Boundary Survey', 'Construction Survey',
    'Hydrographic Survey', 'Archaeological Survey', 'Other'
]

def serialize_listing(listing, include_contact=False, unlock_status=None):
    """Convert listing document to JSON-serializable dict."""
    result = {
        'id': str(listing['_id']),
        'customer_id': str(listing['customer_id']),
        'customer_name': listing.get('customer_name', 'Unknown'),
        'survey_type': listing['survey_type'],
        'area': listing['area'],
        'address': listing['address'],
        'date': listing['date'],
        'time': listing['time'],
        'description': listing.get('description', ''),
        'status': listing.get('status', 'open'),
        'created_at': listing.get('created_at', '').isoformat() if listing.get('created_at') else '',
        'unlock_status': unlock_status  # surveyor's unlock status for this listing
    }
    
    # Only include phone if contact is unlocked
    if include_contact:
        result['phone'] = listing.get('phone', '')
    else:
        result['phone'] = None  # Hidden
    
    return result

@listing_bp.route('/create-listing', methods=['POST'])
@role_required('customer')
def create_listing():
    """Customer creates a new survey listing."""
    data = request.get_json()
    
    # Validate required fields
    required = ['survey_type', 'area', 'address', 'date', 'time', 'phone']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    if data['survey_type'] not in SURVEY_TYPES:
        return jsonify({'error': f'Invalid survey type. Choose from: {", ".join(SURVEY_TYPES)}'}), 400
    
    db = get_db()
    
    listing_doc = {
        'customer_id': ObjectId(request.current_user_id),
        'customer_name': request.current_user.get('name', ''),
        'survey_type': data['survey_type'],
        'area': data['area'].strip(),
        'address': data['address'].strip(),
        'date': data['date'],
        'time': data['time'],
        'description': data.get('description', '').strip(),
        'phone': data['phone'].strip(),  # Stored but only shown after unlock
        'status': 'open',
        'created_at': datetime.utcnow()
    }
    
    result = db.listings.insert_one(listing_doc)
    
    return jsonify({
        'message': 'Listing created successfully',
        'listing_id': str(result.inserted_id)
    }), 201


@listing_bp.route('/listings', methods=['GET'])
@token_required
def get_listings():
    """Get all listings. Surveyors see all; customers see their own."""
    db = get_db()
    role = request.current_user.get('role')
    user_id = request.current_user_id
    
    if role == 'customer':
        # Customers see only their own listings
        listings_cursor = db.listings.find(
            {'customer_id': ObjectId(user_id)}
        ).sort('created_at', -1)
        
        result = []
        for listing in listings_cursor:
            # Get all unlocks for this listing
            unlocks = list(db.contact_unlocks.find({'listing_id': listing['_id']}))
            
            # Enrich with surveyor names
            unlock_data = []
            for unlock in unlocks:
                surveyor = db.users.find_one({'_id': unlock['surveyor_id']})
                unlock_data.append({
                    'unlock_id': str(unlock['_id']),
                    'surveyor_id': str(unlock['surveyor_id']),
                    'surveyor_name': surveyor['name'] if surveyor else 'Unknown',
                    'status': unlock.get('status', 'pending'),
                    'has_review': db.reviews.find_one({
                        'listing_id': listing['_id'],
                        'surveyor_id': unlock['surveyor_id']
                    }) is not None
                })
            
            serialized = serialize_listing(listing, include_contact=True)
            serialized['unlocks'] = unlock_data
            result.append(serialized)
        
        return jsonify({'listings': result}), 200
    
    elif role == 'surveyor':
        # Surveyors see all listings with their unlock status
        listings_cursor = db.listings.find({}).sort('created_at', -1)
        
        result = []
        for listing in listings_cursor:
            # Check if this surveyor has unlocked this listing
            unlock = db.contact_unlocks.find_one({
                'listing_id': listing['_id'],
                'surveyor_id': ObjectId(user_id)
            })
            
            unlocked = unlock is not None
            unlock_status = unlock.get('status') if unlock else None
            
            serialized = serialize_listing(
                listing,
                include_contact=unlocked,
                unlock_status=unlock_status
            )
            serialized['unlocked'] = unlocked
            if unlock:
                serialized['unlock_id'] = str(unlock['_id'])
            result.append(serialized)
        
        return jsonify({'listings': result}), 200
    
    return jsonify({'error': 'Invalid role'}), 400


@listing_bp.route('/survey-types', methods=['GET'])
def get_survey_types():
    """Return list of available survey types."""
    return jsonify({'survey_types': SURVEY_TYPES}), 200


@listing_bp.route('/listing/<listing_id>', methods=['GET'])
@token_required
def get_listing(listing_id):
    """Get a single listing by ID."""
    db = get_db()
    
    try:
        listing = db.listings.find_one({'_id': ObjectId(listing_id)})
    except Exception:
        return jsonify({'error': 'Invalid listing ID'}), 400
    
    if not listing:
        return jsonify({'error': 'Listing not found'}), 404
    
    role = request.current_user.get('role')
    user_id = request.current_user_id
    
    # Check unlock status for surveyors
    unlocked = False
    unlock_status = None
    if role == 'surveyor':
        unlock = db.contact_unlocks.find_one({
            'listing_id': listing['_id'],
            'surveyor_id': ObjectId(user_id)
        })
        unlocked = unlock is not None
        unlock_status = unlock.get('status') if unlock else None
    elif role == 'customer' and str(listing['customer_id']) == user_id:
        unlocked = True
    
    return jsonify(serialize_listing(listing, include_contact=unlocked, unlock_status=unlock_status)), 200
