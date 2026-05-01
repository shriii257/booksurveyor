"""
Authentication Routes - Register and Login
"""
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
from auth_middleware import generate_token
import re

auth_bp = Blueprint('auth', __name__)

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    # Allow 10-digit Indian numbers or international format
    pattern = r'^\+?[0-9]{10,15}$'
    return re.match(pattern, phone) is not None

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user (customer or surveyor)."""
    data = request.get_json()
    
    # Validate required fields
    required = ['name', 'role', 'password']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Must have email OR phone
    if not data.get('email') and not data.get('phone'):
        return jsonify({'error': 'Email or phone number is required'}), 400
    
    # Validate role
    if data['role'] not in ['customer', 'surveyor']:
        return jsonify({'error': 'Role must be customer or surveyor'}), 400
    
    # Validate email if provided
    if data.get('email') and not validate_email(data['email']):
        return jsonify({'error': 'Invalid email format'}), 400
    
    # Validate phone if provided
    if data.get('phone') and not validate_phone(data['phone']):
        return jsonify({'error': 'Invalid phone number format'}), 400
    
    if len(data['password']) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    db = get_db()
    
    # Check if email already exists
    if data.get('email'):
        if db.users.find_one({'email': data['email']}):
            return jsonify({'error': 'Email already registered'}), 409
    
    # Check if phone already exists
    if data.get('phone'):
        if db.users.find_one({'phone': data['phone']}):
            return jsonify({'error': 'Phone number already registered'}), 409
    
    # Create user document
    user_doc = {
        'name': data['name'].strip(),
        'email': data.get('email', '').lower().strip(),
        'phone': data.get('phone', '').strip(),
        'role': data['role'],
        'password_hash': generate_password_hash(data['password']),
        'subscription_active': True,  # MVP: all surveyors have active subscription
        'profile': {
            'company': data.get('company', ''),
            'experience': data.get('experience', ''),
            'specializations': data.get('specializations', [])
        }
    }
    
    result = db.users.insert_one(user_doc)
    user_id = result.inserted_id
    
    # Generate token
    token = generate_token(user_id, data['role'])
    
    return jsonify({
        'message': 'Registration successful',
        'token': token,
        'user': {
            'id': str(user_id),
            'name': user_doc['name'],
            'role': user_doc['role'],
            'email': user_doc['email'],
            'phone': user_doc['phone']
        }
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login with email/phone and password."""
    data = request.get_json()
    
    if not data.get('password'):
        return jsonify({'error': 'Password is required'}), 400
    
    if not data.get('email') and not data.get('phone'):
        return jsonify({'error': 'Email or phone is required'}), 400
    
    db = get_db()
    
    # Find user by email or phone
    user = None
    if data.get('email'):
        user = db.users.find_one({'email': data['email'].lower().strip()})
    elif data.get('phone'):
        user = db.users.find_one({'phone': data['phone'].strip()})
    
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not check_password_hash(user['password_hash'], data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    token = generate_token(user['_id'], user['role'])
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {
            'id': str(user['_id']),
            'name': user['name'],
            'role': user['role'],
            'email': user.get('email', ''),
            'phone': user.get('phone', '')
        }
    }), 200


@auth_bp.route('/me', methods=['GET'])
def get_me():
    """Get current user profile."""
    from auth_middleware import token_required
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'No token provided'}), 401
    
    token = auth_header.split(' ')[1]
    from auth_middleware import decode_token
    payload = decode_token(token)
    
    if not payload:
        return jsonify({'error': 'Invalid token'}), 401
    
    from bson import ObjectId
    db = get_db()
    user = db.users.find_one({'_id': ObjectId(payload['user_id'])})
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'id': str(user['_id']),
        'name': user['name'],
        'role': user['role'],
        'email': user.get('email', ''),
        'phone': user.get('phone', ''),
        'subscription_active': user.get('subscription_active', True),
        'profile': user.get('profile', {})
    }), 200
