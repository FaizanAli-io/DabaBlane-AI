from langchain.tools import tool
import httpx
import requests
from datetime import datetime
from app.chatbot.models import Session
from app.database import SessionLocal
BASEURLFRONT = "https://dbapi.escalarmedia.com/api/front/v1"
BASEURLBACK = "https://dbapi.escalarmedia.com/api/back/v1"

def get_token():

    url = f"https://dbapi.escalarmedia.com/api/login"
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


@tool("list_blanes")
def blanes_list() -> str:
    """
    Lists all active Blanes using the provided token.
    Returns a readable list with name, price, and ID.
    """
    token = get_token()
    if not token:
        return "❌ Failed to retrieve token. Please try again later."
    url = f"{BASEURLBACK}/blanes"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    print(response)
    
    params = {
        "status": "active",
        "sort_by": "created_at",
        "sort_order": "desc",
        "pagination_size": 20 # or any size you want
    }

    try:
        response = httpx.get(url, headers=headers, params=params)
        response.raise_for_status()
        blanes = response.json().get("data", [])

        if not blanes:
            return "No blanes found."

        output = []
        for i, blane in enumerate(blanes, start=1):
            output.append(f"{i}. {blane['name']} — Rs. {blane['price_current']} (ID: {blane['id']})")

        return "\n".join(output)

    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"❌ Error fetching blanes: {str(e)}"


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

        return msg

    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"


@tool("Before_create_reservation")
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
        msg += f"4. *Date*: (Available: {date_range})\n"
        msg += f"5. *Time*: (Available slots: {slots})\n"
        msg += f"6. *Quantity*: (How many slots?)\n"
        msg += f"7. *Number of Persons*: (People attending)\n"
        msg += f"8. *Comments*: (Any requests?)\n"
    elif is_reservation and type_time == "date":
        msg += f"4. *Start Date*: (Between {date_range})\n"
        msg += f"5. *End Date*: (Between {date_range})\n"
        msg += f"6. *Quantity*: \n"
        msg += f"7. *Number of Persons*: (People attending)\n"
        msg += f"8. *Comments*: (Any requests?)\n"

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

    # 🔸 Handle Partial Payments
    partiel_price = 0
    if blane.get("partiel") and blane.get("partiel_field"):
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
            "payment_method": "cash",
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
            "payment_method": "cash",
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

        res = httpx.post(f"{API}", headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
        return f"✅ Success! {data}"
    except Exception as e:
        return f"❌ Error submitting reservation: {str(e)}"


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


@tool("list_reservations")
def list_reservations(email: str) -> str:
    """
    Get the list of the authenticated user's reservations.
    Requires user's email.
    """

    token = get_token()
    if not token:
        return "❌ Failed to retrieve token."

    url = f"{BASEURLBACK}/reservations?email={email}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    print(response)

    if response.status_code != 200:
        return f"❌ Failed to fetch reservations: {response.text}"

    data = response.json()["data"]
    if not data:
        return "📭 You have no reservations at the moment."

    return data
    
    # message = "📋 Your Reservations:\n"
    # for res in data:
    #     message += f"- Ref: {res['NUM_RES']} | Blane ID: {res['blane_id']} | {res['date']} at {res['time']} ({res['status']})\n"

    # return message.strip()


@tool("Search_blanes_by_location")
def search_blanes_by_location(district: str, sub_district: str = "") -> str:
    """
    Retrieves blanes based on sub-district first. If fewer than 3 are found,
    falls back to district-level matching and informs the user accordingly.
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
        "pagination_size": 100
    }

    try:
        response = httpx.get(f"{BASEURLBACK}/blanes", headers=headers, params=params)
        response.raise_for_status()
        blanes = response.json().get("data", [])
    except Exception as e:
        return f"❌ Error fetching blanes: {e}"

    district_lower = district.lower()
    sub_district_lower = sub_district.lower()

    # Step 1: Filter for sub-district matches
    sub_matches = []
    for blane in blanes:
        desc = (blane.get("description") or "").lower()
        if district_lower in desc and sub_district_lower in desc:
            sub_matches.append(blane["id"])

    # Step 2: If less than 3, add more from district-level
    district_matches = sub_matches.copy()
    if len(sub_matches) < 3:
        for blane in blanes:
            desc = (blane.get("description") or "").lower()
            if district_lower in desc and blane["id"] not in district_matches:
                district_matches.append(blane["id"])

    # Step 3: Prepare results
    if not district_matches:
        return f"❌ No blanes found in district *{district}* or sub-district *{sub_district}*."

    # Step 4: Generate summary message
    sub_count = len(sub_matches)
    district_only_count = len(district_matches) - sub_count
    total = len(district_matches)

    if sub_count == 0:
        intro_msg = f"ℹ️ I couldn't find any blanes in *{sub_district}*, but I did find {district_only_count} in *{district}*."
    elif sub_count < 3:
        intro_msg = f"✅ I found {sub_count} blane(s) in *{sub_district}*, and {district_only_count} more in *{district}*."
    else:
        intro_msg = f"✅ I found {sub_count} blane(s) in *{sub_district}*."

    # Step 5: Fetch and list blane info
    result_msgs = []
    for blane_id in district_matches:
        info = get_blane_info.invoke({"blane_id": blane_id})
        result_msgs.append(info)

    return intro_msg + "\n\n" + "\n\n".join(result_msgs)


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