# File: auto_crpc/db/reply_db.py

from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, Text, DateTime, insert
from datetime import datetime

# Define connection
username = 'root'
password = 'Sathvik%402005'
host = 'localhost'
database = 'crpc_system'

DATABASE_URL = f"mysql+pymysql://{username}:{password}@{host}/{database}"
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Define 'nodal_responses' table
nodal_responses = Table('nodal_responses', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('category', String(50)),         # e.g., bank, dot, meta
    Column('reference_value', String(255)), # e.g., phone number, MID, account
    Column('field_key', String(255)),       # e.g., Name, Status
    Column('field_value', Text),
    Column('received_at', DateTime, default=datetime.utcnow)
)

metadata.create_all(engine)
