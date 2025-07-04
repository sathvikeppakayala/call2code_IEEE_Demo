import logging
import re
import time
from collections import defaultdict
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ConversationHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# ====== CONFIG ======
OPENROUTER_KEY = "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"
TELEGRAM_BOT_TOKEN = "7994608495:AAElHCdIN_DAa4NxC7GB38Tbff0g3BUUSRE"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO,
)
logger = logging.getLogger(__name__)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

scammer_data = []
decoy_conversations = defaultdict(lambda: {
    'history': [],
    'last_active': time.time(),
    'decoy_state': None,
    'tries': 0
})

HUMAN_DM = range(1)

def extract_social_or_phone(text):
    phones = re.findall(r"\b[6-9]\d{9}\b", text)
    socials = re.findall(r"(instagram\.com/\S+|facebook\.com/\S+|insta:? ?@?\w+|fb:? ?@?\w+)", text, re.I)
    return phones, socials

def extract_upi_or_bank(text):
    upi = re.findall(r"\b\w+@[a-z]+\b", text)
    bank = re.findall(r"\b\d{9,18}\b", text)
    return upi, bank

def contains_proof_phrase(text):
    triggers = [
        "proof", "screenshot", "receipt", "id card", "upi receipt",
        "transaction slip", "sent my proof", "here is my", "my document", "transaction id"
    ]
    t = text.lower()
    return any(x in t for x in triggers)

def contains_intent_to_share(text):
    intent_phrases = [
        "will share", "will send", "sure", "i will upload", "i'll share", "sending soon",
        "sending now", "wait", "give me a minute", "give me some time", "i'll send it", "i will send it",
        "doing it now", "will upload", "sending proof", "uploading", "please wait"
    ]
    t = text.lower()
    return any(phrase in t for phrase in intent_phrases)

def extract_sensitive_info(text):
    upi_ids = re.findall(r"\b\w+@[a-z]+\b", text)
    phones = re.findall(r"\b[6-9]\d{9}\b", text)
    account_numbers = re.findall(r"\b\d{9,18}\b", text)
    socials = re.findall(r"(facebook\.com/\S+|instagram\.com/\S+|insta:? ?@?\w+|fb:? ?@?\w+)", text, re.I)
    return {
        "upi_ids": upi_ids,
        "phones": phones,
        "account_numbers": account_numbers,
        "socials": socials,
    }

def extract_main_classification(gpt_response):
    gpt_response = gpt_response.lower()
    if "scammer" in gpt_response:
        return "scammer"
    elif "decoy" in gpt_response:
        return "decoy"
    elif "innocent" in gpt_response:
        return "innocent"
    else:
        return gpt_response.strip().split('\n')[0][:32]

async def classify_message_with_gpt(text):
    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://yourwebsite.com",
                "X-Title": "ScamHunterBot",
            },
            model="google/gemma-3n-e4b-it:free",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are a message classifier. Classify the following message as exactly one of: 'scammer', 'decoy', or 'innocent'.\n"
                        "- A 'scammer' is someone trying to get money or personal information, often sharing UPI, bank, or social handles, or asking you to contact them for a reward.\n"
                        "- A 'decoy' is someone posting fake testimonials or reviews (e.g., 'I have won 10 lakhs, thank you!', 'I received my money, this is real!') meant to make others trust the scam.\n"
                        "- 'Innocent' is anything not related to a scam.\n"
                        "\n"
                        "EXAMPLES:\n"
                        "1. 'Send me your UPI to get money.' => scammer\n"
                        "2. 'I have won 10 lakhs, thank you so much!' => decoy\n"
                        "3. 'Is this group legit?' => innocent\n"
                        "4. 'Contact me for your reward: john@upi' => scammer\n"
                        "5. 'This worked for me, I got my payment.' => decoy\n"
                        "6. 'What types of proof do you want?' => decoy\n"
                        "7. 'How can I prove it?' => decoy\n"
                        "8. 'My bank account is 1234567890, send money here.' => scammer\n"
                        "9. 'I have a question about the process.' => innocent\n"
                        "10. 'Why do you need my details?' => decoy\n"
                        "11. 'What do you want as proof?' => decoy\n"
                        "\n"
                        "If the message is a question from someone who appears to be engaging or skeptical, and not asking for money or sharing bank/UPI, classify as 'decoy' or 'innocent'.\n"
                        "Now classify this message:\n"
                        f"{text}\n"
                        "Only reply with one word: scammer, decoy, or innocent."
                    ),
                }
            ],
        )
        logger.info(f"[GPT Output] {completion}")
        return completion.choices[0].message.content.strip().lower()
    except Exception as e:
        logger.error(f"Error in GPT classification: {e}")
        return "unknown"

