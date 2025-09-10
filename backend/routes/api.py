"""API routes for the application"""

from flask import Blueprint, jsonify
from datetime import datetime

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@api_bp.route('/status', methods=['GET'])
def status():
    """Application status endpoint"""
    return jsonify({
        'name': 'React Flask Web App',
        'version': '1.0.0',
        'status': 'running',
        'uptime': 'active'
    })
