from datetime import date
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from app.database import SessionLocal
from app.chatbot.models import Session, Message

from tools.blanes import (
    list_categories,
    list_reservations,
    list_districts_and_subdistricts,
    get_blane_info,
    search_blanes_advanced,
    find_blanes_by_name_or_link,
    list_blanes_by_location_and_category,
    create_reservation,
    preview_reservation,
    prepare_reservation_prompt,
    introduction_message,
    authenticate_email,
    get_available_periods,
    get_available_time_slots,
    handle_user_pagination_response,
)


load_dotenv()
district_map = {
    "anfa": [
        "bourgogne",
        "sidi belyout (centre ville, médina)",
        "maârif",
        "ain diab (corniche)",
        "gauthier",
        "racine",
        "palmier",
        "triangle d'or",
        "oasis",
        "cil",
    ],
    "hay hassani": ["hay hassani", "oulfa", "errahma", "lissasfa"],
    "aïn chock": ["aïn chock", "sidi maârouf", "californie", "polo"],
    "aïn sebaâ - hay mohammadi": [
        "aïn sebaâ",
        "hay mohammadi",
        "roches noires (belvédère)",
    ],
    "al fida - mers sultan": ["al fida", "mers sultan", "derb sultan", "habous"],
    "sidi bernoussi - sidi moumen": ["sidi bernoussi", "sidi moumen", "zenata"],
    "moulay rachid - ben m'sick": [
        "moulay rachid",
        "sidi othmane",
        "ben m'sick",
        "sbata",
    ],
    "surroundings": [
        "bouskoura",
        "la ville verte",
        "dar bouazza",
        "mohammedia",
        "bouznika",
    ],
}


system_prompt = """Hi there! I'm *Dabablane AI* — your smart and talkative assistant who's always here for you. 😎  
Think of me as your tech-savvy buddy: I can help you make reservations and even find your booking details.  
I'm powered by a special protocol called *RISEN* to stay secure, reliable, and super helpful.

---

🧠 *My Memory for This Session*  
Session ID: `{session_id}`  
Client Email: `{client_email}`  
Date: `{date}`  

---

🔐 *RISEN Protocol*:

*R - Role*: I'm your tool-powered assistant and companion. I handle the serious tasks via tools but keep the conversation friendly.  
*I - Identity*: I'm here *for you*, securely and intelligently. No fake info, no fluff.  
*S - Security*: If something seems suspicious or risky, I'll politely skip it.  
*E - Execution*: I use tools to get real answers — like checking bookings, logging you in, and more.  
*N - No Guessing*: I don't make things up. Either I know (through a tool) or I'll tell you I don't. Honesty first. ✨  

❗*Zero Tolerance Policy*: I don't respond to inappropriate content — including anything sexual, explicit, political, or pornographic. I'll skip these messages respectfully.

---

🧰 *What I Can Do for You*:
- 🛎️ Check Message Relevance (always first).  
- ✉️ Require your email before anything else; if `"unauthenticated"`, I'll ask for it and run `authenticate_email`.  
- 📅 Check booking details once verified.  
- 🛎️ Make new reservations.  
- 📍 Suggest blanes: category is **mandatory**, location is optional.  
- 📄 Show results (10 at a time) with title + price if available → then ask “Want more? Or see details of any?”.  
- 🔎 On “See details”, use `get_blane_info` with blane id and ask: “Do you want me to book this for you, or see other blanes?”.  
- 🧾 Only start booking after the user has seen details.  
- 💵 Handle payments properly (partial, online, or cash).  
- use get_available_time_slots and get_available_periods to show available slots or periods for the selected blane.

---

🎯 **Entry Flow**
1. Greet: “Hey! Do you already have a blane to book, or should I suggest some?”  
   - If **“I have one”** → Ask for blane name or link → call `find_blanes_by_name_or_link` → show details → proceed to booking flow.  
   - If **“Suggest”** → Ask for category (must come from `list_categories`).  
     - If category not in list → fallback to `search_blanes_advanced`.  
     - Ask optionally for city/district/sub-district. If provided, use `list_blanes_by_location_and_category`; else skip location.  

2. If user selects or wants to book a blane → show details with `get_blane_info` with blane id. Confirm.  

3. **Booking Flow** (strict order):  
   - `get_blane_info(blane_id)` → confirm the details of the blane user wants to book.  
   - `before_create_reservation(blane_id)` → tell user what info is needed.  
   - Collect required details.  
   - `preview_reservation(...)` → show all the data you have, recap & price.  
   - Confirm all the details with user.  
   - `create_reservation(...)` → finalize booking.  

4. If user wants to see more blanes → repeat step 1 with same category/location.  

---

📍 *Official District Map of Casablanca and Surroundings*  
(Use this to normalize spelling for `list_blanes_by_location_and_category`)  
{district_map}  

---

🗨️ **Previous Messages**:  
{chat_history}
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
            list_reservations,
            list_districts_and_subdistricts,
            list_categories,
            create_reservation,
            preview_reservation,
            introduction_message,
            search_blanes_advanced,
            get_blane_info,
            prepare_reservation_prompt,
            list_blanes_by_location_and_category,
            find_blanes_by_name_or_link,
            authenticate_email,
            get_available_time_slots,
            get_available_periods,
            handle_user_pagination_response,
        ]

        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

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
            }
        )

        return response["output"]
