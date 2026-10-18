#!/bin/bash
cd /workspaces/community-service-outreach
set -a; source .env.local; set +a
python3 -c "from serpapi_quota import get_quota; q=get_quota(force=True); print(f\"SerpApi: {q['remaining']}/{q['total']} remaining\" if q['ok'] else f'Error: {q.get(\"error\")}')"
