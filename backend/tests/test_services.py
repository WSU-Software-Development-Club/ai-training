""" Test Services"""

import unittest
import requests
from unittest.mock import patch, Mock
from app import create_app
from api_vars import NCAA_API_BASE_URL
from services.history_service import get_championship_winners
from services.rankings_service import get_ap_rankings
from services.stats_service import get_all_teams_stats, get_offense_stats
from services.scoreboard_service import get_scoreboard_data


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
                ],
                "page": 1,
                "pages": 1,
                "sport": "Football",
                "title": "Championship History",
                "updated": ""
            },
            "message": "Championship data retrieved successfully",
            "success": True
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
                "data": [],
                "page": 1,
                "pages": 1,
                "sport": "Football",
                "title": "Championship History",
                "updated": ""
            },
            "message": "Championship data retrieved successfully",
            "success": True
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
        mock_response.json.return_value = {
            "error": "Failed to fetch championship data from NCAA API",
            "success": False
        }
        mock_get.return_value = mock_response

        result = get_championship_winners()
        
        self.assertEqual(result['error'], 'Failed to fetch championship data from NCAA API')
    
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
    
    

    @patch('services.rankings_service.requests.get')
    def test_get_ap_rankings_success(self, mock_get):
        """Test successful retrieval of rankings"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "data": [
                {
                    "POINTS": "1633",
                    "PREVIOUS": "1",
                    "RANK": "1",
                    "RECORD": "7-0",
                    "SCHOOL": "Ohio State (54)"
                },
                {
                    "POINTS": "1589",
                    "PREVIOUS": "2",
                    "RANK": "2",
                    "RECORD": "8-0",
                    "SCHOOL": "Indiana (11)"
                },
                {
                    "POINTS": "1523",
                    "PREVIOUS": "3",
                    "RANK": "3",
                    "RECORD": "8-0",
                    "SCHOOL": "Texas A&M (1)"
                }
                ],
                "page": 1,
                "pages": 1,
                "sport": "Football",
                "title": "College football rankings: Associated Press Top 25",
                "updated": "Through Games OCT. 26, 2025"
            },
            "data_type": "AP rankings",
            "success": True
        }
        mock_get.return_value = mock_response
        
        result = get_ap_rankings()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['data_type'], "AP rankings")
        self.assertEqual(len(result['data']['data']), 3)
        
        rank_one = result['data']['data'][0]
        self.assertEqual(rank_one['SCHOOL'], 'Ohio State (54)')
        self.assertEqual(rank_one['RECORD'], '7-0')
        
        mock_get.assert_called_once_with(f'{NCAA_API_BASE_URL}/rankings/football/fbs/associated-press', timeout=10)
    

    @patch('services.rankings_service.requests.get')
    def test_get_ap_rankings_empty_response(self, mock_get):
        """Test successful retrieval of empty rankings"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "data": [],
                "page": 1,
                "pages": 1,
                "sport": "Football",
                "title": "College football rankings: Associated Press Top 25",
                "updated": "Through Games OCT. 26, 2025"
            },
            "data_type": "AP rankings",
            "success": True
        }
        mock_get.return_value = mock_response
        
        result = get_ap_rankings()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['data_type'], "AP rankings")
        self.assertEqual(len(result['data']['data']), 0)
        
        mock_get.assert_called_once_with(f'{NCAA_API_BASE_URL}/rankings/football/fbs/associated-press', timeout = 10)
        
    @patch('services.rankings_service.requests.get')
    def test_get_get_ap_rankings_returns_404(self, mock_get):
        """Test handling when API returns 404"""
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "error": "Failed to fetch AP rankings",
            "success": False
            }
        mock_get.return_value = mock_response

        result = get_ap_rankings()
        
        self.assertEqual(result['error'], 'Failed to fetch AP rankings')


    @patch('services.scoreboard_service.requests.get')
    def test_get_scoreboard_data_success(self, mock_get):
        """Test successful retrieval of scoreboard data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "inputMD5Sum": "d48a34310cf1c71c2ac38ad8ad1b9415",
            "instanceId": "d41d8cd98f00b204e9800998ecf8427e",
            "updated_at": "2025-10-30 04:44:57",
            "games": [
            {
                "game": {
                    "gameID": "6459454",
                    "away": {
                    "score": "10",
                    "names": {
                        "char6": "SAMHOU",
                        "short": "Sam Houston",
                        "seo": "sam-houston-st",
                        "full": "Sam Houston State University"
                    },
                    "winner": False,
                    "seed": "",
                    "description": "(0-1)",
                    "rank": "",
                    "conferences": [
                        {
                        "conferenceName": "CUSA",
                        "conferenceSeo": "cusa"
                        }
                    ]
                    },
                    "finalMessage": "FINAL",
                    "bracketRound": "",
                    "title": "Sam Houston New Mexico St.",
                    "contestName": "",
                    "url": "/game/6459454",
                    "network": "",
                    "home": {
                    "score": "37",
                    "names": {
                        "char6": "NM ST",
                        "short": "New Mexico St.",
                        "seo": "new-mexico-st",
                        "full": "New Mexico State University"
                    },
                    "winner": True,
                    "seed": "",
                    "description": "(0-0)",
                    "rank": "",
                    "conferences": [
                        {
                        "conferenceName": "CUSA",
                        "conferenceSeo": "cusa"
                        }
                    ]
                    },
                    "liveVideoEnabled": False,
                    "startTime": "9:00 PM ET",
                    "startTimeEpoch": "1759453200",
                    "bracketId": "",
                    "gameState": "final",
                    "startDate": "10/02/2025",
                    "currentPeriod": "FINAL",
                    "videoState": "",
                    "bracketRegion": "",
                    "contestClock": "0:00"
                }
            }
            ]
        }


        mock_get.return_value = mock_response
        
        result = get_scoreboard_data(6,2025)
 
        self.assertIsNotNone(result)
        self.assertEqual(result['week'], 6)
        self.assertEqual(result['games'][0]['game_state']['isFinished'], True)
        
        mock_get.assert_called_once_with(f'{NCAA_API_BASE_URL}/scoreboard/football/fbs/2025/06/all-conf', timeout=10)
    
    @patch('services.scoreboard_service.requests.get')
    def test_get_scoreboard_data_404(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        result = get_scoreboard_data(6,2025)
        self.assertIsNone(result)

    @patch('services.stats_service.requests.get')
    def test_get_offense_stats_empty(self, mock_get):
        """Test successful retrieval Total Offense stats with empty data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "data": [],
                    "page": 1,
                    "pages": 3,
                    "sport": "Football",
                    "title": "Total Offense",
                    "total_records": 134,
                    "updated": "Sunday, October 26, 2025 6:10 am - Through games Saturday, October 25, 2025"
                },
                "stat_name": "Total Offense",
                "success": True
            }
        mock_get.return_value = mock_response
        
        result = get_offense_stats()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['stat_name'], "Total Offense")
        
        calls = mock_get.call_args_list
        self.assertEqual(len(calls), 2)
   
    @patch('services.stats_service.requests.get')
    def test_get_all_teams_stats_returns_404(self, mock_get):
        """Test handling when get_team_stats returns 404""" 
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")

        result = get_all_teams_stats(742)
        
        self.assertIsNone(result)



    @patch('services.stats_service.requests.get')
    def test_single_page_response(self, mock_get):
        """Test when all data fits on a single page (no pagination needed)"""
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sport": "Football",
            "title": "Total Offense",
            "updated": "Sunday, October 26, 2025 6:10 am - Through games Saturday, October 25, 2025",
            "page": 1,
            "pages": 1,
            "data": [
                {
                "Rank": "1",
                "Team": "Southern California",
                "G": "7",
                "Plays": "470",
                "YDS": "3710",
                "Yds/Play": "7.89",
                "Off TDs": "35",
                "YPG": "530.0"
                },
                {
                "Rank": "2",
                "Team": "Florida St.",
                "G": "7",
                "Plays": "517",
                "YDS": "3663",
                "Yds/Play": "7.09",
                "Off TDs": "36",
                "YPG": "523.3"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = get_all_teams_stats(21)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result['data']), 2)
        self.assertEqual(result['total_records'], 2)
        
        self.assertEqual(mock_get.call_count, 2)
        mock_get.assert_any_call(f"{NCAA_API_BASE_URL}/stats/football/fbs/current/team/21", timeout=10)
    
    
    
    @patch('services.stats_service.requests.get')
    def test_two_pages_response(self, mock_get):
        """Test pagination with exactly 2 pages of data"""
        
        page1_response = Mock()
        page1_response.status_code = 200
        page1_response.json.return_value = {
            "sport": "Football",
            "title": "Total Offense",
            "updated": "Sunday, October 26, 2025 6:10 am - Through games Saturday, October 25, 2025",
            "page": 1,
            "pages": 2,
            "data": [
                {
                "Rank": "1",
                "Team": "Southern California",
                "G": "7",
                "Plays": "470",
                "YDS": "3710",
                "Yds/Play": "7.89",
                "Off TDs": "35",
                "YPG": "530.0"
                },
                {
                "Rank": "2",
                "Team": "Florida St.",
                "G": "7",
                "Plays": "517",
                "YDS": "3663",
                "Yds/Play": "7.09",
                "Off TDs": "36",
                "YPG": "523.3"
                }
            ]
        }
        
        
        page2_response = Mock()
        page2_response.status_code = 200
        page2_response.json.return_value = {
            "sport": "Football",
            "title": "Total Offense",
            "updated": "Sunday, October 26, 2025 6:10 am - Through games Saturday, October 25, 2025",
            "page": 2,
            "pages": 2,
            "data": [
                {
                "Rank": "51",
                "Team": "Miami (FL)",
                "G": "7",
                "Plays": "470",
                "YDS": "2878",
                "Yds/Play": "6.12",
                "Off TDs": "31",
                "YPG": "411.1"
                },
                {
                "Rank": "52",
                "Team": "Michigan",
                "G": "8",
                "Plays": "508",
                "YDS": "3287",
                "Yds/Play": "6.47",
                "Off TDs": "29",
                "YPG": "410.9"
                }
            ]
        }
        
        mock_get.side_effect = [
            page1_response,  # First call (page 1 in loop)
            page2_response,  # Second call (page 2 in loop)
            page1_response   # Third call (getting metadata)
        ]
        
        result = get_all_teams_stats(21)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result['data']), 4)  
        self.assertEqual(result['total_records'], 4)
        
        team_names = [team['Team'] for team in result['data']]
        self.assertIn("Michigan", team_names)
        self.assertIn("Florida St.", team_names)
        
        self.assertEqual(mock_get.call_count, 3)
        
        calls = mock_get.call_args_list
        self.assertEqual(calls[0][0][0], f"{NCAA_API_BASE_URL}/stats/football/fbs/current/team/21")  # Page 1
        self.assertEqual(calls[1][0][0], f"{NCAA_API_BASE_URL}/stats/football/fbs/current/team/21/p2")  # Page 2
        self.assertEqual(calls[2][0][0], f"{NCAA_API_BASE_URL}/stats/football/fbs/current/team/21")  # Metadata fetch


if __name__ == '__main__':
    unittest.main()
