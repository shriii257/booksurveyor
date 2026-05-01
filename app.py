"""
Surveyor Marketplace Platform - Main Application Entry Point
"""
from flask import Flask
from flask_cors import CORS
from config import Config
from database import init_db

# Import route blueprints
from routes.auth_routes import auth_bp
from routes.listing_routes import listing_bp
from routes.surveyor_routes import surveyor_bp
from routes.customer_routes import customer_bp
from routes.review_routes import review_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS for all routes
    CORS(app)
    
    # Initialize database connection
    init_db(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(listing_bp, url_prefix='/api')
    app.register_blueprint(surveyor_bp, url_prefix='/api')
    app.register_blueprint(customer_bp, url_prefix='/api')
    app.register_blueprint(review_bp, url_prefix='/api')
    
    # Serve frontend pages
    from flask import send_from_directory
    
    @app.route('/')
    def index():
        return send_from_directory('templates', 'index.html')
    
    @app.route('/<path:filename>')
    def serve_template(filename):
        if filename.endswith('.html'):
            return send_from_directory('templates', filename)
        return send_from_directory('static', filename)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
