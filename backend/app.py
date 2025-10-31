import os
from flask import Flask
from flask_cors import CORS
from config import config
from routes.main import main_bp
from routes.api import api_bp
from routes.history import history_bp
from routes.rankings import rankings_bp
from routes.stats import stats_bp
from routes.scoreboard import scoreboard_bp
from routes.team import team_bp
from utils.helpers import setup_logging

def create_app(config_name=None):
    """Application factory function"""
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Setup logging
    setup_logging()
    
    # Enable CORS
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(rankings_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(scoreboard_bp)
    app.register_blueprint(team_bp)
    
    return app

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    app.run(
        debug=app.config['DEBUG'],
        host=app.config['HOST'],
        port=app.config['PORT'],
        use_reloader=True
    )
