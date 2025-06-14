import json
from typing import Any, Dict, List, Optional

import requests

from cyber_shield.sentiment_analyzer_script import TWEETS_SAMPLE_FILE


class SocialMediaDataLoader:
    """Class to load social media data from JSON files or API endpoints."""

    @staticmethod
    def from_json(file_path: str, add_index: bool = False) -> List[Dict[str, Any]]:
        """Load social media data from a local JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    @staticmethod
    def from_api(
        api_url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Load social media data from an API endpoint."""
        response = requests.get(api_url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    # Load data from a JSON file
    try:
        social_data = SocialMediaDataLoader.from_json(TWEETS_SAMPLE_FILE)
        print("Data loaded from JSON file:", social_data)
    except FileNotFoundError as e:
        print(f"Error loading JSON file: {e}")

    # Load data from an API endpoint
    try:
        api_data = SocialMediaDataLoader.from_api(
            "https://api.example.com/social",
            params={"limit": 100},
            headers={"Authorization": "Bearer YOUR_API_KEY"},
        )
        print("Data loaded from API:", api_data)
    except requests.RequestException as e:
        print(f"Error loading data from API: {e}")
