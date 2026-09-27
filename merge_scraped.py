import sys, os
import pandas as pd

def load_blocklist():
    try:
        bl = pd.read_excel("results/blocklist.xlsx")
        return set(bl["Email"].str.lower().dropna().unique())
    except Exception:
        return set()

def merge(scraped_file, output_file):
    df = pd.read_excel(scraped_file)
    df = df[df["Email"].notna() & (df["Email"].astype(str).str.contains("@"))]

    blocked = load_blocklist()
    if blocked:
        df = df[~df["Email"].str.lower().isin(blocked)]

    df = df.head(25).reset_index(drop=True)

    if df.empty:
        print("No new contacts after filtering. Nothing to send.")
        sys.exit(1)

    df["Sent"] = ""
    df.to_excel(output_file, index=False, engine="xlsxwriter")
    print(f"Prepared {len(df)} contacts for sending -> {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python merge_scraped.py <scraped_file.xlsx> <output_file.xlsx>")
        sys.exit(1)
    merge(sys.argv[1], sys.argv[2])
