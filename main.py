# # # from fastapi import FastAPI, Request
# # # from pydantic import BaseModel
# # # import subprocess
# # # import threading
# # # import time
# # # import os
# # # from dotenv import load_dotenv

# # # load_dotenv()

# # # app = FastAPI()

# # # class MessagePayload(BaseModel):
# # #     sender: str
# # #     message: str

# # # @app.post("/webhook")
# # # async def webhook(payload: MessagePayload):
# # #     print(f"📩 From {payload.sender}: {payload.message}")
# # #     # Reply generation logic
# # #     return {"reply": f"🧠 Echo: {payload.message}"}

# # # def start_baileys_bot():
# # #     print("🚀 Starting Baileys bot...")
# # #     subprocess.call(["node", "baileys_bot.js"])

# # # @app.on_event("startup")
# # # def run_bot_on_startup():
# # #     thread = threading.Thread(target=start_baileys_bot)
# # #     thread.start()
# # #     time.sleep(2)  # Give Baileys time to init

# # from fastapi import FastAPI
# # from pydantic import BaseModel
# # import subprocess
# # import threading
# # import time
# # import os
# # from openai import OpenAI
# # from dotenv import load_dotenv

# # load_dotenv()

# # # Load OpenAI key from .env
# # client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# # app = FastAPI()

# # class MessagePayload(BaseModel):
# #     sender: str
# #     message: str

# # def generate_smart_reply(user_message: str) -> str:
# #     try:
# #         response = client.chat.completions.create(
# #             model="gpt-3.5-turbo",
# #             messages=[
# #                 {"role": "system", "content": "You are a helpful, friendly assistant."},
# #                 {"role": "user", "content": user_message}
# #             ],
# #             temperature=0.8,
# #             max_tokens=300
# #         )
# #         return response.choices[0].message.content.strip()
# #     except Exception as e:
# #         print(f"[GPT ERROR]: {e}")
# #         return "⚠️ Sorry, I couldn't generate a reply right now."
    
# # @app.post("/webhook")
# # async def webhook(payload: MessagePayload):
# #     print(f"📩 From {payload.sender}: {payload.message}")
# #     reply = generate_smart_reply(payload.message)
# #     return {"reply": reply}

# # def start_baileys_bot():
# #     print("🚀 Starting Baileys bot...")
# #     subprocess.call(["node", "baileys_bot.js"])

# # @app.on_event("startup")
# # def run_bot_on_startup():
# #     thread = threading.Thread(target=start_baileys_bot)
# #     thread.start()
# #     time.sleep(2)


# from fastapi import FastAPI
# from pydantic import BaseModel
# from dotenv import load_dotenv
# import httpx
# import os

# load_dotenv()
# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# app = FastAPI()

# class MessagePayload(BaseModel):
#     sender: str
#     message: str

# async def get_claude_response(message: str) -> str:
#     headers = {
#         "Authorization": f"Bearer {OPENROUTER_API_KEY}",
#         "HTTP-Referer": "https://yourdomain.com",
#         "X-Title": "whatsapp-bot"
#     }

#     payload = {
#         "model": "anthropic/claude-3-sonnet-20240229",
#         "max_tokens": 50,  # Enforce short responses (under 50 words)
#         "messages": [
#             {
#                 "role": "system",
#                 "content": (
#                     "You are Alex, a 25-year-old shy, emotional, sentimental, and trusting person who falls for kind words but is smart. In a group chat, you see a scam, spam, hate, or bad behavior message. Respond privately to the sender with short sentences (under 50 words), showing vulnerability, confusion, or hope. Use a heartfelt, storytelling tone, e.g., 'I’m trying to understand,' 'Can you help me feel safe?' or 'You seem kind.' Initially, express caution or hurt, gently asking for their name or intent. If they reply kindly, share vague details (e.g., 'I like music,' 'from a small town') but never sensitive information. Avoid confrontation or enabling scams."
#                 )
#             },
#             {"role": "user", "content": message}
#         ]
#     }

#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
#             data = response.json()

#             # Ensure 'choices' exists before accessing
#             if "choices" in data and data["choices"]:
#                 return data["choices"][0]["message"]["content"].strip()
#             else:
#                 print("[Claude Error] Unexpected response:", data)
#                 return "⚠️ Claude did not return a valid response."
#     except Exception as e:
#         print("[Claude Error]", e)
#         return "⚠️ I'm currently unavailable. Please try again later."

#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
#             data = response.json()

#             # Ensure 'choices' exists before accessing
#             if "choices" in data and data["choices"]:
#                 return data["choices"][0]["message"]["content"].strip()
#             else:
#                 print("[Claude Error] Unexpected response:", data)
#                 return "⚠️ Claude did not return a valid response."
#     except Exception as e:
#         print("[Claude Error]", e)
#         return "⚠️ I'm currently unavailable. Please try again later."
    