async def handle_decoy_convo(update, convo, user_id, username):
    text = update.message.text
    convo['history'].append({"role": "user", "content": text})
    convo['last_active'] = time.time()

    upi, bank = extract_upi_or_bank(text)
    phones, socials = extract_social_or_phone(text)

    # 1. Awaiting proof (UPI, screenshot, receipt, etc.)
    if convo.get('decoy_state') == 'awaiting_proof':
        if upi or "screenshot" in text.lower() or contains_proof_phrase(text):
            convo['decoy_state'] = 'awaiting_contact'
            convo['tries'] = 0
            await update.message.reply_text(
                "Thanks for the proof! To proceed, can you share your phone number, Instagram, or Facebook?"
            )
            return
        elif contains_intent_to_share(text):
            convo['tries'] = convo.get('tries', 0) + 1
            if convo['tries'] >= 3:
                await update.message.reply_text(
                    "If you have proof to share later, let me know. Take care!"
                )
                convo['decoy_state'] = 'completed'
                del decoy_conversations[user_id]
            else:
                await update.message.reply_text("Ok, share it.")
            return
        else:
            convo['tries'] = convo.get('tries', 0) + 1
            if convo['tries'] >= 3:
                await update.message.reply_text(
                    "I need your UPI ID or payment screenshot as proof to proceed."
                )
                convo['decoy_state'] = 'completed'
                del decoy_conversations[user_id]
            else:
                await update.message.reply_text(
                    "Can you share your UPI ID or a payment screenshot as proof?"
                )
            return

    # 2. Awaiting contact
    if convo.get('decoy_state') == 'awaiting_contact':
        if phones or socials:
            scammer_data.append({
                "user": username,
                "text": text,
                "classification": "decoy",
                "upi": upi,
                "bank": bank,
                "phones": phones,
                "socials": socials,
            })
            await update.message.reply_text(
                "Thank you so much! This really helps. Stay safe!"
            )
            convo['decoy_state'] = 'completed'
            del decoy_conversations[user_id]
            return
        else:
            convo['tries'] = convo.get('tries', 0) + 1
            if convo['tries'] >= 2:
                await update.message.reply_text(
                    "Sorry, I can't proceed without your phone number or social profile."
                )
                convo['decoy_state'] = 'completed'
                del decoy_conversations[user_id]
            else:
                await update.message.reply_text(
                    "Please share your phone number, Instagram, or Facebook so I can continue."
                )
            return

    # If starting conversation or state missing, always start with proof request
    if not convo.get('decoy_state'):
        convo['decoy_state'] = 'awaiting_proof'
        convo['tries'] = 0
        await update.message.reply_text(
            "Hey! Can you share your UPI ID or a payment screenshot as proof?"
        )
        return

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.text:
            return
        text = update.message.text
        user = update.message.from_user
        user_id = user.id
        username = user.username if user.username else str(user_id)
        logger.info(f"Group message from {user_id}: {text}")

        gpt_response = await classify_message_with_gpt(text)
        main_classification = extract_main_classification(gpt_response)
        is_decoy_in_progress = user_id in decoy_conversations

        logger.info(f"Classified as: {main_classification}, decoy_in_progress: {is_decoy_in_progress}")

        # Timeout old decoy conversations (optional, 1 hour)
        for uid, d in list(decoy_conversations.items()):
            if time.time() - d['last_active'] > 3600:
                del decoy_conversations[uid]

        # Always continue decoy conversation if in progress, regardless of classification
        if main_classification == "decoy" or is_decoy_in_progress:
            convo = decoy_conversations[user_id]
            await handle_decoy_convo(update, convo, user_id, username)
            return

        if main_classification == "scammer":
            extracted = extract_sensitive_info(text)
            if any(extracted.values()):
                scammer_data.append({
                    "user": username,
                    "text": text,
                    "classification": "scammer",
                    **extracted,
                })
            # Do not reply in group

        # Don't reply in group for 'innocent' or unknown
    except Exception as e:
        logger.error(f"Exception in handle_group_message: {e}")

