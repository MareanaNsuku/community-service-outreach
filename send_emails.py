
import os, json

TOKEN_CACHE_FROM_ENV = os.getenv("MSAL_TOKEN_CACHE")
if TOKEN_CACHE_FROM_ENV:
    os.makedirs("o365_token", exist_ok=True)
    with open("o365_token/o365_token.txt", "w") as f:
        f.write(TOKEN_CACHE_FROM_ENV)

import time, os, sys, glob, json, base64, pandas as pd
from dotenv import load_dotenv
import msal, requests
from O365 import Account, FileSystemTokenBackend

load_dotenv()
CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID")
DOCUMENTS_FOLDER = "documents"
SCOPES = ["https://graph.microsoft.com/Mail.Send", "https://graph.microsoft.com/Mail.ReadWrite"]
AUTHORITY = "https://login.microsoftonline.com/common"
CACHE_FILE = "msal_token_cache.json"

SUBJECT = "Student Volunteer Enquiry: 40-Hour Bursary Community Service"

def create_body(org_name):
    return f"""<html>
<body>
<p>Dear Volunteer Coordinator,</p>
<p>I hope this message finds you well.</p>
<p>My name is <strong>Nsuku Mareana</strong>, and I am a Mechanical & Mechatronics Engineering student at the University of Cape Town. My bursary requires me to complete 40 hours of community service with a registered non-profit or community-based organization, and I am very keen to offer my time to support the vital work that <strong>{org_name}</strong> does in our community.</p>
<p>I have a strong interest in contributing to youth development, education, and community care, and I am flexible and willing to assist with any tasks—from administrative support and organizing to hands-on assistance with your programmes.</p>
<p>For convenience, I am generally available during the following times:</p>
<ul>
<li>Weekdays: 14:00 – 17:00</li>
<li>Weekend: 10:00 – 15:00</li>
</ul>
<p>Should another time be more suitable, I would be happy to accommodate where possible. If your organization is currently able to host a volunteer, I would be grateful for the opportunity to briefly discuss how I can contribute. Even a short response or a redirection to the appropriate person would be greatly appreciated.</p>
<p>For ease of reference, I have attached my:</p>
<ul>
<li>CV</li>
<li>Academic Transcript</li>
<li>Reference Letter</li>
</ul>
<p>Thank you for the positive impact you make, and I hope to hear from you soon.</p>
<p>Kind regards,<br>
<strong>Nsuku Mareana</strong><br>
Mechanical & Mechatronics Engineering Student<br>
University of Cape Town<br>
📞 <a href="tel:+27680789360">+27 68 078 9360</a><br>
🔗 <a href="https://www.linkedin.com/in/nsukumareana">LinkedIn Profile</a></p>
</body>
</html>"""

def load_cache():
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache.deserialize(f.read())
    return cache

def save_cache(cache):
    if cache:
        try:
            with open(CACHE_FILE, "w") as f:
                f.write(cache.serialize())
        except: pass

def get_token():
    # Try to get token from MSAL_TOKEN_CACHE environment variable (GitHub secret)
    cache_json = os.getenv("MSAL_TOKEN_CACHE")
    if cache_json:
        try:
            os.makedirs("o365_token", exist_ok=True)
            with open("o365_token/o365_token.txt", "w") as f:
                f.write(cache_json)
        except:
            pass

    # Use FileSystemTokenBackend with the token file
    token_backend = FileSystemTokenBackend(token_path=TOKEN_PATH, token_filename="o365_token.txt")
    account = Account((CLIENT_ID, None), token_backend=token_backend)
    if account.is_authenticated:
        return account.connection.get_access_token()

    # If no valid token, fall back to device code flow
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=msal.SerializableTokenCache())
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise Exception("Failed to create device flow")
    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise Exception(f"Authentication failed: {result.get('error_description', 'Unknown')}")
    # Save token for future use (optional)
    os.makedirs(TOKEN_PATH, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        f.write(json.dumps(result))
    return result["access_token"]


def get_attachments():
    return glob.glob(os.path.join(DOCUMENTS_FOLDER, "*.pdf"))

def send_email_via_graph(token, to_email, subject, body, attachment_paths):
    url = "https://graph.microsoft.com/v1.0/me/sendMail"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
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
    r = requests.post(url, headers=headers, json=payload)
    return r.status_code == 202, f"Error {r.status_code}: {r.text}"

def send_emails(data_file):
    token = get_token()
    print("✅ Authenticated\n")
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
        # Convert NaN or float to empty string
        if not isinstance(email_val, str):
            email_val = str(email_val) if not pd.isna(email_val) else ''
        email = email_val.strip()
        if not email or '@' not in email:
            skipped.append(org)
            continue
        body = create_body(org)
        ok, msg = send_email_via_graph(token, email, SUBJECT, body, attachments)
        if ok:
            sent.append(f"{org} ({email})")
            print(f"[{i+1}/{len(contacts)}] ✅ {org}")
        else:
            failed.append(f"{org} ({email}) – {msg}")
            print(f"[{i+1}/{len(contacts)}] ❌ {org} – {msg}")
        time.sleep(30)
    print("\n" + "="*60)
    print("📋 SEND SUMMARY")
    print("="*60)
    print(f"✅ Sent: {len(sent)}")
    for s in sent: print("   •", s)
    if skipped:
        print(f"\n⚠️ Skipped (no email): {len(skipped)}")
        for s in skipped: print("   •", s)
    if failed:
        print(f"\n❌ Failed: {len(failed)}")
        for f in failed: print("   •", f)
    print("\n🎉 All done. Check Outlook Sent Items for high‑priority messages.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python send_emails.py <contacts.xlsx or .csv>")
        sys.exit(1)
    send_emails(sys.argv[1])
