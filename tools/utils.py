import os
import re
import json
import httpx
import requests
import unicodedata
from datetime import datetime

from .config import BASEURL, BASEURLFRONT


def pprint(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def get_token():
    try:
        email = os.getenv("AGENT_EMAIL", "agent@dabablane.com")
        pwd = os.getenv("AGENT_PASSWORD", "agent")
        response = requests.post(
            f"{BASEURL}/login",
            headers={"Content-Type": "application/json"},
            json={"email": email, "password": pwd},
        )

        if response.status_code == 200:
            return response.json()["data"]["user_token"], None
        else:
            return None, f"Failed to retrieve token {response.text}"
    except Exception as e:
        return None, f"❌ Failed to retrieve token. ({str(e)})"


def get_auth_headers():
    token, error = get_token()
    if not token:
        raise ValueError(error)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


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
    if text is None:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    without_diacritics = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    lowered = without_diacritics.lower().strip()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def list_categories():
    try:
        response = httpx.get(
            url=f"{BASEURLFRONT}/categories",
            params={"include": "subcategories"},
            headers=get_auth_headers(),
        )
        response.raise_for_status()

        return [
            {
                "category_id": cat.get("id"),
                "category_name": cat.get("name"),
                "category_slug": cat.get("slug"),
            }
            for cat in response.json().get("data", [])
        ]

    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error {e.response.status_code}: {e.response.text}")
        return {}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {}
