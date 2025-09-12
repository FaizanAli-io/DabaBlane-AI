import httpx
import requests
from typing import Dict, Any, List
from datetime import datetime, date, time, timedelta

from langchain.tools import tool
from app.database import SessionLocal
from app.chatbot.models import Session

from .config import BASEURLBACK, BASEURLFRONT

from .utils import (
    get_token,
    format_date,
    parse_datetime,
    parse_time_only,
)


# -----------------------------
# Helpers
# -----------------------------


def get_auth_headers() -> Dict[str, str]:
    token = get_token()
    if not token:
        raise ValueError("Failed to retrieve token")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def safe_json_get(resp: httpx.Response) -> Dict[str, Any]:
    try:
        return resp.json()
    except Exception:
        return {"error": resp.text}


def fetch_blane(blane_id: int) -> Dict[str, Any]:
    headers = get_auth_headers()
    url = f"{BASEURLBACK}/blanes/{blane_id}"
    resp = httpx.get(url, headers=headers)
    resp.raise_for_status()
    data = safe_json_get(resp)
    blane = data.get("data")
    if not blane:
        raise ValueError(f"Blane with ID {blane_id} not found")
    return blane


# -----------------------------
# Date / Time helpers
# -----------------------------


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_time(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


def generate_time_slots(start_t: time, end_t: time, interval_minutes: int) -> List[str]:
    slots = []
    cur = datetime.combine(datetime.today(), start_t)
    end_dt = datetime.combine(datetime.today(), end_t)
    if interval_minutes <= 0:
        raise ValueError("Interval must be positive")
    while cur < end_dt:
        slots.append(cur.strftime("%H:%M"))
        cur += timedelta(minutes=interval_minutes)
    return slots


def is_day_open(blane: Dict[str, Any], user_date: date) -> bool:
    jours_open = blane.get("jours_creneaux") or []
    if not jours_open:
        return True
    # convert english weekday to french as in original
    weekday_en = user_date.strftime("%A")
    mapping = {
        "Monday": "Lundi",
        "Tuesday": "Mardi",
        "Wednesday": "Mercredi",
        "Thursday": "Jeudi",
        "Friday": "Vendredi",
        "Saturday": "Samedi",
        "Sunday": "Dimanche",
    }
    return mapping.get(weekday_en, "") in jours_open


# -----------------------------
# Pricing & Payment
# -----------------------------


def calculate_pricing(
    blane: Dict[str, Any], city: str, quantity: int
) -> Dict[str, Any]:
    base_price = 0.0
    try:
        base_price = float(blane.get("price_current", 0) or 0)
    except Exception:
        base_price = 0.0

    qty = max(1, int(quantity or 1))
    total = base_price * qty

    delivery_cost = 0.0
    if blane.get("type") == "order" and not blane.get("is_digital"):
        try:
            if blane.get("city") != city:
                delivery_cost = float(blane.get("livraison_out_city", 0) or 0)
            else:
                delivery_cost = float(blane.get("livraison_in_city", 0) or 0)
        except Exception:
            delivery_cost = 0.0
        total += delivery_cost

    supports_partiel = bool(blane.get("partiel"))
    supports_online = bool(blane.get("online"))
    supports_cash = bool(blane.get("cash"))

    if supports_partiel:
        payment_route = "partiel"
    elif supports_online:
        payment_route = "online"
    elif supports_cash:
        payment_route = "cash"
    else:
        payment_route = "cash"

    partiel_price = 0
    partiel_percent = None
    if payment_route == "partiel" and blane.get("partiel_field"):
        try:
            partiel_percent = float(blane.get("partiel_field"))
            partiel_price = round((partiel_percent / 100.0) * total)
        except Exception:
            partiel_price = 0

    return {
        "base_price": base_price,
        "quantity": qty,
        "total": total,
        "delivery_cost": delivery_cost,
        "payment_route": payment_route,
        "partiel_price": partiel_price,
        "partiel_percent": partiel_percent,
    }


# -----------------------------
# Prompt builder
# -----------------------------


def build_reservation_prompt(blane: Dict[str, Any]) -> str:
    name = blane.get("name", "Unknown")
    type_time = blane.get("type_time")
    is_reservation = blane.get("type") == "reservation"
    is_order = blane.get("type") == "order"

    start = format_date(blane.get("start_date", ""))
    end = format_date(blane.get("expiration_date", ""))
    date_range = f"{start} to {end}" if start and end else "Unknown"

    lines: List[str] = [
        f"To proceed with your reservation for the blane *{name}*, I need the following details:\n"
    ]

    # Base fields (1-4)
    lines.append("*1. User Name*:")
    lines.append("*2. Email*:")
    lines.append("*3. Phone Number*:")
    lines.append("*4. City*:")

    if is_order:
        lines.append("*5. Quantity*: (How many units?)")
        lines.append("*6. Delivery Address*: (Place where order has to be delivered)")
        lines.append("*7. Comments*: (Any special instructions?)")

    elif is_reservation and type_time == "time":
        slots = "Unknown"
        try:
            heure_debut_str = blane.get("heure_debut")
            heure_fin_str = blane.get("heure_fin")
            interval = int(blane.get("intervale_reservation", 0) or 0)
            parsed = None
            for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%H:%M:%S", "%H:%M"):
                try:
                    sd = datetime.strptime(heure_debut_str, fmt).time()
                    ed = datetime.strptime(heure_fin_str, fmt).time()
                    parsed = (sd, ed)
                    break
                except Exception:
                    continue
            if parsed and interval > 0:
                slots = ", ".join(generate_time_slots(parsed[0], parsed[1], interval))
        except Exception:
            slots = "Invalid time format"

        lines.append(f"*5. Date*: (Available: {date_range}) Date Format: YYYY-MM-DD")
        lines.append(f"*6. Time*: (Available slots: {slots}) Time Format: HH:MM")
        lines.append(f"*7. Quantity*: (How many units?)")
        lines.append(f"*8. Number of Persons*: (People attending)")
        lines.append(f"*9. Comments*: (Any requests?)")

    elif is_reservation and type_time == "date":
        lines.append(f"*5. Start Date*: (Between {date_range}) Date Format: YYYY-MM-DD")
        lines.append(f"*6. End Date*: (Between {date_range}) Date Format: YYYY-MM-DD")
        lines.append(f"*7. Quantity*: (How many units?)")
        lines.append(f"*8. Number of Persons*: (People attending)")
        lines.append(f"*9. Comments*: (Any requests?)")

    return "\n".join(lines).strip()


# -----------------------------
# Tool implementations
# -----------------------------


@tool("get_available_time_slots")
def get_available_time_slots(blane_id: int, date: str) -> str:
    """
    Retrieve available time slots for a given reservation-type blane on a specific date.

    Parameters:
        blane_id (int): The ID of the blane to check availability for.
        date (str): The date (YYYY-MM-DD) to fetch available slots.

    Returns:
        str: A formatted string listing available time slots with remaining capacity,
             or an error message if none are available or an issue occurs.
    """
    try:
        blane = fetch_blane(blane_id)
    except ValueError as e:
        return f"❌ {str(e)}"
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

    if blane.get("type") != "reservation" or blane.get("type_time") != "time":
        return "❌ Unsupported reservation type returned by the API."

    slug = blane.get("slug")
    if not slug:
        return "❌ Could not find slug for this blane."

    try:
        headers = get_auth_headers()
        slots_url = f"{BASEURLFRONT}/blanes/{slug}/available-time-slots"
        resp = httpx.get(slots_url, headers=headers, params={"date": date})
        resp.raise_for_status()
        data = safe_json_get(resp)
        if data.get("type") != "time":
            return "❌ Unsupported reservation type returned by the API. Try get_available_periods instead."

        time_slots = data.get("data", [])
        available_slots = [
            f"- {s['time']} → {s.get('remainingCapacity', 0)} spots"
            for s in time_slots
            if s.get("available")
        ]
        if not available_slots:
            return f"No available time slots for '{blane.get('name')}' on {date}."

        output = [
            f"🗓 Available Time Slots for '{blane.get('name')}' on {date}:"
        ] + available_slots
        return "\n".join(output)

    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except ValueError as e:
        return f"❌ {str(e)}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


@tool("get_available_periods")
def get_available_periods(blane_id: int) -> str:
    """
    Retrieve available reservation periods (date-based) for a given blane.

    Parameters:
        blane_id (int): The ID of the blane to check available periods for.

    Returns:
        str: A formatted string listing available periods with remaining capacity,
             or an error message if none are available or an issue occurs.
    """
    try:
        blane = fetch_blane(blane_id)
    except ValueError as e:
        return f"❌ {str(e)}"
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

    if blane.get("type") != "reservation" or blane.get("type_time") != "date":
        return "❌ Unsupported reservation type returned by the API. Try get_available_time_slots instead."

    slug = blane.get("slug")
    if not slug:
        return "❌ Could not find slug for this blane."

    try:
        headers = get_auth_headers()
        front_url = f"{BASEURLFRONT}/blanes/{slug}"
        resp = httpx.get(front_url, headers=headers)
        resp.raise_for_status()
        data = safe_json_get(resp)
        detailed = data.get("data", {})
        available_periods = [
            p for p in detailed.get("available_periods", []) if p.get("available")
        ]
        if not available_periods:
            return f"No available periods found for '{blane.get('name')}'."

        lines = [f"📅 Available Periods for '{blane.get('name')}':"]
        for p in available_periods:
            lines.append(
                f"- {p.get('period_name')} → {p.get('remainingCapacity', 0)} spots"
            )
        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"❌ Error fetching periods: {str(e)}"


@tool("before_create_reservation")
def prepare_reservation_prompt(blane_id: int) -> str:
    """
    Prepare a booking information prompt for a specific blane before creating a reservation.

    Parameters:
        blane_id (int): The ID of the blane to prepare a reservation prompt for.

    Returns:
        str: A formatted reservation prompt with details about the blane,
             or an error message if the blane could not be fetched.
    """
    try:
        blane = fetch_blane(blane_id)
    except Exception as e:
        return f"❌ Error fetching blane: {e}"

    return build_reservation_prompt(blane)


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
    comments: str = "N/A",
) -> str:
    """
    Create a reservation or order for a specific blane, validating session, client info,
    and reservation constraints (dates, times, delivery address, etc.).

    Parameters:
        session_id (str): The ID of the client session to associate with the booking.
        blane_id (int): The ID of the blane to reserve or order.
        name (str): Client's name. Default: "N/A".
        email (str): Client's email. Default: "N/A".
        phone (str): Client's phone number. Default: "N/A".
        city (str): City where the reservation or order applies. Default: "N/A".
        date (str): Reservation date (YYYY-MM-DD). Default: "N/A".
        end_date (str): End date for multi-day reservations. Default: "N/A".
        time (str): Reservation time (HH:MM). Default: "N/A".
        quantity (int): Number of units reserved or ordered. Default: 1.
        number_persons (int): Number of persons for the reservation. Default: 1.
        delivery_address (str): Address for delivery (orders only). Default: "N/A".
        comments (str): Optional notes for the booking. Default: "N/A".

    Returns:
        str: A success message with payment information if applicable,
             or an error message if creation fails.
    """
    try:
        blane = fetch_blane(blane_id)
    except ValueError as e:
        return f"❌ {str(e)}"
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"❌ Error fetching blane: {e}"

    db = SessionLocal()
    try:
        session = db.query(Session).filter_by(id=session_id).first()
        if not session:
            return f"❌ Session with ID {session_id} not found."

        current_email = None
        if email and email != "N/A" and email.strip():
            current_email = email.strip()
            if not session.client_email:
                session.client_email = current_email
                db.commit()
        elif session.client_email and session.client_email.strip():
            current_email = session.client_email.strip()

        if not current_email:
            return "📧 Please provide your email address to create the reservation. I need this to send you the booking confirmation."

        if "@" not in current_email or "." not in current_email.split("@")[-1]:
            return "❌ Please provide a valid email address format (e.g., user@example.com)."

        pricing = calculate_pricing(blane, city, quantity)

        blane_type = blane.get("type")
        type_time = blane.get("type_time")

        today_date = datetime.today().date()
        if date and date != "N/A":
            try:
                date_obj = parse_date(date)
                if date_obj < today_date:
                    return f"❌ Reservation date {date} must not be in the past."
            except Exception:
                return "❌ Invalid date format. Use YYYY-MM-DD."

        if blane_type == "reservation":
            try:
                user_date = parse_date(date)
            except Exception:
                return "❌ Invalid date format. Use YYYY-MM-DD."

            if not is_day_open(blane, user_date):
                return f"🚫 This blane is closed on {user_date.strftime('%A')}."

            if type_time == "time":
                try:
                    heure_debut = parse_time_only(blane.get("heure_debut"))
                    heure_fin = parse_time_only(blane.get("heure_fin"))
                    interval = int(blane.get("intervale_reservation", 0) or 0)
                    if interval <= 0:
                        return "❌ Invalid interval configured for this blane."
                    valid_slots = generate_time_slots(heure_debut, heure_fin, interval)
                except Exception:
                    return "❌ Error parsing blane time slots."

                try:
                    _ = parse_time(time)
                except Exception:
                    return "❌ Invalid time format. Use HH:MM."

                if time not in valid_slots:
                    return f"🕓 Invalid time. Choose from: {', '.join(valid_slots)}"

            elif type_time == "date":
                try:
                    start_dt = parse_datetime(blane.get("start_date"))
                    end_dt = parse_datetime(blane.get("expiration_date"))
                    user_start = datetime.strptime(date, "%Y-%m-%d")
                    user_end = datetime.strptime(end_date, "%Y-%m-%d")
                    if not (start_dt.date() <= user_start.date() <= end_dt.date()):
                        return f"❌ Start date must be within {start_dt.date()} to {end_dt.date()}"
                    if not (start_dt.date() <= user_end.date() <= end_dt.date()):
                        return f"❌ End date must be within {start_dt.date()} to {end_dt.date()}"
                except Exception:
                    return "❌ Invalid start or end date format."

        if blane_type == "reservation":
            payload = {
                "blane_id": blane_id,
                "name": name,
                "email": current_email,
                "phone": phone,
                "city": city,
                "date": date,
                "end_date": end_date if type_time == "date" else None,
                "time": time if type_time == "time" else None,
                "quantity": quantity,
                "number_persons": number_persons,
                "payment_method": pricing["payment_route"],
                "status": "pending",
                "total_price": pricing["total"] - pricing.get("partiel_price", 0),
                "partiel_price": pricing.get("partiel_price", 0),
                "comments": comments,
            }
        elif blane_type == "order":
            if not delivery_address or delivery_address == "N/A":
                return "📦 Please provide a valid delivery address."
            payload = {
                "blane_id": blane_id,
                "name": name,
                "email": current_email,
                "phone": phone,
                "city": city,
                "delivery_address": delivery_address,
                "quantity": quantity,
                "payment_method": pricing["payment_route"],
                "status": "pending",
                "total_price": pricing["total"] - pricing.get("partiel_price", 0),
                "partiel_price": pricing.get("partiel_price", 0),
                "comments": comments,
            }
        else:
            return "❌ Unknown blane type. Only 'reservation' or 'order' supported."

        try:
            headers = get_auth_headers()
            api_endpoint = (
                f"{BASEURLFRONT}/reservations"
                if blane_type == "reservation"
                else f"{BASEURLFRONT}/orders"
            )
            res = httpx.post(api_endpoint, headers=headers, json=payload)
            res.raise_for_status()
            data = safe_json_get(res)

            if pricing["payment_route"] in ("online", "partiel"):
                reference = None
                nested = data.get("data") if isinstance(data, dict) else None
                if isinstance(nested, dict):
                    reference = nested.get("NUM_RES") or nested.get("NUM_ORD")

                if reference:
                    try:
                        pay_url = f"{BASEURLFRONT}/payment/cmi/initiate"
                        pay_res = httpx.post(
                            pay_url, headers=headers, json={"number": reference}
                        )
                        pay_res.raise_for_status()
                        pay_data = pay_res.json()
                        if pay_data.get("status") and pay_data.get("payment_url"):
                            return f"✅ Created. Ref: {reference}. 💳 Pay here: {pay_data.get('payment_url')}"
                        else:
                            return f"✅ Success! {data}. Payment initiation: {pay_data}"
                    except Exception as e:
                        return f"✅ Success! {data}, but payment link failed: {str(e)}"

            return f"✅ Success! {data}"

        except httpx.HTTPStatusError as e:
            return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
        except Exception as e:
            return f"❌ Error submitting reservation: {str(e)}"

    except Exception as e:
        db.rollback()
        return f"❌ Database error: {str(e)}"
    finally:
        db.close()


