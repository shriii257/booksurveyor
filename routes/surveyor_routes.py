"""
Surveyor Routes — includes public profile endpoint for customers
"""
from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime
from database import get_db
from auth_middleware import token_required, role_required

surveyor_bp = Blueprint('surveyor', __name__)


# ─────────────────────────────────────────────
# Helper: serialize ObjectId fields
# ─────────────────────────────────────────────
def serialize(doc):
    """Recursively convert ObjectId → str so jsonify doesn't choke."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize(d) for d in doc]
    if isinstance(doc, dict):
        return {k: serialize(v) for k, v in doc.items()}
    if isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, datetime):
        return doc.isoformat()
    return doc


# ─────────────────────────────────────────────
# POST /api/unlock-contact
# Surveyor unlocks a customer listing's contact
# ─────────────────────────────────────────────
@surveyor_bp.route('/unlock-contact', methods=['POST'])
@role_required('surveyor')
def unlock_contact():
    db = get_db()
    data = request.get_json() or {}
    listing_id_str = data.get('listing_id', '').strip()

    if not listing_id_str:
        return jsonify({'error': 'listing_id is required'}), 400

    try:
        listing_id = ObjectId(listing_id_str)
    except Exception:
        return jsonify({'error': 'Invalid listing_id'}), 400

    surveyor_id = ObjectId(request.current_user_id)

    # Check listing exists
    listing = db.listings.find_one({'_id': listing_id})
    if not listing:
        return jsonify({'error': 'Listing not found'}), 404

    # Prevent surveyor from unlocking their own listing (edge case)
    if str(listing.get('customer_id')) == str(surveyor_id):
        return jsonify({'error': 'Cannot unlock your own listing'}), 400

    # Check subscription
    surveyor = db.users.find_one({'_id': surveyor_id})
    if not surveyor or not surveyor.get('subscription_active', False):
        return jsonify({'error': 'Active subscription required to unlock contacts'}), 403

    # Check already unlocked
    existing = db.contact_unlocks.find_one({
        'listing_id': listing_id,
        'surveyor_id': surveyor_id
    })
    if existing:
        return jsonify({
            'message': 'Already unlocked',
            'contact': {
                'phone': listing.get('phone'),
                'name': listing.get('customer_name')
            }
        }), 200

    # Create unlock record
    unlock_doc = {
        'listing_id': listing_id,
        'surveyor_id': surveyor_id,
        'customer_id': listing['customer_id'],
        'status': 'pending',
        'unlocked_at': datetime.utcnow()
    }
    db.contact_unlocks.insert_one(unlock_doc)

    return jsonify({
        'message': 'Contact unlocked successfully',
        'contact': {
            'phone': listing.get('phone'),
            'name': listing.get('customer_name')
        }
    }), 200


# ─────────────────────────────────────────────
# GET /api/surveyor/unlocked-listings
# All listings this surveyor has unlocked
# ─────────────────────────────────────────────
@surveyor_bp.route('/surveyor/unlocked-listings', methods=['GET'])
@role_required('surveyor')
def get_unlocked_listings():
    db = get_db()
    surveyor_id = ObjectId(request.current_user_id)

    unlocks = list(db.contact_unlocks.find({'surveyor_id': surveyor_id}))

    result = []
    for u in unlocks:
        listing = db.listings.find_one({'_id': u['listing_id']})
        if listing:
            result.append({
                'unlock_id': str(u['_id']),
                'status': u.get('status', 'pending'),
                'unlocked_at': u.get('unlocked_at'),
                'listing': {
                    'id': str(listing['_id']),
                    'survey_type': listing.get('survey_type'),
                    'area': listing.get('area'),
                    'address': listing.get('address'),
                    'date': listing.get('date'),
                    'time': listing.get('time'),
                    'phone': listing.get('phone'),
                    'customer_name': listing.get('customer_name'),
                    'description': listing.get('description', '')
                }
            })

    return jsonify({'unlocked_listings': serialize(result)}), 200


# ─────────────────────────────────────────────
# GET /api/surveyor/profile          (own profile)
# PUT /api/surveyor/profile          (update own profile)
# ─────────────────────────────────────────────
@surveyor_bp.route('/surveyor/profile', methods=['GET'])
@role_required('surveyor')
def get_my_profile():
    db = get_db()
    surveyor_id = ObjectId(request.current_user_id)

    surveyor = db.users.find_one({'_id': surveyor_id})
    if not surveyor:
        return jsonify({'error': 'Surveyor not found'}), 404

    # Stats
    unlocked_count = db.contact_unlocks.count_documents({'surveyor_id': surveyor_id})
    reviews_list = list(db.reviews.find({'surveyor_id': surveyor_id}))
    avg_rating = (
        round(sum(r['rating'] for r in reviews_list) / len(reviews_list), 1)
        if reviews_list else 0
    )

    # Enrich reviews with customer name + survey_type
    enriched_reviews = []
    for r in reviews_list:
        listing = db.listings.find_one({'_id': r.get('listing_id')})
        customer = db.users.find_one({'_id': r.get('customer_id')})
        enriched_reviews.append({
            'rating': r.get('rating'),
            'review_text': r.get('review_text'),
            'customer_name': customer.get('name') if customer else 'Customer',
            'survey_type': listing.get('survey_type') if listing else '',
            'created_at': r.get('created_at')
        })

    return jsonify(serialize({
        'surveyor': {
            'id': str(surveyor['_id']),
            'name': surveyor.get('name'),
            'email': surveyor.get('email'),
            'phone': surveyor.get('phone'),
            'profile': surveyor.get('profile', {}),
            'stats': {
                'unlocked_contacts': unlocked_count,
                'reviews_count': len(reviews_list),
                'average_rating': avg_rating
            }
        },
        'reviews': enriched_reviews
    })), 200


@surveyor_bp.route('/surveyor/profile', methods=['PUT'])
@role_required('surveyor')
def update_my_profile():
    db = get_db()
    surveyor_id = ObjectId(request.current_user_id)
    data = request.get_json() or {}

    # Build profile update — only accept known fields
    allowed = [
        'owner_name', 'company', 'experience', 'specialization',
        'license_no', 'gst_no', 'machines', 'photo'
    ]
    profile_update = {k: data[k] for k in allowed if k in data}

    # Validate machines is a list
    if 'machines' in profile_update and not isinstance(profile_update['machines'], list):
        profile_update['machines'] = []

    # Merge into existing profile (don't overwrite unrelated fields)
    surveyor = db.users.find_one({'_id': surveyor_id})
    if not surveyor:
        return jsonify({'error': 'Surveyor not found'}), 404

    existing_profile = surveyor.get('profile', {})
    existing_profile.update(profile_update)

    db.users.update_one(
        {'_id': surveyor_id},
        {'$set': {'profile': existing_profile}}
    )

    return jsonify({'message': 'Profile updated successfully'}), 200


# ─────────────────────────────────────────────
# GET /api/surveyor/public-profile/<surveyor_id>
# Public profile visible to any logged-in user
# (customers use this to view surveyor profiles)
# ─────────────────────────────────────────────
@surveyor_bp.route('/surveyor/public-profile/<surveyor_id>', methods=['GET'])
@token_required   # any logged-in user (customer OR surveyor) can view
def get_public_profile(surveyor_id):
    db = get_db()

    # Validate ObjectId
    try:
        oid = ObjectId(surveyor_id)
    except Exception:
        return jsonify({'error': 'Invalid surveyor ID'}), 400

    surveyor = db.users.find_one({'_id': oid, 'role': 'surveyor'})
    if not surveyor:
        return jsonify({'error': 'Surveyor not found'}), 404

    # Stats
    unlocked_count = db.contact_unlocks.count_documents({'surveyor_id': oid})
    reviews_list = list(db.reviews.find({'surveyor_id': oid}))
    avg_rating = (
        round(sum(r['rating'] for r in reviews_list) / len(reviews_list), 1)
        if reviews_list else 0
    )

    # Enrich reviews
    enriched_reviews = []
    for r in reviews_list:
        listing = db.listings.find_one({'_id': r.get('listing_id')})
        customer = db.users.find_one({'_id': r.get('customer_id')})
        enriched_reviews.append({
            'rating': r.get('rating'),
            'review_text': r.get('review_text'),
            'customer_name': customer.get('name') if customer else 'Customer',
            'survey_type': listing.get('survey_type') if listing else '',
            'created_at': r.get('created_at')
        })

    # Profile (public-safe — includes photo, machines, etc. but we exclude password_hash)
    profile = surveyor.get('profile', {})

    return jsonify(serialize({
        'surveyor': {
            'id': str(surveyor['_id']),
            'name': surveyor.get('name'),
            'phone': surveyor.get('phone'),   # visible because customer unlocked; adjust if you want to hide
            'profile': profile,
            'stats': {
                'unlocked_contacts': unlocked_count,
                'reviews_count': len(reviews_list),
                'average_rating': avg_rating
            }
        },
        'reviews': enriched_reviews
    })), 200