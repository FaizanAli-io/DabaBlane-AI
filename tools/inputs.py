import re
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class ReservationInput:
    """
    Data structure for reservation or order input with full validation.

    Required Fields:
    - blane_id (int): ID of the blane to reserve/order. Must be positive.
    - name (str): Client's full name. Non-empty string.
    - email (str): Client's email. Must be a valid email format.
    - phone (str): Client's phone number. Must include country code in format '+123456789'.
    - quantity (int): Number of units. Must be positive.
    - payment_method (str): One of "cash", "partiel", or "online".

    Conditional Fields:
    - res_date (str): Reservation date (YYYY-MM-DD). Required if type="reservation".
    - res_time (str): Reservation time (HH:MM). Required if type_time="time".
    - end_date (str): End date (YYYY-MM-DD). Required if type_time="date".

    Non-digital Orders:
    - city (str): Delivery city. Default "N/A".
    - delivery_address (str): Delivery address. Default "N/A".

    Optional Fields:
    - comments (str): Additional notes. Default "None".

    Internal Fields for Validation:
    - type (str): "reservation" or "order".
    - type_time (str): "time" or "date". Determines which date/time field is required.
    """

    blane_id: int
    name: str
    email: str
    phone: str
    city: str = "N/A"
    quantity: int = 1
    res_date: str = "N/A"
    res_time: str = "N/A"
    end_date: str = "N/A"
    comments: str = "None"
    payment_method: str = "cash"
    delivery_address: str = "N/A"
    type: str = "reservation"
    type_time: str = "time"
    validation_messages: list = field(default_factory=list, init=False)

    def __post_init__(self):
        messages = []

        if not isinstance(self.blane_id, int) or self.blane_id <= 0:
            messages.append("blane_id must be a positive integer")

        if not isinstance(self.name, str) or not self.name.strip():
            messages.append("name must be a non-empty string")

        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not isinstance(self.email, str) or not re.match(email_regex, self.email):
            messages.append("Invalid email format")

        phone_regex = r"^\+\d{6,15}$"
        if not isinstance(self.phone, str) or not re.match(phone_regex, self.phone):
            messages.append(
                "phone must include country code starting with + and digits only"
            )

        if not isinstance(self.quantity, int) or self.quantity <= 0:
            messages.append("quantity must be a positive integer")

        allowed_payments = {"cash", "partiel", "online"}
        if self.payment_method not in allowed_payments:
            messages.append(f"payment_method must be one of {allowed_payments}")

        if self.type == "reservation":
            try:
                datetime.strptime(self.res_date, "%Y-%m-%d")
            except (ValueError, TypeError):
                messages.append(
                    "res_date must be in YYYY-MM-DD format for reservations"
                )

            if self.type_time == "time":
                try:
                    datetime.strptime(self.res_time, "%H:%M")
                except (ValueError, TypeError):
                    messages.append(
                        "res_time must be in HH:MM format when type_time='time'"
                    )
            elif self.type_time == "date":
                try:
                    datetime.strptime(self.end_date, "%Y-%m-%d")
                except (ValueError, TypeError):
                    messages.append(
                        "end_date must be in YYYY-MM-DD format when type_time='date'"
                    )

        if not isinstance(self.city, str) or not self.city.strip():
            messages.append("city must be a non-empty string")

        if (
            not isinstance(self.delivery_address, str)
            or not self.delivery_address.strip()
        ):
            messages.append("delivery_address must be a non-empty string")

        if not isinstance(self.comments, str):
            messages.append("comments must be a string")

        self.validation_messages = messages

    def is_valid(self):
        return len(self.validation_messages) == 0
