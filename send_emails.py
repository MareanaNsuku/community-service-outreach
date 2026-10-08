import os
import sys
import time
import smtplib
import glob
from email.message import EmailMessage
import pandas as pd

# ---------- Brevo SMTP config ----------
SMTP_HOST = "smtp-relay.brevo.com"
SMTP_PORT = 587
BREVO_SMTP_LOGIN = os.getenv("BREVO_SMTP_LOGIN")
BREVO_SMTP_PASSWORD = os.getenv("BREVO_SMTP_PASSWORD")

# From address (must be a verified sender in Brevo)
FROM_EMAIL = os.getenv("SENDER_EMAIL", "mrnnsu001@myuct.ac.za")

DOCUMENTS_FOLDER = "documents"
SUBJECT = "Student Volunteer Enquiry: 40-Hour Bursary Community Service"

# Brevo allows 300/day on free plan; send 8 per category to stay safe
MAX_PER_RUN = 40
SLEEP_BETWEEN = 60  # 1 minute between sends (Brevo handles bulk better)


def create_html_body():
    return """<html><body>
<p>Dear Sir/Madam,</p>
<p>I hope this message finds you well.</p>
<p>My name is <strong>Nsuku Mareana</strong>, and I am a Mechanical &amp; Mechatronics Engineering student at the University of Cape Town. My bursary requires me to complete 40 hours of community service with a registered non-profit or community-based organisation, and I am writing to respectfully enquire whether your organisation might be able to host me as a volunteer on any date between now and <strong>31 October 2026</strong>, as I am required to complete these hours before that deadline.</p>
<p>I am currently based in <strong>Cape Town</strong>, and I am very keen to offer my time and energy to support the important work you do in our community.</p>
<p>I am available for a maximum of 40 hours on any date between now and <strong>31 October 2026</strong>, and I would be happy to work around your schedule and needs.</p>
  <p>For your convenience, my weekly availability is:</p>
  <ul>
    <li><strong>Tuesday:</strong> 12:00 - 17:00</li>
    <li><strong>Wednesday:</strong> 12:00 - 17:00</li>
    <li><strong>Thursday:</strong> 11:00 - 17:00</li>
    <li><strong>Saturday:</strong> 08:00 - 17:00</li>
    <li><strong>Sunday:</strong> 08:00 - 17:00</li>
  </ul>
  <p><em>(I am not available on Mondays and Fridays.)</em></p>
<p>For your reference, I have attached my CV, Academic Transcript, and Reference Letter.</p>
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
    msg.add_alternative(create_html_body(), subtype="html")
    for path in attachments:
        with open(path, "rb") as f:
            data = f.read()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="pdf",
            filename=os.path.basename(path),
        )
    return msg


def connect_smtp():
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=45)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(BREVO_SMTP_LOGIN, BREVO_SMTP_PASSWORD)
        return server
    except Exception as e:
        print("   SMTP connect failed: " + str(e))
        return None


def safe_quit(server):
    if server is None:
        return
    try:
        server.quit()
    except Exception:
        pass


def send_emails(data_file):
    if not BREVO_SMTP_PASSWORD:
        print("ERROR: BREVO_SMTP_PASSWORD not set")
        return
    if not BREVO_SMTP_LOGIN:
        print("ERROR: BREVO_SMTP_LOGIN not set")
        return

    if data_file.endswith(".xlsx"):
        df = pd.read_excel(data_file)
    else:
        df = pd.read_csv(data_file)

    if "Sent" not in df.columns:
        df["Sent"] = ""
    df["Sent"] = df["Sent"].fillna("")

    attachments = glob.glob(os.path.join(DOCUMENTS_FOLDER, "*.pdf"))
    if not attachments:
        print("ERROR: No PDFs in documents/")
        return

    to_send = df[df["Sent"].astype(str).str.lower() != "yes"].head(MAX_PER_RUN)
    if to_send.empty:
        print("No unsent contacts")
        return

    print("Sending to " + str(len(to_send)) + " contacts (max " + str(MAX_PER_RUN) + "/run)")
    print("   Attachments: " + str(len(attachments)) + " PDFs")
    print("   Delay: " + str(SLEEP_BETWEEN) + "s between sends")
    print("   Provider: Brevo SMTP")
    print("   From: " + FROM_EMAIL)
    print("")

    sent = []
    skipped = []
    failed = []

    for i, (idx, row) in enumerate(to_send.iterrows()):
        org = str(row.get("Organisation Name", "your organisation"))
        email = str(row.get("Email", "")).strip()

        if "@" not in email:
            skipped.append(org)
            print("[" + str(i + 1) + "/" + str(len(to_send)) + "] SKIP " + org + " - no email")
            continue

        server = connect_smtp()
        if server is None:
            failed.append(org + ": could not connect")
            print("[" + str(i + 1) + "/" + str(len(to_send)) + "] FAIL " + org + " - could not connect")
            time.sleep(30)
            continue

        try:
            msg = build_message(email, attachments)
            server.send_message(msg)
            df.at[idx, "Sent"] = "Yes"
            sent.append(org + " (" + email + ")")
            print("[" + str(i + 1) + "/" + str(len(to_send)) + "] OK " + org)
        except Exception as e:
            failed.append(org + ": " + str(e))
            print("[" + str(i + 1) + "/" + str(len(to_send)) + "] FAIL " + org + " - " + str(e))
        finally:
            safe_quit(server)

        try:
            if data_file.endswith(".xlsx"):
                df.to_excel(data_file, index=False, engine="xlsxwriter")
            else:
                df.to_csv(data_file, index=False)
        except Exception as e:
            print("   Could not save progress: " + str(e))

        if i < len(to_send) - 1:
            time.sleep(SLEEP_BETWEEN)

    print("")
    print("=" * 60)
    print("SEND SUMMARY")
    print("=" * 60)
    print("Sent: " + str(len(sent)))
    for s in sent:
        print("   - " + s)
    if skipped:
        print("Skipped: " + str(len(skipped)))
    if failed:
        print("Failed: " + str(len(failed)))
        for f in failed:
            print("   - " + f)
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python send_emails.py <file.xlsx>")
        sys.exit(1)
    send_emails(sys.argv[1])
