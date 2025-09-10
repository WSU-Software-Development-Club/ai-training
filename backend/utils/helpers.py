"""Simple utility functions"""

import logging

def setup_logging():
    """Setup basic logging"""
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(__name__)
