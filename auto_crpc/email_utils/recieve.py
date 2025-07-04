# Directory: auto_crpc/email
# File: receive.py

import imaplib
import email
import mysql.connector

def check_replies():
    user = 'isronasaesa@gmail.com'
    password = 'mbtz admz ifym kftb'

    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(user, password)
    mail.select('inbox')

    typ, data = mail.search(None, '(UNSEEN SUBJECT "Re:")')

    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Sathvik%402005',
        database='crpc_system'
    )
    cursor = conn.cursor()

    for num in data[0].split():
        typ, msg_data = mail.fetch(num, '(RFC822)')
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        subject = msg['subject']
        from_email = msg['from']

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        cursor.execute("""
            INSERT INTO replies (sender_email, subject, body)
            VALUES (%s, %s, %s)
        """, (from_email, subject, body))

    conn.commit()
    cursor.close()
    conn.close()
    mail.logout()
