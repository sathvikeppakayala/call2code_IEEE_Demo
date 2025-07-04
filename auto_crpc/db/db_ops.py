# Directory: auto_crpc/db
# File: db_ops.py

from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, Text, insert, DateTime, select, update
from datetime import datetime, timedelta
import pandas as pd

# Define database connection using SQLAlchemy
username = 'root'
password = 'Sathvik%402005'
host = '127.0.0.1'
port='3306'
database = 'crpc_system'
table_name = '49mR'

DATABASE_URL = f"mysql+pymysql://{username}:{password}@{host}/{database}"
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Define table structure for 'requests' table
requests = Table('requests', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('category', String(50)),
    Column('suspect_number', Integer),
    Column('suspect_type', String(50)),
    Column('suspect_value', String(255)),
    Column('recipient_email', String(255)),
    Column('subject', String(255)),
    Column('body', Text),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('reminder_sent', Integer, default=0)
)

# Define table for nodal officer responses
nodal_responses = Table('nodal_responses', metadata,
    Column('id', Integer, primary_key=True),
    Column('source_email', String(255)),
    Column('suspect_value', String(255)),
    Column('response_data', Text),
    Column('received_at', DateTime, default=datetime.utcnow),
    Column('sla_hours', Integer)
)

# Create the tables if they don't exist
metadata.create_all(engine)

# Function to insert a request
def insert_request(category, suspects, to_email, subject, body):
    with engine.connect() as conn:
        for i, suspect in enumerate(suspects, 1):
            stmt = insert(requests).values(
                category=category,
                suspect_number=i,
                suspect_type=suspect['type'],
                suspect_value=suspect['value'],
                recipient_email=to_email,
                subject=subject,
                body=body,
                created_at=datetime.utcnow(),
                reminder_sent=0
            )
            conn.execute(stmt)
        conn.commit()

# Optional: Function to push a DataFrame to a specified table (e.g., '49mR')
def push_dataframe_to_table(df):
    df.to_sql(table_name, con=engine, if_exists='append', index=False)
    print(f"DataFrame successfully pushed to {database}.{table_name}")

# Function to send reminder emails after a time threshold
def send_reminders(send_email_callback, delay_hours=24):
    with engine.connect() as conn:
        now = datetime.utcnow()
        threshold_time = now - timedelta(hours=delay_hours)

        stmt = select(requests).where(
            requests.c.reminder_sent == 0,
            requests.c.created_at < threshold_time
        )

        results = conn.execute(stmt).fetchall()

        for row in results:
            # Use the callback to send the email
            send_email_callback(row.recipient_email, row.subject, row.body)

            # Mark as reminder sent
            upd = update(requests).where(requests.c.id == row.id).values(reminder_sent=1)
            conn.execute(upd)

        conn.commit()

# Utility: Get all nodal officer recipient emails (sent earlier)
def get_all_recipient_emails():
    with engine.connect() as conn:
        stmt = select(requests.c.recipient_email).distinct()
        results = conn.execute(stmt).fetchall()
        return {r.recipient_email.lower() for r in results}

# Utility: Get request record by suspect value
def get_request_by_suspect_value(suspect_value):
    with engine.connect() as conn:
        stmt = select(requests).where(requests.c.suspect_value == suspect_value).limit(1)
        result = conn.execute(stmt).fetchone()
        return result

# Save response to DB after OpenAI/Gemma formatting
def insert_nodal_response(source_email, suspect_value, formatted_response, received_at=None):
    if received_at is None:
        received_at = datetime.utcnow()

    matched_request = get_request_by_suspect_value(suspect_value)
    sla_hours = None
    if matched_request:
        created_at = matched_request.created_at
        sla_hours = int((received_at - created_at).total_seconds() // 3600)

    with engine.connect() as conn:
        stmt = insert(nodal_responses).values(
            source_email=source_email,
            suspect_value=suspect_value,
            response_data=formatted_response,
            received_at=received_at,
            sla_hours=sla_hours
        )
        conn.execute(stmt)
        conn.commit()
