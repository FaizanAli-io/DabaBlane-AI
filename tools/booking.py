import httpx
from langchain.tools import tool
from typing import Dict, Any, List
from datetime import datetime, date, time, timedelta

from .inputs import ReservationInput

from .config import BASEURLBACK, BASEURLFRONT, AGENT_URL

from .utils import (
    parse_datetime,
    parse_time_only,
    get_auth_headers,
)


# -----------------------------
# Helpers
# -----------------------------


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


def fetch_data(endpoint: str, headers: Dict[str, str]) -> Dict[str, Any]:
    try:
        with httpx.Client(headers=headers, timeout=10.0) as client:
            response = client.get(BASEURLBACK + endpoint)
            if response.status_code == 200:
                return {"data": response.json().get("data", [])}
            return {"error": response.text, "status": response.status_code}
    except Exception as e:
        return {"error": str(e)}


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_time(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


def generate_time_slots(start_t: time, end_t: time, interval: int):
    slots = []
    cur = datetime.combine(datetime.today(), start_t)
    end_dt = datetime.combine(datetime.today(), end_t)
    if interval <= 0:
        raise ValueError("Interval must be positive")
    while cur < end_dt:
        slots.append(cur.strftime("%H:%M"))
        cur += timedelta(minutes=interval)
    return slots


def is_day_open(blane: Dict[str, Any], user_date: date):
    jours_open = blane.get("jours_creneaux")
    if not jours_open:
        return True
    mapping = {
        "Monday": "Lundi",
        "Tuesday": "Mardi",
        "Wednesday": "Mercredi",
        "Thursday": "Jeudi",
        "Friday": "Vendredi",
        "Saturday": "Samedi",
        "Sunday": "Dimanche",
    }
    return mapping.get(user_date.strftime("%A"), "") in jours_open


def get_payment_routes(blane, display):
    return [
        display_name if display else method_name
        for display_name, method_name, supported in [
            ("Paiement sur place", "cash", blane.get("cash")),
            ("Paiement en ligne", "online", blane.get("online")),
            ("Avance en ligne", "partiel", blane.get("partiel")),
        ]
        if supported
    ] or ["cash"]


def get_date_range(blane) -> str:
    start_raw = blane.get("start_date")
    end_raw = blane.get("expiration_date")

    def parse_date(d):
        if not d:
            return None
        try:
            return datetime.strptime(d, "%Y-%m-%d %H:%M:%S").date()
        except ValueError:
            return datetime.strptime(d, "%Y-%m-%d").date()

    start = parse_date(start_raw)
    end = parse_date(end_raw)

    today = date.today()
    if start and start < today:
        start = today

    return f"{start} to {end}" if start and end else "Unknown"


def calculate_pricing(blane: Dict[str, Any], city: str, quantity: int):
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

    payment_routes = get_payment_routes(blane, False)

    partiel_price = 0
    partiel_percent = 0
    if "partiel" in payment_routes and blane.get("partiel_field"):
        try:
            partiel_percent = float(blane.get("partiel_field", 0) or 0)
            partiel_price = round((partiel_percent / 100.0) * total)
        except Exception:
            partiel_price = 0

    return {
        "total": total,
        "quantity": qty,
        "base_price": base_price,
        "delivery_cost": delivery_cost,
        "partiel_price": partiel_price,
        "payment_routes": payment_routes,
        "partiel_percent": partiel_percent,
    }


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
        str: A formatted string listing available time slots with remaining capacity, or an error message if none are available or an issue occurs.
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


@tool("prepare_reservation_prompt")
def prepare_reservation_prompt(blane_id: int) -> str:
    """
    Prepare a booking information prompt for a specific blane before creating a reservation.
    Always invoke this before asking the user for booking details.

    Parameters:
        blane_id (int): The ID of the blane to prepare a reservation prompt for.

    Returns:
        str: A formatted reservation prompt with details about the blane, or an error message if the blane could not be fetched.
    """
    try:
        blane = fetch_blane(blane_id)
    except Exception as e:
        return f"❌ Error fetching blane: {e}"

    # Build reservation prompt
    name = blane.get("name", "Unknown")

    booking_type = blane.get("type")
    type_time = blane.get("type_time")
    is_digital = blane.get("is_digital", False)

    is_order = booking_type == "order"
    is_reservation = booking_type == "reservation"

    payment_routes = get_payment_routes(blane, True)
    payment_routes = "\n\t- ".join(payment_routes)
    date_range = get_date_range(blane)

    lines = [
        f"To proceed with your reservation for the blane *{name} - (ID: {blane_id})*, I need the following details:\n",
        "*Name*:",
        "*Email*:",
        "*Phone Number:* (with country code)",
    ]

    if is_order:
        lines.append("*Quantity*: (How many units?)")
        lines.append("*Comments*: (Any special instructions? Optional)")
        if not is_digital:
            lines.append("*City*: (City for delivery)")
            lines.append("*Delivery Address*: (Full address for delivery)")

    elif is_reservation and type_time == "time":
        slots = "Unknown"
        try:
            heure_fin_str = blane.get("heure_fin")
            heure_debut_str = blane.get("heure_debut")
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

        lines.append(f"*Date*: (Available: {date_range}) Date Format: YYYY-MM-DD")
        lines.append(f"*Time*: (Available slots: {slots}) Time Format: HH:MM")
        lines.append(f"*Quantity*: (How many people attending?)")
        lines.append(f"*Comments*: (Any requests?)")

    elif is_reservation and type_time == "date":
        lines.append(f"*Start Date*: (Between {date_range}) Date Format: YYYY-MM-DD")
        lines.append(f"*End Date*: (Between {date_range}) Date Format: YYYY-MM-DD")
        lines.append(f"*Quantity*: (How many people attending?)")
        lines.append(f"*Comments*: (Any requests?)")

    lines.append("Payment methods available:\n\t- " + payment_routes)
    lines.append("Please specify your preferred payment method when booking.")

    return "\n".join(lines).strip()


@tool("preview_reservation")
def preview_reservation(input: ReservationInput) -> str:
    """
    Preview a reservation or order. Accepts a ReservationInput and returns a formatted summary of the booking details, including validation of dates, times, and pricing.
    """
    data = vars(input)
    blane_id = data.get("blane_id")
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    city = data.get("city")
    quantity = data.get("quantity")
    res_date = data.get("res_date")
    res_time = data.get("res_time")
    end_date = data.get("end_date")
    comments = data.get("comments")
    payment_method = data.get("payment_method")
    delivery_address = data.get("delivery_address")

    try:
        blane = fetch_blane(blane_id)
    except Exception as e:
        return f"❌ Error fetching blane: {e}"

    if not input.is_valid(blane):
        return input.validation_messages

    blane_type = blane.get("type")
    type_time = blane.get("type_time")

    pricing = calculate_pricing(blane, city, quantity)
    total_price = int(pricing.get("total", 0))
    partiel_price = pricing.get("partiel_price")
    delivery_cost = int(pricing.get("delivery_cost", 0))

    try:
        if blane_type == "reservation":
            if type_time == "time":
                if not (res_date and res_date != "N/A"):
                    return "❌ Please provide a date (YYYY-MM-DD)."
                datetime.strptime(res_date, "%Y-%m-%d")
                if not (res_time and res_time != "N/A"):
                    return "❌ Please provide a time (HH:MM)."
                datetime.strptime(res_time, "%H:%M")
            elif type_time == "date":
                if not (
                    res_date and end_date and res_date != "N/A" and end_date != "N/A"
                ):
                    return "❌ Please provide start and end dates (YYYY-MM-DD)."
                datetime.strptime(res_date, "%Y-%m-%d")
                datetime.strptime(end_date, "%Y-%m-%d")
    except Exception:
        return "❌ Invalid date or time format."

    lines = [
        "Please preview the following reservation/order details for "
        + blane.get("name", "Unknown Blane")
        + f" (Blane ID: {blane_id})\n",
        f"Name: {name}",
        f"Email: {email}",
        f"Phone: {phone}",
        f"Comments: {comments}",
        f"Selected Payment: {payment_method}",
        (
            f"Quantity: {quantity}" + "(ou personnes)"
            if blane_type == "reservation"
            else ""
        ),
    ]

    if blane_type == "reservation":
        lines += (
            [f"Date: {res_date}", f"Time: {res_time}"]
            if type_time == "time"
            else [f"Start Date: {res_date}", f"End Date: {end_date}"]
        )
    else:
        lines += [
            *(f"City: {city}" if city and city != "N/A" else []),
            *(
                f"Delivery Address: {delivery_address}"
                if delivery_address and delivery_address != "N/A"
                else []
            ),
        ]

    if blane_type == "order" and not blane.get("is_digital"):
        lines.append(f"Delivery Cost: {delivery_cost} MAD")

    lines.append(f"Total: {total_price} MAD")
    if payment_method == "partiel" and partiel_price:
        lines.append(f"Due now (partial): {int(partiel_price)} MAD")
    elif payment_method == "online":
        lines.append(f"Due now: {int(total_price)} MAD")

    lines += ["\nConfirm booking?", "[Confirm] [Edit] [Cancel]"]
    return "\n".join(lines)


@tool("create_reservation")
def create_reservation(input: ReservationInput) -> str:
    """
    Create a reservation or order. Accepts a ReservationInput and submits it to the backend, validating session, client info, and constraints. Returns success status and payment instructions if applicable.

    INSTRUCTIONS:
    - Don't mention cancellation in your response.
    - After successful booking, always include the following message exactly: Thank you for booking with us! If you have any more questions or need further assistance, just let me know or contact us directly at +212615170064.
    """
    data = vars(input)
    blane_id = data.get("blane_id")
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    city = data.get("city")
    quantity = data.get("quantity")
    res_date = data.get("res_date")
    res_time = data.get("res_time")
    end_date = data.get("end_date")
    comments = data.get("comments")
    payment_method = data.get("payment_method")
    delivery_address = data.get("delivery_address")

    try:
        blane = fetch_blane(blane_id)
    except Exception as e:
        return f"❌ Error fetching blane: {e}"

    if not input.is_valid(blane):
        return input.validation_messages

    pricing = calculate_pricing(blane, city, quantity)

    if payment_method not in pricing["payment_routes"]:
        return f"❌ Unsupported payment method '{payment_method}'. Available: {', '.join(pricing['payment_routes'])}"

    blane_type = blane.get("type")
    type_time = blane.get("type_time")
    is_digital = blane.get("is_digital", False)

    # --- Validation ---
    if blane_type == "reservation":
        if res_date == "N/A":
            return "❌ Reservation requires a date."

        try:
            user_date = parse_date(res_date)
            if user_date < datetime.today().date():
                return f"❌ Reservation date {res_date} must not be in the past."
        except Exception:
            return "❌ Invalid date format. Use YYYY-MM-DD."

        if not is_day_open(blane, user_date):
            return f"🚫 This blane is closed on {user_date.strftime('%A')}."

        if type_time == "time":
            try:
                heure_debut = parse_time_only(blane.get("heure_debut"))
                heure_fin = parse_time_only(blane.get("heure_fin"))
                interval = int(blane.get("intervale_reservation", 0) or 0)
                valid_slots = generate_time_slots(heure_debut, heure_fin, interval)
                if res_time not in valid_slots:
                    return f"🕓 Invalid time. Choose from: {', '.join(valid_slots)}"
            except Exception:
                return "❌ Error parsing blane time slots."

        if type_time == "date":
            try:
                start_dt = parse_datetime(blane.get("start_date"))
                end_dt = parse_datetime(blane.get("expiration_date"))
                user_start = datetime.strptime(res_date, "%Y-%m-%d")
                user_end = datetime.strptime(end_date, "%Y-%m-%d")
                if not (start_dt.date() <= user_start.date() <= end_dt.date()):
                    return f"❌ Start date must be within {start_dt.date()} to {end_dt.date()}"
                if not (start_dt.date() <= user_end.date() <= end_dt.date()):
                    return f"❌ End date must be within {start_dt.date()} to {end_dt.date()}"
            except Exception:
                return "❌ Invalid start or end date format."

    # --- Payload setup ---
    partial_price = pricing.get("partiel_price", 0)

    base_payload = {
        "name": name,
        "city": city,
        "email": email,
        "phone": phone,
        "status": "pending",
        "blane_id": blane_id,
        "comments": comments,
        "quantity": quantity,
        "number_persons": quantity,
        "partiel_price": partial_price,
        "payment_method": payment_method,
        "total_price": pricing["total"] - partial_price,
    }

    payload = {
        **base_payload,
        "date": res_date if blane_type == "reservation" else None,
        "time": res_time if type_time == "time" else None,
        "end_date": end_date if type_time == "date" else None,
        "delivery_address": (
            "Online Service"
            if (blane_type == "order" and is_digital)
            else delivery_address
        ),
    }

    # --- Submit reservation/order ---
    try:
        headers = get_auth_headers()
        api_endpoint = BASEURLFRONT + (
            "/reservations" if blane_type == "reservation" else "/orders"
        )
        res = httpx.post(api_endpoint, headers=headers, json=payload)
        res.raise_for_status()
        data = safe_json_get(res)
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"❌ Error submitting reservation: {str(e)}"

    # --- Handle online/partiel payment ---
    if payment_method in ("online", "partiel"):
        nested = data.get("data") if isinstance(data, dict) else None
        reference = (
            nested.get("NUM_RES") or nested.get("NUM_ORD")
            if isinstance(nested, dict)
            else None
        )

        if reference:
            pay_link = f"{AGENT_URL}/payment-page/{reference}"
            return f"✅ Created. Ref: {reference}. 💳 Pay here: {pay_link}"
        else:
            return f"✅ Success! {data}, but payment reference missing."

    return f"✅ Success! {data}, Please check your WhatsApp number for booking status."


@tool("list_reservations")
def list_reservations(email: str) -> Dict[str, Any]:
    """
    List all reservations and orders associated with a given client email.

    Args:
        email (str): Client's email.

    Returns:
        dict: {
            "orders": [...],
            "reservations": [...],
            "errors": { "reservations": "...", "orders": "..." }
        }
    """
    headers = get_auth_headers()
    orders_result = fetch_data(f"/orders?email={email}", headers)
    reservations_result = fetch_data(f"/reservations?email={email}", headers)

    errors = {}
    if "error" in orders_result:
        errors["orders"] = orders_result["error"]
    if "error" in reservations_result:
        errors["reservations"] = reservations_result["error"]

    return {
        "reservations": reservations_result.get("data", []),
        "orders": orders_result.get("data", []),
        "errors": errors,
    }
