import httpx
from fuzzywuzzy import fuzz
from langchain.tools import tool
from urllib.parse import urlparse, unquote
from typing import Optional, List, Tuple, Dict, Any

from .config import BASEURLBACK, district_map

from .utils import get_token, normalize_text, _list_categories


# -----------------------
# Helper functions
# -----------------------
def get_token_or_error() -> Tuple[Optional[str], Optional[str]]:
    try:
        token = get_token()
    except Exception as e:
        return None, f"❌ Failed to retrieve token. Please try again later. ({str(e)})"
    if not token:
        return None, "❌ Failed to retrieve token. Please try again later."
    return token, None


def build_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def fetch_blanes_paginated(
    headers: Dict[str, str],
    category_id: Optional[str] = None,
    per_page: int = 100,
    max_pages: Optional[int] = None,
    endpoint: Optional[str] = None,
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    try:
        blanes: List[Dict[str, Any]] = []
        page = 1
        if endpoint is None:
            endpoint = (
                f"{BASEURLBACK}/getBlanesByCategory"
                if category_id
                else f"{BASEURLBACK}/blanes"
            )

        while True:
            params: Dict[str, Any] = {}
            if category_id:
                params.update(
                    {
                        "page": page,
                        "sort_order": "asc",
                        "category_id": category_id,
                        "paginationSize": per_page,
                    }
                )
            else:
                params.update(
                    {
                        "status": "active",
                        "sort_by": "created_at",
                        "sort_order": "desc",
                        "pagination_size": per_page,
                        "page": page,
                    }
                )

            resp = httpx.get(endpoint, headers=headers, params=params)
            resp.raise_for_status()
            payload = resp.json()
            data = payload.get("data", []) if isinstance(payload, dict) else []
            if not data:
                break
            blanes.extend(data)

            meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
            last_page = meta.get("last_page")
            if last_page and page >= last_page:
                break

            if len(data) < per_page:
                break

            page += 1
            if max_pages and page > max_pages:
                break

        return blanes, None
    except httpx.HTTPStatusError as e:
        try:
            text = e.response.text
        except Exception:
            text = str(e)
        return None, f"❌ HTTP Error {e.response.status_code}: {text}"
    except Exception as e:
        return None, f"❌ Error fetching blanes: {str(e)}"


def resolve_category_id(category_name: str) -> Tuple[Optional[str], Optional[str]]:
    if not category_name:
        return None, None
    try:
        categories = _list_categories()
    except Exception as e:
        return None, f"❌ Error fetching categories: {str(e)}"

    if not isinstance(categories, dict):
        # If categories returned as list, normalize to dict {id: name}
        try:
            categories = {str(c.get("id")): c.get("name") for c in categories}
        except Exception:
            return None, "❌ Unexpected categories format."

    name_norm = category_name.lower().strip()
    # exact match first
    for cat_id, cat_name in categories.items():
        if cat_name and cat_name.lower().strip() == name_norm:
            return cat_id, None

    # partial match fallback
    for cat_id, cat_name in categories.items():
        if cat_name and (
            name_norm in cat_name.lower() or cat_name.lower() in name_norm
        ):
            return cat_id, None

    available_categories = list(categories.values())
    return (
        None,
        f"❌ Category '{category_name}' not found. Available categories: {', '.join(available_categories)}",
    )


def extract_name_from_query(q: str) -> str:
    q = (q or "").strip()
    if not q:
        return ""
    try:
        if q.startswith("http://") or q.startswith("https://") or q.startswith("www."):
            parsed = urlparse(q if q.startswith("http") else f"https://{q}")
            last = [seg for seg in parsed.path.split("/") if seg][-1:] or [""]
            candidate = unquote(last[0])
            candidate = candidate.replace("-", " ").replace("_", " ").strip()
            return candidate if candidate else q
    except Exception:
        return q
    return q


def score_blane_against_query(blane: Dict[str, Any], query_norm: str) -> int:
    name = (blane.get("name") or "").lower()
    slug = (blane.get("slug") or "").lower().replace("-", " ").replace("_", " ")
    s1 = fuzz.WRatio(query_norm, name) if name else 0
    s2 = fuzz.partial_ratio(query_norm, name) if name else 0
    s3 = fuzz.WRatio(query_norm, slug) if slug else 0
    s4 = fuzz.partial_ratio(query_norm, slug) if slug else 0
    return max(s1, s2, s3, s4)


def format_blanes_list(
    blanes: List[Dict[str, Any]], start: int, offset: int, filters_summary: str
) -> str:
    total_matches = len(blanes)
    end_pos = min(start + offset - 1, total_matches)
    if start > total_matches:
        return f"❌ Start position {start} exceeds total results ({total_matches}). Try a lower start position."

    paginated = blanes[start - 1 : end_pos]

    output_lines: List[str] = ["Here are some options:"]
    output_lines.append(f"📋 Filtered Results: {filters_summary}")
    output_lines.append(
        f"📊 Showing items {start}-{end_pos} of {total_matches} matches"
    )
    output_lines.append("")

    for idx, blane in enumerate(paginated, start=start):
        name = blane.get("name", "Unknown")
        price = blane.get("price_current")
        blane_id = blane.get("id")
        if price:
            output_lines.append(f"{idx}. {name} — {price} Dhs (blane_id: {blane_id})")
        else:
            output_lines.append(f"{idx}. {name} (blane_id: {blane_id})")

    output_lines.append("")
    if end_pos < total_matches:
        next_start = end_pos + 1
        max_next_end = min(next_start + offset - 1, total_matches)
        output_lines.append(
            f"💡 More results available (Items {next_start}-{max_next_end})"
        )
    else:
        output_lines.append("That's all for these filters.")
        output_lines.append("Want to try different search criteria or see details?")

    return "\n".join(output_lines)


# -----------------------
# Tool implementations
# -----------------------


@tool("list_blanes_by_location_and_category")
def list_blanes_by_location_and_category(
    district: str = "",
    category: str = "",
    city: str = "",
    start: int = 1,
    offset: int = 10,
) -> str:
    """
    Retrieve a paginated list of active blanes filtered by category, and optionally by city and district.

    This tool is used when a user wants to discover blanes (venues/experiences)
    by specifying a category (required) and optionally a city or district.
    It fetches all available blanes from the backend API, filters them locally by district name
    (using known sub-areas of the district for text matching), and returns a formatted list with prices and IDs.

    Args:
        district (str): The district name to filter blanes by (optional).
        category (str): The category of blanes to search (required).
        city (str): The city name to filter blanes by (optional).
        start (int): The starting index of results for pagination (1-based, default 1).
        offset (int): The number of items to return (default 10, max 25).

    Returns:
        str: A human-readable, paginated list of matching blanes including their name, price (if available),
            and blane_id. Returns an error message string if no results are found or if any validation fails.
    """

    # --- Validate pagination inputs ---
    try:
        start = max(1, int(start))
    except Exception:
        start = 1
    try:
        offset = max(1, min(25, int(offset)))
    except Exception:
        offset = 10

    # --- Normalize filters ---
    city_norm = normalize_text(city) if city else ""
    district_norm = normalize_text(district) if district else ""
    category_norm = category.strip() if category else ""

    # --- Ensure category is provided ---
    if not category_norm:
        try:
            categories = _list_categories()
            available_categories = (
                list(categories.values())
                if isinstance(categories, dict)
                else [c.get("name") for c in categories]
            )
            return f"Please provide a category. Available categories: {', '.join(available_categories)}"
        except Exception as e:
            return f"❌ Error fetching categories: {str(e)}"

    # --- Auth ---
    token, token_err = get_token_or_error()
    if token_err:
        return token_err
    headers = build_headers(token)

    # --- Resolve category id ---
    category_id, cat_err = resolve_category_id(category_norm)
    if cat_err:
        return cat_err

    # --- Fetch data ---
    blanes_data, fetch_err = fetch_blanes_paginated(
        headers, category_id=category_id, per_page=100
    )
    if fetch_err:
        return fetch_err
    if not blanes_data:
        return "❌ No blanes found."

    # --- Build sub-areas list from district for text matching ---
    district_subs = []
    if district_norm:
        district_subs = [
            normalize_text(sub) for sub in district_map.get(district_norm, [])
        ]

    # --- Filter blanes ---
    matched: List[Dict[str, Any]] = []
    for blane in blanes_data:
        name = blane.get("name") or ""
        description = blane.get("description") or ""
        blane_city = normalize_text(blane.get("city") or "")
        searchable_text = normalize_text(f"{name} {description}")

        passes_city_filter = not city_norm or (city_norm in blane_city)

        # ✅ Only district-based location filter
        passes_location_filter = True
        location_score = 0
        if district_norm:
            passes_location_filter = False
            for sub in district_subs:
                if sub and sub in searchable_text:
                    passes_location_filter = True
                    location_score = 1
                    break

        if passes_city_filter and passes_location_filter:
            blane["_location_score"] = location_score
            matched.append(blane)

    # --- Sort by score (district matches first) ---
    matched.sort(key=lambda x: x.get("_location_score", 0), reverse=True)

    # --- No matches case ---
    total_matches = len(matched)
    if total_matches == 0:
        filter_description = []
        if city_norm:
            filter_description.append(f"city: {city}")
        if district_norm:
            filter_description.append(f"district: {district}")
        if category_norm:
            filter_description.append(f"category: {category}")

        filters_text = (
            ", ".join(filter_description) if filter_description else "the given filters"
        )
        return f"❌ No blanes found for {filters_text}. Try different search criteria."

    # --- Build output ---
    active_filters = []
    if city_norm:
        active_filters.append(f"City: {city}")
    if district_norm:
        active_filters.append(f"District: {district}")
    if category_norm:
        active_filters.append(f"Category: {category}")
    filter_summary = " | ".join(active_filters) if active_filters else "All locations"

    return format_blanes_list(matched, start, offset, filter_summary)


@tool("find_blanes_by_name_or_link")
def find_blanes_by_name_or_link(
    query: str, limit: int = 10, score_threshold: int = 60
) -> str:
    """
    Find active blanes by their name or from a given link, using fuzzy matching.

    This tool is used when a user already knows the name or has a link to a specific blane.
    It extracts a name from the link if needed, retrieves all active blanes from the backend,
    and applies fuzzy matching on both their names and slugs.
    It then returns the top matches sorted by similarity score.

    Args:
        query (str): The user-provided blane name or link.
        limit (int): Maximum number of top matches to return (default 10).
        score_threshold (int): Minimum fuzzy match score (0-100) required to include a result (default 60).

    Returns:
        str: A ranked list of the closest matching blanes in the format:
             "{idx} - {name} — {price} Dhs (blane_id: {id})".
             Returns an error message string if no matches are found or if input is invalid.
    """

    user_text = extract_name_from_query(query)
    if not user_text:
        return "❌ Please provide a valid blane name or link."

    token, token_err = get_token_or_error()
    if token_err:
        return token_err
    headers = build_headers(token)

    blanes_data, fetch_err = fetch_blanes_paginated(
        headers,
        category_id=None,
        per_page=100,
        endpoint=f"{BASEURLBACK}/getBlanesByCategory",
    )
    if fetch_err:
        return fetch_err
    if not blanes_data:
        return "❌ No blanes found."

    query_norm = user_text.lower()
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for blane in blanes_data:
        score = score_blane_against_query(blane, query_norm)
        if score >= int(score_threshold):
            scored.append((score, blane))

    if not scored:
        return f"❌ No similar blanes found for '{user_text}'."

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [b for _, b in scored[: max(1, int(limit))]]

    lines: List[str] = []
    for idx, blane in enumerate(top, start=1):
        name = blane.get("name", "Unknown")
        price = blane.get("price_current")
        blane_id = blane.get("id")
        if price:
            lines.append(f"{idx} - {name} — {price} Dhs (blane_id: {blane_id})")
        else:
            lines.append(f"{idx} - {name} (blane_id: {blane_id})")

    return "\n".join(lines)
