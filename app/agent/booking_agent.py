import os
from datetime import date
from sqlalchemy import desc
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor

from app.database import SessionLocal
from app.chatbot.models import Message

from tools.utils import list_categories

from tools.blanes import (
    get_blane_info,
    introduction_message,
    find_blanes_by_name_or_link,
    handle_user_pagination_response,
    list_blanes_by_district_and_category,
)

from tools.booking import (
    create_reservation,
    preview_reservation,
    get_available_periods,
    get_available_time_slots,
    prepare_reservation_prompt,
)

from .system_prompts import prompts
from tools.config import district_map


load_dotenv()

language = os.getenv("LANGUAGE", "FRENCH")

system_prompt = prompts[language]


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
            introduction_message,
            get_blane_info,
            find_blanes_by_name_or_link,
            list_blanes_by_district_and_category,
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
                ("placeholder", "{agent_scratchpad}"),
                ("system", system_prompt),
                ("human", "{input}"),
            ]
        ).partial()

        self.agent = create_tool_calling_agent(
            llm=self.llm, tools=self.tools, prompt=self.prompt
        )

        self.executor = AgentExecutor(
            verbose=True,
            agent=self.agent,
            tools=self.tools,
            return_intermediate_steps=True,
        )

    def get_response(self, incoming_text: str, session_id: str):
        raw_history = get_chat_history(session_id)
        formatted_history = "\n".join(
            [f"{i+1}. {sender}: {msg}" for i, (sender, msg) in enumerate(raw_history)]
        )

        response = self.executor.invoke(
            {
                "input": incoming_text,
                "session_id": session_id,
                "district_map": district_map,
                "date": date.today().isoformat(),
                "chat_history": formatted_history,
                "categories_list": list_categories(),
            }
        )

        for action, observation in response.get("intermediate_steps", []):
            if action.tool == "introduction_message":
                return observation

        return response["output"]
