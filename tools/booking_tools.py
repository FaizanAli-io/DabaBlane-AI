from langchain_core.tools import tool
import requests
import os
from dotenv import load_dotenv
from typing import Optional
from datetime import datetime, timezone

load_dotenv()
BASE_URL = os.getenv("NOCODB_BASE_URL")
TOKEN = os.getenv("NOCODB_API_TOKEN")

headers = {"accept": "application/json", "xc-token": TOKEN}


@tool("check_reservation_by_client")
def check_reservation_by_client(client_email: str) -> str:
    """
    Check if any reservation exists for a specific client email.
    """
    table_id = "mb92g41bhfubow2"  # Booking-Reservation table ID
    url = f"{BASE_URL}/api/v2/tables/{table_id}/records?where=(Email%20Client,eq,{client_email})"

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return f"Failed to fetch data. Status code: {response.status_code}"

    records = response.json().get("list", [])
    if not records:
        return f"No reservations found for {client_email}."

    # Customize the info you want to return
    return f"Found {len(records)} reservation(s) for {client_email}. Example: ID Réservation = {records[0].get('ID Réservation')}"


# final_total_price_incl_tax: Final price including tax (e.g., '1000 MAD').
#         reservation_id: ID of the reservation (e.g., "#RES-QC000000").
# reservation_type: Type of the reservation (default 'Instante').
# reservation_status: Status of the reservation (default 'Client Confirmed').
# ready: Whether it's ready (default True).


@tool("create_reservation_for_client")
def create_reservation_for_client(
    client_name: str,
    client_whatsapp: str,
    client_email: str,
    hotel_name: str,
    no_of_reservations: int,
    # reservation_type: str = "Instante",
    # reservation_status: str = "Client Confirmed",
    # ready: bool = True,
    starting_date_time: str,
    ending_date_time: str,
    **extra_fields,
) -> str:
    """
    Create a new reservation for a client.

    Args:
        client_name: Name of the client.
        client_whatsapp: Client's WhatsApp phone.
        client_email: Client's email.
        hotel_name: Name of the hotel the client want to reserve.
        no_of_reservations: Number of rooms/suits/etc to be reserved/booked.
        starting_date_time: Start of the booking in iso format
        ending_date_time: End of the booking in iso format
        **extra_fields: Additional fields as needed.

    Returns:
        str: Result message from the operation.
    """
    payload = {
        # "ID Réservation": reservation_id,
        "Nom Client": client_name,
        "Tel Whatsapp Client": client_whatsapp,
        "Email Client": client_email,
        "jour de booking": datetime.now(timezone.utc).isoformat(),
        "Nom du commerce": hotel_name,
        "Qté bookée": no_of_reservations,
        # "Prix final total TTC": final_total_price_incl_tax,
        # "Reservation Type": reservation_type or "Instante",
        "Reservation Type": "Instante",
        # "Réservation Statut": reservation_status or "Client Confirmed",
        "Réservation Statut": "Client Confirmed",
        # "Pret?": ready if ready is not None else True,
        "Pret?": True,
        "Créneau de début": starting_date_time,
        "Créneau de fin": ending_date_time,
    }

    payload.update(extra_fields)

    url = f"{BASE_URL}/api/v2/tables/{TABLE_ID}/records"

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return f"✅ Reservation created successfully: {response.json().get('id')}"
    else:
        return f"❌ Failed to create reservation. Status: {response.status_code}, Response: {response.text}"


import requests
from langchain_core.tools import tool

BASE_URL = "https://database.dabablane.com"
TOKEN = "PvRd94S5nqUOtplcdu4ZDq-4O45TGuls72CAekYT"
TABLE_ID = "mb92g41bhfubow2"  # Booking-Reservation
HEADERS = {"xc-token": TOKEN}


@tool
def get_all_reservations() -> str:
    """
    Fetches all reservation records from the Booking-Reservation table.
    Only performs read (SELECT) operations.
    """
    url = f"{BASE_URL}/api/v2/tables/{TABLE_ID}/records?limit=1000"

    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return f"❌ Failed to fetch reservations. Status code: {response.status_code}"

    data = response.json().get("list", [])
    if not data:
        return "ℹ️ No reservations found."

    results = []
    for record in data:
        info = f"Reservation ID: {record.get('ID Réservation')}, Client: {record.get('Nom Client')}, Email: {record.get('Email Client')}, Status: {record.get('Réservation Statut')}, Booking Day: {record.get('jour de booking')}"
        results.append(info)

    return "\n".join(results[:10]) + ("\n...and more." if len(results) > 10 else "")


# import requests
# from langchain_core.tools import tool

