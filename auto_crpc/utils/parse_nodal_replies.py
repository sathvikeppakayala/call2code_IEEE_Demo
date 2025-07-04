# File: auto_crpc/utils/parse_nodal_replies.py

import re
from datetime import datetime
from auto_crpc.db.reply_db import engine, nodal_responses
from sqlalchemy import insert

def parse_and_store_response(email_body: str, category: str):
    with engine.connect() as conn:
        entries = []
        lines = email_body.strip().splitlines()
        block = {}
        current_ref = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Start of a new entry
            ref_match = re.match(r'(Number|Account|MID|UPI ID):\s*(.+)', line, re.I)
            if ref_match:
                if block and current_ref:
                    for k, v in block.items():
                        entries.append({
                            'category': category,
                            'reference_value': current_ref,
                            'field_key': k,
                            'field_value': v,
                            'received_at': datetime.utcnow()
                        })
                    block = {}
                current_ref = ref_match.group(2).strip()
                continue

            # Key-value inside an entry
            kv_match = re.match(r'([\w\s/().-]+):\s*(.+)', line)
            if kv_match:
                key = kv_match.group(1).strip()
                val = kv_match.group(2).strip()
                block[key] = val

        # Handle last block
        if block and current_ref:
            for k, v in block.items():
                entries.append({
                    'category': category,
                    'reference_value': current_ref,
                    'field_key': k,
                    'field_value': v,
                    'received_at': datetime.utcnow()
                })

        # Store
        if entries:
            conn.execute(insert(nodal_responses), entries)
            conn.commit()
            print(f"[✓] Stored {len(entries)} entries from category '{category}'.")
        else:
            print("[!] No entries parsed.")
