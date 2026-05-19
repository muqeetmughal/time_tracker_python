import requests

from time_tracker.config import load_config


class FrappeAPI:
    def __init__(self, config=None):
        if config is None:
            config = load_config()
        creds = config.get("credentials", {})
        self.base_url = creds.get("siteUrl", "http://localhost:8001")
        self.api_key = creds.get("apiKey", "")
        self.api_secret = creds.get("apiSecret", "")

    def _get_headers(self):
        return {
            'Authorization': f'token {self.api_key}:{self.api_secret}',
            'Content-Type': 'application/json'
        }

    def projects(self):
        url = f"{self.base_url}/api/resource/Project?fields=[\"name\", \"project_name\"]"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])

    def tasks(self, project):
        url = f"{self.base_url}/api/resource/Task?fields=[\"name\", \"subject\"]&filters=[[\"project\", \"=\", \"{project}\"]]"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])

    def activity_types(self):
        url = f"{self.base_url}/api/resource/Activity Type?fields=[\"name\"]"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])
