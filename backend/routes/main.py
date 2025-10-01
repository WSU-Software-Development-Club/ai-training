"""Main application routes"""

from flask import Blueprint, jsonify
from datetime import datetime, timezone

# Create main blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET'])
def home():
    """Home endpoint"""
    return jsonify({
        'message': 'Hello from Flask backend!',
        'app_name': 'React Flask Web App',
        'version': '1.0.0',
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

@main_bp.route('/about', methods=['GET'])
def about():
    """About endpoint"""
    return jsonify({
        'name': 'React Flask Web App',
        'version': '1.0.0',
        'description': 'A simple React and Flask application',
        'status': 'running'
    })
