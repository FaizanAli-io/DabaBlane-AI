import os
import httpx
from enum import Enum
from fuzzywuzzy import fuzz
from functools import lru_cache
from langchain.tools import tool
from urllib.parse import urlparse, unquote

from .config import (
    BASEURLBACK,
    district_map,
)

from .utils import (
    format_date,
    format_time,
    normalize_text,
    list_categories,
    get_auth_headers,
)

language = os.getenv("LANGUAGE", "FRENCH")


class PaginationSentiment(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


@lru_cache(maxsize=1)
def _build_normalized_location_maps():
    """
    Prepare normalized lookup maps from the configured district_map.

    Returns a dict with:
    - districts_norm: { district_norm: { 'label': original, 'subs_norm': [..], 'subs_label': [..] } }
    - sub_to_district_norm: { sub_norm: district_norm }
    """
    districts_norm = {}
    sub_to_district_norm = {}

    for d_label, subs in district_map.items():
        d_norm = normalize_text(d_label)
        subs_label = subs or []
        subs_norm = [normalize_text(s) for s in subs_label]

        districts_norm[d_norm] = {
            "label": d_label,
            "subs_label": subs_label,
            "subs_norm": subs_norm,
        }

        # Map each sub-district back to parent district
        for s_norm in subs_norm:
            sub_to_district_norm[s_norm] = d_norm

        # Some maps include the district name also in its sub list; ensure mapping too
        sub_to_district_norm.setdefault(d_norm, d_norm)

    return {
        "districts_norm": districts_norm,
        "sub_to_district_norm": sub_to_district_norm,
    }


def resolve_location(location: str | None):
    """
    Resolve a user-provided location string to a canonical district and its sub-districts.

    Behavior:
    - If input is a district: return that district and all its sub-districts.
    - If input is a sub-district: find its parent district and return that district with all sub-districts.

    Returns:
    - dict with keys: { 'district', 'district_norm', 'sub_districts', 'sub_districts_norm' }
    - None if cannot resolve
    """
    if not location:
        return None

    loc_norm = normalize_text(location)
    maps = _build_normalized_location_maps()
    districts_norm = maps["districts_norm"]
    sub_to_district_norm = maps["sub_to_district_norm"]

    # Case 1: It's a known district
    if loc_norm in districts_norm:
        entry = districts_norm[loc_norm]
        return {
            "district": entry["label"],
            "district_norm": loc_norm,
            "sub_districts": entry["subs_label"],
            "sub_districts_norm": entry["subs_norm"],
        }

    # Case 2: It's a known sub-district → resolve to its parent
    parent_norm = sub_to_district_norm.get(loc_norm)
    if parent_norm and parent_norm in districts_norm:
        entry = districts_norm[parent_norm]
        return {
            "district": entry["label"],
            "district_norm": parent_norm,
            "sub_districts": entry["subs_label"],
            "sub_districts_norm": entry["subs_norm"],
        }

    # Not resolvable
    return None


def get_all_blanes_simple():
    url = f"{BASEURLBACK}/getBlanesByCategory"
    headers = get_auth_headers()

    all_blanes = []
    current_page = 1

    try:
        while True:
            params = {
                "status": "active",
                "sort_order": "desc",
                "sort_by": "created_at",
                "page": current_page,
                "per_page": 10,
            }

            response = httpx.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            meta = data.get("meta", {})
            page_blanes = data.get("data", [])
            total_blanes = meta.get("total", 0)

            if not page_blanes:
                break

            all_blanes.extend(page_blanes)
            current_page += 1

            if len(all_blanes) >= total_blanes:
                break

            if current_page > 1000:  # Safety limit
                break

    except Exception as e:
        print(f"Error fetching all blanes: {str(e)}")
        return []

    return all_blanes


@tool("introduction_message")
def introduction_message() -> str:
    """
    Provides the introduction message for DabaGPT.
    Use this tool ONLY ONCE when the user greets you.
    """

    return {
        "FRENCH": (
            "Bonjour, je suis *DabaGPT*, l'assistant de réservation des établissements "
            "partenaires DabaBlane.\n\n"
            "Je suis à votre service pour traiter votre demande de réservation, "
            "vérifier les disponibilités et assurer la prise en charge avec l'établissement.\n\n"
            "Pour quel établissement souhaitez-vous réserver ?\n\n"
            "La réservation est également possible via dabablane.com ou l'application."
        ),
        "ENGLISH": (
            "Hello, I'm *DabaGPT*, the reservation assistant for DabaBlane partner establishments.\n\n"
            "I handle reservation requests, check availability, and manage the booking process "
            "with the establishment.\n\n"
            "Which establishment would you like to book?\n\n"
            "Reservations can also be made via dabablane.com or the mobile app."
        ),
    }[language]


@tool("list_blanes")
def list_blanes(start: int = 1, offset: int = 10) -> str:
    """
    Lists all Blanes without any constraints.
    If you have any constraints like category(like restaurant, spa, activity, etc), city, district, sub-district, etc. you can use the tool list_blanes_by_location_and_category to get the blanes.

    Args:
        start: Starting position (default: 1, minimum: 1)
        offset: Number of items to show (default: 10, maximum: 25)

    Returns a readable list with range info.
    """
    start = max(start, 1)
    offset = max(min(offset, 25), 5)

    # Since API uses 1-based pagination with per_page
    api_page = ((start - 1) // 10) + 1
    items_needed = offset

    # We might need multiple API pages if offset spans across pages
    url = f"{BASEURLBACK}/blanes"
    headers = get_auth_headers()

    all_fetched_blanes = []
    total_blanes = 0

    try:
        # Fetch enough pages to get our desired range
        current_api_page = api_page
        items_collected = 0

        while items_collected < items_needed:
            params = {
                "status": "active",
                "sort_by": "created_at",
                "sort_order": "desc",
                "per_page": 10,
                "page": current_api_page,
            }

            response = httpx.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            page_blanes = data.get("data", [])
            meta = data.get("meta", {})
            total_blanes = meta.get("total", 0)

            if start + offset > total_blanes:
                offset = total_blanes - start + 1

            if not page_blanes:
                break

            all_fetched_blanes.extend(page_blanes)
            items_collected += len(page_blanes)
            current_api_page += 1

            # Stop if we've reached the end of available data
            if len(all_fetched_blanes) >= total_blanes:
                break

        # Calculate the actual start position in our fetched data
        start_in_fetched = (
            (start - 1) % 10 if api_page == ((start - 1) // 10) + 1 else 0
        )

        # Get the exact slice we need
        if start > total_blanes:
            return f"❌ Start position {start} is beyond available blanes. Total blanes: {total_blanes}"

        # Adjust for the actual position in the complete dataset
        actual_start_index = start - ((api_page - 1) * 10) - 1
        if actual_start_index < 0:
            actual_start_index = 0

        end_index = min(actual_start_index + offset, len(all_fetched_blanes))
        selected_blanes = all_fetched_blanes[actual_start_index:end_index]

        if not selected_blanes:
            return f"❌ No blanes found in range {start} to {start + offset - 1}"

    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"❌ Error fetching blanes: {str(e)}"

    # Build output
    output = ["Here are some options:"]

    # Calculate actual end position
    actual_end = min(start + len(selected_blanes) - 1, total_blanes)

    # Add header with range info
    output.append(
        f"📋 Blanes List (Items {start}-{actual_end} of {total_blanes} total)"
    )
    output.append("")

    # Add blanes with their actual position numbers (title + price if available)
    for i, blane in enumerate(selected_blanes, start=start):
        name = blane.get("name", "Unknown")
        price = blane.get("price_current")
        id = blane.get("id")
        if price:
            output.append(f"{i}. {name} — {price} Dhs (blane_id: {id})")
        else:
            output.append(f"{i}. {name} (blane_id: {id})")
        # output.append(f"{i}. {blane['name']} — MAD. {blane['price_current']} (ID: {blane['id']}) - BlaneType: {blane['type']} - TimeType: {blane['type_time']}")

    # Add navigation hints
    output.append("")
    if actual_end < total_blanes:
        next_start = actual_end + 1
        output.append(
            f"💡 Voulez-vous voir les suivants? (Items {next_start}-{min(next_start + offset - 1, total_blanes)})"
        )
        # output.append(f"\nWant more?\nButtons: [Show 10 more] [See details]")
    else:
        output.append(
            "\nThat's all in this district. Want me to suggest blanes in another district?"
        )
    return "\n".join(output)


@tool("handle_user_pagination_response")
def handle_user_pagination_response(
    user_sentiment: PaginationSentiment,
    current_start: int,
    current_offset: int,
    total_blanes: int,
) -> str:
    """
    Handle user response for pagination navigation.

    Args:
        user_sentiment: PaginationSentiment.POSITIVE or PaginationSentiment.NEGATIVE
        current_start: Current start position from session
        current_offset: Current offset from session
        total_blanes: Total number of blanes

    Returns:
        Next set of blanes if positive, or appropriate message if negative
    """
    if user_sentiment == PaginationSentiment.POSITIVE:
        # Calculate next start position
        next_start = current_start + current_offset

        if next_start <= total_blanes:
            # Update session with new start position
            return list_blanes(next_start, current_offset)
        else:
            return "❌ Vous êtes déjà à la fin de la liste. (You're already at the end of the list.)"

    elif user_sentiment == PaginationSentiment.NEGATIVE:
        return "👍 D'accord! Y a-t-il autre chose que je puisse vous aider? (Alright! Is there anything else I can help you with?)"

    else:
        return "❓ Je n'ai pas compris votre réponse. Dites 'oui' pour voir plus ou 'non' pour arrêter. (I didn't understand your response. Say 'yes' to see more or 'no' to stop.)"


@tool("get_blane_info")
def get_blane_info(blane_id: int):
    """
    Gives details of any blane using its ID.
    Returns a detailed, user-friendly WhatsApp message about a specific blane.
    """
    url = f"{BASEURLBACK}/blanes/{blane_id}"
    headers = get_auth_headers()

    try:
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        blane = response.json().get("data", [])

        msg = f"📋 *Blane Details*\n\n"
        msg += f"🏷 *ID:* {blane.get('id')}\n"
        msg += f"🏷 *Name:* {blane.get('name')}\n"
        msg += f"🏙 *City:* {blane.get('city')}\n"
        msg += f"🏪 *Vendor:* {blane.get('commerce_name', 'N/A')}\n"

        msg += f"\n💬 *Description:*\n{blane.get('description')}\n"
        msg += f"\n💰 *Price:* {blane.get('price_current')} MAD"
        if blane.get("price_old"):
            msg += f"\n~~Old Price: {blane.get('price_old')} MAD~~"

        # General Type
        main_type = blane.get("type")
        msg += f"\n\n📍 *Type:* {main_type.capitalize()}"

        # Sub Type
        if main_type == "reservation":
            subtype = (
                "Hour-Based" if blane.get("type_time") == "time" else "Daily-Based"
            )
            msg += f"\n📆 *Reservation Type:* {subtype}"
        elif main_type == "order":
            product_type = (
                "Digital Product" if blane.get("is_digital") else "Physical Product"
            )
            msg += f"\n🛍 *Product Type:* {product_type}"

        # Time Slot Info
        if blane.get("type_time") == "time":
            msg += f"\n🕒 *Slot Duration:* {blane.get('intervale_reservation')} minutes"
            msg += f"\n🕓 *Opens:* {format_time(blane.get('heure_debut'))}"
            msg += f"\n🕔 *Closes:* {format_time(blane.get('heure_fin'))}"

        # Reservation Info
        if main_type == "reservation":
            msg += f"\n📅 *Available From:* {format_date(blane.get('start_date'))}"
            msg += f"\n📅 *Expires On:* {format_date(blane.get('expiration_date'))}"
            jours = blane.get("jours_creneaux")
            if isinstance(jours, list) and jours:
                msg += f"\n📆 *Days Open:* {', '.join(jours)}"

            msg += f"\n👥 *Max Per Slot:* {blane.get('max_reservation_par_creneau')}"
            msg += f"\n👤 *Persons per Deal:* {blane.get('nombre_personnes')}"
            msg += (
                f"\n🔢 *Total Reservation Limit:* {blane.get('nombre_max_reservation')}"
            )

        # Order Info
        elif main_type == "order":
            msg += f"\n📦 *Stock Available:* {blane.get('stock')}"
            msg += f"\n🛒 *Max Orders per Transaction:* {blane.get('max_orders')}"
            if not blane.get("is_digital"):
                if blane.get("livraison_in_city"):
                    msg += f"\n🚚 *Delivery (Same City):* {blane.get('livraison_in_city')} MAD"
                if blane.get("livraison_out_city"):
                    msg += f"\n🚛 *Delivery (Other City):* {blane.get('livraison_out_city')} MAD"

        # Payment Info
        msg += f"\n\n💳 *Payment Options:*"
        msg += f"\n- 💵 Cash: {'✅' if blane.get('cash') else '❌'}"
        msg += f"\n- 💳 Online Full: {'✅' if blane.get('online') else '❌'}"
        partiel = blane.get("partiel")
        partiel_percent = blane.get("partiel_field")
        msg += f"\n- 💳 Online Partial: {'✅' if partiel else '❌'}"
        if partiel and partiel_percent:
            msg += f" ({partiel_percent}%)"

        # Optional
        if blane.get("advantages"):
            msg += f"\n\n🎁 *Advantages:* {blane['advantages']}"
        if blane.get("conditions"):
            msg += f"\n📌 *Conditions:* {blane['conditions']}"
        if blane.get("rating") is not None:
            msg += f"\n⭐ *Rating:* {float(blane['rating']):.1f}"

        msg += "\n\nDo you want me to book this for you, or see other blanes?\nButtons: [Book this] [See others]"
        return msg

    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"


@tool("find_blanes_by_name_or_link")
def find_blanes_by_name_or_link(
    query: str, limit: int = 10, score_threshold: int = 60
) -> str:
    """
    Find blanes when the user provides a blane name or a link.
    - If a link is provided, extracts the last path segment as the blane name (decodes hyphens and %20).
    - Uses fuzzy matching to search across all active blanes by name/slug.
    - Returns matches formatted as: "{idx} - {name} — {price} Dhs (blane_id: {id})".

    Args:
        query: Blane name or link.
        limit: Maximum number of results to return (default 10).
        score_threshold: Minimum fuzzy match score to include (default 60).
    """

    # Normalize user query (handle link vs. plain name)
    def _extract_name_from_query(q: str) -> str:
        q = (q or "").strip()
        try:
            if (
                q.startswith("http://")
                or q.startswith("https://")
                or q.startswith("www.")
            ):
                parsed = urlparse(q if q.startswith("http") else f"https://{q}")
                last = [seg for seg in parsed.path.split("/") if seg][-1:] or [""]
                candidate = unquote(last[0]).replace("-", " ").replace("_", " ").strip()
                return candidate if candidate else q
            return q
        except Exception:
            return q

    user_text = _extract_name_from_query(query)
    if not user_text:
        return "❌ Please provide a valid blane name or link."

    headers = get_auth_headers()

    # Fetch all active blanes with pagination
    collected = []
    page = 1
    try:
        while True:
            params = {
                "status": "active",
                "sort_by": "created_at",
                "sort_order": "desc",
                "per_page": 500,
                "page": page,
            }
            resp = httpx.get(
                f"{BASEURLBACK}/getBlanesByCategory", headers=headers, params=params
            )
            resp.raise_for_status()
            payload = resp.json()
            data = payload.get("data", [])
            meta = payload.get("meta", {})
            if not data:
                break
            collected.extend(data)
            total = meta.get("total")
            last_page = meta.get("last_page")
            if last_page and page >= last_page:
                break
            if total and len(collected) >= int(total):
                break
            page += 1
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"❌ Error fetching blanes: {str(e)}"

    if not collected:
        return "❌ No blanes found."

    # Fuzzy score per blane (compare against name and slug)
    query_norm = user_text.lower()
    scored = []
    for blane in collected:
        name = (blane.get("name") or "").lower()
        slug = (blane.get("slug") or "").lower().replace("-", " ").replace("_", " ")
        s1 = fuzz.WRatio(query_norm, name) if name else 0
        s2 = fuzz.partial_ratio(query_norm, name) if name else 0
        s3 = fuzz.WRatio(query_norm, slug) if slug else 0
        s4 = fuzz.partial_ratio(query_norm, slug) if slug else 0
        score = max(s1, s2, s3, s4)
        if score >= score_threshold:
            scored.append((score, blane))

    if not scored:
        return f"❌ No similar blanes found for '{user_text}'."

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [b for _, b in scored[: max(1, int(limit))]]

    lines = []
    for idx, blane in enumerate(top, start=1):
        name = blane.get("name", "Unknown")
        price = blane.get("price_current")
        blane_id = blane.get("id")
        if price:
            lines.append(f"{idx} - {name} — {price} Dhs (blane_id: {blane_id})")
        else:
            lines.append(f"{idx} - {name} (blane_id: {blane_id})")

    return "\n".join(lines)


@tool("list_blanes_by_district_and_category")
def list_blanes_by_district_and_category(
    category_id: int,
    city: str = None,
    district: str = None,
) -> str:
    """
    List blanes by district (or sub-district) and category with simple text-based filtering.

    Args:
        category_id: Category ID to filter by (required).
        city: Optional city name to apply as a substring filter on blane city.
        district: District or sub-district to search within. If empty, location filtering is skipped.

    Returns:
        A formatted string of matching blanes (with name, price when available,
        and blane_id), including a filter summary. Returns a readable error message
        if token retrieval fails, HTTP requests fail, or no blanes match the filters.
    """
    city_norm = normalize_text(city)
    resolved = resolve_location(district) if district else None

    try:
        page = 1
        data = []

        while True:
            params = {
                "page": page,
                "sort_order": "asc",
                "paginationSize": 100,
                "category_id": category_id,
            }

            resp = httpx.get(
                f"{BASEURLBACK}/getBlanesByCategory",
                headers=get_auth_headers(),
                params=params,
            )

            resp.raise_for_status()
            batch = resp.json().get("data", [])
            if not batch:
                break

            data.extend(batch)
            if len(batch) < 100:
                break

            page += 1
    except Exception as e:
        return f"❌ Error fetching blanes: {str(e)}"

    # Build matchers from resolved location
    district_label = None
    sub_norms = []
    if resolved:
        district_label = resolved["district"]
        district_norm = resolved.get("district_norm")
        sub_norms = resolved.get("sub_districts_norm") or []
    else:
        district_norm = ""

    # Filter by city + location mentions
    matched = []
    for blane in data:
        name = blane.get("name") or ""
        description = blane.get("description") or ""
        blane_city = normalize_text(blane.get("city") or "")

        # City filter (substring match)
        if city_norm and city_norm not in blane_city:
            continue

        # Location filter
        passes_loc = True if not resolved else False
        if resolved:
            text = normalize_text(f"{name} {description}")
            terms = set(sub_norms)
            if district_norm:
                terms.add(district_norm)
            if any(term and term in text for term in terms):
                passes_loc = True
                blane["_location_score"] = 1
            else:
                blane["_location_score"] = 0
        else:
            blane["_location_score"] = 0

        if passes_loc:
            matched.append(blane)

    if not matched:
        pieces = []
        if city:
            pieces.append(f"city: {city}")
        if district:
            pieces.append(f"district: {district}")
        pieces.append(f"category_id: {category_id}")
        return f"❌ No blanes found for {', '.join(pieces)}. Try different search criteria."

    matched.sort(key=lambda x: x.get("_location_score", 0), reverse=True)

    # Build output
    lines = ["Here are some options:"]
    filters = []
    if city:
        filters.append(f"City: {city}")
    if district_label or district:
        filters.append(f"District: {district_label or district}")
    filters.append(f"Category ID: {category_id}")
    lines.append(f"📋 Filtered Results: {' | '.join(filters)}")
    lines.append(f"📊 Showing {len(matched)} matches")
    lines.append("")

    for idx, blane in enumerate(matched, start=1):
        name = blane.get("name", "Unknown")
        price = blane.get("price_current")
        bid = blane.get("id")
        if price:
            lines.append(f"{idx}. {name} — {price} Dhs (blane_id: {bid})")
        else:
            lines.append(f"{idx}. {name} (blane_id: {bid})")

    lines.append("")
    lines.append("That's all for these filters.")
    lines.append("Want to try different search criteria or see details?")

    return "\n".join(lines)
