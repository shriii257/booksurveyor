"""
Review Routes - Submit and view reviews
"""
from flask import Blueprint, request, jsonify
from database import get_db
from auth_middleware import role_required, token_required
from bson import ObjectId
from datetime import datetime

review_bp = Blueprint('reviews', __name__)

@review_bp.route('/submit-review', methods=['POST'])
@role_required('customer')
def submit_review():
    """Customer submits a review for a surveyor. Only allowed if status = contacted."""
    data = request.get_json()
    
    required = ['unlock_id', 'rating', 'review_text']
    for field in required:
        if data.get(field) is None:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Validate rating range
    try:
        rating = int(data['rating'])
        if rating < 1 or rating > 5:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    
    if not data.get('review_text', '').strip():
        return jsonify({'error': 'Review text cannot be empty'}), 400
    
    db = get_db()
    
    # Get unlock record
    try:
        unlock = db.contact_unlocks.find_one({'_id': ObjectId(data['unlock_id'])})
    except Exception:
        return jsonify({'error': 'Invalid unlock ID'}), 400
    
    if not unlock:
        return jsonify({'error': 'Unlock record not found'}), 404
    
    # Verify this customer owns this unlock
    if str(unlock['customer_id']) != request.current_user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # CRITICAL: Only allow review if status = contacted
    if unlock.get('status') != 'contacted':
        return jsonify({
            'error': 'You can only review a surveyor after marking them as "Contacted"'
        }), 403
    
    # Check if review already submitted for this unlock
    existing_review = db.reviews.find_one({
        'listing_id': unlock['listing_id'],
        'surveyor_id': unlock['surveyor_id'],
        'customer_id': ObjectId(request.current_user_id)
    })
    
    if existing_review:
        return jsonify({'error': 'You have already submitted a review for this surveyor'}), 409
    
    # Create review
    review_doc = {
        'listing_id': unlock['listing_id'],
        'surveyor_id': unlock['surveyor_id'],
        'customer_id': ObjectId(request.current_user_id),
        'unlock_id': unlock['_id'],
        'rating': rating,
        'review_text': data['review_text'].strip(),
        'created_at': datetime.utcnow()
    }
    
    result = db.reviews.insert_one(review_doc)
    
    return jsonify({
        'message': 'Review submitted successfully',
        'review_id': str(result.inserted_id)
    }), 201


@review_bp.route('/reviews/surveyor/<surveyor_id>', methods=['GET'])
@token_required
def get_surveyor_reviews(surveyor_id):
    """Get all reviews for a specific surveyor."""
    db = get_db()
    
    try:
        reviews = list(db.reviews.find({'surveyor_id': ObjectId(surveyor_id)}).sort('created_at', -1))
    except Exception:
        return jsonify({'error': 'Invalid surveyor ID'}), 400
    
    result = []
    for review in reviews:
        customer = db.users.find_one({'_id': review['customer_id']})
        listing = db.listings.find_one({'_id': review['listing_id']})
        result.append({
            'id': str(review['_id']),
            'customer_name': customer['name'] if customer else 'Anonymous',
            'survey_type': listing.get('survey_type', '') if listing else '',
            'rating': review.get('rating', 0),
            'review_text': review.get('review_text', ''),
            'created_at': review.get('created_at', '').isoformat() if review.get('created_at') else ''
        })
    
    # Calculate average
    avg_rating = 0
    if result:
        avg_rating = sum(r['rating'] for r in result) / len(result)
    
    return jsonify({
        'reviews': result,
        'average_rating': round(avg_rating, 1),
        'total_reviews': len(result)
    }), 200
