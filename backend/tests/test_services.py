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
from services.matchup_service import get_matchup_polymarket_history
from services.team_service import (
    canonical_team_key,
    get_team_record,
    _get_team_record_cfbd,
)


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

    @patch('services.scoreboard_service.get_db')
    @patch('services.scoreboard_service.requests.get')
    def test_get_scoreboard_data_attaches_prediction_with_mismatched_week(self, mock_get, mock_get_db):
        """Regression test: a prediction row stored under a DIFFERENT
        season/week than the scoreboard is queried with (e.g. the ML writer's
        CFBD week vs. the NCAA scoreboard's display week) must still attach,
        because ncaa_game_id is UNIQUE and is matched on alone.
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "updated_at": "2025-10-30 04:44:57",
            "games": [
                {
                    "game": {
                        "gameID": "6459454",
                        "away": {"score": "10", "names": {"full": "Sam Houston State University"}},
                        "home": {"score": "37", "names": {"full": "New Mexico State University"}},
                        "startTimeEpoch": "1759453200",
                        "gameState": "final",
                    }
                }
            ],
        }
        mock_get.return_value = mock_response

        # Seed a predictions row whose ncaa_game_id matches the scoreboard game,
        # but whose season/week were stored differently (e.g. postseason
        # cfbd_week+15, or the NCAA "week 01" that folds in CFBD week 0) than
        # the (season=2025, week=6) the scoreboard is being queried with.
        stored_prediction = {
            "id": "fake-uuid",
            "game_id": 401520000,
            "ncaa_game_id": 6459454,
            "season": 2025,
            "week": 21,  # mismatched vs the queried week (6)
            "game_date": "2025-10-02T21:00:00Z",
            "home_team": "New Mexico State",
            "away_team": "Sam Houston State",
            "predicted_home_score": 34.0,
            "predicted_away_score": 14.0,
            "predicted_winner": "New Mexico State",
            "predicted_margin": 20.0,
            "predicted_total": 48.0,
            "betting_over_under": None,
            "over_probability": None,
            "under_probability": None,
            "neutral_site": False,
            "prediction_made_at": "2025-09-30T00:00:00Z",
            "created_at": "2025-09-30T00:00:00Z",
        }

        mock_db = Mock()
        mock_db.is_connected = True
        # The batch query is season/week-scoped, so with a mismatched stored
        # week it legitimately finds nothing for THIS week...
        mock_db.get_predictions_by_week.return_value = []
        # ...but the id-only lookup (the fix) finds it regardless of week.
        mock_db.get_prediction_by_ncaa_game_id.return_value = stored_prediction
        mock_get_db.return_value = mock_db

        result = get_scoreboard_data(6, 2025)

        self.assertIsNotNone(result)
        self.assertTrue(result['hasPredictions'])
        self.assertIn('prediction', result['games'][0])
        self.assertEqual(result['games'][0]['prediction']['ncaa_game_id'], 6459454)
        self.assertEqual(result['games'][0]['prediction']['week'], 21)

        # Confirm the fixed lookup was called id-only (no season/week args).
        mock_db.get_prediction_by_ncaa_game_id.assert_called_once_with(6459454)

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


    @patch('services.matchup_service.get_db')
    def test_polymarket_history_no_prediction_returns_none(self, mock_get_db):
        """No prediction row for the game -> None (route turns this into a 404).
        Both id lookups miss: the NCAA-id one and the CFBD game-id fallback that
        _resolve_prediction also tries for future-season games."""
        mock_db = Mock()
        mock_db.is_connected = True
        mock_db.get_prediction_by_ncaa_game_id.return_value = None
        mock_db.get_prediction_by_game_id.return_value = None
        mock_get_db.return_value = mock_db

        self.assertIsNone(get_matchup_polymarket_history(6459454))

    @patch('services.matchup_service.get_db')
    def test_polymarket_history_shapes_series(self, mock_get_db):
        """A prediction + snapshots -> ordered points, team names from the
        prediction, and market metadata backfilled from the latest snapshot."""
        mock_db = Mock()
        mock_db.is_connected = True
        mock_db.get_prediction_by_ncaa_game_id.return_value = {
            "ncaa_game_id": 6459454,
            "home_team": "New Mexico State",
            "away_team": "Sam Houston State",
        }
        # db.get_polymarket_history returns ascending snapshots; the latest one
        # carries the market question/url used for the whole series.
        mock_db.get_polymarket_history.return_value = [
            {"as_of": "2025-10-01T00:00:00+00:00", "home_win_prob": 0.55,
             "away_win_prob": 0.45, "question": None, "source_url": None},
            {"as_of": "2025-10-02T00:00:00+00:00", "home_win_prob": 0.62,
             "away_win_prob": 0.38, "question": "Who wins?",
             "source_url": "https://polymarket.com/event/x"},
        ]
        mock_get_db.return_value = mock_db

        result = get_matchup_polymarket_history(6459454)

        self.assertEqual(result["home_team"], "New Mexico State")
        self.assertEqual(result["away_team"], "Sam Houston State")
        self.assertEqual(result["question"], "Who wins?")
        self.assertEqual(result["source_url"], "https://polymarket.com/event/x")
        self.assertEqual(len(result["points"]), 2)
        # Points keep only the series fields (no metadata duplicated per point).
        self.assertEqual(result["points"][0],
                         {"as_of": "2025-10-01T00:00:00+00:00",
                          "home_win_prob": 0.55, "away_win_prob": 0.45})
        self.assertEqual(result["points"][1]["home_win_prob"], 0.62)

    @patch('services.matchup_service.get_db')
    def test_polymarket_history_no_market_returns_empty_points(self, mock_get_db):
        """A game with a prediction but no Polymarket market -> 200 with an
        empty points list (not a 404), so the UI shows a 'no market' state."""
        mock_db = Mock()
        mock_db.is_connected = True
        mock_db.get_prediction_by_ncaa_game_id.return_value = {
            "ncaa_game_id": 6459454,
            "home_team": "New Mexico State",
            "away_team": "Sam Houston State",
        }
        mock_db.get_polymarket_history.return_value = []
        mock_get_db.return_value = mock_db

        result = get_matchup_polymarket_history(6459454)

        self.assertIsNotNone(result)
        self.assertEqual(result["points"], [])
        self.assertIsNone(result["question"])


class TestTeamNameMatching(unittest.TestCase):
    """The frontend navigates to a team page using the CSV's canonical school
    name (e.g. "South Florida"), but the NCAA standings feed spells many schools
    differently ("South Fla.", "FIU", "Miami (FL)"). These verify the two feeds
    join so every team's record page loads."""

    def test_state_abbreviation_join(self):
        """A CSV full state name matches the standings' abbreviated form."""
        pairs = [
            ("South Florida", "South Fla."),
            ("Florida Atlantic", "Fla. Atlantic"),
            ("Central Michigan", "Central Mich."),
            ("Georgia Southern", "Ga. Southern"),
            ("Middle Tennessee", "Middle Tenn."),
            ("Western Kentucky", "Western Ky."),
        ]
        for csv_name, standings_name in pairs:
            self.assertEqual(
                canonical_team_key(csv_name),
                canonical_team_key(standings_name),
                f"{csv_name!r} should join {standings_name!r}",
            )

    def test_acronym_and_special_case_join(self):
        """Acronym/qualifier mismatches are reconciled by the alias map."""
        pairs = [
            ("Florida International", "FIU"),
            ("Northern Illinois", "NIU"),
            ("UL Monroe", "ULM"),
            ("Army", "Army West Point"),
            ("Miami", "Miami (FL)"),
            ("USC", "Southern California"),
            ("Hawai'i", "Hawaii"),
        ]
        for csv_name, standings_name in pairs:
            self.assertEqual(
                canonical_team_key(csv_name),
                canonical_team_key(standings_name),
                f"{csv_name!r} should join {standings_name!r}",
            )

    def test_distinct_teams_do_not_collide(self):
        """The reconciliation must not merge genuinely different schools."""
        self.assertNotEqual(
            canonical_team_key("Miami"), canonical_team_key("Miami (OH)")
        )
        self.assertNotEqual(
            canonical_team_key("Ohio State"), canonical_team_key("Ohio")
        )

    @patch('services.team_service.requests.get')
    def test_get_team_record_resolves_abbreviated_standings(self, mock_get):
        """Requesting the CSV name finds the abbreviated standings row."""
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {
            "data": [
                {"standings": [
                    {"School": "South Fla.", "Overall W": 7, "Overall L": 5},
                    {"School": "Miami (OH)", "Overall W": 4, "Overall L": 8},
                ]}
            ]
        }
        mock_get.return_value = mock_resp

        record = get_team_record("South Florida")
        self.assertIsNotNone(record)
        self.assertEqual(record["School"], "South Fla.")


