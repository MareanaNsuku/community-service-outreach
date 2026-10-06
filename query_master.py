import sys
import argparse
import pandas as pd

MASTER = "results/master_contacts.xlsx"
BLOCKLIST = "results/blocklist.xlsx"


def load_blocklist():
    try:
        bl = pd.read_excel(BLOCKLIST)
        return set(bl["Email"].dropna().astype(str).str.lower().unique())
    except Exception:
        return set()


def filter_master(location, category, output_file):
    df = pd.read_excel(MASTER)

    for c in ["Organisation Name", "Category", "Location", "Email", "Phone", "Website", "Sent"]:
        if c not in df.columns:
            df[c] = ""

    mask_loc = pd.Series([True] * len(df))  # Location filter disabled
    df_loc = df[mask_loc].copy()

    mask_cat = df_loc["Category"].astype(str).str.contains(category, case=False, na=False)
    df_loc = df_loc[mask_cat]

    df_loc = df_loc[df_loc["Email"].notna()]
    df_loc["Email"] = df_loc["Email"].astype(str)
    df_loc = df_loc[df_loc["Email"].str.contains("@", na=False)]

    df_loc = df_loc[df_loc["Sent"].astype(str).str.lower() != "yes"]

    blocked = load_blocklist()
    if blocked:
        df_loc = df_loc[~df_loc["Email"].str.lower().isin(blocked)]

    if df_loc.empty:
        print("No new contacts found for " + location + " / " + category)
        return False

    df_out = df_loc.head(25).copy()
    cols = ["Organisation Name", "Category", "Location", "Email", "Phone", "Website", "Sent"]
    df_out = df_out[cols]
    df_out.to_excel(output_file, index=False, engine="xlsxwriter")
    print("Saved " + str(len(df_out)) + " new contacts to " + output_file)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("location")
    parser.add_argument("category")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    filter_master(args.location, args.category, args.output)
