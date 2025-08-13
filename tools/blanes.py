from langchain.tools import tool
import httpx
import requests
from datetime import datetime
from app.chatbot.models import Session
from app.database import SessionLocal
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


# @tool("list_blanes")
# def blanes_list(page_num: int = 1) -> str:
#     """
#     Lists active Blanes with pagination.
#     Shows 10 blanes per page.
    
#     Args:
#         page_num: Page number to display from session (default: 1)
    
#     Returns a readable list with pagination info.
#     """
#     # Since page_num comes from session, no need for global variables
    
#     token = get_token()
#     if not token:
#         return "❌ Failed to retrieve token. Please try again later."
    
#     # Get cached blanes from session (you'll need to implement session storage)
#     # cached_blanes = get_from_session('cached_blanes') or []
    
#     # For now, we'll always fetch fresh data - you can optimize this later with proper session caching
#     url = f"{BASEURLBACK}/blanes"
#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json"
#     }

#     all_blanes = []
#     api_page = 1
    
#     try:
#         while True:
#             params = {
#                 "status": "active",
#                 "sort_by": "created_at",
#                 "sort_order": "desc",
#                 "per_page": 10,
#                 "page": api_page
#             }
            
#             response = httpx.get(url, headers=headers, params=params)
#             response.raise_for_status()
#             data = response.json()
            
#             blanes = data.get('data', [])
            
#             if not blanes:
#                 break
                
#             all_blanes.extend(blanes)
            
#             # Check if we've got all items
#             total_blanes = data.get('meta', {}).get('total', 0)
            
#             if len(all_blanes) >= total_blanes:
#                 break
                
#             api_page += 1

#         # Store in session/cache for pagination
#         # set_session('cached_blanes', all_blanes)
#         cached_blanes = all_blanes
        
#     except httpx.HTTPStatusError as e:
#         return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
#     except Exception as e:
#         return f"❌ Error fetching blanes: {str(e)}"

#     if not cached_blanes:
#         return "No blanes found."

#     # Calculate pagination
#     total_blanes = len(cached_blanes)
#     per_page = 10
#     total_pages = (total_blanes + per_page - 1) // per_page  # Ceiling division
    
#     # Validate page number
#     if page_num < 1 or page_num > total_pages:
#         return f"❌ Invalid page number. Please choose between 1 and {total_pages}."
    
#     # Get blanes for current page
#     start_index = (page_num - 1) * per_page
#     end_index = min(start_index + per_page, total_blanes)
#     page_blanes = cached_blanes[start_index:end_index]
    
#     # Build output
#     output = []
    
#     # Add header with pagination info
#     output.append(f"📋 Blanes List (Page {page_num} of {total_pages})")
#     output.append(f"Showing {start_index + 1}-{end_index} of {total_blanes} total blanes")
#     output.append("")
    
#     # Add blanes for this page
#     for i, blane in enumerate(page_blanes, start=start_index + 1):
#         output.append(f"{i}. {blane['name']} — MAD. {blane['price_current']} (ID: {blane['id']}) - BlaneType: {blane['type']} - TimeType: {blane['type_time']}")
    
#     # Add navigation hints
#     output.append("")
#     if page_num < total_pages:
#         output.append(f"💡 Voulez-vous voir les 10 suivants? (Do you want to see the next 10?)")
#     if page_num > 1:
#         output.append(f"💡 Retourner aux 10 précédents? (Go back to previous 10?)")
    
#     return "\n".join(output)
from enum import Enum
from typing import List, Dict

