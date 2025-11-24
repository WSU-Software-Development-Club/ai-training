"""
Supabase Client Initialization and Helper Functions
Provides a centralized Supabase client for database operations
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("Warning: Supabase client not installed. Install with: pip install supabase")


class SupabaseClient:
    """Wrapper class for Supabase client operations"""
    
    def __init__(self):
        """Initialize Supabase client from environment variables"""
        self._client: Optional[Client] = None
        
        if not SUPABASE_AVAILABLE:
            return
        
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_KEY')
        
        if supabase_url and supabase_key:
            try:
                self._client = create_client(supabase_url, supabase_key)
            except Exception as e:
                print(f"Error initializing Supabase client: {e}")
                self._client = None
        else:
            print("Warning: SUPABASE_URL or SUPABASE_KEY not set in environment")
    
    @property
    def client(self) -> Optional[Client]:
        """Get the Supabase client instance"""
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """Check if Supabase client is connected"""
        return self._client is not None
    
    def get_predictions(self, 
                       limit: int = 100,
                       season: Optional[int] = None,
                       week: Optional[int] = None,
                       team: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get predictions with optional filters
        
        Args:
            limit: Maximum number of predictions to return
            season: Filter by season year
            week: Filter by week number
            team: Filter by team name (home or away)
        
        Returns:
            List of prediction dictionaries
        """
        if not self.is_connected:
            return []
        
        try:
            query = self._client.table('predictions').select('*')
            
            if season:
                query = query.eq('season', season)
            
            if week:
                query = query.eq('week', week)
            
            if team:
                # Search for team in either home_team or away_team
                query = query.or_(f'home_team.eq.{team},away_team.eq.{team}')
            
            query = query.order('game_date', desc=False).limit(limit)
            
            response = query.execute()
            return response.data if response.data else []
        
        except Exception as e:
            print(f"Error fetching predictions: {e}")
            return []
    
    def get_prediction_by_game_id(self, game_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the most recent prediction for a specific game
        
        Args:
            game_id: Game ID from College Football Data API
        
        Returns:
            Prediction dictionary or None
        """
        if not self.is_connected:
            return None
        
        try:
            response = self._client.table('predictions')\
                .select('*')\
                .eq('game_id', game_id)\
                .order('prediction_made_at', desc=True)\
                .limit(1)\
                .execute()
            
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error fetching prediction for game {game_id}: {e}")
            return None
    
    def get_predictions_by_week(self, season: int, week: int) -> List[Dict[str, Any]]:
        """
        Get all predictions for a specific week
        
        Args:
            season: Season year
            week: Week number
        
        Returns:
            List of prediction dictionaries
        """
        if not self.is_connected:
            return []
        
        try:
            response = self._client.table('predictions')\
                .select('*')\
                .eq('season', season)\
                .eq('week', week)\
                .order('game_date', desc=False)\
                .execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            print(f"Error fetching predictions for week {week}: {e}")
            return []
    
    def get_predictions_by_team(self, team_name: str, season: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all predictions involving a specific team
        
        Args:
            team_name: Team name
            season: Optional season filter
        
        Returns:
            List of prediction dictionaries
        """
        if not self.is_connected:
            return []
        
        try:
            query = self._client.table('predictions')\
                .select('*')\
                .or_(f'home_team.eq.{team_name},away_team.eq.{team_name}')
            
            if season:
                query = query.eq('season', season)
            
            response = query.order('game_date', desc=False).execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            print(f"Error fetching predictions for team {team_name}: {e}")
            return []
    
    def get_latest_predictions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get the most recently created predictions
        
        Args:
            limit: Maximum number of predictions to return
        
        Returns:
            List of prediction dictionaries
        """
        if not self.is_connected:
            return []
        
        try:
            response = self._client.table('predictions')\
                .select('*')\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            print(f"Error fetching latest predictions: {e}")
            return []


# Global Supabase client instance
supabase_client = SupabaseClient()


def get_supabase_client() -> SupabaseClient:
    """
    Get the global Supabase client instance
    
    Returns:
        SupabaseClient instance
    """
    return supabase_client

