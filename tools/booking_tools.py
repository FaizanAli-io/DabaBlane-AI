import os
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
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


@tool("create_reservation_for_client")
def create_reservation_for_client(
    client_name: str,
    client_whatsapp: str,
    client_email: str,
    hotel_name: str,
    no_of_reservations: int,
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
        "Nom Client": client_name,
        "Tel Whatsapp Client": client_whatsapp,
        "Email Client": client_email,
        "jour de booking": datetime.now(timezone.utc).isoformat(),
        "Nom du commerce": hotel_name,
        "Qté bookée": no_of_reservations,
        "Reservation Type": "Instante",
        "Réservation Statut": "Client Confirmed",
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

    return "\n".join(lines)
