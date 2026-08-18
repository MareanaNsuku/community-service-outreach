import sys, argparse, pandas as pd

MASTER = "results/master_contacts.xlsx"
BLOCKLIST = "results/blocklist.xlsx"

def load_blocklist():
    try:
        bl = pd.read_excel(BLOCKLIST)
        return set(bl['Email'].str.lower().unique())
    except:
        return set()

def filter_master(location, category, output_file, keyword=None):
    df = pd.read_excel(MASTER)
    
    # 1. Broad location filter (exact or contains)
    mask_loc = df['Location'].str.contains(location, case=False, na=False)
    df_loc = df[mask_loc].copy()
    
    # 2. If a sub‑area keyword is given, further narrow down:
    #    Search in Organisation Name, Location, and (if exists) Address
    if keyword:
        # Combine text columns
        text_cols = []
        if 'Organisation Name' in df_loc.columns:
            text_cols.append(df_loc['Organisation Name'].astype(str))
        if 'Location' in df_loc.columns:
            text_cols.append(df_loc['Location'].astype(str))
        if 'Address' in df_loc.columns:
            text_cols.append(df_loc['Address'].astype(str))
        if text_cols:
            combined = pd.concat(text_cols, axis=1).apply(' '.join, axis=1)
            mask_keyword = combined.str.contains(keyword, case=False, na=False)
            df_loc = df_loc[mask_keyword]
    
    # 3. Category filter
    mask_cat = df_loc['Category'].str.contains(category, case=False, na=False)
    df_loc = df_loc[mask_cat]
    
    # 4. Only rows with an email
    df_loc = df_loc[df_loc['Email'].notna() & (df_loc['Email'].str.contains('@'))]
    
    # 5. Remove previously sent / blocked emails
    blocked_emails = load_blocklist()
    if blocked_emails:
        df_loc = df_loc[~df_loc['Email'].str.lower().isin(blocked_emails)]
    
    if df_loc.empty:
        print(f"No new contacts found for {location} / {category}" + (f" (keyword: {keyword})" if keyword else ""))
        return False
    
    # Max 25
    df_out = df_loc.head(25).copy()
    
    # Ensure standard columns
    cols = ['Organisation Name', 'Category', 'Location', 'Email', 'Phone', 'Website', 'Sent']
    for c in cols:
        if c not in df_out.columns:
            df_out[c] = ''
    df_out = df_out[cols]
    df_out.to_excel(output_file, index=False, engine='xlsxwriter')
    print(f"Saved {len(df_out)} new contacts to {output_file}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("location")
    parser.add_argument("category")
    parser.add_argument("--output", required=True)
    parser.add_argument("--keyword", help="Further narrow results to a sub-area or street name", default=None)
    args = parser.parse_args()
    filter_master(args.location, args.category, args.output, args.keyword)