class TestScoreboardCfbdFallback(unittest.TestCase):
    """When the NCAA scoreboard has no games for a week (e.g. a future season),
    the service falls back to the CFBD schedule so those games still show."""

    @patch.dict('os.environ', {'CFBD_API_KEY': 'test-key'})
    @patch('services.scoreboard_service.get_db')
    @patch('services.scoreboard_service.requests.get')
    def test_falls_back_to_cfbd_when_ncaa_empty(self, mock_get, mock_get_db):
        # DB not connected → no predictions attached.
        mock_db = Mock()
        mock_db.is_connected = False
        mock_get_db.return_value = mock_db

        ncaa_resp = Mock()
        ncaa_resp.raise_for_status = Mock()
        ncaa_resp.json.return_value = {"games": []}  # NCAA has nothing

        cfbd_resp = Mock()
        cfbd_resp.raise_for_status = Mock()
        cfbd_resp.json.return_value = [{
            "id": 401856766, "week": 1, "startDate": "2026-08-29T16:00:00.000Z",
            "completed": False, "neutralSite": True,
            "homeTeam": "TCU", "homeConference": "Big 12", "homePoints": None,
            "awayTeam": "North Carolina", "awayConference": "ACC", "awayPoints": None,
        }]
        # 1st requests.get = NCAA (empty), 2nd = CFBD (schedule).
        mock_get.side_effect = [ncaa_resp, cfbd_resp]

        data = get_scoreboard_data(1, 2026)
        self.assertEqual(data["source"], "cfbd")
        self.assertEqual(len(data["games"]), 1)
        g = data["games"][0]
        self.assertEqual(g["home"]["names"]["short"], "TCU")
        self.assertEqual(g["away"]["names"]["short"], "North Carolina")
        self.assertTrue(g["game_state"]["isUpcoming"])
        self.assertIsNotNone(g["epoch"])

    @patch.dict('os.environ', {}, clear=True)
    @patch('services.scoreboard_service.get_db')
    @patch('services.scoreboard_service.requests.get')
    def test_no_cfbd_key_stays_empty(self, mock_get, mock_get_db):
        mock_db = Mock()
        mock_db.is_connected = False
        mock_get_db.return_value = mock_db
        ncaa_resp = Mock()
        ncaa_resp.raise_for_status = Mock()
        ncaa_resp.json.return_value = {"games": []}
        mock_get.return_value = ncaa_resp
        # No CFBD key → fallback yields nothing → the empty NCAA payload is
        # returned unchanged (no games, no cfbd source flag).
        data = get_scoreboard_data(1, 2026)
        self.assertEqual(data["games"], [])
        self.assertNotIn("source", data)


