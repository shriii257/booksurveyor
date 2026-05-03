"""
Surveyor Marketplace Platform - Main Application Entry Point
"""
from flask import Flask, render_template
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
    
    # Serve frontend
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)