# BASE_URL = "https://database.dabablane.com"
# TOKEN = "PvRd94S5nqUOtplcdu4ZDq-4O45TGuls72CAekYT"
# TABLE_ID = "mb92g41bhfubow2"
# HEADERS = {"xc-token": TOKEN}

# @tool
# def check_reservation_by_email(email: str, question: str) -> str:
#     """
#     Checks reservations by filtering rows using the provided email.
#     Responds only using data related to the client's email.
#     """

#     # "Email Client" has a space, must be URL encoded as "Email%20Client"
#     encoded_column = "Email%20Client"
#     url = f"{BASE_URL}/api/v2/tables/{TABLE_ID}/records"
#     params = {"where": f"{encoded_column},eq,{email}"}

#     response = requests.get(url, headers=HEADERS, params=params)
#     if response.status_code != 200:
#         return f"Failed to fetch reservations for {email}. Status: {response.status_code}"

#     data = response.json().get("list", [])
#     if not data:
#         return f"No reservations found for {email}."

#     # Simple response based on a few common questions
#     if "upcoming" in question.lower():
#         upcoming = [
#             r for r in data if r.get("Réservation Statut", "").lower() in ["client confirmed", "pending"]
#         ]
#         if upcoming:
#             r = upcoming[0]
#             return f"Upcoming reservation ID: {r.get('ID Réservation')} on {r.get('jour de booking')}"
#         return "No upcoming reservations found."

#     elif "how many" in question.lower():
#         return f"Total reservations found for {email}: {len(data)}"

#     elif "price" in question.lower():
#         prices = [r.get("Prix final total TTC") for r in data if r.get("Prix final total TTC")]
#         return f"Prices for your bookings: {', '.join(prices)}" if prices else "No price data found."

#     else:
#         # Default fallback: summarize all reservations
#         return f"Found {len(data)} reservations for {email}. Example: ID {data[0].get('ID Réservation')} on {data[0].get('jour de booking')}"


# import requests
# from langchain_core.tools import tool

# BASE_URL = "https://database.dabablane.com"
# TOKEN = "PvRd94S5nqUOtplcdu4ZDq-4O45TGuls72CAekYT"
# TABLE_ID = "mb92g41bhfubow2"  # Booking-Reservation
# HEADERS = {"xc-token": TOKEN}

# @tool
# def authenticate_email(email: str) -> str:
#     """
#     Verifies if the provided email exists in the reservation database.
#     Returns success message if found, otherwise fails authentication.
#     """
#     url = f"{BASE_URL}/api/v2/tables/{TABLE_ID}/records"
#     encoded_column = "Email%20Client"
#     params = {"where": f"{encoded_column},eq,{email}"}

#     response = requests.get(url, headers=HEADERS, params=params)
#     if response.status_code != 200:
#         return f"Error while verifying email. Status code: {response.status_code}"

#     data = response.json().get("list", [])
#     if data:
#         return f"✅ Email verified. Found {len(data)} reservation(s) for {email}."
#     else:
#         return f"❌ Email not found in reservations. Please check and try again."


# ---------------------------------

import requests
from langchain_core.tools import tool
from app.database import SessionLocal
from app.chatbot.models import Session

BASE_URL = "https://database.dabablane.com"
TOKEN = "PvRd94S5nqUOtplcdu4ZDq-4O45TGuls72CAekYT"
HEADERS = {"xc-token": TOKEN}
TABLE_ID = "mb92g41bhfubow2"  # Booking-Reservation table

# from app.chatbot.models import Client, Session
from app.chatbot.models import Session
from app.database import SessionLocal
from datetime import datetime


@tool("is_authenticated")
def is_authenticated(session_id: str) -> str:
    """
    Checks if a session has an associated email.
    Returns the email if authenticated, otherwise asks for an email.
    """
    with SessionLocal() as db:
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            return f"Session {session_id} not found."

        if session.client_email:
            return f"Session {session_id} is authenticated for email: {session.client_email}"
        else:
            return f"Session {session_id} is NOT authenticated. Please provide an email address."


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


