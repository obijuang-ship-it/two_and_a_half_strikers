import requests
import json
import base64
import os
from datetime import datetime

# ── CONFIG ──────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "TU_TOKEN_AQUI")
REPO         = "obijuang-ship-it/two_and_a_half_strikers"
JSON_PATH    = "goles.json"

PLAYERS = [
    {"owner": "Juan Carlos", "name": "Luis Suárez",     "fotmobId": "792303"},
    {"owner": "Adolfo",      "name": "Dušan Vlahović",  "fotmobId": "737857"},
    {"owner": "Yeye",        "name": "Kylian Mbappé",   "fotmobId": "701154"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.fotmob.com/",
}
# ────────────────────────────────────────────────────────


def fetch_goals(fotmob_id):
    url = f"https://www.fotmob.com/api/playerData?id={fotmob_id}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
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
    print("Consultando FotMob...")
    result = []
    for p in PLAYERS:
        try:
            goles = fetch_goals(p["fotmobId"])
            print(f"  {p['name']}: {goles} goles")
        except Exception as e:
            print(f"  {p['name']}: ERROR ({e})")
            goles = None
        result.append({**p, "goles": goles})

    result.append({"updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")})

    sha = get_file_sha()
    push_json(result, sha)


if __name__ == "__main__":
    main()
