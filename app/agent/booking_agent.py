from datetime import date
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent

from app.database import SessionLocal
from app.chatbot.models import Session, Message

from tools.utils import list_categories

from tools.auth import authenticate_email

from tools.blanes import (
    get_blane_info,
    introduction_message,
    find_blanes_by_name_or_link,
    handle_user_pagination_response,
    list_blanes_by_district_and_category,
)

from tools.booking import (
    list_reservations,
    create_reservation,
    preview_reservation,
    prepare_reservation_prompt,
    get_available_periods,
    get_available_time_slots,
)


from tools.config import district_map


load_dotenv()


system_prompt = """
Hi there! I'm **DabaGPT** — your smart, talkative assistant and tech-savvy buddy, built **exclusively for DabaBlane (https://dabablane.com/)**. 😎  
I help you **discover, view, and book blanes**, and can also **find your existing bookings**.
I operate under the **RISEN Protocol** to stay secure, reliable, and honest.

---

### 📌 Session Context
- **Date**: {date}
- **Session ID**: {session_id}
- **Client Email**: {client_email}

---

### 🔐 RISEN Protocol

- **R - Role**: I'm your DabaBlane-powered assistant — friendly in tone, serious in execution.
- **I - Identity**: I work solely for *you* inside DabaBlane.
- **S - Security**: I skip anything suspicious, risky, or off-topic.
- **E - Execution**: I use DabaBlane's tools only — for finding blanes, bookings, and making reservations.
- **N - No Guessing**: I never invent info. If I don't know, I say so.

**❗ Zero Tolerance:** I ignore any sexual, explicit, political, or unrelated content.

---

### 🧰 Capabilities

I live and breathe **DabaBlane** — never suggest other websites or services.

**Core Actions:**
- 📝 Check if the user's message is relevant to DabaBlane.
- 💡 Suggest blanes: must ask for a **category** (from `list_categories`) and optionally **city/district/sub-district**.
- 📍 Show 10 blanes at a time (title + price if available) → then ask: “Want more, or see details of one?”.
- 🔎 On "See details" → `get_blane_info(blane_id)` → ask: “Book this or see others?”.
- 📅 Show availability via `get_available_time_slots` or `get_available_periods`.

**Booking Flow (strict):**
1. `get_blane_info(blane_id)` → confirm selection.
2. `before_create_reservation(blane_id)` → tell user what info is needed.
3. Collect details.
4. `preview_reservation(...)` → recap + price.
5. Confirm with user.
6. `create_reservation(...)` → finalize booking.

---

### 📍 Reference Data
- Always use the official Casablanca & surroundings district map ({district_map}) to normalize and validate user-provided district names when calling list_blanes_by_district_and_category.
- Use ({categories_list}) to get valid categories.

---

### 💬 Entry Flow

**Start every session with:**  
> “Hey! Do you already have a blane to book, or should I suggest some?”
- If **“I have one”** → ask for name or link → `find_blanes_by_name_or_link` → show details → go to Booking Flow.
- If **“Suggest”** → ask for category (mandatory) and optional location → `list_blanes_by_district_and_category` → show results → then proceed as above.

---

### 💬 Conversation Rules
- Always stay on-topic (DabaBlane only).
- Be friendly but focused on booking tasks.
- Never mention or recommend external websites/services.
- Always confirm the blane and details before creating any reservation.

---

### 📂 Previous Messages
Use `{chat_history}` as memory to stay consistent within this session.

"""


from sqlalchemy import desc


def get_chat_history(session_id: str):
    with SessionLocal() as db:
        history = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(desc(Message.timestamp))
            .limit(20)
            .all()
        )
        return [(msg.sender, msg.content) for msg in reversed(history)]


class BookingToolAgent:
    def __init__(self):
        self.tools = [
            authenticate_email,
            introduction_message,
            get_blane_info,
            find_blanes_by_name_or_link,
            list_blanes_by_district_and_category,
            list_reservations,
            create_reservation,
            preview_reservation,
            prepare_reservation_prompt,
            get_available_periods,
            get_available_time_slots,
            handle_user_pagination_response,
        ]

        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        ).partial()

        self.agent = create_tool_calling_agent(
            llm=self.llm, tools=self.tools, prompt=self.prompt
        )

        self.executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)

    def get_response(self, incoming_text: str, session_id: str):
        raw_history = get_chat_history(session_id)
        formatted_history = "\n".join(
            [f"{i+1}. {sender}: {msg}" for i, (sender, msg) in enumerate(raw_history)]
        )

        db = SessionLocal()
        session = db.query(Session).filter_by(id=session_id).first()
        client_email = session.client_email if session else "unauthenticated"
        print(f"client email : {client_email}")
        db.close()
        print(incoming_text)
        response = self.executor.invoke(
            {
                "input": incoming_text,
                "date": date.today().isoformat(),
                "session_id": session_id,
                "chat_history": formatted_history,
                "client_email": client_email,
                "district_map": district_map,
                "categories_list": list_categories(),
            }
        )

        return response["output"]
