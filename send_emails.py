import os
import sys
import json
import time
import base64
import pandas as pd
import requests
import msal

# ----- CONFIG -----
CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID", "79832521-06f3-4eb8-89f6-20545b6d9a19")
SCOPES = ["https://graph.microsoft.com/Mail.Send", "https://graph.microsoft.com/Mail.ReadWrite"]
AUTHORITY = "https://login.microsoftonline.com/common"
DOCUMENTS_FOLDER = "documents"

SUBJECT = "Student Volunteer Enquiry: 40-Hour Bursary Community Service"

def create_body():
    return """<html>
<body>
<p>Dear Sir/Madam,</p>
<p>I hope this message finds you well.</p>
<p>My name is <strong>Nsuku Mareana</strong>, and I am a Mechanical & Mechatronics Engineering student at the University of Cape Town. My bursary requires me to complete 40 hours of community service with a registered non-profit or community-based organisation, and I am writing to respectfully enquire whether your organisation might be able to host me as a volunteer during the upcoming <strong>June/July holidays</strong>.</p>
<p>I am based in <strong>Randburg, Johannesburg</strong>, and I am very keen to offer my time and energy to support the important work you do in our community. I have a strong interest in contributing to youth development, education, and community care, and I am flexible and willing to assist with any tasks—from administrative support and organising to hands-on assistance with your programmes.</p>
<p>I am available for a maximum of 40 hours over the holiday period, and I would be happy to work around your schedule and needs.</p>
<p>For your reference, I have attached my:</p>
<ul>
<li>CV</li>
<li>Academic Transcript</li>
<li>Reference Letter</li>
</ul>
<p>Should a short call or an email response be possible, I would be very grateful for any guidance or direction you might be able to provide. Even a brief reply would mean a great deal to me.</p>
<p>Thank you for the positive impact you make, and I hope to hear from you soon.</p>
<p>Kind regards,<br>
<strong>Nsuku Mareana</strong><br>
Mechanical & Mechatronics Engineering Student<br>
University of Cape Town<br>
📞 <a href="tel:+27680789360">+27 68 078 9360</a><br>
🔗 <a href="https://www.linkedin.com/in/nsukumareana">LinkedIn Profile</a></p>
</body>
</html>"""

def get_token():
    """Get an access token using the MSAL token cache provided via environment."""
    cache_json = os.getenv("MSAL_TOKEN_CACHE")
    if not cache_json:
        raise Exception("MSAL_TOKEN_CACHE environment variable not set")

    # Deserialize the token cache
    cache = msal.SerializableTokenCache()
    cache.deserialize(cache_json)

    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)

    # Try to get token silently from existing account
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"]

    # If silent fails, try to use refresh token directly (should not be needed)
    # But we can raise an informative error
    raise Exception("Unable to obtain access token from cached credentials. Please refresh the MSAL_TOKEN_CACHE secret.")

def get_attachments():
    """Return list of PDF files in documents folder."""
    import glob
    return glob.glob(os.path.join(DOCUMENTS_FOLDER, "*.pdf"))

def send_email_via_graph(token, to_email, subject, body, attachment_paths):
    """Send email with attachments using Microsoft Graph API."""
    url = "https://graph.microsoft.com/v1.0/me/sendMail"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    message = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": body},
        "toRecipients": [{"emailAddress": {"address": to_email}}],
        "importance": "high",
        "attachments": []
    }

    for att_path in attachment_paths:
        with open(att_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")
        message["attachments"].append({
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": os.path.basename(att_path),
            "contentBytes": content
        })

    payload = {"message": message, "saveToSentItems": True}
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 202:
        return True, "Accepted"
    else:
        return False, f"Error {response.status_code}: {response.text}"

def send_emails(data_file):
    token = get_token()
    print("✅ Authenticated\n")

    # Read contacts
    if data_file.endswith('.xlsx'):
        df = pd.read_excel(data_file)
        contacts = df.to_dict('records')
    else:
        import csv
        with open(data_file, 'r', encoding='utf-8') as f:
            contacts = list(csv.DictReader(f))

    attachments = get_attachments()
    if not attachments:
        print("⚠️ No PDFs in 'documents/'")
        return

    print(f"📧 Sending to {len(contacts)} contacts, {len(attachments)} attachments\n")
    sent, skipped, failed = [], [], []

    for i, c in enumerate(contacts):
        org = c.get('Organisation Name', 'your organisation')
        email_val = c.get('Email', '')
        if not isinstance(email_val, str):
            email_val = str(email_val) if not pd.isna(email_val) else ''
        email = email_val.strip()
        if not email or '@' not in email:
            skipped.append(org)
            continue

        body = create_body()
        ok, msg = send_email_via_graph(token, email, SUBJECT, body, attachments)
        if ok:
            sent.append(f"{org} ({email})")
            print(f"[{i+1}/{len(contacts)}] ✅ {org}")
        else:
            failed.append(f"{org} ({email}) – {msg}")
            print(f"[{i+1}/{len(contacts)}] ❌ {org} – {msg}")

        # Be gentle to the server / avoid rate limits
        time.sleep(2)

    print("\n" + "="*60)
    print("📋 SEND SUMMARY")
    print("="*60)
    print(f"✅ Sent: {len(sent)}")
    for s in sent: print(f"   • {s}")
    if skipped:
        print(f"\n⚠️ Skipped (no email): {len(skipped)}")
        for s in skipped: print(f"   • {s}")
    if failed:
        print(f"\n❌ Failed: {len(failed)}")
        for f in failed: print(f"   • {f}")
    print("\n🎉 All done. Check Outlook Sent Items for high‑priority messages.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python send_emails.py <contacts.xlsx or .csv>")
        sys.exit(1)
    send_emails(sys.argv[1])
