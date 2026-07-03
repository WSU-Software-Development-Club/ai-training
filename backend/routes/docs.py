"""API documentation routes.

Serves interactive Swagger UI at ``/apidocs`` backed by the hand-written
OpenAPI spec in ``backend/openapi.yaml``. The raw spec is exposed at
``/openapi.yaml`` so it can also be imported into Postman/Insomnia or rendered
by any other OpenAPI tool.

The spec is authored by hand (not introspected from the routes) to keep the
route handlers thin — see ``openapi.yaml`` for the source of truth.
"""

import os

from flask import Blueprint, send_file
from flask_swagger_ui import get_swaggerui_blueprint

# Path to the API docs UI and the raw spec URL it loads.
SWAGGER_UI_URL = '/apidocs'
OPENAPI_SPEC_ROUTE = '/openapi.yaml'

_SPEC_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'openapi.yaml')

# Blueprint that serves the raw spec file.
docs_bp = Blueprint('docs', __name__)


@docs_bp.route(OPENAPI_SPEC_ROUTE, methods=['GET'])
def openapi_spec():
    """Serve the raw OpenAPI YAML spec."""
    return send_file(_SPEC_PATH, mimetype='application/yaml')


# Swagger UI blueprint (renders the interactive docs at /apidocs).
swagger_ui_bp = get_swaggerui_blueprint(
    SWAGGER_UI_URL,
    OPENAPI_SPEC_ROUTE,
    config={'app_name': 'CFB Analytics & Predictions API'},
)
