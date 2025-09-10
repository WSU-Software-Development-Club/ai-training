import os
from flask import Flask
from flask_cors import CORS
from config import config
from routes.main import main_bp
from routes.api import api_bp
from utils.helpers import setup_logging

# Create the Flask application
app = Flask(__name__)

# Load configuration
config_name = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[config_name])

# Setup logging
setup_logging()

# Enable CORS
CORS(app, origins=app.config['CORS_ORIGINS'])

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)

if __name__ == '__main__':
    app.run(
        debug=app.config['DEBUG'],
        host=app.config['HOST'],
        port=app.config['PORT'],
        use_reloader=True
    )
