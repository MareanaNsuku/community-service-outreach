import pandas as pd, os, glob

master_path = "results/master_contacts.xlsx"
if not os.path.exists(master_path):
    print("No master file, skipping sync")
    exit(0)

master = pd.read_excel(master_path)
updated = 0

for auto_file in glob.glob("results/auto_*.xlsx"):
    try:
        auto = pd.read_excel(auto_file)
        for _, row in auto.iterrows():
            if str(row.get("Sent", "")).lower() == "yes":
                mask = master["Email"] == row["Email"]
                if mask.any() and master.loc[mask, "Sent"].astype(str).str.lower().iloc[0] != "yes":
                    master.loc[mask, "Sent"] = "Yes"
                    updated += 1
                    print(f"Synced: {row['Organisation Name']}")
    except Exception as e:
        print(f"Could not process {auto_file}: {e}")

if updated > 0:
    master.to_excel(master_path, index=False)
    print(f"Master updated: {updated} rows synced")
else:
    print("No rows to sync")