@tool("check_reservation_info")
def check_reservation_info(session_id: str, question: str) -> str:
    """
    Answer any reservation-related questions for the authenticated user.
    """

    db = SessionLocal()
    session = db.query(Session).filter_by(id=session_id).first()
    client_email = session.client_email if session else None
    db.close()

    if not client_email:
        return "Please authenticate first by providing your email."

    # Fetch reservations
    url = f"{BASE_URL}/api/v2/tables/{TABLE_ID}/records?where=(Email%20Client,eq,{client_email})"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return "Failed to fetch reservation records."

    reservations = response.json().get("list", [])
    if not reservations:
        return f"No reservations found for {client_email}."

    lines = []
    for r in reservations:
        fields = {
            "ID Réservation": "ID Réservation",
            "Réservation Statut": "Réservation Statut",
            "Pret?": "Pret?",
            "Reservation Type": "Reservation Type",
            "jour de booking": "jour de booking",
            "Créneau de début": "Créneau de début",
            "Créneau de fin": "Créneau de fin",
            "Nom Client": "Nom Client",
            "Tel Whatsapp Client": "Tel Whatsapp Client",
            "Client Conf MSG 1 Time": "Client Conf MSG 1 Time",
            "MSG 1": "MSG 1",
            "Client Conf MSG 2 Time": "Client Conf MSG 2 Time",
            "MSG 2": "MSG 2",
            "MSG 3": "MSG 3",
            "Retailer Conf MSG 1 Time": "Retailer Conf MSG 1 Time",
            "C MSG 1": "C MSG 1",
            "Retailer Conf MSG 2 Time": "Retailer Conf MSG 2 Time",
            "C MSG 2": "C MSG 2",
            "C MSG 3": "C MSG 3",
            "Retailer WA Convo ID": "Retailer WA Convo ID",
            "WA Convo ID": "WA Convo ID",
            "Rappel Client et Retailer": "Rappel Client et Retailer",
            "Google Reviews MSG": "Google Reviews MSG",
            "Google Reviews Rating": "Google Reviews Rating",
            "Nom du commerce": "Nom du commerce",
            "Tel Whatsapp du commerce": "Tel Whatsapp du commerce",
            "Qté bookée": "Qté bookée",
            "Prix final total TTC": "Prix final total TTC",
            "Commentaires": "Commentaires",
            "Offer": "Offer",
            "Paiement": "Paiement",
            "Email Client": "Email Client",
            "Prix final Total avec frais de livraison": "Prix final Total avec frais de livraison",
            "Ville du Commerce": "Ville du Commerce",
            "Ville du client": "Ville du client",
        }

        line_parts = []
        for key, label in fields.items():
            value = r.get(key)
            if value is not None and value != "":
                line_parts.append(f"{label}: {value}")

        line = " | ".join(line_parts)

        lines.append(line)

        # lines.append(f"ID: {r.get('Reservation ID')} | Date: {r.get('Booking Day') or r.get('jour de booking')} | Status: {r.get('Reservation Status')}")
    return "\n".join(lines)

    # # Normalize question
    # q = question.lower()

    # # 1. Total reservations
    # if "how many" in q or "total reservations" in q:
    #     return f"You have {len(reservations)} reservation(s)."

    # # 2. Latest reservation
    # if "latest" in q or "recent" in q:
    #     latest = sorted(reservations, key=lambda r: r.get("CreatedAt", ""), reverse=True)[0]
    #     return f"Latest reservation ID: {latest.get('Reservation ID', 'N/A')}, Status: {latest.get('Reservation Status', 'N/A')}."

    # # 3. Status breakdown
    # if "status" in q:
    #     statuses = {}
    #     for r in reservations:
    #         status = r.get("Reservation Status", "Unknown")
    #         statuses[status] = statuses.get(status, 0) + 1
    #     return "\n".join([f"{s}: {c}" for s, c in statuses.items()])

    # # 4. Total Price
    # if "price" in q or "total price" in q:
    #     prices = [r.get("Final Total Price Including Tax") for r in reservations if r.get("Final Total Price Including Tax")]
    #     return f"Prices found: {', '.join(prices)}" if prices else "No prices found."

    # # 5. Upcoming reservations
    # if "upcoming" in q or "future" in q:
    #     upcoming = [
    #         r for r in reservations
    #         if r.get("Start Slot") and datetime.fromisoformat(r["Start Slot"].replace("Z", "+00:00")) > datetime.utcnow()
    #     ]
    #     return f"You have {len(upcoming)} upcoming reservation(s)."

    # # ✅ 6. Reservation dates
    # if "date" in q or "when" in q or "day" in q:
    #     dates = []
    #     for r in reservations:
    #         date_str = r.get("Booking Day") or r.get("jour de booking")  # handle French/English fields
    #         if date_str:
    #             try:
    #                 dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    #                 dates.append(dt.strftime("%Y-%m-%d"))
    #             except Exception:
    #                 dates.append(date_str)
    #     if dates:
    #         return f"Your reservation dates: {', '.join(dates)}"
    #     else:
    #         return "No reservation dates found."

    # # 7. All details (optional)
    # if "details" in q or "show all" in q:
    #     lines = []
    #     for r in reservations:
    #         lines.append(f"ID: {r.get('Reservation ID')} | Date: {r.get('Booking Day') or r.get('jour de booking')} | Status: {r.get('Reservation Status')}")
    #     return "\n".join(lines)

    # # Default fallback
    # return f"Found {len(reservations)} reservation(s). Try asking for 'status', 'date', 'price', 'latest', or 'upcoming'."
