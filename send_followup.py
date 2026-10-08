#!/usr/bin/env python3
"""
Follow-up campaign for orgs that were sent the original email but have not replied.
Gated: only sends if MIN_DAYS_SINCE days have passed since FollowUpDate gate.
"""
import os, sys, time, glob
from email.message import EmailMessage
from datetime import datetime, timedelta
import pandas as pd
from send_emails import (
    BREVO_SMTP_LOGIN, BREVO_SMTP_PASSWORD, FROM_EMAIL,
    connect_smtp, safe_quit, DOCUMENTS_FOLDER, load_blocklist,
)

SUBJECT = "Follow-up: Student Volunteer Enquiry - 40-Hour Bursary Community Service"
MIN_DAYS_SINCE = 5
MAX_PER_RUN = 40
SLEEP_BETWEEN = 60
GATE_FILE = ".followup_gate"   # created after first run to enforce 5-day wait


def create_followup_html():
    return """<html><body>
<p>Dear Sir/Madam,</p>
<p>I hope this message finds you well. I am writing to gently follow up on my earlier email regarding the 40 hours of community service I need to complete for my bursary before <strong>31 October 2026</strong>.</p>
<p>I understand you are very busy, and I do not wish to be a nuisance &mdash; I simply wanted to make sure my earlier message did not get lost. If your organisation is unable to host me, I would be very grateful if you could point me toward another organisation that might be able to help.</p>
<p>For your convenience, my weekly availability is:</p>
<ul>
  <li><strong>Tuesday:</strong> 12:00 - 17:00</li>
  <li><strong>Wednesday:</strong> 12:00 - 17:00</li>
  <li><strong>Thursday:</strong> 11:00 - 17:00</li>
  <li><strong>Saturday:</strong> 08:00 - 17:00</li>
  <li><strong>Sunday:</strong> 08:00 - 17:00</li>
</ul>
<p><em>(I am not available on Mondays and Fridays.)</em></p>
<p>My CV and supporting documents are attached again for your convenience.</p>
<p>Thank you for your time and consideration.</p>
<p>Kind regards,<br>
<strong>Nsuku Mareana</strong><br>
Mechanical &amp; Mechatronics Engineering Student<br>
University of Cape Town<br>
Phone: <a href="tel:+27680789360">+27 68 078 9360</a><br>
LinkedIn: <a href="https://www.linkedin.com/in/nsukumareana">nsukumareana</a></p>
</body></html>"""


def build_message(to_email, attachments):
    msg = EmailMessage()
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = SUBJECT
    msg["Importance"] = "High"
    msg["X-Priority"] = "1"
    msg.set_content("Please view this message in HTML.")
    msg.add_alternative(create_followup_html(), subtype="html")
    for path in attachments:
        with open(path, "rb") as f:
            data = f.read()
        msg.add_attachment(
            data, maintype="application", subtype="pdf",
            filename=os.path.basename(path),
        )
    return msg


def gate_check():
    """Refuse to run until MIN_DAYS_SINCE after last send."""
    if not os.path.exists(GATE_FILE):
        # First run: create gate, tell user to wait
        with open(GATE_FILE, "w") as f:
            f.write(datetime.now().isoformat())
        print(f"📅 Gate created. Follow-up can run on "
              f"{(datetime.now() + timedelta(days=MIN_DAYS_SINCE)).date()}.")
        print("   Re-run this script on that date to send follow-ups.")
        return False
    with open(GATE_FILE) as f:
        last = datetime.fromisoformat(f.read().strip())
    elapsed = (datetime.now() - last).days
    if elapsed < MIN_DAYS_SINCE:
        print(f"⏳ Too soon: {elapsed} days since last run. "
              f"Need {MIN_DAYS_SINCE}.")
        return False
    return True


def send_followups(data_file):
    if not BREVO_SMTP_PASSWORD or not BREVO_SMTP_LOGIN:
        print("ERROR: Brevo creds not set. Run: set -a; source .env.local; set +a")
        return

    if not gate_check():
        return

    df = pd.read_excel(data_file)
    for col in ("FollowUpSent", "Replied", "Sent"):
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)

    # Eligible: original was sent, no reply, no follow-up yet, has email
    mask = (
        (df["Sent"].str.lower() == "yes")
        & (df["FollowUpSent"].str.lower() != "yes")
        & (df["Replied"].str.lower() != "yes")
        & (df["Email"].astype(str).str.contains("@", na=False))
    )
    blocklist = load_blocklist()
    df["_email_lc"] = df["Email"].astype(str).str.lower().str.strip()
    mask = mask & (~df["_email_lc"].isin(blocklist))
    to_send = df[mask].head(MAX_PER_RUN)
    df.drop(columns=["_email_lc"], inplace=True, errors="ignore")
    if to_send.empty:
        print("No eligible contacts for follow-up.")
        return

    attachments = glob.glob(os.path.join(DOCUMENTS_FOLDER, "*.pdf"))
    print(f"Follow-up send: {len(to_send)} contacts "
          f"(max {MAX_PER_RUN}/run, {SLEEP_BETWEEN}s delay)")

    sent, failed = [], []
    for i, (idx, row) in enumerate(to_send.iterrows()):
        org = str(row.get("Organisation Name", "?"))
        email = str(row.get("Email", "")).strip()
        server = connect_smtp()
        if server is None:
            failed.append(f"{org}: connect failed")
            time.sleep(30)
            continue
        try:
            msg = build_message(email, attachments)
            server.send_message(msg)
            df.at[idx, "FollowUpSent"] = "Yes"
            df.at[idx, "FollowUpDate"] = datetime.now().strftime("%Y-%m-%d")
            sent.append(f"{org} ({email})")
            print(f"[{i+1}/{len(to_send)}] OK {org}")
        except Exception as e:
            failed.append(f"{org}: {e}")
            print(f"[{i+1}/{len(to_send)}] FAIL {org} - {e}")
        finally:
            safe_quit(server)

        try:
            df.to_excel(data_file, index=False, engine="xlsxwriter")
        except Exception as e:
            print(f"   save error: {e}")

        if i < len(to_send) - 1:
            time.sleep(SLEEP_BETWEEN)

    # Reset gate to today (so next follow-up waits 5 days again)
    with open(GATE_FILE, "w") as f:
        f.write(datetime.now().isoformat())

    print("\n" + "=" * 60)
    print(f"FOLLOW-UP SUMMARY: Sent {len(sent)}, Failed {len(failed)}")
    for s in sent:
        print(f"   - {s}")
    for f in failed:
        print(f"   ! {f}")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python send_followup.py results/master_contacts.xlsx")
        sys.exit(1)
    send_followups(sys.argv[1])
