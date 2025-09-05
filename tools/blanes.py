from langchain.tools import tool
from urllib.parse import urlparse, unquote
from fuzzywuzzy import fuzz
import httpx
import requests
from datetime import datetime
from app.chatbot.models import Session
from app.database import SessionLocal
from enum import Enum
BASEURLFRONT = "https://api.dabablane.com/api/front/v1"
BASEURL = "https://api.dabablane.com/api"
BASEURLBACK = "https://api.dabablane.com/api/back/v1"

def get_token():

    url = f"https://api.dabablane.com/api/login"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "email": "admin@dabablane.com",
        "password": "admin"
    }
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

@tool("authenticate_email")
def authenticate_email(session_id: str, client_email: str) -> str:
    """
    Authenticates a user by email and associates it with a session.
    """
    with SessionLocal() as db:
        # Check if client exists
        # client = db.query(Client).filter(Client.email == client_email).first()
        # if not client:
        #     client = Client(email=client_email)
        #     db.add(client)
        #     db.commit()

        # Fetch the session
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            return f"Session {session_id} not found."

        # Set client_email and commit
        session.client_email = client_email
        db.commit()

    return f"Authenticated {client_email} for session {session_id}"

class PaginationSentiment(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


@tool("list_categories")
def list_categories() -> str:
    """
    
    
    """
    token = get_token()
    if not token:
        return "❌ Failed to retrieve token. Please try again later."
    url = f"{BASEURLBACK}/categories"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
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


def get_all_blanes_simple() -> list:
    """
    Retrieves ALL blanes from the API and returns them as a simple list of dictionaries.
    This version is more suitable for programmatic use.
    
    Returns:
        list: List of dictionaries containing blane data, or empty list on error
    """
    token = get_token()
    if not token:
        return []
    
    url = f"{BASEURLBACK}/blanes"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    all_blanes = []
    current_page = 1
    
    try:
        while True:
            params = {
                "status": "active",
                "sort_by": "created_at",
                "sort_order": "desc",
                "per_page": 10,
                "page": current_page
            }
            
            response = httpx.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            page_blanes = data.get('data', [])
            meta = data.get('meta', {})
            total_blanes = meta.get('total', 0)
            
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

@tool("search_blanes_advanced")
def search_blanes_advanced(session_id: str, keywords: str, min_relevance: float = 0.5) -> str:
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

        AI-Powered Matching: Uses GPT-4o-mini for semantic understanding
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
            "id": blane.get('id', 'Unknown'),
            "title": blane.get('name', 'Unknown'),
            "description": blane.get('description', ''),
            "category": blane.get('category', ''),
            "type": blane.get('type', '')
        }
        blanes_info.append(blane_entry)
    
    try:
        # Initialize OpenAI model (same as BookingToolAgent)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
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
            if ai_content.startswith('```json'):
                ai_content = ai_content.replace('```json', '').replace('```', '').strip()
            elif ai_content.startswith('```'):
                ai_content = ai_content.replace('```', '').strip()
            
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
            score = blane.get('relevance_score', 0)
            reason = blane.get('reason', 'Meets relevance criteria')
            
            score_emoji = "🎯" if score >= 0.9 else "🔥" if score >= 0.8 else "✨" if score >= 0.7 else "💫"
            
            output.append(f"{i}. {score_emoji} {blane['title']} (ID: {blane['id']})")
            # output.append(f"   📊 Score: {score:.2f}/1.0")
            output.append(f"   💡 {reason}")
            output.append("")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"❌ Error in advanced search: {str(e)}"


