"""
Safety guard — refuse to send to any contact already marked Sent.
Usage: python3 safe_send.py <batch_file.xlsx>
"""
import pandas as pd
import sys
import os

def main(batch_file):
    if not os.path.exists(batch_file):
        print(f"❌ Batch file not found: {batch_file}")
        sys.exit(1)

    batch = pd.read_excel(batch_file)
    master = pd.read_excel('results/master_contacts.xlsx')

    # Find contacts in batch that are already Sent in master
    sent_emails = set(
        master[master['Sent'].astype(str).str.lower() == 'yes']['Email']
        .astype(str).str.lower().dropna()
    )

    batch_emails = batch['Email'].astype(str).str.lower().dropna()
    duplicates = batch_emails[batch_emails.isin(sent_emails)].unique()

    if len(duplicates) > 0:
        print(f"🚨 REFUSED TO SEND — {len(duplicates)} contacts already marked Sent:")
        for d in duplicates:
            print(f"   ❌ {d}")
        print()
        print("These were already emailed. Remove them from the batch or abort.")
        sys.exit(1)

    print(f"✅ Safe to send — {len(batch)} contacts, none already Sent")
    sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 safe_send.py <batch_file.xlsx>")
        sys.exit(1)
    main(sys.argv[1])
