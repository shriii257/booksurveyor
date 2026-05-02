"""
Customer Routes
"""
from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime
from database import get_db
from auth_middleware import token_required, role_required

customer_bp = Blueprint('customer', __name__)


def serialize(doc):
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
# GET /api/customer/dashboard
# ─────────────────────────────────────────────
@customer_bp.route('/customer/dashboard', methods=['GET'])
@role_required('customer')
def customer_dashboard():
    db = get_db()
    customer_id = ObjectId(request.current_user_id)

    # All listings by this customer
    listings = list(db.listings.find({'customer_id': customer_id}).sort('created_at', -1))

    result = []
    for listing in listings:
        listing_id = listing['_id']

        # Find all surveyors who unlocked this listing
        unlocks = list(db.contact_unlocks.find({'listing_id': listing_id}))

        unlock_details = []
        for u in unlocks:
            surveyor = db.users.find_one({'_id': u['surveyor_id']})
            has_review = db.reviews.find_one({
                'listing_id': listing_id,
                'surveyor_id': u['surveyor_id']
            }) is not None

            unlock_details.append({
                'unlock_id': str(u['_id']),
                'surveyor_id': str(u['surveyor_id']),   # ← needed for "View Profile"
                'surveyor_name': surveyor.get('name') if surveyor else 'Unknown',
                'status': u.get('status', 'pending'),
                'has_review': has_review,
                'unlocked_at': u.get('unlocked_at')
            })

        result.append({
            'id': str(listing_id),
            'survey_type': listing.get('survey_type'),
            'area': listing.get('area'),
            'address': listing.get('address'),
            'date': listing.get('date'),
            'time': listing.get('time'),
            'phone': listing.get('phone'),
            'description': listing.get('description', ''),
            'status': listing.get('status', 'open'),
            'unlocks': unlock_details
        })

    # Summary stats
    all_unlocks = list(db.contact_unlocks.find({'customer_id': customer_id}))
    contacted_count = sum(1 for u in all_unlocks if u.get('status') == 'contacted')

    return jsonify(serialize({
        'listings': result,
        'stats': {
            'total_listings': len(listings),
            'total_unlocks': len(all_unlocks),
            'contacted': contacted_count
        }
    })), 200


# ─────────────────────────────────────────────
# POST /api/mark-contacted
# ─────────────────────────────────────────────
@customer_bp.route('/mark-contacted', methods=['POST'])
@role_required('customer')
def mark_contacted():
    db = get_db()
    data = request.get_json() or {}
    unlock_id_str = data.get('unlock_id', '').strip()

    if not unlock_id_str:
        return jsonify({'error': 'unlock_id is required'}), 400

    try:
        unlock_id = ObjectId(unlock_id_str)
    except Exception:
        return jsonify({'error': 'Invalid unlock_id'}), 400

    customer_id = ObjectId(request.current_user_id)

    unlock = db.contact_unlocks.find_one({'_id': unlock_id, 'customer_id': customer_id})
    if not unlock:
        return jsonify({'error': 'Unlock record not found or access denied'}), 404

    db.contact_unlocks.update_one(
        {'_id': unlock_id},
        {'$set': {'status': 'contacted', 'contacted_at': datetime.utcnow()}}
    )

    return jsonify({'message': 'Marked as contacted'}), 200


# ─────────────────────────────────────────────
# POST /api/mark-not-contacted
# ─────────────────────────────────────────────
@customer_bp.route('/mark-not-contacted', methods=['POST'])
@role_required('customer')
def mark_not_contacted():
    db = get_db()
    data = request.get_json() or {}
    unlock_id_str = data.get('unlock_id', '').strip()

    if not unlock_id_str:
        return jsonify({'error': 'unlock_id is required'}), 400

    try:
        unlock_id = ObjectId(unlock_id_str)
    except Exception:
        return jsonify({'error': 'Invalid unlock_id'}), 400

    customer_id = ObjectId(request.current_user_id)

    unlock = db.contact_unlocks.find_one({'_id': unlock_id, 'customer_id': customer_id})
    if not unlock:
        return jsonify({'error': 'Unlock record not found or access denied'}), 404

    db.contact_unlocks.update_one(
        {'_id': unlock_id},
        {'$set': {'status': 'not_contacted'}}
    )

    return jsonify({'message': 'Marked as not contacted'}), 200