@tool("list_blanes")
def blanes_list(start: int = 1, offset: int = 10) -> str:
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
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

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
                "page": current_api_page
            }
            
            response = httpx.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            page_blanes = data.get('data', [])
            meta = data.get('meta', {})
            total_blanes = meta.get('total', 0)

            if start+offset > total_blanes:
                offset = total_blanes-start + 1
            
            if not page_blanes:
                break
            
            all_fetched_blanes.extend(page_blanes)
            items_collected += len(page_blanes)
            current_api_page += 1
            
            # Stop if we've reached the end of available data
            if len(all_fetched_blanes) >= total_blanes:
                break
        
        # Calculate the actual start position in our fetched data
        start_in_fetched = (start - 1) % 10 if api_page == ((start - 1) // 10) + 1 else 0
        
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
    output.append(f"📋 Blanes List (Items {start}-{actual_end} of {total_blanes} total)")
    output.append("")
    
    # Add blanes with their actual position numbers (title + price if available)
    for i, blane in enumerate(selected_blanes, start=start):
        name = blane.get('name', 'Unknown')
        price = blane.get('price_current')
        id = blane.get('id')
        if price:
            output.append(f"{i}. {name} — {price} Dhs (blane_id: {id})")
        else:
            output.append(f"{i}. {name} (blane_id: {id})")
        #output.append(f"{i}. {blane['name']} — MAD. {blane['price_current']} (ID: {blane['id']}) - BlaneType: {blane['type']} - TimeType: {blane['type_time']}")
    
    # Add navigation hints
    output.append("")
    if actual_end < total_blanes:
        next_start = actual_end + 1
        # output.append(f"💡 Voulez-vous voir les suivants? (Items {next_start}-{min(next_start + offset - 1, total_blanes)})")
        output.append(f"\nWant more?\nButtons: [Show 10 more] [See details]")
    else:
        output.append("\nThat’s all in this district. Want me to suggest blanes in another district?")
    return "\n".join(output)

@tool("handle_user_pagination_response")
def handle_user_pagination_response(user_sentiment: PaginationSentiment, current_start: int, current_offset: int, total_blanes: int) -> str:
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
            # set_session('current_start', next_start)
            return blanes_list(next_start, current_offset)
        else:
            return "❌ Vous êtes déjà à la fin de la liste. (You're already at the end of the list.)"
    
    elif user_sentiment == PaginationSentiment.NEGATIVE:
        return "👍 D'accord! Y a-t-il autre chose que je puisse vous aider? (Alright! Is there anything else I can help you with?)"
    
    else:
        return "❓ Je n'ai pas compris votre réponse. Dites 'oui' pour voir plus ou 'non' pour arrêter. (I didn't understand your response. Say 'yes' to see more or 'no' to stop.)"

@tool("get_available_time_slots")
def get_available_time_slots(blane_id: int, date: str) -> str:
    """
    Retrieves available time slots for a specific blane on a given date using blane ID.
    Only returns slots that are available, along with their remaining capacity.

    Parameters:
    - blane_id: The ID of the blane (integer)
    - date: The date to check availability for (format: YYYY-MM-DD)
    """
    token = get_token()
    if not token:
        return "❌ Failed to retrieve token. Please try again later."

    # Step 1: Get blane details directly
    url = f"{BASEURLBACK}/blanes/{blane_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        blane = response.json().get("data", {})

        if not blane:
            return f"❌ Blane with ID {blane_id} not found."

        if blane.get("type") != "reservation" or blane.get("type_time") != "time":
            return "❌ Unsupported reservation type returned by the API."

        slug = blane.get("slug")
        if not slug:
            return "❌ Could not find slug for this blane."

        # Step 2: Get available time slots using slug
        slots_url = f"{BASEURLFRONT}/blanes/{slug}/available-time-slots"
        slot_params = {"date": date}

        slots_response = httpx.get(slots_url, headers=headers, params=slot_params)
        slots_response.raise_for_status()
        result = slots_response.json()

        if result.get("type") != "time":
            return "❌ Unsupported reservation type returned by the API. Try get_available_periods instead."

        time_slots = result.get("data", [])
        available_slots = [
            f"- {slot['time']} → {slot['remainingCapacity']} spots"
            for slot in time_slots if slot["available"]
        ]

        if not available_slots:
            return f"No available time slots for '{blane['name']}' on {date}."

        output = [f"🗓 Available Time Slots for '{blane['name']}' on {date}:"]
        output.extend(available_slots)
        return "\n".join(output)

    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


@tool("get_available_periods")
def get_available_periods(blane_id: int) -> str:
    """
    Retrieves available periods for a date-based reservation blane using its ID.
    Only shows periods that are available, along with remaining capacity.

    Parameters:
    - blane_id: The ID of the blane (integer)
    """
    token = get_token()
    if not token:
        return "❌ Failed to retrieve token. Please try again later."

    # Step 1: Get blane info by ID
    url = f"{BASEURLBACK}/blanes/{blane_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        blane = response.json().get("data", {})

        if not blane:
            return f"❌ Blane with ID {blane_id} not found."

        if blane.get("type") != "reservation" or blane.get("type_time") != "date":
            return "❌ Unsupported reservation type returned by the API. Try get_available_time_slots instead."

        slug = blane.get("slug")
        if not slug:
            return "❌ Could not find slug for this blane."

        # Step 2: Get detailed info including available periods using slug
        front_url = f"{BASEURLFRONT}/blanes/{slug}"
        front_response = httpx.get(front_url, headers=headers)
        front_response.raise_for_status()
        detailed_blane = front_response.json().get("data", {})

        available_periods = detailed_blane.get("available_periods", [])
        available_periods = [p for p in available_periods if p.get("available")]

        if not available_periods:
            return f"No available periods found for '{blane['name']}'."

        output = [f"📅 Available Periods for '{blane['name']}':"]
        for period in available_periods:
            output.append(
                f"- {period['period_name']} → {period['remainingCapacity']} spots"
            )

        return "\n".join(output)

    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"❌ Error fetching periods: {str(e)}"


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
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

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
            subtype = "Hour-Based" if blane.get("type_time") == "time" else "Daily-Based"
            msg += f"\n📆 *Reservation Type:* {subtype}"
        elif main_type == "order":
            product_type = "Digital Product" if blane.get("is_digital") else "Physical Product"
            msg += f"\n🛍 *Product Type:* {product_type}"

        # Time Slot Info
        if blane.get("type_time") == 'time':
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
            msg += f"\n🔢 *Total Reservation Limit:* {blane.get('nombre_max_reservation')}"

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


@tool("before_create_reservation")
def prepare_reservation_prompt(blane_id: int) -> str:
    """
    This tool will prepare a reservation prompt for a specific blane. Run this tool before `create_reservation`.
    Returns a dynamic WhatsApp-style prompt with date/time or general info needed to make a reservation for a blane.
    """
    from datetime import datetime, timedelta
    import httpx

    token = get_token()
    if not token:
        return "❌ Failed to retrieve token."

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        res = httpx.get(f"{BASEURLBACK}/blanes/{blane_id}", headers=headers)
        res.raise_for_status()
        # blane = next((b for b in res.json()["data"] if b["id"] == blane_id), None)
        blane = res.json()["data"]
        if not blane:
            return f"❌ Blane with ID {blane_id} not found."
    except Exception as e:
        return f"❌ Error fetching blane: {e}"

   
    # Determine blane details
    name = blane.get("name", "Unknown")
    type_time = blane.get("type_time")  # 'time' or 'date'
    is_reservation = blane.get("type") == "reservation"
    is_order = blane.get("type") == "order"

    start = format_date(blane.get("start_date", ""))
    end = format_date(blane.get("expiration_date", ""))
    date_range = f"{start} to {end}" if start and end else "Unknown"

    # Generate time slots if applicable
    slots = ""
    if is_reservation and type_time == "time":
        try:
            heure_debut_str = blane["heure_debut"]
            heure_fin_str = blane["heure_fin"]
            interval = int(blane["intervale_reservation"])

            for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%H:%M:%S"):
                try:
                    heure_debut = datetime.strptime(heure_debut_str, fmt).time()
                    heure_fin = datetime.strptime(heure_fin_str, fmt).time()
                    break
                except ValueError:
                    continue
            else:
                return "❌ Could not parse blane time format."

            current = datetime.combine(datetime.today(), heure_debut)
            end_dt = datetime.combine(datetime.today(), heure_fin)
            time_slots = []
            while current <= end_dt:
                time_slots.append(current.strftime("%H:%M"))
                current += timedelta(minutes=interval)
            slots = ", ".join(time_slots)
        except Exception:
            slots = "Invalid time format"

    # Build prompt dynamically
    msg = f"To proceed with your reservation for the blane *{name}*, I need the following details:\n\n"
    msg = f"*1. User Name*:\n"
    msg = f"*2. Email*:\n"
    msg += f"3. *Phone Number*:\n"
    msg += f"4. *City*:\n"

    if is_order:
        msg += f"5. *Quantity*: (How many units?)\n"
        msg += f"6. *Delivery Address*: (Place where order has to be delivered)\n"
        msg += f"7. *Comments*: (Any special instructions?)\n"
    elif is_reservation and type_time == "time":
        msg += f"5. *Date*: (Available: {date_range}) Date Format: YYYY-MM-DD\n"
        msg += f"6. *Time*: (Available slots: {slots}) Time Format: HH:MM\n"
        msg += f"7. *Quantity*: (How many units?)\n"
        msg += f"8. *Number of Persons*: (People attending)\n"
        msg += f"9. *Comments*: (Any requests?)\n"
    elif is_reservation and type_time == "date":
        msg += f"5. *Start Date*: (Between {date_range}) Date Format: YYYY-MM-DD\n"
        msg += f"6. *End Date*: (Between {date_range}) Date Format: YYYY-MM-DD\n"
        msg += f"7. *Quantity*: (How many units?)\n"
        msg += f"8. *Number of Persons*: (People attending)\n"
        msg += f"9. *Comments*: (Any requests?)\n"

    return msg.strip()


@tool("create_reservation")
def create_reservation(
    session_id: str,
    blane_id: int,
    name: str = "N/A",
    email: str = "N/A",
    phone: str = "N/A",
    city: str = "N/A",
    date: str = "N/A",
    end_date: str = "N/A",
    time: str = "N/A",
    quantity: int = 1,
    number_persons: int = 1,
    delivery_address: str = "N/A",
    comments: str = "N/A"
) -> str:
    """
    Handles reservation or order creation.
    """
    from datetime import datetime, timedelta
    import httpx

    token = get_token()
    if not token:
        return "❌ Failed to retrieve token."

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        res = httpx.get(f"{BASEURLBACK}/blanes/{blane_id}", headers=headers)
        res.raise_for_status()
        blane = res.json()["data"]
        if not blane:
            return f"❌ Blane with ID {blane_id} not found."
    except Exception as e:
        return f"❌ Error fetching blane: {e}"

    blane_type = blane.get("type")
    type_time = blane.get("type_time")
    base_price = float(blane.get("price_current", 0))
    total_price = base_price * quantity

    # 🔸 Handle Delivery Cost (for orders)
    if blane_type == "order" and not blane.get("is_digital"):
        if blane.get("city") != city:
            total_price += float(blane.get("livraison_out_city", 0))
        else:
            total_price += float(blane.get("livraison_in_city", 0))

    # 🔸 Determine supported payment options from blane
    supports_online = bool(blane.get("online"))
    supports_partiel = bool(blane.get("partiel"))
    supports_cash = bool(blane.get("cash"))

    # 🔸 Choose payment route: prefer partial if available, else full online, else cash
    payment_route = "cash"
    if supports_partiel:
        payment_route = "partiel"
    elif supports_online:
        payment_route = "online"
    elif supports_cash:
        payment_route = "cash"

    # 🔸 Handle Partial Payments amount
    partiel_price = 0
    if payment_route == "partiel" and blane.get("partiel_field"):
        percent = float(blane["partiel_field"])
        partiel_price = round((percent / 100) * total_price)

    # 🔸 Validate reservation date
    today = datetime.today().date()
    if date != "N/A":
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()
            if date_obj < today:
                return f"❌ Reservation date {date} must not be in the past."
        except Exception:
            return f"❌ Invalid date format. Use YYYY-MM-DD."

    # 🔸 Reservation Logic
    if blane_type == "reservation":
        jours_open = blane.get("jours_creneaux", [])
        user_day = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
        user_day_fr = {
            "Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi",
            "Thursday": "Jeudi", "Friday": "Vendredi", "Saturday": "Samedi", "Sunday": "Dimanche"
        }.get(user_day, "")

        if jours_open and user_day_fr not in jours_open:
            return f"🚫 This blane is closed on {user_day}."

        if type_time == "time":
            heure_debut = parse_time_only(blane["heure_debut"])
            heure_fin = parse_time_only(blane["heure_fin"])
            try:
                slot_time = datetime.strptime(time, "%H:%M").time()
            except:
                return "❌ Invalid time format. Use HH:MM."

            # Check time is in valid slots
            current = datetime.combine(datetime.today(), heure_debut)
            end_dt = datetime.combine(datetime.today(), heure_fin)
            interval = int(blane["intervale_reservation"])
            valid_slots = []

            while current <= end_dt:
                valid_slots.append(current.strftime("%H:%M"))
                current += timedelta(minutes=interval)

            if time not in valid_slots:
                return f"🕓 Invalid time. Choose from: {', '.join(valid_slots)}"

        elif type_time == "date":
            try:
                start = parse_datetime(blane.get("start_date"))
                end = parse_datetime(blane.get("expiration_date"))
                user_date = datetime.strptime(date, "%Y-%m-%d")
                user_end_date = datetime.strptime(end_date, "%Y-%m-%d")
                if not (start.date() <= user_date.date() <= end.date()):
                    return f"❌ Start date must be within {start.date()} to {end.date()}"
                if not (start.date() <= user_end_date.date() <= end.date()):
                    return f"❌ End date must be within {start.date()} to {end.date()}"
            except:
                return "❌ Invalid start or end date format."

        payload = {
            "blane_id": blane_id,
            "name": name,
            "email": email,
            "phone": phone,
            "city": city,
            "date": date,
            "end_date": end_date if type_time == "date" else None,
            "time": time if type_time == "time" else None,
            "quantity": quantity,
            "number_persons": number_persons,
            "payment_method": payment_route,
            "status": "pending",
            "total_price": total_price - partiel_price,
            "partiel_price": partiel_price,
            "comments": comments
        }

    # 🔸 Order Logic
    elif blane_type == "order":
        if not delivery_address or delivery_address == "N/A":
            return "📦 Please provide a valid delivery address."

        payload = {
            "blane_id": blane_id,
            "name": name,
            "email": email,
            "phone": phone,
            "city": city,
            "delivery_address": delivery_address,
            "quantity": quantity,
            "payment_method": payment_route,
            "status": "pending",
            "total_price": total_price - partiel_price,
            "partiel_price": partiel_price,
            "comments": comments
        }

    else:
        return "❌ Unknown blane type. Only 'reservation' or 'order' supported."

    # 🔸 Create Reservation or Order
    try:
        API = ""
        if blane_type == "reservation":
            API = f"{BASEURLFRONT}/reservations"
        elif blane_type == "order":
            API = f"{BASEURLFRONT}/orders"

        print(payload)
        print(API)

        res = httpx.post(f"{API}", headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()

        # If online or partial payment is selected/supported, initiate payment and return URL
        if payment_route in ("online", "partiel"):
            # Extract reference from response payload: data.data.NUM_RES or data.data.NUM_ORD
            reference = None
            try:
                nested = data.get("data") if isinstance(data, dict) else None
                if isinstance(nested, dict):
                    reference = nested.get("NUM_RES") or nested.get("NUM_ORD")
            except Exception:
                reference = None

            if reference:
                try:
                    pay_url = f"{BASEURLFRONT}/payment/cmi/initiate"
                    pay_res = httpx.post(pay_url, headers=headers, json={"number": reference})
                    pay_res.raise_for_status()
                    pay_data = pay_res.json()
                    if pay_data.get("status") and pay_data.get("payment_url"):
                        return f"✅ Created. Ref: {reference}. 💳 Pay here: {pay_data.get('payment_url')}"
                    else:
                        return f"✅ Success! {data}. Payment initiation: {pay_data}"
                except Exception as e:
                    return f"✅ Success! {data}, but payment link failed: {str(e)}"

        # Cash/offline flow
        return f"✅ Success! {data}"
    except Exception as e:
        return f"❌ Error submitting reservation: {str(e)}"


    

@tool("preview_reservation")
def preview_reservation(
    session_id: str,
    blane_id: int,
    name: str = "N/A",
    email: str = "N/A",
    phone: str = "N/A",
    city: str = "N/A",
    date: str = "N/A",
    end_date: str = "N/A",
    time: str = "N/A",
    quantity: int = 1,
    number_persons: int = 1,
    delivery_address: str = "N/A",
    comments: str = "N/A"
) -> str:
    """
    Prepare a booking recap with dynamic price calculation (including delivery and partial payments) WITHOUT creating it.
    Shows a confirmation prompt with Buttons: [Confirm] [Edit] [Cancel].
    """
    from datetime import datetime, timedelta
    import httpx

    token = get_token()
    if not token:
        return "❌ Failed to retrieve token. Please try again later."

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Fetch blane
    try:
        res = httpx.get(f"{BASEURLBACK}/blanes/{blane_id}", headers=headers)
        res.raise_for_status()
        blane = res.json().get("data", {})
        if not blane:
            return f"❌ Blane with ID {blane_id} not found."
    except Exception as e:
        return f"❌ Error fetching blane: {e}"

    blane_type = blane.get("type")
    type_time = blane.get("type_time")

    # Pricing
    try:
        base_price = float(blane.get("price_current", 0))
    except Exception:
        base_price = 0.0
    total_price = base_price * max(1, int(quantity))

    # Delivery for physical orders
    delivery_cost = 0.0
    if blane_type == "order" and not blane.get("is_digital"):
        if blane.get("city") != city:
            delivery_cost = float(blane.get("livraison_out_city", 0))
        else:
            delivery_cost = float(blane.get("livraison_in_city", 0))
        total_price += delivery_cost

    # Payment route
    supports_online = bool(blane.get("online"))
    supports_partiel = bool(blane.get("partiel"))
    supports_cash = bool(blane.get("cash"))

    payment_route = "cash"
    if supports_partiel:
        payment_route = "partiel"
    elif supports_online:
        payment_route = "online"
    elif supports_cash:
        payment_route = "cash"

    # Partial amount
    partiel_percent = None
    partiel_price = 0
    if payment_route == "partiel" and blane.get("partiel_field"):
        try:
            partiel_percent = float(blane.get("partiel_field"))
            partiel_price = round((partiel_percent / 100) * total_price)
        except Exception:
            partiel_percent = None
            partiel_price = 0

    # Validate date/time inputs for reservation
    try:
        if blane_type == "reservation":
            if type_time == "time":
                # validate date
                if date and date != "N/A":
                    _ = datetime.strptime(date, "%Y-%m-%d")
                else:
                    return "❌ Please provide a date (YYYY-MM-DD)."
                # validate time
                if time and time != "N/A":
                    _ = datetime.strptime(time, "%H:%M")
                else:
                    return "❌ Please provide a time (HH:MM)."
            elif type_time == "date":
                if not (date and end_date and date != "N/A" and end_date != "N/A"):
                    return "❌ Please provide start and end dates (YYYY-MM-DD)."
                _ = datetime.strptime(date, "%Y-%m-%d")
                _ = datetime.strptime(end_date, "%Y-%m-%d")
    except Exception:
        return "❌ Invalid date or time format."

    # Build recap
    blane_name = blane.get("name", "Unknown")
    lines = [
        "Great. I’ll need the booking info.",
        "",
        f"Please review:",
        f"- Blane: {blane_name}",
    ]

    if blane_type == "reservation":
        if type_time == "time":
            lines += [
                f"- Date: {date}",
                f"- Time: {time}",
            ]
        else:
            lines += [
                f"- Start Date: {date}",
                f"- End Date: {end_date}",
            ]
        lines += [
            f"- Quantity: {quantity}",
            f"- Persons: {number_persons}",
        ]
    else:
        lines += [
            f"- Quantity: {quantity}",
        ]
        if delivery_address and delivery_address != "N/A":
            lines.append(f"- Delivery Address: {delivery_address}")

    lines += [
        f"- City: {city}",
        f"- Payment: {'Partial' if payment_route=='partiel' else ('Online' if payment_route=='online' else 'Cash')}",
    ]

    if blane_type == "order" and not blane.get("is_digital"):
        lines.append(f"- Delivery Cost: {int(delivery_cost)} MAD")

    lines.append(f"- Total: {int(total_price)} MAD")
    if payment_route == "partiel" and partiel_price:
        lines.append(f"- Due now (partial): {int(partiel_price)} MAD")
    elif payment_route == "online":
        lines.append(f"- Due now: {int(total_price)} MAD")

    lines += [
        "",
        "Confirm booking?",
        "Buttons: [Confirm] [Edit] [Cancel]",
    ]

    return "\n".join(lines)

@tool("list_reservations")
def list_reservations(email: str) -> str:
    """
    Get the list of the authenticated user's reservations.
    Requires user's email.
    """

    token = get_token()
    if not token:
        return {"error": "❌ Failed to retrieve token."}

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    result = {
        "reservations": [],
        "orders": []
    }

    # Fetch Reservations
    res_url = f"{BASEURLBACK}/reservations?email={email}"
    res_response = requests.get(res_url, headers=headers)
    if res_response.status_code == 200:
        result["reservations"] = res_response.json().get("data", [])
    else:
        result["reservations_error"] = res_response.text

    # Fetch Orders
    orders_url = f"{BASEURLBACK}/orders?email={email}"
    orders_response = requests.get(orders_url, headers=headers)
    if orders_response.status_code == 200:
        result["orders"] = orders_response.json().get("data", [])
    else:
        result["orders_error"] = orders_response.text

    return result

# District mapping with corrected structure
district_map = {
    "anfa": [
        "bourgogne",
        "sidi belyout",
        "centre ville", 
        "médina",
        "maârif",
        "ain diab",
        "corniche",
        "gauthier",
        "racine",
        "palmier",
        "triangle d'or",
        "oasis",
        "cil"
    ],
    "hay hassani": [
        "hay hassani",
        "oulfa",
        "errahma",
        "lissasfa"
    ],
    "aïn chock": [
        "aïn chock",
        "sidi maârouf",
        "californie",
        "polo"
    ],
    "aïn sebaâ – hay mohammadi": [
        "aïn sebaâ",
        "hay mohammadi",
        "roches noires",
        "belvédère"
    ],
    "al fida – mers sultan": [
        "al fida",
        "mers sultan",
        "derb sultan",
        "habous"
    ],
    "sidi bernoussi – sidi moumen": [
        "sidi bernoussi",
        "sidi moumen",
        "zenata"
    ],
    "moulay rachid – ben m'sick": [
        "moulay rachid",
        "sidi othmane",
        "ben m'sick",
        "sbata"
    ],
    "surroundings": [
        "bouskoura",
        "la ville verte",
        "dar bouazza",
        "mohammedia",
        "bouznika"
    ]
}

def _matches_category(name: str, description: str, category: str) -> bool:
    """
    Improved category matching with better keyword organization and fuzzy matching.
    """
    if not category:
        return True
    
    category_lower = category.strip().lower()
    text_to_search = f"{name} {description or ''}".lower()
    
    # Enhanced keyword mapping with more comprehensive terms
    category_keywords = {
        "restaurant": [
            # Core restaurant terms
            "restaurant", "resto", "food", "cuisine", "kitchen", "dining",
            # Meal types
            "café", "brunch", "goûters", "déjeunez", "dinner", "lunch", "breakfast",
            # Food items
            "pizzeria", "pizzas", "pâte", "sauce", "tomate", "ingrédients",
            # Experience terms  
            "gastronomie", "ambiance", "gnaoua", "artisanat", "créativité",
            # Drink terms
            "drinks", "bar", "cocktail", "beverage",
            # Specific restaurant names/types
            "bazenne", "cappero"
        ],
        "spa": [
            # Core spa services
            "spa", "massage", "hammam", "soin", "wellness", "détente", "relaxation",
            # Beauty services
            "beauté", "esthétique", "institut", "salon", "coiffure",
            # Hair services
            "cheveux", "brushing", "coupe", "lissant",
            # Nail services
            "manucure", "pédicure", "vernis",
            # Facial services
            "visage", "facial", "hydra", "gommage",
            # Treatment types
            "relaxant", "hydratant", "réparateur", "hydromassage",
            # Facilities
            "transats", "pool", "piscine",
            # Specific spa brands/names
            "fish", "musc", "taha", "nashi", "nelya", "jasmin"
        ],
        "activity": [
            # Core activity terms
            "activité", "activities", "activity", "fun", "entertainment",
            # Adventure activities
            "escape", "paintball", "accrobranche", "quad", "aventures",
            # Water activities  
            "toboggans", "piscines", "aquatiques", "natation", "eau", "tubing", "slide",
            # Gaming
            "laser game", "jeux", "bowling", "cinema", "cinéma",
            # Sports
            "sports", "sportives", "équipe", "team building",
            # Kids activities
            "enfants", "summer camp", "éducatif", "plein air",
            # Tech activities
            "robotique", "lego", "codage", "intelligence artificielle",
            # Creative activities
            "créatives", "culturelles", "projets innovants",
            # Business activities
            "corporate", "présentation", "team", "building",
            # Event spaces
            "villa", "terrain", "décor"
        ]
    }
    
    # Get keywords for the category, fallback to the category itself
    keywords = category_keywords.get(category_lower, [category_lower])
    
    # Check for exact matches and partial matches
    for keyword in keywords:
        if keyword in text_to_search:
            return True
    
    # Additional fuzzy matching for common variations
    if category_lower in ["restaurant", "resto"]:
        return any(term in text_to_search for term in ["manger", "plat", "menu", "chef"])
    elif category_lower == "spa":
        return any(term in text_to_search for term in ["bien-être", "soins", "thérapie"])
    elif category_lower in ["activity", "activité"]:
        return any(term in text_to_search for term in ["loisir", "divertissement", "adventure"])
    
    return False

def _normalize_location_text(text: str) -> str:
    """
    Normalize location text for better matching.
    """
    if not text:
        return ""
    
    # Convert to lowercase and strip
    normalized = text.lower().strip()
    
    # Handle common variations and abbreviations
    location_variations = {
        "ain": "aïn",
        "centre-ville": "centre ville",
        "sidi belyout (centre ville, médina)": ["sidi belyout", "centre ville", "médina"],
        "ain diab (corniche)": ["ain diab", "corniche", "aïn diab"],
        "roches noires (belvédère)": ["roches noires", "belvédère"],
    }
    
    return normalized

@tool("introduction_message")
def introduction_message() -> str:
    """
    Returns the introduction message for DabaBlane AI booking assistant.
    
    Use this tool when:
    - User sends greeting messages like "hello", "hi", "salam", "assalam o alaikum"
    - User asks "what can you do" or "help me"
    - User starts a new conversation
    - User asks about the bot's capabilities or services
    - User sends any initial greeting or inquiry about services
    
    The tool provides a comprehensive introduction explaining:
    - Bot identity as DabaBlane AI booking assistant
    - Available services (finding blanes, checking availability, making reservations)
    - Required information needed from users (category, city, district, sub-district, date)
    - Friendly greeting response in local language (French/Roman)
    
    Also use this when user says "salam" in any form - respond with "Walikum Assalam" instead of Hello.

    """
    message = """
    Bonjour! Je suis *DabaBlane AI*, votre assistant de réservation intelligent. 🤖✨

    Je peux vous aider à :
    ‣   🔍 Trouver des *blanes* (selon catégorie, ville, district et sous-district)
    ‣   📅 Vérifier la disponibilité
    ‣   🛎️ Réserver un blane pour vous
    ‣   💸 Vous guider dans le processus de paiement et de réservation

    Pour vous montrer les meilleures options, j’aurai besoin de quelques détails :
       ‣ *Catégorie* (par ex: ferme, villa, appartement, etc.)
       ‣ *Ville*
       ‣ *District / Sous-district*
       ‣ *Date de réservation*
       ‣ *Plage de prix* (optionnel)

    Donnez-moi ces informations et je m’occupe du reste. 🚀
    """
    return message


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
        return "irrelevant: Please provide a valid message about blanes or reservations."
    
    message_lower = user_message.lower().strip()
    
    # Blane/business related keywords
    blane_keywords = [
        "blane", "blanes", "dabablane", "reservation", "booking", "book", 
        "reserve", "restaurant", "spa", "activity", "massage", "food", 
        "eat", "dine", "activities", "entertainment", "wellness", "relax",
        "casablanca", "morocco", "maroc", "price", "cost", "available",
        "time slot", "appointment", "order", "delivery", "table",
        "treatment", "service", "deal", "offer", "discount", "photo shoot",
        "photography", "studio", "event", "venue", "location"
    ]
    
    # Location keywords
    location_keywords = [
        "anfa", "hay hassani", "ain chock", "mers sultan", "sidi bernoussi",
        "moulay rachid", "casablanca", "morocco", "maroc", "near me",
        "my area", "district", "neighbourhood", "location", "where",
        "corniche", "centre ville", "medina", "maârif", "gauthier"
    ]
    
    # Greeting keywords
    greeting_keywords = [
        "hello", "hi", "hey", "bonjour", "salut", "salam", "good morning",
        "good afternoon", "good evening", "how are you", "start", "begin"
    ]
    
    # Irrelevant keywords (clearly off-topic)
    irrelevant_keywords = [
        "weather", "politics", "news", "stock market", "crypto", "bitcoin",
        "programming", "code", "technical support", "computer", "software",
        "medicine", "health advice", "legal advice", "homework", "study",
        "recipe", "cooking tutorial", "travel outside morocco"
    ]
    
    # Calculate relevance scores
    blane_score = sum(1 for keyword in blane_keywords if keyword in message_lower)
    location_score = sum(1 for keyword in location_keywords if keyword in message_lower)
    greeting_score = sum(1 for keyword in greeting_keywords if keyword in message_lower)
    irrelevant_score = sum(1 for keyword in irrelevant_keywords if keyword in message_lower)
    
    # Determine category and relevance
    total_positive = blane_score + location_score + greeting_score
    
    if irrelevant_score > 0 and total_positive == 0:
        return "irrelevant: I'm Dabablane AI, specialized in helping with blane reservations, bookings, and finding activities, restaurants, and spa services in Casablanca. How can I help you with that?"
    
    if greeting_score > 0:
        return "greeting"
    
    if blane_score > 0 or location_score > 0 or total_positive > 0:
        return "relevant"
    
    # Try to find any possible connection to blanes
    possible_blane_connection = any([
        "suggest" in message_lower,
        "looking for" in message_lower,
        "want" in message_lower,
        "help" in message_lower,
        "show me" in message_lower,
        "find" in message_lower,
        "search" in message_lower
    ])
    
    if possible_blane_connection:
        return "relevant"
    
    # Default to irrelevant
    return "irrelevant: I'm Dabablane AI, specialized in blane reservations and bookings. I can help you find restaurants, spas, activities, and more in Casablanca. What interests you?"
    # import re
    
    # if not user_message or not user_message.strip():
    #     return {
    #         "is_relevant": False,
    #         "category": "irrelevant",
    #         "confidence": 0.0,
    #         "suggested_response": "Please provide a valid message.",
    #         "next_action": "ask_for_input"
    #     }
    
    # message_lower = user_message.lower().strip()
    
    # # Blane/business related keywords
    # blane_keywords = [
    #     "blane", "blanes", "dabablane", "reservation", "booking", "book", 
    #     "reserve", "restaurant", "spa", "activity", "massage", "food", 
    #     "eat", "dine", "activities", "entertainment", "wellness", "relax",
    #     "casablanca", "morocco", "maroc", "price", "cost", "available",
    #     "time slot", "appointment", "order", "delivery", "table",
    #     "treatment", "service", "deal", "offer", "discount"
    # ]
    
    # # Location keywords
    # location_keywords = [
    #     "anfa", "hay hassani", "ain chock", "mers sultan", "sidi bernoussi",
    #     "moulay rachid", "casablanca", "morocco", "maroc", "near me",
    #     "my area", "district", "neighbourhood", "location", "where",
    #     "corniche", "centre ville", "medina", "maârif", "gauthier"
    # ]
    
    # # Greeting keywords
    # greeting_keywords = [
    #     "hello", "hi", "hey", "bonjour", "salut", "salam", "good morning",
    #     "good afternoon", "good evening", "how are you", "start", "begin"
    # ]
    
    # # Irrelevant keywords (clearly off-topic)
    # irrelevant_keywords = [
    #     "weather", "politics", "news", "stock market", "crypto", "bitcoin",
    #     "programming", "code", "technical support", "computer", "software",
    #     "medicine", "health advice", "legal advice", "homework", "study",
    #     "recipe", "cooking tutorial", "travel outside morocco"
    # ]
    
    # # Question about platform/creator
    # creator_keywords = [
    #     "who created you", "who made you", "your creator", "your developer",
    #     "how were you built", "what technology", "ai model", "chatbot",
    #     "artificial intelligence"
    # ]
    
    # # Calculate relevance scores
    # blane_score = sum(1 for keyword in blane_keywords if keyword in message_lower)
    # location_score = sum(1 for keyword in location_keywords if keyword in message_lower)
    # greeting_score = sum(1 for keyword in greeting_keywords if keyword in message_lower)
    # irrelevant_score = sum(1 for keyword in irrelevant_keywords if keyword in message_lower)
    # creator_score = sum(1 for keyword in creator_keywords if keyword in message_lower)
    
    # # Determine category and relevance
    # total_positive = blane_score + location_score + greeting_score
    
    # if irrelevant_score > 0 and total_positive == 0:
    #     return {
    #         "is_relevant": False,
    #         "category": "irrelevant",
    #         "confidence": 0.9,
    #         "suggested_response": "I'm Dabablane AI, specialized in helping with blane reservations, bookings, and finding activities, restaurants, and spa services in Casablanca. How can I help you with that?",
    #         "next_action": "redirect_to_blanes"
    #     }
    
    # if creator_score > 0:
    #     return {
    #         "is_relevant": True,  # Still relevant as it's about the platform
    #         "category": "creator_question",
    #         "confidence": 0.8,
    #         "suggested_response": "I'm Dabablane AI, created to help you with blane reservations and bookings. Let's focus on finding you some great deals! What are you interested in?",
    #         "next_action": "brief_answer_then_redirect"
    #     }
    
    # if greeting_score > 0:
    #     return {
    #         "is_relevant": True,
    #         "category": "greeting",
    #         "confidence": 0.9,
    #         "suggested_response": "Hello! I'm Dabablane AI, your assistant for blane bookings and reservations.",
    #         "next_action": "brief_answer_then_redirect"
    #     }
    
    # if blane_score > 2 or (blane_score > 0 and location_score > 0):
    #     # High confidence blane-related
    #     if any(word in message_lower for word in ["book", "reserve", "reservation", "booking"]):
    #         category = "booking"
    #     else:
    #         category = "search_blanes"
        
    #     return {
    #         "is_relevant": True,
    #         "category": category,
    #         "confidence": 0.9,
    #         "suggested_response": "Great! I can help you with that.",
    #         "next_action": "proceed_with_authentication"
    #     }
    
    # if total_positive > 0:
    #     return {
    #         "is_relevant": True,
    #         "category": "question_about_blanes",
    #         "confidence": 0.7,
    #         "suggested_response": "I can help you with blane-related questions.",
    #         "next_action": "proceed_with_authentication"
    #     }
    
    # # Try to find any possible connection to blanes
    # possible_blane_connection = any([
    #     "suggest" in message_lower and "website" in message_lower,  # website creation blane?
    #     "learn" in message_lower and any(skill in message_lower for skill in ["skill", "course", "training"]),
    #     "service" in message_lower,
    #     "experience" in message_lower,
    #     "looking for" in message_lower,
    #     "want" in message_lower and "something" in message_lower,
    #     "help" in message_lower and ("me" in message_lower or "with" in message_lower)
    # ])
    
    # if possible_blane_connection:
    #     return {
    #         "is_relevant": True,
    #         "category": "question_about_blanes",
    #         "confidence": 0.6,
    #         "suggested_response": "Are you looking for a blane related to that? I can help you find activities, services, or experiences.",
    #         "next_action": "clarify_then_proceed"
    #     }
    
    # # Default to irrelevant
    # return {
    #     "is_relevant": False,
    #     "category": "irrelevant",
    #     "confidence": 0.8,
    #     "suggested_response": "I'm Dabablane AI, specialized in blane reservations and bookings. I can help you find restaurants, spas, activities, and more in Casablanca. What interests you?",
    #     "next_action": "redirect_to_blanes"
    # }

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
    offset: int = 10
) -> str:
    """
    Retrieve blanes by location and/or category with improved filtering logic.
    
    Args:
        district: District name
        sub_district: Sub-district name  
        category: Category (restaurant, spa, activity, etc.)
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
    
    # Use larger pagination size to get more comprehensive results for filtering
    params = {
        "status": "active",
        "sort_by": "created_at",
        "sort_order": "desc",
        "pagination_size": 500  # Increased for better filtering
    }

    try:
        response = httpx.get(f"{BASEURLBACK}/blanes", headers=headers, params=params)
        response.raise_for_status()
        all_blanes = response.json().get("data", [])
    except Exception as e:
        return f"❌ Error fetching blanes: {str(e)}"

    for blane in all_blanes:
        print(blane["id"])
    # Normalize input filters
    district_norm = _normalize_location_text(district)
    sub_district_norm = _normalize_location_text(sub_district)
    city_norm = _normalize_location_text(city)
    category_norm = category.lower().strip() if category else ""

    # Get all sub-districts for the specified district
    district_subs = []
    if district_norm:
        district_subs = [_normalize_location_text(sub) for sub in district_map.get(district_norm, [])]

    # Filter blanes based on criteria
    matched_blanes = []
    
    for blane in all_blanes:
        name = blane.get("name", "")
        description = blane.get("description") or ""
        blane_city = _normalize_location_text(blane.get("city", ""))
        
        # Create searchable text
        searchable_text = _normalize_location_text(f"{name} {description}")
        
        # Apply filters
        passes_city_filter = not city_norm or city_norm in blane_city
        passes_category_filter = not category_norm or _matches_category(name, description, category_norm)
        
        # Location filtering logic
        passes_location_filter = True
        location_score = 0  # For prioritization
        
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
        
        # Only include blanes that pass all filters
        if passes_city_filter and passes_category_filter and passes_location_filter:
            blane['_location_score'] = location_score
            matched_blanes.append(blane)
    
    # Sort by location score (prioritize exact sub-district matches)
    matched_blanes.sort(key=lambda x: x.get('_location_score', 0), reverse=True)
    
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
        
        filters_text = ", ".join(filter_description) if filter_description else "the given filters"
        return f"❌ No blanes found for {filters_text}. Try different search criteria."

    # Apply pagination
    end_pos = min(start + offset - 1, total_matches)
    if start > total_matches:
        return f"❌ Start position {start} exceeds total results ({total_matches}). Try a lower start position."

    paginated_blanes = matched_blanes[start - 1:end_pos]

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
    output_lines.append(f"📊 Showing items {start}-{end_pos} of {total_matches} matches")
    output_lines.append("")
    
    # Add blanes
    for idx, blane in enumerate(paginated_blanes, start=start):
        name = blane.get("name", "Unknown")
        price = blane.get("price_current")
        blane_id = blane.get('id')
        
        if price:
            output_lines.append(f"{idx}. {name} — {price} Dhs (blane_id: {blane_id})")
        else:
            output_lines.append(f"{idx}. {name} (blane_id: {blane_id})")

    # Add pagination info
    output_lines.append("")
    if end_pos < total_matches:
        next_start = end_pos + 1
        max_next_end = min(next_start + offset - 1, total_matches)
        output_lines.append(f"💡 More results available (Items {next_start}-{max_next_end})")
        output_lines.append("Buttons: [Show more] [See details] [Change filters]")
    else:
        output_lines.append("That's all for these filters.")
        output_lines.append("Want to try different search criteria or see details?")

    return "\n".join(output_lines)



@tool("find_blanes_by_name_or_link")
def find_blanes_by_name_or_link(query: str, limit: int = 10, score_threshold: int = 60) -> str:
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
            if q.startswith("http://") or q.startswith("https://") or q.startswith("www."):
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

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

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
                "page": page
            }
            resp = httpx.get(f"{BASEURLBACK}/blanes", headers=headers, params=params)
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

