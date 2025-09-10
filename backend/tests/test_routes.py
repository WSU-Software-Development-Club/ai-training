"""Test routes"""

import unittest
from app import create_app

class TestRoutes(unittest.TestCase):
    """Test cases for routes"""
    
    def setUp(self):
        """Set up test client"""
        self.app = create_app('development')
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    def test_home_route(self):
        """Test home route"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
    
    def test_health_route(self):
        """Test health route"""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('status', data)
    
    def test_about_route(self):
        """Test about route"""
        response = self.client.get('/about')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('name', data)

if __name__ == '__main__':
    unittest.main()
