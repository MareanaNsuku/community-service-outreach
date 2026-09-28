import os, sys, time, smtplib, glob
from email.message import EmailMessage
import pandas as pd

# ---------- Gmail SMTP config ----------
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
GMAIL_USER = os.getenv("GMAIL_USER", "mareanansuku@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

DOCUMENTS_FOLDER = "documents"
SUBJECT = "Student Volunteer Enquiry: 40-Hour Bursary Community Service"

MAX_PER_RUN = 10
SLEEP_BETWEEN = 300


def create_html_body():
    return """<html><body>
<p>Dear Sir/Madam,</p>
<p>I hope this message finds you well.</p>
<p>My name is <strong>Nsuku Mareana</strong>, and I am a Mechanical &amp; Mechatronics Engineering student at the University of Cape Town. My bursary requires me to complete 40 hours of community service with a registered non-profit or community-based organisation, and I am writing to respectfully enquire whether your organisation might be able to host me as a volunteer on any date between now and <strong>31 October 2026</strong>, as I am required to complete these hours before that deadline.</p>
<p>I am currently based in <strong>Cape Town</strong>, and I am very keen to offer my time and energy to support the important work you do in our community.</p>
<p>I am available for a maximum of 40 hours on any date between now and <strong>31 October 2026</strong>, and I would be happy to work around your schedule and needs.</p>
<p>For your reference, I have attached my CV, Academic Transcript, and Reference Letter.</p>
<p>Thank you for your time and consideration.</p>
<p>Kind regards,<br>
<strong>Nsuku Mareana</strong><br>
Mechanical &amp; Mechatronics Engineering Student<br>
University of Cape Town<br>
📞 <a href="tel:+27680789360">+27 68 078 9360</a><br>
🔗 <a href="https://www.linkedin.com/in/nsukumareana">LinkedIn Profile</a></p>
</body></html>"""


def build_message(to_email, attachments):
    msg = EmailMessage()
    msg["From"] = GMAIL_USER
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
    """Create a fresh SMTP connection. Returns None on failure."""
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=45)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        return server
    except Exception as e:
        print(f"   ⚠️ SMTP connect failed: {e}")
        return None


def safe_quit(server):
    """Close the SMTP connection quietly."""
    if server is None:
        return
    try:
        server.quit()
    except Exception:
        pass


def send_emails(data_file):
    if not GMAIL_APP_PASSWORD:
        print("❌ GMAIL_APP_PASSWORD not set")
        return

    # Read contacts
    if data_file.endswith(".xlsx"):
        df = pd.read_excel(data_file)
    else:
        df = pd.read_csv(data_file)

    if "Sent" not in df.columns:
        df["Sent"] = ""
    df["Sent"] = df["Sent"].fillna("")

    attachments = glob.glob(os.path.join(DOCUMENTS_FOLDER, "*.pdf"))
    if not attachments:
        print("❌ No PDFs in documents/")
        return

    to_send = df[df["Sent"].astype(str).str.lower() != "yes"].head(MAX_PER_RUN)
    if to_send.empty:
        print("📭 No unsent contacts")
        return

    print(f"📧 Sending to {len(to_send)} contacts (max {MAX_PER_RUN}/run)")
    print(f"   Attachments: {len(attachments)} PDFs")
    print(f"   Delay: {SLEEP_BETWEEN}s between sends")
    print(f"   Each email gets a fresh SMTP connection\n")

    sent, skipped, failed = [], [], []

    for i, (idx, row) in enumerate(to_send.iterrows()):
        org = str(row.get("Organisation Name", "your organisation"))
        email = str(row.get("Email", "")).strip()

        if "@" not in email:
            skipped.append(org)
            print(f"[{i+1}/{len(to_send)}] ⚠️ Skip {org} – no valid email")
            continue

        # --- FRESH CONNECTION for every email ---
        server = connect_smtp()
        if server is None:
            failed.append(f"{org}: could not connect to SMTP")
            print(f"[{i+1}/{len(to_send)}] ❌ {org} – could not connect")
            time.sleep(30)
            continue

        try:
            msg = build_message(email, attachments)
            server.send_message(msg)
            df.at[idx, "Sent"] = "Yes"
            sent.append(f"{org} ({email})")
            print(f"[{i+1}/{len(to_send)}] ✅ {org}")
        except Exception as e:
            failed.append(f"{org}: {e}")
            print(f"[{i+1}/{len(to_send)}] ❌ {org} – {e}")
        finally:
            safe_quit(server)

        # Save progress immediately after each send
        try:
            if data_file.endswith(".xlsx"):
                df.to_excel(data_file, index=False, engine="xlsxwriter")
            else:
                df.to_csv(data_file, index=False)
        except Exception as e:
            print(f"   ⚠️ Could not save progress: {e}")

        if i < len(to_send) - 1:
            time.sleep(SLEEP_BETWEEN)

    print("\n" + "=" * 60)
    print("📋 SEND SUMMARY")
    print("=" * 60)
    print(f"✅ Sent: {len(sent)}")
    if sent:
        for s in sent:
            print(f"   • {s}")
    if skipped:
        print(f"\n⚠️ Skipped: {len(skipped)}")
        for s in skipped:
            print(f"   • {s}")
    if failed:
        print(f"\n❌ Failed: {len(failed)}")
        for f in failed:
            print(f"   • {f}")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python send_emails.py <file.xlsx>")
        sys.exit(1)
    send_emails(sys.argv[1])
