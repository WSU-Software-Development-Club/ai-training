""" Test Services"""

import unittest
from unittest.mock import patch, Mock
from app import create_app
from api_vars import NCAA_API_BASE_URL
from services.history_service import get_championship_winners


class TestServices(unittest.TestCase):
  
    def setUp(self):
        """Set up test client"""
        self.app = create_app('development')
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
       
    
    @patch('services.history_service.requests.get')
    def test_get_championship_winners_success(self, mock_get):
        """Test successful retrieval of championship winners"""
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "count": 3,
            "data": {
                "data": [
                    {
                        "Champion": "Ohio State",
                        "Season": "2024",
                        "Selecting Organization": "CFP"
                    },
                    {
                        "Champion": "Michigan",
                        "Season": "2023",
                        "Selecting Organization": "CFP"
                    },
                    {
                        "Champion": "Georgia",
                        "Season": "2022",
                        "Selecting Organization": "CFP"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        result = get_championship_winners()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['count'], 3)
        self.assertEqual(len(result['data']['data']), 3)
        
        first_champion = result['data']['data'][0]
        self.assertEqual(first_champion['Champion'], 'Ohio State')
        self.assertEqual(first_champion['Season'], '2024')
        
        mock_get.assert_called_once_with(f'{NCAA_API_BASE_URL}/history/football/fbs')
    
    @patch('services.history_service.requests.get')
    def test_get_championship_winners_empty_response(self, mock_get):
        """Test handling of empty championship data"""
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "count": 0,
            "data": {
                "data": []
            }
        }
        mock_get.return_value = mock_response
        
        result = get_championship_winners()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['count'], 0)
        self.assertEqual(len(result['data']['data']), 0)
    
    @patch('services.history_service.requests.get')
    def test_get_championship_winners_api_returns_404(self, mock_get):
        """Test handling when API returns 404"""
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Not Found"}
        mock_get.return_value = mock_response

        result = get_championship_winners()
        
        self.assertEqual(result['error'], 'Not Found')
    
    @patch('services.history_service.requests.get')
    def test_get_championship_winners_api_returns_500(self, mock_get):
        """Test handling when API returns server error"""
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal Server Error"}
        mock_get.return_value = mock_response
        
        result = get_championship_winners()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['error'], 'Internal Server Error')
    
    
    
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
