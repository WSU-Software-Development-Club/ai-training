""" Test Services"""

import unittest
from app import create_app

class TestServices(unittest.TestCase):
    # test cases for services functions
    def setUp(self):
        """Set up test client"""
        self.app = create_app('development')
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
       
    
    def test_history_service(self):
        """Test history service"""
        response = self.client.get('/history/football/fbs')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
    
    def test_ranking_service(self):
        """Test ranking service"""
        response = self.client.get('/rankings/football/fbs/associated-press')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('status', data)
    
    def test_stats_service(self):
        """Test stats service"""
        response = self.client.get('/stats/football/fbs/current/team/')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('name', data)

if __name__ == '__main__':
    unittest.main()
