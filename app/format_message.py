import re


def formatting(text):
    # Convert Markdown bold to WhatsApp bold
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)
    # Optionally block other illegal formatting
    text = re.sub(r"<[^>]*>", "", text)  # Remove HTML tags
    return text
