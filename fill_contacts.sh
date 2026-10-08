#!/bin/bash
cd /workspaces/community-service-outreach

CSV="new_contacts.csv"
> "$CSV"
echo "Organisation Name,Email,Suburb" >> "$CSV"

echo "=================================================="
echo "  Mowbray / Rondebosch contact collector"
echo "=================================================="
echo "Type 'done' at any prompt to finish."
echo ""

i=1
while true; do
  echo "--- Contact #$i ---"
  read -p "Organisation Name (or 'done'): " name
  [ "$name" = "done" ] && break
  [ -z "$name" ] && echo "⚠️  Empty, try again" && continue

  read -p "Email: " email
  [ "$email" = "done" ] && break
  if [[ "$email" != *"@"* ]]; then
    echo "⚠️  Not a valid email (needs @). Skipping."
    continue
  fi

  read -p "Suburb (Mowbray / Rondebosch): " suburb
  [ "$suburb" = "done" ] && break
  lc=$(echo "$suburb" | tr '[:upper:]' '[:lower:]' | xargs)
  if [ "$lc" != "mowbray" ] && [ "$lc" != "rondebosch" ]; then
    echo "⚠️  Only 'Mowbray' or 'Rondebosch' allowed. Skipping."
    continue
  fi
  # Normalise capitalisation
  if [ "$lc" = "mowbray" ]; then suburb="Mowbray"; else suburb="Rondebosch"; fi

  echo "$name,$email,$suburb" >> "$CSV"
  echo "✅ Added: $name"
  echo ""
  i=$((i+1))
done

echo ""
echo "=================================================="
echo "Saved to $CSV:"
echo "=================================================="
cat "$CSV"
