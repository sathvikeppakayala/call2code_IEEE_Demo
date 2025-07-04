# File: main.py

import json
import time
import os
import imaplib
import email
import pandas as pd
import tempfile
from datetime import datetime
from openai import OpenAI
from email.header import decode_header
from utils.filler import fill_template
from email_utils.send import send_email
from db.db_ops import insert_request, insert_nodal_response, get_all_recipient_emails
from config_utils.mapper import get_config
# Sample input (Replace with actual data input)
from sqlalchemy import create_engine, text
import json


# Email credentials (set via env vars or config)
EMAIL_USER = "isronasaesa@gmail.com"
EMAIL_PASS = "mbtz admz ifym kftb"
IMAP_SERVER = "imap.gmail.com"

# OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)


# DB connection
engine = create_engine("mysql+pymysql://root:Sathvik%402005@127.0.0.1/crpc_system")

input_data = []

with engine.connect() as conn:
    result = conn.execute(text("SELECT data FROM json_entities_onlyblob"))
    rows = result.fetchall()

    for row in rows:
        try:
            suspects = json.loads(row[0])  # each row[0] is a JSON string
            if isinstance(suspects, list):
                for suspect in suspects:
                    input_data.append({
                        "type": suspect.get("type", "unknown").strip().lower(),
                        "value": suspect.get("value", "unknown").strip(),
                        "name": suspect.get("name", "Unknown").strip(),
                        "date": suspect.get("date", "Unknown").strip()
                    })
        except Exception as e:
            print(f"❌ Skipped a row due to error: {e}")


# Group inputs and send CRPC requests

grouped = {}
for item in input_data:
    grouped.setdefault(item['type'], []).append(item)

for category, suspects in grouped.items():
    try:
        config = get_config(category)
    except ValueError as e:
        print(f"⚠️ Skipping unsupported category '{category}': {e}")
        continue

    context = {"suspects": suspects}
    filled_body = fill_template(category, context)
    send_email(config['to_email'], config['subject'], filled_body)
    insert_request(category, suspects, config['to_email'], config['subject'], filled_body)

# Monitor inbox for nodal officer replies and process attachments

def check_nodal_responses():
    nodal_emails = get_all_recipient_emails()

    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")

    result, data = mail.search(None, "ALL")
    email_ids = data[0].split()

    for email_id in reversed(email_ids[-30:]):
        result, message_data = mail.fetch(email_id, "(RFC822)")
        raw_email = message_data[0][1]
        msg = email.message_from_bytes(raw_email)

        from_email = email.utils.parseaddr(msg.get("From"))[1].lower()
        if from_email not in nodal_emails:
            continue

        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition"))
            if "attachment" in content_disposition and part.get_filename().endswith(".xlsx"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp.write(part.get_payload(decode=True))
                    tmp_path = tmp.name
                process_attachment(tmp_path, from_email)
                os.remove(tmp_path)

    mail.logout()

def process_attachment(filepath, source_email):
    try:
        df = pd.read_excel(filepath)
        if df.empty:
            return

        for _, row in df.iterrows():
            suspect_value = infer_suspect_value(row)
            content = f"Structure this data properly as JSON: {row.to_dict()}"

            completion = client.chat.completions.create(
                model="google/gemma-3n-e4b-it:free",
                messages=[{"role": "user", "content": content}]
            )

            formatted = completion.choices[0].message.content
            insert_nodal_response(
                source_email=source_email,
                suspect_value=suspect_value,
                formatted_response=formatted,
                received_at=datetime.utcnow()
            )
    except Exception as e:
        print(f"Failed to process attachment: {e}")

def infer_suspect_value(row):
    for key in row.keys():
        if "mobile" in key.lower() or "account" in key.lower() or "upi" in key.lower():
            return str(row[key])
    return "unknown"

if __name__ == "__main__":
    while True:
        print("Checking inbox for nodal replies...")
        check_nodal_responses()
        time.sleep(120)  # Every 2 minutes
