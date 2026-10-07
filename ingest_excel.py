"""
Ingest any Excel from inbox/ into master_contacts.xlsx.
Usage: python3 ingest_excel.py inbox/my_file.xlsx
"""
import pandas as pd
import sys, os

MASTER = 'results/master_contacts.xlsx'

def find_col(df, candidates):
    for c in df.columns:
        for cand in candidates:
            if cand.lower() in str(c).lower():
                return c
    return None

def main(f):
    if not os.path.exists(f):
        print(f"❌ {f} not found"); return
    df_in = pd.read_excel(f)
    print(f"Loaded {len(df_in)} rows. Columns: {list(df_in.columns)}")
    
    col_map = {
        'Organisation Name': find_col(df_in, ['organisation','organization','org','name','company']),
        'Email': find_col(df_in, ['email','e-mail','mail']),
        'Category': find_col(df_in, ['category','type','sector','industry']),
        'Location': find_col(df_in, ['location','city','suburb','area']),
        'Phone': find_col(df_in, ['phone','tel','contact']),
        'Website': find_col(df_in, ['website','url','web']),
    }
    
    df_new = pd.DataFrame()
    for k, v in col_map.items():
        df_new[k] = df_in[v] if v else ''
    df_new['Sent'] = ''
    df_new.loc[df_new['Category'].astype(str).str.strip() == '', 'Category'] = 'Imported'
    df_new.loc[df_new['Location'].astype(str).str.strip() == '', 'Location'] = 'Cape Town'
    
    master = pd.read_excel(MASTER)
    existing = set(master['Email'].astype(str).str.lower().dropna())
    df_new = df_new[df_new['Email'].notna() & (df_new['Email'].astype(str) != '')]
    df_new = df_new[~df_new['Email'].astype(str).str.lower().isin(existing)]
    
    if len(df_new) == 0:
        print("ℹ️  No new contacts (all duplicates)"); return
    
    combined = pd.concat([master, df_new], ignore_index=True)
    combined.to_excel(MASTER, index=False)
    print(f"✅ Added {len(df_new)} new contacts. Total now: {len(combined)}")
    print(df_new[['Organisation Name','Email','Category']].head(20).to_string(index=False))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 ingest_excel.py inbox/file.xlsx"); sys.exit(1)
    main(sys.argv[1])
