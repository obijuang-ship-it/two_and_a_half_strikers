import requests
import json
import base64
import os
import time
from datetime import datetime

# ── CONFIG ──────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO         = "obijuang-ship-it/two_and_a_half_strikers"
JSON_PATH    = "goles.json"

PLAYERS = [
    {"owner": "Juan Carlos", "name": "Luis Suárez",     "fotmobId": "792303"},
    {"owner": "Adolfo",      "name": "Dušan Vlahović",  "fotmobId": "737857"},
    {"owner": "Yeye",        "name": "Kylian Mbappé",   "fotmobId": "701154"},
]
# ────────────────────────────────────────────────────────


def get_fotmob_token():
    """Get FotMob auth token from their init endpoint"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9",
        "Origin": "https://www.fotmob.com",
        "Referer": "https://www.fotmob.com/",
    })
    # Visit homepage first to get cookies
    session.get("https://www.fotmob.com", timeout=10)
    time.sleep(1)
    return session


def fetch_goals(session, fotmob_id):
    url = f"https://www.fotmob.com/api/playerData?id={fotmob_id}"
    r = session.get(url, timeout=15)
    print(f"  Status: {r.status_code}, Content-Type: {r.headers.get('Content-Type','')}")
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code}")
    
    # Check if we got JSON or HTML
    ct = r.headers.get('Content-Type', '')
    if 'html' in ct:
        raise Exception("Got HTML instead of JSON — blocked")
    
    data = r.json()
    total = 0
    entries = (data.get("careerStatistics", {})
                   .get("seasonEntries", [{}])[0]
                   .get("entries", []))
    for e in entries:
        total += e.get("stats", {}).get("Goals", 0)
    return total


def get_file_sha():
    url = f"https://api.github.com/repos/{REPO}/contents/{JSON_PATH}"
    r = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if r.status_code == 200:
        return r.json()["sha"]
    return None


def push_json(content, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{JSON_PATH}"
    encoded = base64.b64encode(json.dumps(content, ensure_ascii=False, indent=2).encode()).decode()
    payload = {
        "message": f"update: goles {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
        "content": encoded,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, json=payload, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    r.raise_for_status()
    print("✓ goles.json actualizado en GitHub")


def main():
    print("Iniciando sesión en FotMob...")
    session = get_fotmob_token()
    
    # Load existing goles to keep last known values if fetch fails
    sha = get_file_sha()
    existing = {}
    if sha:
        url = f"https://api.github.com/repos/{REPO}/contents/{JSON_PATH}"
        r = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode()
            for item in json.loads(raw):
                if "fotmobId" in item and item.get("goles") is not None:
                    existing[item["fotmobId"]] = item["goles"]

    print("Consultando FotMob...")
    result = []
    for p in PLAYERS:
        try:
            time.sleep(1)  # be polite
            goles = fetch_goals(session, p["fotmobId"])
            print(f"  ✓ {p['name']}: {goles} goles")
        except Exception as e:
            print(f"  ✗ {p['name']}: ERROR ({e}) — manteniendo valor anterior")
            goles = existing.get(p["fotmobId"], 0)
        result.append({**p, "goles": goles})

    result.append({"updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")})
    push_json(result, sha)


if __name__ == "__main__":
    main()
