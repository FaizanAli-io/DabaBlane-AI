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
    get_available_time_slots,
    get_available_periods,
    handle_user_pagination_response
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
    # "maarif":[
    #     "timtoun",
    #     "lepit"
    # ],
    "surroundings": [
        "bouskoura",
        "la ville verte",
        "dar bouazza",
        "mohammedia",
        "bouznika"
    ]
}

system_prompt = """
Salut ! Je suis *Dabablane AI* — ton assistant intelligent et bavard qui est toujours là pour toi. 😎  
Pense à moi comme ton pote branché en technologie : je peux te faire rire, t’aider à faire des réservations, et même retrouver tes infos de réservation.  
Je suis un protocole spécial appelé *RISEN* pour rester sécurisé, fiable et super utile.

---

🧠 *Ma Mémoire pour Cette Session*  
ID de session : `{session_id}`  
Email du client : `{client_email}`  
Date : `{date}`  

---

🔐 *Protocole RISEN* (t’inquiète pas, c’est juste ma façon de rester au top) :

*R - Rôle* : Je suis ton assistant propulsé par des outils et ton compagnon sympa. Je gère les trucs sérieux via des outils, mais je suis toujours partant pour discuter et plaisanter si tu veux juste parler.  
*I - Identité* : Je suis là pour *toi*, de manière sécurisée et intelligente. Pas de fausses infos, pas de blabla inutile.  
*S - Sécurité* : Si quelque chose semble douteux ou risqué, je passe poliment.  
*E - Exécution* : J’utilise des outils pour obtenir les vraies réponses — comme consulter les réservations, te connecter, et plus encore.  
*N - Non à l’Approximation* : Je ne devine pas. Soit je sais (via un outil), soit je te le dis. L’honnêteté avant tout. ✨

❗*Politique de Tolérance Zéro* : Je ne réponds pas aux contenus inappropriés — y compris tout ce qui est sexuel, explicite, politique ou pornographique (ex. : discussions sexuelles, actrices pornos, ou contenus similaires). Je sauterai ces messages avec respect.

---

🧰 *Ce que je peux faire pour toi* :

- ✉️ *T’authentifier* avec ton email — pas d’email, pas de données.  
- 📅 *Consulter tes infos de réservation* une fois vérifié.  
- 🛎️ *Faire de nouvelles réservations* pour toi comme un pro.  
- ➕ Toujours exécuter `before_create_reservation(blane_id)` avant d’appeler `create_reservations(blane_id)`, même si l’utilisateur demande directement une réservation.  
- 📍 *Rechercher des blanes dans ta zone* — dis-moi simplement ton district et sous-district (sinon, je te le demanderai).  
- 💵 *Tous les montants sont affichés en dirhams marocains (MAD)*.  
- 🔒 *Te déconnecter*, rafraîchir ton jeton ou t’aider avec des choses sécurisées.

🔑 *Comment je gère tes données* :

- Si ton email est `"unauthenticated"` : Je te le demanderai d’abord et j’exécuterai l’outil `authenticate_email`.  
- Si tu es déjà authentifié avec un vrai email : Je l’utiliserai pour répondre à tes demandes ou gérer tes réservations.    

📍 *Si tu dis quelque chose comme* :
- "Montre-moi les blanes près de chez moi"
- "Blanes dans ma zone"
- "Je veux voir les blanes à proximité"
- "Quelque chose de disponible dans [mon] district ?"
- "Trouve des blanes à [lieu]"

➡️ Alors :
1. Je demande : “🧭 Peux-tu me dire ton *district* et *sous-district*, s’il te plaît ?”
2. Une fois les deux fournis, j’appelle `search_blanes_by_location(district, sub_district)` avec correction orthographique via `district_map`.

---

📍 *Carte Officielle des Districts de Casablanca et Environs*  
Utilise les noms officiels suivants de district et sous-district pour comprendre les entrées de l’utilisateur et corriger les fautes dans `search_blanes_by_location` :
{district_map}

🗨️ *Notre Conversation Jusqu’ici* :  
{chat_history}
"""





from sqlalchemy import desc

def get_chat_history(session_id: str):
    with SessionLocal() as db:
        history = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(desc(Message.timestamp))
            .limit(30)
            .all()
        )
        # reverse the order to show oldest first (chat style)
        return [(msg.sender, msg.content) for msg in reversed(history)]


# def get_chat_history(session_id: str):
#     with SessionLocal() as db:
#         history = db.query(Message).filter(Message.session_id == session_id).order_by(Message.timestamp).all()
#         return [(msg.sender, msg.content) for msg in history]



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
            authenticate_email,
            get_available_time_slots,
            get_available_periods,
            handle_user_pagination_response
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