class TestHistoricalTeamRecord(unittest.TestCase):
    """Past-season records come from CFBD and are reshaped into the NCAA
    standings row the frontend renders, with points/streak left as None."""

    @staticmethod
    def _resp(payload):
        m = Mock()
        m.raise_for_status = Mock()
        m.json.return_value = payload
        return m

    @patch.dict('os.environ', {'CFBD_API_KEY': 'test-key'})
    @patch('services.team_service.requests.get')
    def test_cfbd_record_reshaped_to_standings_row(self, mock_get):
        records = [{
            "year": 2023,
            "team": "Alabama",
            "total": {"games": 14, "wins": 12, "losses": 2, "ties": 0},
            "conferenceGames": {"wins": 9, "losses": 0},
            "homeGames": {"wins": 6, "losses": 1},
            "awayGames": {"wins": 5, "losses": 0},
        }]
        # Two completed games: win 30-7 (home), then loss 10-20 (away) -> a
        # current streak of "Lost 1", PF 40, PA 27.
        games = [
            {"startDate": "2023-09-02", "completed": True, "homeTeam": "Alabama",
             "awayTeam": "X", "homePoints": 30, "awayPoints": 7},
            {"startDate": "2023-09-09", "completed": True, "homeTeam": "Y",
             "awayTeam": "Alabama", "homePoints": 20, "awayPoints": 10},
        ]
        # /records first, then /games.
        mock_get.side_effect = [self._resp(records), self._resp(games)]

        rec = _get_team_record_cfbd("Alabama", 2023)
        self.assertEqual(rec["Overall W"], 12)
        self.assertEqual(rec["Overall L"], 2)
        self.assertEqual(rec["Conference W"], 9)
        self.assertEqual(rec["Overall HOME"], "6-1")
        self.assertEqual(rec["Overall AWAY"], "5-0")
        # Derived from the season's games.
        self.assertEqual(rec["Overall PF"], 40)
        self.assertEqual(rec["Overall PA"], 27)
        self.assertEqual(rec["Overall STREAK"], "Lost 1")

    @patch.dict('os.environ', {}, clear=True)
    def test_missing_api_key_returns_none(self):
        self.assertIsNone(_get_team_record_cfbd("Alabama", 2023))

    @patch.dict('os.environ', {'CFBD_API_KEY': 'test-key'})
    @patch('services.team_service.requests.get')
    def test_team_with_no_season_record_returns_none(self, mock_get):
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = []  # CFBD returns [] for a team/year miss
        mock_get.return_value = mock_resp
        self.assertIsNone(_get_team_record_cfbd("Alabama", 1899))


if __name__ == '__main__':
    unittest.main()
