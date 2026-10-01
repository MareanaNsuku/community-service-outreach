import os
import sys
import re
import imaplib
import email
from datetime import datetime, timedelta
import pandas as pd

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
GMAIL_USER = os.getenv("GMAIL_USER", "mareanansuku@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

BLOCKLIST_PATH = "results/blocklist.xlsx"
MASTER_PATH = "results/master_contacts.xlsx"

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def get_body_text(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype in ("text/plain", "message/delivery-status"):
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode("utf-8", errors="ignore")
                except Exception:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="ignore")
        except Exception:
            pass
    return body


def extract_failed_recipients(msg):
    failed = set()
    body = get_body_text(msg)

    for match in re.findall(r"Final-Recipient:\s*rfc822;\s*([^\s;]+)", body, re.IGNORECASE):
        if "@" in match:
            failed.add(match.strip().lower())
    for match in re.findall(r"Original-Recipient:\s*rfc822;\s*([^\s;]+)", body, re.IGNORECASE):
        if "@" in match:
            failed.add(match.strip().lower())
    for match in re.findall(r"X-Failed-Recipients:\s*([^\s,]+)", body, re.IGNORECASE):
        if "@" in match:
            failed.add(match.strip().lower())
    for match in re.findall(
        r"(?:wasn.t delivered to|was not delivered to|couldn.t be delivered to|could not be delivered to)\s+([^\s<>]+@[^\s<>]+)",
        body, re.IGNORECASE
    ):
        failed.add(match.strip().lower())
    for match in re.findall(
        r"<([^<>]+@[^<>]+)>:\s*(?:Host|Remote|Message|SMTP)", body, re.IGNORECASE
    ):
        failed.add(match.strip().lower())

    cleaned = set()
    for addr in failed:
        addr = addr.strip(".,;:<>()[]")
        if EMAIL_REGEX.fullmatch(addr):
            cleaned.add(addr)
    return cleaned


def connect_imap():
    print("Connecting to " + IMAP_HOST + ":" + str(IMAP_PORT) + "...")
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        print("OK IMAP connected")
        return mail
    except Exception as e:
        print("FAIL IMAP connect: " + str(e))
        return None


def fetch_bounces(mail, days_back=30):
    bounces = []
    since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
    folders = ["INBOX", "[Gmail]/Spam", "[Gmail]/All Mail"]
    seen_ids = set()

    for folder in folders:
        try:
            status, _ = mail.select('"' + folder + '"', readonly=True)
            if status != "OK":
                continue
        except Exception:
            continue
        print("   Scanning " + folder + "...")
        try:
            status, data = mail.search(None, '(SINCE "' + since_date + '" FROM "mailer-daemon")')
        except Exception:
            continue
        if status != "OK":
            continue
        msg_ids = data[0].split()
        print("   Found " + str(len(msg_ids)) + " candidate messages")
        for msg_id in msg_ids:
            if msg_id in seen_ids:
                continue
            seen_ids.add(msg_id)
            try:
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                recipients = extract_failed_recipients(msg)
                if recipients:
                    bounces.append((msg, recipients))
            except Exception:
                continue
    return bounces


def load_blocklist():
    try:
        bl = pd.read_excel(BLOCKLIST_PATH)
        return set(bl["Email"].dropna().astype(str).str.lower().unique())
    except Exception:
        return set()


def save_blocklist(emails):
    os.makedirs("results", exist_ok=True)
    df = pd.DataFrame({"Email": sorted(emails), "Reason": "Bounce detected"})
    df.to_excel(BLOCKLIST_PATH, index=False, engine="xlsxwriter")
    print("   Blocklist saved: " + str(len(emails)) + " entries")


def remove_from_master(bad_emails):
    if not os.path.exists(MASTER_PATH):
        print("   Master file not found")
        return 0
    master = pd.read_excel(MASTER_PATH)
    if "Email" not in master.columns:
        return 0
    before = len(master)
    master["Email"] = master["Email"].fillna("").astype(str)
    mask = master["Email"].str.lower().isin(bad_emails)
    master = master[~mask].reset_index(drop=True)
    after = len(master)
    if before != after:
        master.to_excel(MASTER_PATH, index=False, engine="xlsxwriter")
        print("   Removed " + str(before - after) + " bad rows from master file")
    else:
        print("   No rows removed from master file")
    return before - after


def main():
    if not GMAIL_APP_PASSWORD:
        print("FAIL GMAIL_APP_PASSWORD not set")
        sys.exit(1)
    mail = connect_imap()
    if mail is None:
        sys.exit(1)
    try:
        print("Scanning for bounce messages from mailer-daemon...")
        bounces = fetch_bounces(mail, days_back=30)
        print("")
        print("Found " + str(len(bounces)) + " bounce messages")
        if not bounces:
            print("No bounces to process.")
            return
        all_failed = set()
        for msg, recipients in bounces:
            all_failed.update(recipients)
        print("")
        print("Extracted " + str(len(all_failed)) + " unique failed addresses:")
        for addr in sorted(all_failed):
            print("   - " + addr)
        existing = load_blocklist()
        combined = existing | all_failed
        new_additions = all_failed - existing
        print("")
        print("Blocklist update:")
        print("   Existing entries: " + str(len(existing)))
        print("   New additions: " + str(len(new_additions)))
        print("   Total after merge: " + str(len(combined)))
        save_blocklist(combined)
        print("")
        print("Cleaning master_contacts.xlsx...")
        removed = remove_from_master(all_failed)
        print("")
        print("=" * 60)
        print("BOUNCE HANDLING COMPLETE")
        print("=" * 60)
        print("New blocked emails: " + str(len(new_additions)))
        print("Master file rows removed: " + str(removed))
        print("=" * 60)
    finally:
        try:
            mail.logout()
        except Exception:
            pass


if __name__ == "__main__":
    main()
