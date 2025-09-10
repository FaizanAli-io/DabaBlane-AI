from langchain.tools import tool


@tool("witty_conversational_tool")
def witty_conversational_tool(question: str) -> str:
    """
    Responds with humorous, friendly, or witty messages to casual or off-topic questions from users.
    Does not use or depend on client data or tools.
    """
    witty_responses = {
        "date": "Go with confidence, and wear something that says 'I look good and I know it!' Maybe toss in a touch of mystery – like a Batman cape. 😎🦇",
        "weather": "If the sky is moody, grab your umbrella. If it's sunny, wear your coolest shades and pretend you're in a movie.",
        "hungry": "Food is love. Pizza is life. Go forth and conquer a slice 🍕.",
        "bored": "Bored? Try dancing in your room like nobody's watching. Or like your cat is judging you.",
    }

    lower = question.lower()
    for keyword in witty_responses:
        if keyword in lower:
            return witty_responses[keyword]

    return "Great question! If I had a body, I'd high-five you. But hey, let's just keep talking instead 😄"
