import sys, os
import pandas as pd

def load_blocklist():
    try:
        bl = pd.read_excel("results/blocklist.xlsx")
        return set(bl["Email"].dropna().astype(str).str.lower().unique())
    except Exception:
        return set()

def merge(scraped_file, output_file):
    df = pd.read_excel(scraped_file)
    
    # Ensure Email column exists and is string type
    if "Email" not in df.columns:
        df["Email"] = ""
    df["Email"] = df["Email"].fillna("").astype(str)
    
    # Keep only rows with @ in Email
    df = df[df["Email"].str.contains("@", na=False)]
    
    # Remove blocklisted emails
    blocked = load_blocklist()
    if blocked:
        df = df[~df["Email"].str.lower().isin(blocked)]
    
    # Remove obvious garbage (URLs, single chars before @)
    df = df[~df["Email"].str.contains(r"\.(png|jpg|gif|css|js)$", regex=True, na=False)]
    df = df[df["Email"].str.len() > 5]
    
    df = df.head(25).reset_index(drop=True)
    
    if df.empty:
        print("No new contacts after filtering. Nothing to send.")
    return  # exit 0 — not an error
        sys.exit(1)
    
    df["Sent"] = ""
    df.to_excel(output_file, index=False, engine="xlsxwriter")
    print(f"Prepared {len(df)} contacts for sending -> {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python merge_scraped.py <scraped.xlsx> <output.xlsx>")
        sys.exit(1)
    merge(sys.argv[1], sys.argv[2])
