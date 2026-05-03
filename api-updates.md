## DabaBlane — WhatsApp AI Agent API Specification

**Base URL:** `[https://api.dabablane.com/api](https://api.dabablane.com/api)`  
**Standard Headers:**

- `Authorization: Bearer {token}` (Required for browsing)
- `Accept: application/json`

---

### 1. Agent Scope & Capabilities

The AI Agent is designed for a **linear conversion flow**. It does not handle post-booking management.

- **Allowed:** Browse active "Blanes," check real-time availability, calculate prices, create reservations/orders, and provide payment links.
- **Prohibited:** No booking lookups, no follow-ups (_relance_), and no cancellations.

---

### 2. Authentication

The agent uses a dedicated service account. The token should be requested once and reused until expiration.

**POST** `/login`

```json
{
  "email": "agent@dabablane.com",
  "password": "..."
}
```

> **Response:** `data.user_token` contains the Bearer token.

---

### 3. Discovery & Browsing

Use these endpoints to find offers based on user queries. Always filter by `status=active`.

**GET** `/front/v1/blanes`

| Parameter  | Type   | Description                |
| :--------- | :----- | :------------------------- |
| `type`     | string | `reservation` or `order`   |
| `city`     | string | Filter by city name        |
| `category` | string | Category slug              |
| `search`   | string | Free text search           |
| `include`  | string | Use `blaneImages,category` |
| `status`   | string | **Always** send `active`   |

**Key Fields for Logic:**

- `type_time`: `time` (slot-based) or `date` (period-based).
- `cash` / `online` / `partiel`: Booleans indicating accepted payment methods.
- `is_digital`: If `true`, skip delivery address for orders.

---

### 4. Availability Check

**Mandatory** before proposing a specific time or confirming a booking.

- **For Reservations (Slot-based):**  
  `GET /front/v1/blanes/{slug}/available-time-slots?date=YYYY-MM-DD`  
  _Only propose slots where `available: true`._
- **For Reservations (Period-based):**  
  `GET /front/v1/blanes/{slug}`  
  _Check the `available_periods` array in the response._
- **For Orders:**  
  _Check `stock > 0` in the initial Blane response._

---

### 5. Price Calculation Logic

The agent **must** calculate the price manually before submission. If the `total_price` sent does not match the server's calculation, the request will be rejected.

$$base\_price = price\_current \times quantity$$
$$tva\_amount = base\_price \times (tva / 100)$$
$$total\_price = base\_price + tva\_amount$$

**For Partiel (Deposit) Payments:**
$$partiel\_price = total\_price \times (partiel\_field / 100)$$

---

### 6. Booking & Conversion

Create the record once the client confirms details. No Auth token is required for these POST requests.

#### A. Create Reservation

**POST** `/front/v1/reservations`

| Field            | Type    | Note                                      |
| :--------------- | :------ | :---------------------------------------- |
| `blane_id`       | Integer | ID from browsing step                     |
| `payment_method` | String  | `cash`, `online`, or `partiel`            |
| `time`           | String  | Required if `type_time` is `time`         |
| `end_date`       | String  | Required if `type_time` is `date`         |
| `partiel_price`  | Float   | Required if `payment_method` is `partiel` |

#### B. Create Order

**POST** `/front/v1/orders`

- **Physical Goods:** Must include `delivery_address` and `city`.
- **Digital Goods:** (`is_digital: true`) No address required.

---

### 7. Payment Handling

- **Cash / Partiel:** Response returns a status of `waiting`. Provide the client with their reference number (`NUM_RES` or `NUM_ORD`).
- **Online:** Response returns a status of `pending_payment` and a `payment_url`.
  > **Action:** The agent must immediately send the `payment_url` (CMI link) to the client on WhatsApp.

---

### 8. Decision Flow Summary

1.  **Search:** `GET /blanes` (filter by city/category).
2.  **Verify:** Check availability via `available-time-slots` or `stock`.
3.  **Calculate:** Compute `total_price` + `tva`.
4.  **Execute:** `POST` to reservations or orders.
5.  **Close:** Provide Reference ID or CMI Payment Link.
