import httpx
import requests
from datetime import datetime

from .config import BASEURL, BASEURLBACK


def get_token():
    url = f"{BASEURL}/login"
    headers = {"Content-Type": "application/json"}
    payload = {"email": "admin@dabablane.com", "password": "admin"}
    response = requests.post(url, headers=headers, json=payload)
    print(response)
    token = None
    if response.status_code == 200:
        token = response.json()["data"]["user_token"]
        return token
    else:
        return "Try again later."


def format_date(date_str):
    if not date_str:
        return "N/A"
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%d %B %Y")
        except ValueError:
            continue
    return date_str


def format_time(time_str):
    if not time_str:
        return "N/A"
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%H:%M:%S"):
        try:
            return datetime.strptime(time_str, fmt).strftime("%I:%M %p")
        except ValueError:
            continue
    return time_str


def parse_datetime(date_str):
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S", "%H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def parse_time_only(time_str):
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%H:%M:%S"):
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    return None


def normalize_text(text: str) -> str:
    return text.lower().strip()


def _list_categories():
    token = get_token()
    if not token:
        return "❌ Failed to retrieve token. Please try again later."
    url = f"{BASEURLBACK}/categories"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        categories = data.get("data", [])
        result = {cat["id"]: cat["name"] for cat in categories}

        return result

    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error {e.response.status_code}: {e.response.text}")
        return {}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {}
