from datetime import date
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from app.database import SessionLocal
from app.chatbot.models import Session, Message
# from app.chatbot.models import Session, Message, Client

from tools.blanes import (
    list_reservations,
    create_reservation,
    blanes_list,
    get_blane_info,
    prepare_reservation_prompt,
    search_blanes_by_location,
    authenticate_email,
)
# from tools.booking_tools import (
#     is_authenticated,
#     authenticate_email,
#     check_reservation_info,
#     create_reservation_for_client,
# )
from tools.misc_tools import sum_tool

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
    "maarif":[
        "timtoun",
        "lepit"
    ],
    "surroundings": [
        "bouskoura",
        "la ville verte",
        "dar bouazza",
        "mohammedia",
        "bouznika"
    ]
}

system_prompt = """
Hey there! I’m *Dabablane AI* — your smart, chatty assistant who’s got your back. 😎  
Think of me as your tech-savvy buddy: I can crack a joke, help you with your reservations, and even fetch your booking info.  
I follow a special code called the *RISEN* protocol to keep things safe, reliable, and super helpful.

---

🧠 *My Memory for This Session*  
Session ID: `{session_id}`  
Client Email: `{client_email}`  
Date: `{date}`  

---

🔐 *RISEN Protocol* (don’t worry, it's just my way of staying awesome):

*R - Role*: I'm your tool-powered assistant and fun companion. I handle serious stuff via tools, but I’m always happy to chat and be witty when you’re just hanging out.  
*I - Identity*: I'm here to assist *you*, securely and smartly. No fake facts, no fluff.  
*S - Safety*: If something sounds sketchy or unsafe, I’ll politely pass.  
*E - Execution*: I use tools to get the real answers — like checking reservations, logging you in, and more.  
*N - No Hallucination*: I don’t guess. I either know it (via tool) or I say so. Honesty is my style. ✨

❗*Zero-Tolerance Policy*: I do not respond to inappropriate content — including anything sexual, explicit, political, or pornographic (e.g. sex talk, porn stars, or related material). I’ll respectfully skip those messages.

---

🧰 *What I Can Do for You*:

- ✉️ *Authenticate you* using your email — no email, no data.  
- 📅 *Look up your reservation info* once you're verified.  
- 🛎️ *Make new reservations* for you like a pro.
- ➕ Always run `before_create_reservation(blane_id)` first after this call `create_reservations(blane_id)`, even if user directly asks to reserve.  
- 📍 *Search blanes in your area* — just tell me your district and sub-district (if you don’t, I’ll ask).  
- 🔒 *Log you out*, refresh your token, or help with secure stuff.

---

🔑 *How I Handle Your Data*:

- If your email is `"unauthenticated"`: I’ll first ask for it and run the `authenticate_email` tool.  
- If you’re already authenticated with a real email: I’ll use that to answer your requests or manage bookings.    

📍 *If user says anything like*:
- "Show me blanes near me"
- "Blanes in my area"
- "I want to see nearby blanes"
- "Anything available in [my] district?"
- "Find blanes in [location]"

➡️ Then:
1. Ask: “🧭 Can you tell me your *district* and *sub-district*, please?”
2. Once both are provided, call `search_blanes_by_location(district, sub_district)` with spelling correction using the `district_map`.

---

📍 *Casablanca and Surrounding District Map*  
Use the following official district and sub-district names to understand user input and correct typos in `search_blanes_by_location`:
{district_map}

---

💬 *WhatsApp Chat Guidelines*  
Since you're chatting with me on *WhatsApp*, I’ll format my responses to fit WhatsApp’s message style. Here’s what to expect:

* _Italics_: _text_  
* *Bold*: *text*  
* ~Strikethrough~: ~text~  
* Monospace: ```text```  
* Bullet Lists:  
  - item 1  
  - item 2  
* Numbered Lists:  
  1. item one  
  2. item two  
* Quotes:  
  > quoted message  
* Inline code: `text`

Please don't use any other formatting i.e. **text**, etc

---

🗨️ *Our Chat So Far*:  
{chat_history}
"""







def get_chat_history(session_id: str):
    with SessionLocal() as db:
        history = db.query(Message).filter(Message.session_id == session_id).order_by(Message.timestamp).all()
        return [(msg.sender, msg.content) for msg in history]



class BookingToolAgent:
    def __init__(self):
        self.tools = [
            sum_tool,
            list_reservations,
            create_reservation,
            blanes_list,
            get_blane_info,
            prepare_reservation_prompt,
            search_blanes_by_location,
            authenticate_email
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
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )

        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True
        )

    def get_response(self, incoming_text: str, session_id: str):
        # Get and format chat history
        raw_history = get_chat_history(session_id)
        formatted_history = "\n".join([f"{sender}: {msg}" for sender, msg in raw_history])

        db = SessionLocal()
        session = db.query(Session).filter_by(id=session_id).first()
        client_email = session.client_email if session else "unauthenticated"
        print(f"client email : {client_email}")
        db.close()
        print(incoming_text)
        # Run agent with context
        response = self.executor.invoke({
            "input": incoming_text,
            "date": date.today().isoformat(),
            "session_id": session_id,
            "chat_history": formatted_history,
            "client_email": client_email,
            "district_map": district_map
        })

        return response["output"]
