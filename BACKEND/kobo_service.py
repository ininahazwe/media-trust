import requests
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

class KoboService:
    def __init__(self):
        self.api_url = os.getenv("KOBO_API_URL", "https://kf.kobotoolbox.org/api/v2")
        self.username = os.getenv("KOBO_USERNAME", "ininahazweyves")
        self.token = os.getenv("KOBO_TOKEN", "")

    def get_auth_headers(self):
        """Retourne les headers pour l'authentification"""
        if self.token:
            return {"Authorization": f"Token {self.token}"}
        return {}

    def get_forms(self) -> List[Dict]:
        """Récupère la liste des formulaires"""
        # Kobo utilise /assets/ au lieu de /forms/
        url = f"{self.api_url}/assets/"
        headers = self.get_auth_headers()

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Kobo retourne les forms dans 'results'
            if isinstance(data, dict) and 'results' in data:
                return data['results']
            return data if isinstance(data, list) else []
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la récupération des formulaires: {e}")
            return []

    def get_form_submissions(self, form_id: int) -> List[Dict]:
        """Récupère les soumissions d'un formulaire"""
        # Endpoint pour les données
        url = f"{self.api_url}/data/{form_id}"
        headers = self.get_auth_headers()

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la récupération des soumissions: {e}")
            return []

    def get_form_details(self, form_id: int) -> Dict:
        """Récupère les détails d'un formulaire"""
        url = f"{self.api_url}/assets/{form_id}/"
        headers = self.get_auth_headers()

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la récupération des détails: {e}")
            return {}

# Instance globale
kobo_service = KoboService()