@tool("preview_reservation")
def preview_reservation(
    blane_id: int,
    city: str = "N/A",
    date: str = "N/A",
    end_date: str = "N/A",
    time: str = "N/A",
    quantity: int = 1,
    number_persons: int = 1,
    delivery_address: str = "N/A",
) -> str:
    """
    Preview the reservation or order details before confirming,
    including validation of dates, times, and pricing.

    Parameters:
        blane_id (int): The ID of the blane to preview.
        city (str): City where the reservation or order applies. Default: "N/A".
        date (str): Reservation date (YYYY-MM-DD). Default: "N/A".
        end_date (str): End date for multi-day reservations. Default: "N/A".
        time (str): Reservation time (HH:MM). Default: "N/A".
        quantity (int): Number of units reserved or ordered. Default: 1.
        number_persons (int): Number of persons for the reservation. Default: 1.
        delivery_address (str): Address for delivery (orders only). Default: "N/A".

    Returns:
        str: A formatted preview of the booking details,
             or an error message if validation fails.
    """
    try:
        blane = fetch_blane(blane_id)
    except Exception as e:
        return f"❌ Error fetching blane: {e}"

    blane_type = blane.get("type")
    type_time = blane.get("type_time")

    pricing = calculate_pricing(blane, city, quantity)
    total_price = int(pricing.get("total", 0))
    delivery_cost = int(pricing.get("delivery_cost", 0))
    payment_route = pricing.get("payment_route")
    partiel_price = pricing.get("partiel_price", 0)

    try:
        if blane_type == "reservation":
            if type_time == "time":
                if not (date and date != "N/A"):
                    return "❌ Please provide a date (YYYY-MM-DD)."
                datetime.strptime(date, "%Y-%m-%d")
                if not (time and time != "N/A"):
                    return "❌ Please provide a time (HH:MM)."
                datetime.strptime(time, "%H:%M")
            elif type_time == "date":
                if not (date and end_date and date != "N/A" and end_date != "N/A"):
                    return "❌ Please provide start and end dates (YYYY-MM-DD)."
                datetime.strptime(date, "%Y-%m-%d")
                datetime.strptime(end_date, "%Y-%m-%d")
    except Exception:
        return "❌ Invalid date or time format."

    blane_name = blane.get("name", "Unknown")
    lines = [
        "Great. I'll need the booking info.",
        "",
        "Please review:",
        f"- Blane: {blane_name}",
    ]

    if blane_type == "reservation":
        if type_time == "time":
            lines += [f"- Date: {date}", f"- Time: {time}"]
        else:
            lines += [f"- Start Date: {date}", f"- End Date: {end_date}"]
        lines += [f"- Quantity: {quantity}", f"- Persons: {number_persons}"]
    else:
        lines += [f"- Quantity: {quantity}"]
        if delivery_address and delivery_address != "N/A":
            lines.append(f"- Delivery Address: {delivery_address}")

    lines += [
        f"- City: {city}",
        f"- Payment: {'Partial' if payment_route=='partiel' else ('Online' if payment_route=='online' else 'Cash')}",
    ]

    if blane_type == "order" and not blane.get("is_digital"):
        lines.append(f"- Delivery Cost: {delivery_cost} MAD")

    lines.append(f"- Total: {total_price} MAD")
    if payment_route == "partiel" and partiel_price:
        lines.append(f"- Due now (partial): {int(partiel_price)} MAD")
    elif payment_route == "online":
        lines.append(f"- Due now: {int(total_price)} MAD")

    lines += ["", "Confirm booking?", "Buttons: [Confirm] [Edit] [Cancel]"]
    return "\n".join(lines)


