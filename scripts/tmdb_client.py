#!/usr/bin/env python3
"""
TMDB API Client for Movie Notifier
Handles all interactions with The Movie Database API
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class TMDBClient:
    """Client for interacting with The Movie Database API"""

    def __init__(self, read_access_token: str, base_url: str = "https://api.themoviedb.org/3"):
        """
        Initialize TMDB client

        Args:
            read_access_token: TMDB read access token
            base_url: TMDB API base URL
        """
        self.read_access_token = read_access_token
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {read_access_token}",
            "Content-Type": "application/json;charset=utf-8"
        })

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make a request to TMDB API

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            JSON response or None if error
        """
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to {endpoint}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
            return None

    def get_person_details(self, person_id: int) -> Optional[Dict]:
        """
        Get details for a specific person (actor/director)

        Args:
            person_id: TMDB person ID

        Returns:
            Person details or None if error
        """
        return self._make_request(f"person/{person_id}")

    def get_person_movie_credits(self, person_id: int) -> Optional[Dict]:
        """
        Get movie credits for a person

        Args:
            person_id: TMDB person ID

        Returns:
            Movie credits or None if error
        """
        return self._make_request(f"person/{person_id}/movie_credits")

    def get_movie_details(self, movie_id: int) -> Optional[Dict]:
        """
        Get details for a specific movie

        Args:
            movie_id: TMDB movie ID

        Returns:
            Movie details or None if error
        """
        return self._make_request(f"movie/{movie_id}")

    def get_now_playing_movies(self, page: int = 1, region: str = "US") -> Optional[Dict]:
        """
        Get movies currently playing in theaters

        Args:
            page: Page number
            region: Region code (ISO 3166-1 alpha-2)

        Returns:
            Now playing movies or None if error
        """
        params = {"page": page, "region": region}
        return self._make_request("movie/now_playing", params)

    def get_upcoming_movies(self, page: int = 1, region: str = "US") -> Optional[Dict]:
        """
        Get upcoming movies

        Args:
            page: Page number
            region: Region code (ISO 3166-1 alpha-2)

        Returns:
            Upcoming movies or None if error
        """
        params = {"page": page, "region": region}
        return self._make_request("movie/upcoming", params)

    def search_person(self, query: str, page: int = 1) -> Optional[Dict]:
        """
        Search for a person by name

        Args:
            query: Search query
            page: Page number

        Returns:
            Search results or None if error
        """
        params = {"query": query, "page": page}
        return self._make_request("search/person", params)

    def discover_movies(self, params: Dict) -> Optional[Dict]:
        """
        Discover movies with various filters

        Args:
            params: Discovery parameters

        Returns:
            Discovered movies or None if error
        """
        return self._make_request("discover/movie", params)

    def get_recent_movies_for_person(self, person_id: int, days_back: int = 30) -> List[Dict]:
        """
        Get recent movies for a person within the specified number of days

        Args:
            person_id: TMDB person ID
            days_back: Number of days to look back

        Returns:
            List of recent movies
        """
        credits = self.get_person_movie_credits(person_id)
        if not credits:
            return []

        recent_movies = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        # Check both cast and crew credits
        for credit_type in ["cast", "crew"]:
            if credit_type in credits:
                for movie in credits[credit_type]:
                    # Check if movie has a release date
                    if movie.get("release_date"):
                        try:
                            release_date = datetime.strptime(
                                movie["release_date"], "%Y-%m-%d")
                            if release_date >= cutoff_date:
                                # Get more details about the movie
                                movie_details = self.get_movie_details(
                                    movie["id"])
                                if movie_details:
                                    movie_details["credit_type"] = credit_type
                                    movie_details["character"] = movie.get(
                                        "character", "")
                                    movie_details["job"] = movie.get("job", "")
                                    recent_movies.append(movie_details)
                        except ValueError:
                            # Skip movies with invalid date format
                            continue

        return recent_movies

    def get_upcoming_movies_for_person(self, person_id: int, days_ahead: int = 30) -> List[Dict]:
        """
        Get upcoming movies for a person within the specified number of days

        Args:
            person_id: TMDB person ID
            days_ahead: Number of days to look ahead

        Returns:
            List of upcoming movies
        """
        credits = self.get_person_movie_credits(person_id)
        if not credits:
            return []

        upcoming_movies = []
        cutoff_date = datetime.now() + timedelta(days=days_ahead)

        # Check both cast and crew credits
        for credit_type in ["cast", "crew"]:
            if credit_type in credits:
                for movie in credits[credit_type]:
                    # Check if movie has a release date
                    if movie.get("release_date"):
                        try:
                            release_date = datetime.strptime(
                                movie["release_date"], "%Y-%m-%d")
                            today = datetime.now()
                            if today <= release_date <= cutoff_date:
                                # Get more details about the movie
                                movie_details = self.get_movie_details(
                                    movie["id"])
                                if movie_details:
                                    movie_details["credit_type"] = credit_type
                                    movie_details["character"] = movie.get(
                                        "character", "")
                                    movie_details["job"] = movie.get("job", "")
                                    upcoming_movies.append(movie_details)
                        except ValueError:
                            # Skip movies with invalid date format
                            continue

        return upcoming_movies


def test_connection():
    """Test TMDB connection when run directly"""
    import sys
    import argparse
    from config_manager import ConfigManager

    parser = argparse.ArgumentParser(description="Test TMDB API connection")
    parser.add_argument("--config", "-c", default="config/config.yaml",
                        help="Path to configuration file")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    config_manager = ConfigManager(args.config)
    if not config_manager.load_config():
        logger.error("Failed to load configuration")
        return

    tmdb_config = config_manager.get_tmdb_config()
    if not tmdb_config or not tmdb_config.read_access_token:
        logger.error("TMDB configuration not found")
        return

    client = TMDBClient(
        read_access_token=tmdb_config.read_access_token,
        base_url=tmdb_config.base_url
    )

    logger.info("Testing TMDB connection...")
    try:
        result = client.get_now_playing_movies(page=1)
        if result:
            logger.info("✓ TMDB API connection successful")
            sys.exit(0)
        else:
            logger.error("✗ TMDB API connection failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"✗ TMDB API connection error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_connection()
