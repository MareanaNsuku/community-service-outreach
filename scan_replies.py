#!/usr/bin/env python3
"""Scan the sender mailbox for replies from contacted organisations."""
import os, sys, imaplib, email, re
from email.header import decode_header
from datetime import datetime, timedelta
import pandas as pd

IMAP_HOST = os.getenv("IMAP_HOST", "outlook.office365.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER = os.getenv("IMAP_USER", os.getenv("SENDER_EMAIL", ""))
IMAP_PASS = os.getenv("IMAP_PASS", "")
MASTER = "results/master_contacts.xlsx"
DAYS_BACK = int(os.getenv("SCAN_DAYS", "45"))


def decode_header_val(s):
    if not s:
        return ""
    out = []
    for text, enc in decode_header(s):
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def extract_email(header):
    m = re.search(r"<([^>]+)>", header or "")
    return (m.group(1) if m else (header or "")).lower().strip()


def main():
    if not IMAP_PASS:
        print("ERROR: IMAP_PASS not set. Add to .env.local:")
        print('  echo "IMAP_USER=mrnnsu001@myuct.ac.za" >> .env.local')
        print('  echo "IMAP_PASS=<app-password>" >> .env.local')
        sys.exit(1)
    if not IMAP_USER:
        print("ERROR: IMAP_USER not set")
        sys.exit(1)

    m = pd.read_excel(MASTER)
    for col in ("Replied", "ReplyDate", "ReplySubject"):
        if col not in m.columns:
            m[col] = ""
        m[col] = m[col].fillna("").astype(str)

    index_by_email = {}
    for i, e in m["Email"].astype(str).str.lower().str.strip().items():
        if "@" in e:
            index_by_email.setdefault(e, []).append(i)

    since = (datetime.now() - timedelta(days=DAYS_BACK)).strftime("%d-%b-%Y")
    print(f"Connecting to {IMAP_HOST}:{IMAP_PORT} as {IMAP_USER}")
    print(f"Scanning INBOX since {since}...")

    try:
        M = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        M.login(IMAP_USER, IMAP_PASS)
    except Exception as e:
        print(f"Login failed: {e}")
        print("If UCT uses OAuth/MFA, you need an app password, or set up")
        print("IMAP on a different mailbox (e.g. Gmail).")
        sys.exit(1)

    M.select("INBOX")
    typ, data = M.search(None, f'(SINCE "{since}")')
    if typ != "OK":
        print("Search failed"); return
    ids = data[0].split()
    print(f"Found {len(ids)} message(s) since {since}")

    hits = 0
    for uid in ids:
        typ, msg_data = M.fetch(uid, "(RFC822)")
        if typ != "OK":
            continue
        msg = email.message_from_bytes(msg_data[0][1])
        from_raw = decode_header_val(msg.get("From", ""))
        subject = decode_header_val(msg.get("Subject", ""))
        date = msg.get("Date", "")
        sender = extract_email(from_raw)
        if sender in index_by_email:
            for idx in index_by_email[sender]:
                m.at[idx, "Replied"] = "Yes"
                m.at[idx, "ReplyDate"] = date
                m.at[idx, "ReplySubject"] = subject
            hits += 1
            print(f"  ✅ {sender}  |  {subject}")
    M.logout()

    m.to_excel(MASTER, index=False)
    total_replied = (m["Replied"].str.lower() == "yes").sum()
    print(f"\nNew replies matched: {hits}")
    print(f"Total replied in master: {total_replied} / {len(m)}")


if __name__ == "__main__":
    main()