# @app.post("/webhook")
# async def webhook(payload: MessagePayload):
#     print(f"📩 {payload.sender}: {payload.message}")
#     reply = await get_claude_response(payload.message)
#     return {"reply": reply}


from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
import os
import re
from typing import Dict

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = FastAPI()

# In-memory store for conversation state (sender_id: kind_reply_count)
conversation_state: Dict[str, int] = {}

# Keywords for detecting problematic messages
BANKING_KEYWORDS = r"(bank|account|pin|password|otp|verification|transfer|card|login|secure)"
CSAM_KEYWORDS = r"(explicit|adult|nsfw|inappropriate|content|private photo|sext|18\+)"
BETTING_KEYWORDS = r"(bet|gambling|casino|odds|wager|stake|win big|jackpot)"
SCAM_KEYWORDS = r"(win|free|click|prize|claim|cash|gift|urgent offer|deal)"
SPAM_KEYWORDS = r"(send money|urgent|pay|stranded|account|donate|cashapp)"
HATE_KEYWORDS = r"(loser|idiot|pathetic|stupid|weak|dumb|moron)"
RUDE_KEYWORDS = r"(shut up|grow up|whining|toughen|quiet|stop crying)"

# Keywords for detecting kind replies (basic sentiment heuristic)
KIND_KEYWORDS = r"(sorry|apologize|didn’t mean|friend|trust|okay|calm|nice)"

class MessagePayload(BaseModel):
    sender: str
    message: str

async def get_claude_response(sender: str, message: str, message_type: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://yourdomain.com",
        "X-Title": "whatsapp-bot"
    }

    # Initialize conversation state
    if sender not in conversation_state:
        conversation_state[sender] = 0

    # Determine if we should share vague details (after 1 kind reply)
    share_details = conversation_state[sender] > 0

    # Tailor prompt based on message type
    tone_instruction = {
        "banking": "Show extra caution, mentioning trust issues with banks.",
        "csam": "Express discomfort and fear, avoiding engagement with content.",
        "betting": "Show hopeful curiosity but nervousness about risks.",
        "scam": "Show excitement but past hurt from tricks.",
        "spam": "Show concern and eagerness to help but fear of tricks.",
        "hate": "Show hurt and sadness, seeking kindness.",
        "rude": "Show sensitivity and a plea for nicer talk."
    }.get(message_type, "Show vulnerability and confusion.")

    system_content = (
        "You're Alex, a 25-year-old shy, emotional, sentimental person who trusts kind words but is smart. "
        "In a group chat, you spot a problematic message. Text the sender privately like a real person, "
        "starting with casual openers like 'Hey,' 'Wow,' or 'Um.' Use heartfelt, casual words (under 50 words). "
        f"{tone_instruction} Include phrases like 'I’m kinda scared,' 'Can you make me feel okay?' or 'You seem nice.' "
        "Start cautious, asking for their name or why they said it. "
        f"{'If they replied kindly before, share vague details (e.g., "I like music," "from a small town") but never private info.' if share_details else ''}"
        "No confrontation or robotic tone. Avoid enabling scams."
    )

    payload = {
        "model": "anthropic/claude-3-sonnet-20240229",
        "max_tokens": 20,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": message}
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
            data = response.json()

            # Ensure 'choices' exists
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"].strip()
            else:
                print("[Claude Error] Unexpected response:", data)
                return "⚠️ I’m having trouble replying. Try again soon?"
    except Exception as e:
        print("[Claude Error]", e)
        return "⚠️ I’m having trouble replying. Try again soon?"

@app.post("/webhook")
async def webhook(payload: MessagePayload):
    print(f"📩 {payload.sender}: {payload.message}")
    
    # Detect message type
    message_type = None
    if re.search(BANKING_KEYWORDS, payload.message, re.IGNORECASE):
        message_type = "banking"
    elif re.search(CSAM_KEYWORDS, payload.message, re.IGNORECASE):
        message_type = "csam"
    elif re.search(BETTING_KEYWORDS, payload.message, re.IGNORECASE):
        message_type = "betting"
    elif re.search(SCAM_KEYWORDS, payload.message, re.IGNORECASE):
        message_type = "scam"
    elif re.search(SPAM_KEYWORDS, payload.message, re.IGNORECASE):
        message_type = "spam"
    elif re.search(HATE_KEYWORDS, payload.message, re.IGNORECASE):
        message_type = "hate"
    elif re.search(RUDE_KEYWORDS, payload.message, re.IGNORECASE):
        message_type = "rude"

    # Check for kind reply in subsequent interactions
    if conversation_state.get(payload.sender, 0) > 0 and re.search(KIND_KEYWORDS, payload.message, re.IGNORECASE):
        conversation_state[payload.sender] += 1

    # Only respond to problematic messages
    if message_type:
        reply = await get_claude_response(payload.sender, payload.message, message_type)
        # Increment kind reply count (assuming processed message could be a reply)
        conversation_state[payload.sender] += 1
        return {"reply": reply}
    return {"reply": ""}  # Skip non-problematic messages