class PaginationSentiment(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"

@tool("list_blanes")
def blanes_list(start: int = 1, offset: int = 10) -> str:
    """
    Lists active Blanes with start position and offset without knowing district and sub-district information. Always show total blanes in output.
    
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
        if price:
            output.append(f"{i}. {name} — {price} Dhs")
        else:
            output.append(f"{i}. {name}")
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
            return "❌ Unsupported reservation type returned by the API."

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
            return "❌ Unsupported reservation type returned by the API."

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
    # params = {
    #     "status": "active",
    #     "sort_by": "created_at",
    #     "sort_order": "desc",
    #     "pagination_size": 100
    # }

    try:
        # response = httpx.get(url, headers=headers, params=params)
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        blane = response.json().get("data", [])
        print(blane)
        # blane = next((b for b in blanes if b["id"] == blane_id), None)
        # if not blane:
        #     return f"❌ Blane with ID {blane_id} not found."


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
        msg += f"5. *Date*: (Available: {date_range}) Date Format: DD-MM-YYYY\n"
        msg += f"6. *Time*: (Available slots: {slots}) Time Format: HH:MM\n"
        msg += f"7. *Quantity*: (How many units?)\n"
        msg += f"8. *Number of Persons*: (People attending)\n"
        msg += f"9. *Comments*: (Any requests?)\n"
    elif is_reservation and type_time == "date":
        msg += f"5. *Start Date*: (Between {date_range}) Date Format: DD-MM-YYYY\n"
        msg += f"6. *End Date*: (Between {date_range}) Date Format: DD-MM-YYYY\n"
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
    Handles reservation or order creation. Must run `before_create_reservation` first.
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
                    pay_url = f"{BASEURL}/payment/cmi/initiate"
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

# @tool("initiate_payment")
# def initiate_payment(number: str) -> str:
#     """
#     Initiates payment for an existing order or reservation and returns the payment URL.

#     Args:
#         number: The reference number (e.g., RES-XXXX or ORDER-XXXX)
#     """
#     token = get_token()
#     if not token:
#         return "❌ Failed to retrieve token. Please try again later."

#     url = f"{BASEURLFRONT}/payment/cmi/initiate"
#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json"
#     }
#     payload = {"number": number}

#     try:
#         response = httpx.post(url, headers=headers, json=payload)
#         response.raise_for_status()
#         data = response.json()
#         if not data.get("status"):
#             code = data.get("code", "")
#             message = data.get("message", "Unknown error")
#             return f"❌ Payment initiation failed. {code} {message}"

#         payment_url = data.get("payment_url")
#         if payment_url:
#             return f"💳 Payment link: {payment_url}"
#         return f"✅ Payment initiated. Open the provided payment page to complete the transaction."

#     except httpx.HTTPStatusError as e:
#         return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
#     except Exception as e:
#         return f"❌ Error initiating payment: {str(e)}"

# @tool("create_reservation")
# def create_reservation(session_id: str, blane_id: int, name: str = "N/A", email: str = "N/A", phone: str = "N/A", city: str = "N/A", date: str = "N/A", end_date: str = "N/A", time: str = "N/A", quantity: int = 1, number_persons: int = 0, comments: str = "N/A") -> str:
#     """
#     Handles reservation creation.
#     IMPORTANT: Do not call this tool directly. Always call `before_create_reservation` first to determine required fields, collect them from the user, and then call this tool.
#     """
#     from datetime import datetime, timedelta
#     import httpx

#     token = get_token()
#     if not token:
#         return "❌ Failed to retrieve token."

#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json"
#     }

#     # Step 1: Get blane info
#     try:
#         res = httpx.get(f"{BASEURLBACK}/blanes/{blane_id}", headers=headers)
#         res.raise_for_status()
#         # blane = next((b for b in res.json()["data"] if b["id"] == blane_id), None)
#         if not blane:
#             return f"❌ Blane with ID {blane_id} not found."
#     except Exception as e:
#         return f"❌ Error fetching blane: {e}"

#     blane_type = blane.get("type")
#     blane_time_type = blane.get("type_time")

#     # Step 2: Calculate Total Cost
#     base_price = float(blane.get("price_current", 0))
#     total_price = base_price * quantity

#     # Step 3: Add delivery cost if order and physical
#     if blane["type"] == "order" and not blane.get("is_digital"):
#         if blane.get("city") != city:
#             total_price += float(blane.get("livraison_out_city", 0))
#         else:
#             total_price += float(blane.get("livraison_in_city", 0))

#     # Step 4: Handle partiel payments
#     partiel_price = 0
#     if blane.get("partiel") and blane.get("partiel_field"):
#         percent = float(blane["partiel_field"])
#         partiel_price = round((percent / 100) * total_price)

#     english_to_french_days = {
#         "Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi",
#         "Thursday": "Jeudi", "Friday": "Vendredi", "Saturday": "Samedi", "Sunday": "Dimanche"
#     }

#     current_date = datetime.now().strftime("%Y-%m-%d")
#     if date != "N/A" and date < current_date:
#         return f"❌ Invalid reservation date: {date}. Please choose a future date."

#     # Step 5: Validate time/date based on type
#     if blane_type == "reservation":
#         jours_open = blane.get("jours_creneaux", [])
#         user_day = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
#         user_day_fr = english_to_french_days.get(user_day, "")

#         if jours_open and user_day_fr.capitalize() not in jours_open:
#             return f"🚫 Blane is closed on {user_day}. Open days: {', '.join(jours_open)}"

#         if blane_time_type == "time":
#             heure_debut = parse_time_only(blane["heure_debut"])
#             heure_fin = parse_time_only(blane["heure_fin"])
#             slot_time = datetime.strptime(time, "%H:%M").time()

#             if not heure_debut or not heure_fin:
#                 return f"❌ Invalid opening/closing time format in blane."

#             interval = int(blane["intervale_reservation"])
#             current = datetime.combine(datetime.today(), heure_debut)
#             end = datetime.combine(datetime.today(), heure_fin)
#             valid_slots = []

#             while current <= end:
#                 valid_slots.append(current.strftime("%H:%M"))
#                 current += timedelta(minutes=interval)

#             if time not in valid_slots:
#                 return f"🕓 Invalid slot. Valid slots: {', '.join(valid_slots)}"

#         else:
#             start = parse_datetime(blane.get("start_date"))
#             end = parse_datetime(blane.get("expiration_date"))
#             user_date = datetime.strptime(date, "%Y-%m-%d")
#             user_end_date = datetime.strptime(end_date, "%Y-%m-%d")

#             if not start or not end:
#                 return f"❌ Invalid start or expiration date format in blane."

#             if not (start.date() <= user_date.date() <= end.date()):
#                 return f"❌ Start date must be within {start.date()} to {end.date()}"

#             if not (start.date() <= user_end_date.date() <= end.date()):
#                 return f"❌ End date must be within {start.date()} to {end.date()}"

#     # Step 6: Build Payload
#     payload = {
#         "blane_id": blane_id,
#         "name": name,
#         "email": email,
#         "phone": phone,
#         "city": city,
#         "date": date,
#         "end_date": end_date,
#         "time": time,
#         "comments": comments,
#         "quantity": quantity,
#         "number_persons": number_persons,
#         "status": "pending",
#         "total_price": total_price - partiel_price,
#         "payment_method": "cash",
#         "partiel_price": partiel_price
#     }
#     print(payload)
#     # Step 7: Send Reservation Request
#     try:
#         res = httpx.post(f"{BASEURLBACK}/reservations", headers=headers, json=payload)
#         res.raise_for_status()
#         reservation = res.json()
#         return f"✅ Reservation successful! Reservation Number: {reservation.get('reservation_number')}"
#     except Exception as e:
#         return f"❌ Error creating reservation: {str(e)}"


# @tool("list_reservations")
# def list_reservations(email: str) -> str:
#     """
#     Get the list of the authenticated user's reservations.
#     Requires user's email.
#     """

#     token = get_token()
#     if not token:
#         return "❌ Failed to retrieve token."

#     url = f"{BASEURLBACK}/reservations?email={email}"
#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json"
#     }

#     response = requests.get(url, headers=headers)
#     print(response)

#     if response.status_code != 200:
#         return f"❌ Failed to fetch reservations: {response.text}"

#     data = response.json()["data"]
#     if not data:
#         return "📭 You have no reservations at the moment."

#     return data
    
#     # message = "📋 Your Reservations:\n"
#     # for res in data:
#     #     message += f"- Ref: {res['NUM_RES']} | Blane ID: {res['blane_id']} | {res['date']} at {res['time']} ({res['status']})\n"

#     # return message.strip()

district_map = {
    "anfa": [
        "bourgogne",
        "sidi belyout (centre ville, médina)",
        "maârif",
        "ain diab (corniche)",
        "gauthier",
        "racine",
        "palmier",
        "triangle d’or",
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
        "roches noires (belvédère)"
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
    "moulay rachid – ben m’sick": [
        "moulay rachid",
        "sidi othmane",
        "ben m’sick",
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
    if not category:
        return True
    c = category.strip().lower()
    text = f"{name} {description}".lower()
    keywords = {
        "restaurant": ["restaurant", "resto", "food", "café", "cafe", "diner", "brunch"],
        "spa": ["spa", "massage", "hammam", "wellness", "soin"],
        "activity": ["activity", "activité", "escape", "kart", "cinema", "cinéma", "bowling", "paintball"],
    }.get(c, [c])
    return any(k in text for k in keywords)


@tool("Search_blanes_by_location")
def search_blanes_by_location(district: str, sub_district: str = "", category: str = "", city: str = "", start: int = 1, offset: int = 10) -> str:
    """
    Retrieve blanes by location and optional category/city. Titles only + price (if available).
    - Prioritize sub-district matches first, then other sub-districts of district.
    - Supports pagination via start/offset (default 1, 10).
    """
    token = get_token()
    if not token:
        return "❌ Failed to retrieve token. Please try again later."

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    params = {
        "status": "active",
        "sort_by": "created_at",
        "sort_order": "desc",
        "pagination_size": 200
    }

    try:
        response = httpx.get(f"{BASEURLBACK}/blanes", headers=headers, params=params)
        response.raise_for_status()
        blanes = response.json().get("data", [])
    except Exception as e:
        return f"❌ Error fetching blanes: {e}"

    district_lower = district.lower().strip()
    sub_district_lower = sub_district.lower().strip()
    city_lower = city.lower().strip()

    # Get all sub-districts in the specified district
    all_subs_in_district = district_map.get(district_lower, [])
    all_subs_in_district_cleaned = [s.lower() for s in all_subs_in_district]

    prioritized: list[dict] = []
    secondary: list[dict] = []

    for blane in blanes:
        name = blane.get("name", "")
        desc = (blane.get("description") or "")
        this_city = (blane.get("city") or "").lower().strip()

        if city_lower and city_lower != this_city:
            continue

        if not _matches_category(name, desc, category):
            continue

        in_sub = False
        in_district = False
        content_lower = f"{name} {desc}".lower()

        if sub_district_lower and sub_district_lower in content_lower:
            in_sub = True
        else:
            for sd in all_subs_in_district_cleaned:
                if sd in content_lower:
                    in_district = True
                    break

        if in_sub:
            prioritized.append(blane)
        elif in_district or not sub_district_lower:
            secondary.append(blane)

    ordered = prioritized + [b for b in secondary if b not in prioritized]
    total_matches = len(ordered)

    if total_matches == 0:
        return f"❌ No blanes found in district *{district}* or sub-district *{sub_district}*."

    # Pagination normalization
    if start < 1:
        start = 1
    if offset < 1:
        offset = 10
    end = min(start - 1 + offset, total_matches)
    if start > total_matches:
        return f"❌ Start position {start} is beyond available results. Total: {total_matches}"

    # Slice
    slice_items = ordered[start - 1:end]

    # Build output list
    lines = ["Here are some options:"]
    for idx, blane in enumerate(slice_items, start=start):
        name = blane.get("name", "Unknown")
        price = blane.get("price_current")
        if price:
            lines.append(f"{idx} - {name} — {price} Dhs")
        else:
            lines.append(f"{idx} - {name}")

    # Next prompt
    if end < total_matches:
        lines.append("\nWant more?\nButtons: [Show 10 more] [See details]")
    else:
        lines.append("\nThat’s all in this district. Want me to suggest blanes in another district?")

    return "\n".join(lines)


# @tool("Search_blanes_by_location")
# def search_blanes_by_location(district: str, sub_district: str = "") -> str:
#     """
#     Retrieves blanes based on sub-district first. If fewer than 3 are found,
#     falls back to district-level matching and informs the user accordingly.
#     """
#     token = get_token()
#     if not token:
#         return "❌ Failed to retrieve token. Please try again later."

#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json"
#     }

#     params = {
#         "status": "active",
#         "sort_by": "created_at",
#         "sort_order": "desc",
#         "pagination_size": 100
#     }

#     try:
#         response = httpx.get(f"{BASEURLBACK}/blanes", headers=headers, params=params)
#         response.raise_for_status()
#         blanes = response.json().get("data", [])
#     except Exception as e:
#         return f"❌ Error fetching blanes: {e}"

#     district_lower = district.lower()
#     sub_district_lower = sub_district.lower()

#     # Step 1: Filter for sub-district matches
#     sub_matches = []
#     for blane in blanes:
#         desc = (blane.get("description") or "").lower()
#         if district_lower in desc and sub_district_lower in desc:
#             sub_matches.append(blane["id"])

#     # Step 2: If less than 3, add more from district-level
#     district_matches = sub_matches.copy()
#     if len(sub_matches) < 3:
#         for blane in blanes:
#             desc = (blane.get("description") or "").lower()
#             if district_lower in desc and blane["id"] not in district_matches:
#                 district_matches.append(blane["id"])

#     # Step 3: Prepare results
#     if not district_matches:
#         return f"❌ No blanes found in district *{district}* or sub-district *{sub_district}*."

#     # Step 4: Generate summary message
#     sub_count = len(sub_matches)
#     district_only_count = len(district_matches) - sub_count
#     total = len(district_matches)

#     if sub_count == 0:
#         intro_msg = f"ℹ️ I couldn't find any blanes in *{sub_district}*, but I did find {district_only_count} in *{district}*."
#     elif sub_count < 3:
#         intro_msg = f"✅ I found {sub_count} blane(s) in *{sub_district}*, and {district_only_count} more in *{district}*."
#     else:
#         intro_msg = f"✅ I found {sub_count} blane(s) in *{sub_district}*."

#     # Step 5: Fetch and list blane info
#     result_msgs = []
#     for blane_id in district_matches:
#         info = get_blane_info.invoke({"blane_id": blane_id})
#         result_msgs.append(info)

#     return intro_msg + "\n\n" + "\n\n".join(result_msgs)


# @tool("create_reservation")
# def create_reservation(session_id: str, blane_id: int, name: str, email: str, phone: str, city: str, date: str, end_date: str, time: str, quantity: int, number_persons: int, comments: str = "") -> str:
#     """
#     Handles reservation creation for:
#     - Reservation Blanes (daily and hourly)
#     - Order Blanes (digital and physical)
#     """
#     from datetime import datetime, timedelta
#     import httpx

#     def parse_datetime(date_str):
#         for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S", "%H:%M:%S"):
#             try:
#                 return datetime.strptime(date_str, fmt)
#             except ValueError:
#                 continue
#         return None

#     def parse_time_only(time_str):
#         for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%H:%M:%S"):
#             try:
#                 return datetime.strptime(time_str, fmt).time()
#             except ValueError:
#                 continue
#         return None

#     token = get_token()
#     if not token:
#         return "❌ Failed to retrieve token."

#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json"
#     }

#     # Step 1: Get blane info
#     try:
#         res = httpx.get(f"{BASEURLBACK}/blanes", headers=headers)
#         res.raise_for_status()
#         blane = next((b for b in res.json()["data"] if b["id"] == blane_id), None)
#         if not blane:
#             return f"❌ Blane with ID {blane_id} not found."
#     except Exception as e:
#         return f"❌ Error fetching blane: {e}"

#     # Step 2: Calculate Total Cost
#     base_price = float(blane.get("price_current", 0))
#     total_price = base_price * quantity

#     # Step 3: Add delivery cost if order and physical
#     if blane["type"] == "order" and not blane.get("is_digital"):
#         if blane.get("city") != city:
#             total_price += float(blane.get("livraison_out_city", 0))
#         else:
#             total_price += float(blane.get("livraison_in_city", 0))

#     # Step 4: Handle partiel payments
#     partiel_price = 0
#     if blane.get("partiel") and blane.get("partiel_field"):
#         percent = float(blane["partiel_field"])
#         partiel_price = round((percent / 100) * total_price)

#     english_to_french_days = {
#         "Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi",
#         "Thursday": "Jeudi", "Friday": "Vendredi", "Saturday": "Samedi", "Sunday": "Dimanche"
#     }
#     current_date = datetime.now().strftime("%Y-%m-%d")
#     if date < current_date:
#         return f"❌ Invalid reservation date: {date}. Please choose a future date."


#     # Step 5: Validate time/date based on type
#     if blane["type"] == "reservation":
#         jours_open = blane.get("jours_creneaux", [])
#         user_day = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
#         user_day_fr = english_to_french_days.get(user_day, "")

#         if user_day_fr.capitalize() not in jours_open:
#             return f"🚫 Blane is closed on {user_day}. Open days: {', '.join(jours_open)}"

#         if blane["type_time"] == "time":
#             heure_debut = parse_time_only(blane["heure_debut"])
#             heure_fin = parse_time_only(blane["heure_fin"])
#             slot_time = datetime.strptime(time, "%H:%M").time()

#             if not heure_debut or not heure_fin:
#                 return f"❌ Invalid opening/closing time format in blane."

#             interval = int(blane["intervale_reservation"])
#             current = datetime.combine(datetime.today(), heure_debut)
#             end = datetime.combine(datetime.today(), heure_fin)
#             valid_slots = []

#             while current <= end:
#                 valid_slots.append(current.strftime("%H:%M"))
#                 current += timedelta(minutes=interval)

#             if time not in valid_slots:
#                 return f"🕓 Invalid slot. Valid slots: {', '.join(valid_slots)}"

#         else:  # Daily
#             start = parse_datetime(blane.get("start_date"))
#             end = parse_datetime(blane.get("expiration_date"))
#             user_date = datetime.strptime(date, "%Y-%m-%d")
#             user_end_date = datetime.strptime(end_date, "%Y-%m-%d")

#             if not start or not end:
#                 return f"❌ Invalid start or expiration date format in blane."

#             if not (start.date() <= user_date.date() <= end.date()):
#                 return f"❌ Start date must be within {start.date()} to {end.date()}"

#             if not (start.date() <= user_end_date.date() <= end.date()):
#                 return f"❌ End date must be within {start.date()} to {end.date()}"

#     # Step 6: Build Payload

#     print(blane_id, name, email, phone, city, date, end_date, time, comments, quantity, number_persons, total_price, partiel_price)

#     payload = {
#         "blane_id": blane_id,
#         "name": name,
#         "email": email,
#         "phone": phone,
#         "city": city,
#         "date": date,
#         "end_date": end_date,
#         "time": time,
#         "comments": comments,
#         "quantity": quantity,
#         "number_persons": number_persons,
#         "status": "pending",
#         "total_price": total_price - partiel_price,
#         "payment_method": "cash",
#         "partiel_price": partiel_price
#     }

#     # Step 7: Send Reservation Request
#     try:
#         res = httpx.post(f"{BASEURLBACK}/reservations", headers=headers, json=payload)
#         res.raise_for_status()
#         reservation = res.json()
#         return f"✅ Reservation successful! Reservation Number: {reservation.get('reservation_number')}"
#     except Exception as e:
#         return f"❌ Error creating reservation: {str(e)}"



# @tool("list_reservations")
# def list_reservations(email: str) -> str:
#     """
#     Get the list of the authenticated user's reservations.
#     Requires user's email.
#     """
#     client_id = get_client_id(email)
#     url = f"{BASEURLFRONT}/reservations"
#     headers = {
#         "Content-Type": "application/json"
#     }
#     params = {
#         "include": "blane",
#         "sort_by": "date",
#         "sort_order": "asc"
#     }
#     payload = {
#         "email": email
#     }

#     response = requests.get(url, json=payload, headers=headers, params=params)

#     if response.status_code != 200:
#         return f"❌ Failed to fetch reservations: {response.text}"

#     data = response.json()["data"]
#     if not data:
#         return "📭 You have no reservations at the moment."

#     message = "📋 Your Reservations:\n"
#     for res in data:
#         message += f"- Ref: {res['NUM_RES']} | Blane ID: {res['blane_id']} | {res['date']} at {res['time']} ({res['status']})\n"

#     return message.strip()

# @tool("blanes_info")
# def get_blane_info(blane_id: int):
#     """
#     Requires blane_id.
#     Returns blane info.
#     """
#     url = f"{BASEURLFRONT}/blanes"

#     headers = {
#         "Content-Type": "application/json"
#     }

#     params = {
#         "status": "active",
#         "sort_by": "created_at",
#         "sort_order": "desc",
#         "pagination_size": 10  # or any size you want
#     }

#     try:
#         response = httpx.get(url, headers=headers, params=params)
#         response.raise_for_status()
#         blanes = response.json().get("data", [])
#         print(blanes)

#         if not blanes:
#             return "No blanes found."

#         output = []
#         for i, blane in enumerate(blanes, start=1):
#             if blane_id == blane['id']:
#                 return blane

#         return None

#     except httpx.HTTPStatusError as e:
#         return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
#     except Exception as e:
#         return f"❌ Error fetching blanes: {str(e)}"

# def get_total_price(blane_id: int):
#     url = f"{BASEURLFRONT}/blanes"

#     headers = {
#         "Content-Type": "application/json"
#     }

#     params = {
#         "status": "active",
#         "sort_by": "created_at",
#         "sort_order": "desc",
#         "pagination_size": 10  # or any size you want
#     }

#     try:
#         response = httpx.get(url, headers=headers, params=params)
#         response.raise_for_status()
#         blanes = response.json().get("data", [])
#         print(blanes)

#         if not blanes:
#             return "No blanes found."

#         output = []
#         for i, blane in enumerate(blanes, start=1):
#             if blane_id == blane['id']:
#                 return blane['price_current']

#         return None

#     except httpx.HTTPStatusError as e:
#         return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
#     except Exception as e:
#         return f"❌ Error fetching blanes: {str(e)}"

# def set_client_id(session_id: str, client_id: int) -> str:
#     """
#     Associates client_id with a session.
#     """
#     with SessionLocal() as db:
#         # Fetch the session
#         session = db.query(Session).filter(Session.id == session_id).first()
#         if not session:
#             return f"Session {session_id} not found."

#         # Set client_email and commit
#         session.client_id = client_id
#         db.commit()

#     return f"Set {client_id} for session {session_id}"

# def get_client_id(client_email: str) -> str:
#     """
#     gets client_id associated with client_email
#     """
#     client_id = None
#     with SessionLocal() as db:
#         # Fetch the session
#         session = db.query(Session).filter(Session.client_email == client_email).first()
#         if not session:
#             return f"Email {client_email} not found."

#         # Set client_email and commit
#         client_id = session.client_id

#     return client_id


# @tool("create_reservation")
# def create_reservation(session_id: str, blane_id: int, name: str, email:str, phone: str, city: str, date: str, end_date: str, time: str, quantity: int, number_persons: int, comments: str = "") -> str:
#     """
#     Create a new reservation for a blane.
#     Requires blane_id, user's name, email, phone, city of booking, date of booking, end_date, time, comments (if any), quantity of blanes to be booked, number of persons, payment_method
#     """
#     status: str = "confirmed"
#     payment_method: str = "cash"
#     url = f"{BASEURLFRONT}/reservations"
#     headers = {
#         "Content-Type": "application/json"
#     }
#     total_price = get_total_price(blane_id)
#     print(total_price)
#     if total_price is not None:
#         pass
#     else:
#         return "Blane not found"
#     print("hello")
#     payload = {
#         "blane_id": blane_id,
#         "name": name,
#         "email": email,
#         "phone": phone,
#         "city": city,
#         "date": date,
#         "end_date": end_date,
#         "time": time,
#         "comments": comments,
#         "quantity": quantity,
#         "number_persons": number_persons,
#         "status": status,
#         "total_price": total_price,
#         "payment_method": payment_method,
#         "partiel_price": 0
#     }

#     response = requests.post(url, json=payload, headers=headers)

#     if response.status_code == 201:
#         data = response.json()["data"]
#         # set_client_id(session_id, data['customer']['id'])
#         return f"🎉 Reservation confirmed!\nRef: {data}"
#         # return f"🎉 Reservation confirmed!\nRef: {data['NUM_RES']}\nDate: {data['date']}\nTime: {data['time']}"
#     else:
#         return f"❌ Failed to create reservation: {response.text}"