async def human_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    logger.info(f"DM from {user_id}: {text}")

    if "human_histories" not in context.bot_data:
        context.bot_data["human_histories"] = {}
    if user_id not in context.bot_data["human_histories"]:
        context.bot_data["human_histories"][user_id] = [
            {"role": "system", "content": (
                "You are a real person who is skeptical but hopeful. "
                "You've lost money to scams before. "
                "You're chatting privately with someone who claims to have received money. "
                "Try to get concrete proof or details (such as UPI, bank, or social) before trusting. "
                "Use natural, informal language, and never admit you are a bot or AI."
            )}
        ]
    history = context.bot_data["human_histories"][user_id]
    history.append({"role": "user", "content": text})

    extracted = extract_sensitive_info(text)
    if any(extracted.values()):
        scammer_data.append({
            "user": user_id,
            "text": text,
            "classification": "decoy followup",
            **extracted,
        })
        await update.message.reply_text(
            "Wow, thank you for sharing that! I really appreciate your honesty. Stay safe!"
        )
        context.bot_data["human_histories"].pop(user_id, None)
        return ConversationHandler.END

    # GPT conversational reply
    try:
        reply = client.chat.completions.create(
            model="google/gemma-3n-e4b-it:free",
            messages=history + [
                {"role": "system", "content":
                    "Continue acting like a real, informal, slightly emotional, skeptical human. "
                    "Ask for more details or proof if you haven't received it yet. "
                    "Do not repeat yourself word for word. Never reveal you are not human. "
                    "If the conversation seems stuck or repetitive, politely end it. "
                    "If the user keeps asking what kind of proof you want, list examples (like UPI ID, payment screenshot, bank details), but after two times, politely say you can't help further and end the conversation. "
                    "Use casual, natural language and try to sound different each time."
                }
            ],
            max_tokens=80,
        )
        gpt_reply = reply.choices[0].message.content.strip()
        if not gpt_reply or "fuzzy" in gpt_reply.lower():
            raise ValueError("Bad GPT reply")
    except Exception as e:
        logger.error(f"GPT DM error: {e}")
        gpt_reply = "Hey there! 😊 Can you tell me a bit more? I'm just being careful because of my past experiences."

    history.append({"role": "assistant", "content": gpt_reply})
    await update.message.reply_text(gpt_reply)
    if len(history) > 16:
        await update.message.reply_text("I'll let you go for now. Thanks for chatting with me!")
        context.bot_data["human_histories"].pop(user_id, None)
        return ConversationHandler.END
    return HUMAN_DM

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! You can now interact with me and I'll message you directly if needed."
    )

def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # GROUP HANDLER: Only for group/supergroup, all text messages
    group_handler = MessageHandler(
        filters.TEXT & (filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP),
        handle_group_message,
    )

    # PRIVATE DM HANDLER: For private chat, all text, handle as conversation
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, human_dm)],
        states={HUMAN_DM: [MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, human_dm)]},
        fallbacks=[],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(group_handler)
    application.add_handler(conv_handler)
    print("✅ Bot setup complete. Listening for messages...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()