@tool("list_reservations")
def list_reservations(email: str) -> Dict[str, Any]:
    """
    List all reservations and orders associated with a given client email.

    Parameters:
        email (str): The client's email to search reservations and orders for.

    Returns:
        dict: A dictionary with two keys:
            - "reservations": List of reservations linked to the email.
            - "orders": List of orders linked to the email.
            May also include "reservations_error" or "orders_error" if API calls fail,
            or "error" if token retrieval or a general error occurs.
    """
    token = None
    try:
        token = get_token()
        if not token:
            return {"error": "❌ Failed to retrieve token."}
    except Exception:
        return {"error": "❌ Failed to retrieve token."}

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    result: Dict[str, Any] = {"reservations": [], "orders": []}

    try:
        res_url = f"{BASEURLBACK}/reservations?email={email}"
        res_response = requests.get(res_url, headers=headers)
        if res_response.status_code == 200:
            result["reservations"] = res_response.json().get("data", [])
        else:
            result["reservations_error"] = res_response.text

        orders_url = f"{BASEURLBACK}/orders?email={email}"
        orders_response = requests.get(orders_url, headers=headers)
        if orders_response.status_code == 200:
            result["orders"] = orders_response.json().get("data", [])
        else:
            result["orders_error"] = orders_response.text

        return result
    except Exception as e:
        return {"error": str(e)}
