import httpx
from enum import Enum
from fuzzywuzzy import fuzz
from langchain.tools import tool
from urllib.parse import urlparse, unquote

from .config import (
    BASEURLBACK,
    district_map,
    blane_keywords,
    location_keywords,
    greeting_keywords,
    irrelevant_keywords,
)

from .utils import (
    get_token,
    format_date,
    format_time,
    normalize_text,
    _list_categories,
)


class PaginationSentiment(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


def get_all_blanes_simple():
    token = get_token()
    if not token:
        return []

    url = f"{BASEURLBACK}/getBlanesByCategory"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

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


@tool("list_categories")
def list_categories() -> str:
    "List all categories from the API"
    return _list_categories()


@tool("introduction_message", return_direct=True)
def introduction_message() -> str:
    """
    Returns the introduction message for DabaGPT booking assistant.

    Use this tool when:
    - User sends greeting messages like "hello", "hi", "salam", "assalam o alaikum"
    - User asks "what can you do" or "help me"
    - User starts a new conversation
    - User asks about the bot's capabilities or services
    - User sends any initial greeting or inquiry about services

    The tool provides a comprehensive introduction explaining:
    - Bot identity as DabaGPT booking assistant
    - Available services (finding blanes, checking availability, making reservations)
    - Required information needed from users (category, city, district, sub-district, date)
    - Friendly greeting response in local language (French/Roman)

    Also when user says "Salam" in any form - respond with "Walikum Assalam" instead of Hello.
    """

    categories = ", ".join(_list_categories().values())

    return f"""Bonjour! Je suis *DabaGPT*, votre assistant de réservation intelligent. 🤖✨

    Je peux vous aider à :
    ‣   🔍 Trouver des *blanes* (par catégorie ou localisation)
    ‣   📅 Vérifier la disponibilité
    ‣   🛎️ Réserver un blane pour vous
    ‣   💸 Vous guider dans le processus de paiement et de réservation

    Pour vous montrer les meilleures options, j'aurai besoin de quelques détails :
       ‣ *Catégorie* (par ex: {categories})
       ‣ *Quartier* (Si tu veux)
       ‣ *Ville*

    Donnez-moi ces informations et je m'occupe du reste. 🚀"""


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
    # Validate parameters

    if start < 1:
        start = 1
    if offset < 1:
        offset = 10
    if offset > 25:
        offset = 25

    token = get_token()
    if not token:
        return "❌ Failed to retrieve token. Please try again later."

    # Calculate which API page we need and how many items to fetch
    # Since API uses 1-based pagination with per_page
    api_page = ((start - 1) // 10) + 1  # Which API page contains our start position
    items_needed = offset

    # We might need multiple API pages if offset spans across pages
    url = f"{BASEURLBACK}/blanes"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

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
            return blanes_list(next_start, current_offset)
        else:
            return "❌ Vous êtes déjà à la fin de la liste. (You're already at the end of the list.)"

    elif user_sentiment == PaginationSentiment.NEGATIVE:
        return "👍 D'accord! Y a-t-il autre chose que je puisse vous aider? (Alright! Is there anything else I can help you with?)"

    else:
        return "❓ Je n'ai pas compris votre réponse. Dites 'oui' pour voir plus ou 'non' pour arrêter. (I didn't understand your response. Say 'yes' to see more or 'no' to stop.)"


@tool("blanes_info")
def get_blane_info(blane_id: int):
    """
    Gives details of any blane using its ID.
    Returns a detailed, user-friendly WhatsApp message about a specific blane.
    """
    token = get_token()
    if not token:
        return "❌ Failed to retrieve token. Please try again later."

    url = f"{BASEURLBACK}/blanes/{blane_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        blane = response.json().get("data", [])
        print(blane)

        msg = f"📋 *Blane Details*\n\n"
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


@tool("check_message_relevance")
def check_message_relevance(user_message: str) -> str:
    """
    MANDATORY FIRST TOOL: Check if user message is relevant to blanes/dabablane business.
    This tool MUST be called before any other tool for every user interaction.
    For greeting messages like hi, hey, hello, bonjour, call `introduction_message` instead.

    Args:
        user_message: User's input message

    Returns:
        "relevant" if message is about blanes/booking/reservations
        "greeting" if it's a greeting message
        "irrelevant" with redirect message if not related to blanes
    """

    if not user_message or not user_message.strip():
        return (
            "irrelevant: Please provide a valid message about blanes or reservations."
        )

    message_lower = user_message.lower().strip()

    # Calculate relevance scores
    blane_score = sum(1 for keyword in blane_keywords if keyword in message_lower)
    location_score = sum(1 for keyword in location_keywords if keyword in message_lower)
    greeting_score = sum(1 for keyword in greeting_keywords if keyword in message_lower)
    irrelevant_score = sum(
        1 for keyword in irrelevant_keywords if keyword in message_lower
    )

    # Determine category and relevance
    total_positive = blane_score + location_score + greeting_score

    if irrelevant_score > 0 and total_positive == 0:
        return "irrelevant: I'm DabaGPT, specialized in helping with blane reservations, bookings, and finding activities, restaurants, and spa services in Casablanca. How can I help you with that?"

    if greeting_score > 0:
        return "greeting"

    if blane_score > 0 or location_score > 0 or total_positive > 0:
        return "relevant"

    # Try to find any possible connection to blanes
    possible_blane_connection = any(
        [
            "suggest" in message_lower,
            "looking for" in message_lower,
            "want" in message_lower,
            "help" in message_lower,
            "show me" in message_lower,
            "find" in message_lower,
            "search" in message_lower,
        ]
    )

    if possible_blane_connection:
        return "relevant"

    # Default to irrelevant
    return "irrelevant: I'm DabaGPT, specialized in blane reservations and bookings. I can help you find restaurants, spas, activities, and more in Casablanca. What interests you?"


@tool("list_districts_and_subdistricts")
def list_districts_and_subdistricts() -> str:
    """Lists all districts and sub districts."""
    return district_map


@tool("list_blanes_by_location_and_category")
def list_blanes_by_location_and_category(
    district: str = "",
    sub_district: str = "",
    category: str = "",
    city: str = "",
    start: int = 1,
    offset: int = 10,
) -> str:
    """
    Retrieve blanes by location and/or category with improved filtering logic.

    Args:
        district: District name
        sub_district: Sub-district name
        category: Category name (restaurant, spa, activity, etc.)
        city: City name
        start: Starting position (default: 1)
        offset: Number of items to show (default: 10, max: 25)
    """
    # Validate and normalize parameters
    start = max(1, int(start))
    offset = max(1, min(25, int(offset)))

    token = get_token()
    if not token:
        return "❌ Failed to retrieve token. Please try again later."

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Normalize input filters
    city_norm = normalize_text(city)
    district_norm = normalize_text(district)
    sub_district_norm = normalize_text(sub_district)
    category_norm = ""
    if category:
        category_norm = normalize_text(category)
    else:
        categories = _list_categories()
        available_categories = list(categories.values())
        return f"Please provide a category. Available categories: {', '.join(available_categories)}"

    # Get category ID if category is specified
    category_id = None
    if category_norm:
        try:
            categories = _list_categories()
            if isinstance(categories, dict):
                # Find category ID by matching category name (case-insensitive)
                for cat_id, cat_name in categories.items():
                    if cat_name.lower().strip() == category_norm:
                        category_id = cat_id
                        break

                # If exact match not found, try partial matching
                if not category_id:
                    for cat_id, cat_name in categories.items():
                        if (
                            category_norm in cat_name.lower()
                            or cat_name.lower() in category_norm
                        ):
                            category_id = cat_id
                            break

                if not category_id:
                    available_categories = list(categories.values())
                    return f"❌ Category '{category}' not found. Available categories: {', '.join(available_categories)}"
        except Exception as e:
            return f"❌ Error fetching categories: {str(e)}"

    try:
        all_blanes = []

        # Use category-specific endpoint if category is specified
        if category_id:
            # Calculate pagination for API call
            api_page = ((start - 1) // 100) + 1

            params = {
                "page": api_page,
                "sort_order": "asc",
                "category_id": category_id,
                "paginationSize": 100,
            }

            response = httpx.get(
                f"{BASEURLBACK}/getBlanesByCategory", headers=headers, params=params
            )
            response.raise_for_status()
            category_blanes = response.json().get("data", [])

            # If we need more results, fetch additional pages
            total_needed = start + offset - 1
            current_page = api_page
            while len(category_blanes) < total_needed:
                current_page += 1
                params["page"] = current_page
                response = httpx.get(
                    f"{BASEURLBACK}/getBlanesByCategory", headers=headers, params=params
                )
                response.raise_for_status()
                next_batch = response.json().get("data", [])
                if not next_batch:  # No more results
                    break
                category_blanes.extend(next_batch)

            all_blanes = category_blanes
        else:
            # Use general endpoint for non-category searches
            params = {
                "status": "active",
                "sort_by": "created_at",
                "sort_order": "desc",
                "pagination_size": 500,
            }
            response = httpx.get(
                f"{BASEURLBACK}/blanes", headers=headers, params=params
            )
            response.raise_for_status()
            all_blanes = response.json().get("data", [])

    except Exception as e:
        return f"❌ Error fetching blanes: {str(e)}"

    # Debug output (remove in production)
    for blane in all_blanes[:5]:  # Just show first 5 for debugging
        print(f"Debug - Blane ID: {blane.get('id')}")

    # Get all sub-districts for the specified district
    district_subs = []
    if district_norm:
        district_subs = [
            normalize_text(sub) for sub in district_map.get(district_norm, [])
        ]

    # Filter blanes based on location criteria (category already filtered by API)
    matched_blanes = []

    for blane in all_blanes:
        name = blane.get("name") or ""
        description = blane.get("description") or ""
        blane_city = normalize_text(blane.get("city") or "")

        # Create searchable text
        searchable_text = normalize_text(f"{name} {description}")

        # Apply city filter
        passes_city_filter = not city_norm or city_norm in blane_city

        # Apply location filter (district/sub-district)
        passes_location_filter = True
        location_score = 0

        if sub_district_norm or district_norm:
            passes_location_filter = False

            # Check for sub-district match (highest priority)
            if sub_district_norm and sub_district_norm in searchable_text:
                passes_location_filter = True
                location_score = 3
            # Check for other sub-districts in the same district (medium priority)
            elif district_norm:
                for sub in district_subs:
                    if sub and sub in searchable_text:
                        passes_location_filter = True
                        location_score = 2 if sub == sub_district_norm else 1
                        break

        # Include blanes that pass all remaining filters
        if passes_city_filter and passes_location_filter:
            blane["_location_score"] = location_score
            matched_blanes.append(blane)

    # Sort by location score (prioritize exact sub-district matches)
    matched_blanes.sort(key=lambda x: x.get("_location_score", 0), reverse=True)

    total_matches = len(matched_blanes)

    if total_matches == 0:
        filter_description = []
        if city_norm:
            filter_description.append(f"city: {city}")
        if district_norm:
            filter_description.append(f"district: {district}")
        if sub_district_norm:
            filter_description.append(f"sub-district: {sub_district}")
        if category_norm:
            filter_description.append(f"category: {category}")

        filters_text = (
            ", ".join(filter_description) if filter_description else "the given filters"
        )
        return f"❌ No blanes found for {filters_text}. Try different search criteria."

    # Apply pagination
    end_pos = min(start + offset - 1, total_matches)
    if start > total_matches:
        return f"❌ Start position {start} exceeds total results ({total_matches}). Try a lower start position."

    paginated_blanes = matched_blanes[start - 1 : end_pos]

    # Build output
    output_lines = ["Here are some options:"]

    # Add filter summary
    active_filters = []
    if city_norm:
        active_filters.append(f"City: {city}")
    if district_norm:
        active_filters.append(f"District: {district}")
    if sub_district_norm:
        active_filters.append(f"Sub-district: {sub_district}")
    if category_norm:
        active_filters.append(f"Category: {category}")

    filter_summary = " | ".join(active_filters) if active_filters else "All locations"
    output_lines.append(f"📋 Filtered Results: {filter_summary}")
    output_lines.append(
        f"📊 Showing items {start}-{end_pos} of {total_matches} matches"
    )
    output_lines.append("")

    # Add blanes
    for idx, blane in enumerate(paginated_blanes, start=start):
        name = blane.get("name", "Unknown")
        price = blane.get("price_current")
        blane_id = blane.get("id")

        if price:
            output_lines.append(f"{idx}. {name} — {price} Dhs (blane_id: {blane_id})")
        else:
            output_lines.append(f"{idx}. {name} (blane_id: {blane_id})")

    # Add pagination info
    output_lines.append("")
    if end_pos < total_matches:
        next_start = end_pos + 1
        max_next_end = min(next_start + offset - 1, total_matches)
        output_lines.append(
            f"💡 More results available (Items {next_start}-{max_next_end})"
        )
        # output_lines.append("Buttons: [Show more] [See details] [Change filters]")
    else:
        output_lines.append("That's all for these filters.")
        output_lines.append("Want to try different search criteria or see details?")

    return "\n".join(output_lines)


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
                candidate = unquote(last[0])
                # Convert common slug separators to spaces
                candidate = candidate.replace("-", " ").replace("_", " ").strip()
                return candidate if candidate else q
            return q
        except Exception:
            return q

    user_text = _extract_name_from_query(query)
    if not user_text:
        return "❌ Please provide a valid blane name or link."

    token = get_token()
    if not token:
        return "❌ Failed to retrieve token. Please try again later."

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Fetch all active blanes with pagination
    collected = []
    page = 1
    try:
        while True:
            params = {
                "status": "active",
                "sort_by": "created_at",
                "sort_order": "desc",
                "per_page": 100,
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


# Not in use
@tool("search_blanes_advanced")
def search_blanes_advanced(
    session_id: str, keywords: str, min_relevance: float = 0.9
) -> str:
    """
    An AI-powered semantic search tool that finds relevant "blanes" (services/providers) based on user keywords and intent, with configurable relevance scoring.
    When to Use This Tool
    Call this tool when users ask queries similar to:
    Service Discovery Queries

    "Show me blanes related to photoshoot" (keyword: photoshoot)
    "I need photographers for my wedding" (keyword: wedding photography)
    "Find me spa services" (keyword: spa)
    "Looking for catering options" (keyword: catering)

    Business/Project Needs

    "I want to create a website, suggest me something?" (keyword: website creation)
    "Help me find marketing services" (keyword: marketing)
    "I need event planning assistance" (keyword: event planning)
    "Looking for graphic design services" (keyword: graphic design)

    General Service Exploration

    "What blanes do you have for restaurants?" (keyword: restaurants)
    "Show me fitness-related services" (keyword: fitness)
    "Find me beauty and wellness providers" (keyword: beauty wellness)
    "I need home improvement services" (keyword: home improvement)

    Key Features

    AI-Powered Matching: Uses gpt-4o for semantic understanding
    Relevance Scoring: Configurable minimum relevance threshold (0.0-1.0)
    Multi-Criteria Analysis: Considers direct matches, semantic similarity, and contextual relevance
    Detailed Explanations: Provides reasoning for each match

    Input Parameters

    session_id: Unique identifier for the search session
    keywords: The search terms or user intent (extracted from user query)
    min_relevance: Optional threshold (default 0.5) - higher values return fewer, more precise results

    Scoring System

    0.9-1.0: Perfect match, exactly what user wants
    0.7-0.8: Very relevant, strong semantic connection
    0.5-0.6: Moderately relevant, related services
    0.3-0.4: Weakly related, might be useful
    Below 0.3: Not relevant (filtered out)
    """
    from langchain_openai import ChatOpenAI
    import json

    if not 0.0 <= min_relevance <= 1.0:
        min_relevance = 0.5

    # Get all blanes
    all_blanes_data = get_all_blanes_simple()
    if not all_blanes_data:
        return "❌ Failed to retrieve blanes data"

    # Prepare data for AI analysis
    blanes_info = []
    for blane in all_blanes_data:
        blane_entry = {
            "id": blane.get("id", "Unknown"),
            "title": blane.get("name", "Unknown"),
            "description": blane.get("description", ""),
            "category": blane.get("category", ""),
            "type": blane.get("type", ""),
        }
        blanes_info.append(blane_entry)

    try:
        # Initialize OpenAI model (same as BookingToolAgent)
        llm = ChatOpenAI(model="gpt-4o", temperature=0)

        # Create advanced AI prompt
        ai_prompt = f"""You are an expert at semantic matching of services with user search intent.

                        TASK: Find blanes highly relevant to: "{keywords}" with minimum relevance of {min_relevance}

                        BLANES DATA:
                        {json.dumps(blanes_info, indent=2)}

                        ANALYSIS CRITERIA:
                        1. Direct keyword matches in title/description (high score)
                        2. Semantic similarity and related concepts (medium score)
                        3. Contextual relevance (e.g., wedding → photography, catering)
                        4. Industry connections and complementary services

                        SCORING GUIDE:
                        - 0.9-1.0: Perfect match, exactly what user wants
                        - 0.7-0.8: Very relevant, strong semantic connection
                        - 0.5-0.6: Moderately relevant, related services
                        - 0.3-0.4: Weakly related, might be useful
                        - Below 0.3: Not relevant

                        Return ONLY JSON array with scores >= {min_relevance}:
                        [
                            {{"id": "blane_id", "title": "blane_title", "relevance_score": 0.85, "reason": "detailed explanation"}}
                        ]

                        If no matches meet the threshold, return []"""

        # Get AI response
        response = llm.invoke(ai_prompt)
        ai_content = response.content.strip()

        # Parse JSON response
        try:
            if ai_content.startswith("```json"):
                ai_content = (
                    ai_content.replace("```json", "").replace("```", "").strip()
                )
            elif ai_content.startswith("```"):
                ai_content = ai_content.replace("```", "").strip()

            relevant_blanes = json.loads(ai_content)

            if not isinstance(relevant_blanes, list):
                raise ValueError("AI response is not a list")

        except (json.JSONDecodeError, ValueError) as e:
            # Fallback to rule-based matching
            print(f"AI parsing failed: {e}, using fallback")
            # relevant_blanes = analyze_blanes_with_ai("", keywords, blanes_info)
            # relevant_blanes = [b for b in relevant_blanes if b.get('relevance_score', 0) >= min_relevance]

        if not relevant_blanes:
            return f"❌ No blanes found with relevance >= {min_relevance} for keywords: '{keywords}'"

        # Format output
        output = [f"🎯 Advanced Search Results (Session: {session_id})"]
        output.append(f"Keywords: '{keywords}' | Min Relevance: {min_relevance}")
        output.append(f"Found {len(relevant_blanes)} highly relevant blanes:")
        output.append("")

        for i, blane in enumerate(relevant_blanes, 1):
            score = blane.get("relevance_score", 0)
            reason = blane.get("reason", "Meets relevance criteria")

            score_emoji = (
                "🎯"
                if score >= 0.9
                else "🔥" if score >= 0.8 else "✨" if score >= 0.7 else "💫"
            )

            output.append(f"{i}. {score_emoji} {blane['title']} (ID: {blane['id']})")
            # output.append(f"   📊 Score: {score:.2f}/1.0")
            output.append(f"   💡 {reason}")
            output.append("")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error in advanced search: {str(e)}"
