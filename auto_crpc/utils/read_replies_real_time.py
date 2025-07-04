# File: auto_crpc/utils/read_replies_real_time.py

import imaplib
import email
import os
import pandas as pd
import time
from email.utils import parseaddr
from datetime import datetime
from db.db_ops import get_all_recipient_emails, insert_nodal_response

EMAIL = "isronasaesa@gmail.com"
PASSWORD = "mbtz admz ifym kftb"
IMAP_SERVER = "imap.gmail.com"
ATTACHMENTS_DIR = "nodal_attachments"

def watch_inbox(interval_seconds=300):
    os.makedirs(ATTACHMENTS_DIR, exist_ok=True)
    allowed_senders = get_all_recipient_emails()

    while True:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(EMAIL, PASSWORD)
            mail.select("inbox")

            status, messages = mail.search(None, '(UNSEEN)')
            email_ids = messages[0].split()

            for e_id in email_ids:
                _, msg_data = mail.fetch(e_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        from_email = parseaddr(msg["From"])[1].lower()

                        if from_email not in allowed_senders:
                            continue

                        for part in msg.walk():
                            if part.get_content_maintype() == 'multipart':
                                continue
                            if part.get('Content-Disposition') is None:
                                continue

                            filename = part.get_filename()
                            if filename and filename.endswith(('.xls', '.xlsx')):
                                filepath = os.path.join(ATTACHMENTS_DIR, filename)
                                with open(filepath, 'wb') as f:
                                    f.write(part.get_payload(decode=True))
                                parse_excel_and_store(filepath, from_email)

            mail.logout()
        except Exception as e:
            print(f"Error checking mail: {e}")

        time.sleep(interval_seconds)

def parse_excel_and_store(filepath, from_email):
    df = pd.read_excel(filepath)

    for _, row in df.iterrows():
        suspect_value = str(row[0]).strip()
        response_dict = row.to_dict()
        insert_nodal_response(from_email, suspect_value, response_dict)
