# Directory: auto_crpc/db
# File: db_ops.py

from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, Text, insert, DateTime, select, update
from datetime import datetime, timedelta
import pandas as pd

# Define database connection using SQLAlchemy
username = 'root'
password = 'Sathvik%402005'
host = 'localhost'
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

# Create the table if it doesn't exist
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
