import requests
import json
import re
import time
import os
import base64
from datetime import datetime

# === CONFIGURACIÓN ===
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
REPO = "obijuang-ship-it/two_and_a_half_strikers"
JSON_PATH = "goles.json"

PLAYERS = [
    {"owner": "Juan Carlos", "name": "Luis Suárez",    "fotmobId": "792303", "slug": "luis-suarez"},
    {"owner": "Adolfo",      "name": "Dušan Vlahović", "fotmobId": "737857", "slug": "dusan-vlahovic"},
    {"owner": "Yeye",        "name": "Kylian Mbappé",  "fotmobId": "701154", "slug": "kylian-mbappe"},
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def find_season_entries(obj):
    if isinstance(obj, dict):
        if "seasonEntries" in obj:
            return obj["seasonEntries"]
        for v in obj.values():
            res = find_season_entries(v)
            if res:
                return res
    elif isinstance(obj, list):
        for item in obj:
            res = find_season_entries(item)
            if res:
                return res
    return None


def fetch_player_stats(pid, slug):
    html_url = f"https://www.fotmob.com/es/players/{pid}/{slug}"
    html = requests.get(html_url, headers=HEADERS, timeout=15)
    html.raise_for_status()

    match = re.search(r'"buildId":"(.*?)"', html.text)
    if not match:
        raise Exception("No se encontró buildId")
    build_id = match.group(1)

    json_url = f"https://www.fotmob.com/_next/data/{build_id}/es/players/{pid}/{slug}.json"
    r = requests.get(json_url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    data = r.json()

    season_entries = find_season_entries(data)
    if not season_entries:
        raise KeyError("No se encontró 'seasonEntries'")

    selected = None
    for s in season_entries:
        if "2025/2026" in s.get("seasonName", ""):
            selected = s
            break
    if not selected and season_entries:
        selected = season_entries[-1]

    goals = assists = matches = 0
    if selected:
        goals   = int(selected.get("goals", 0))
        assists = int(selected.get("assists", 0))
        matches = int(selected.get("appearances", 0))

        if not any([goals, assists, matches]):
            for stat in selected.get("teamStats", []):
                title = stat.get("title", "").lower()
                if "goles" in title or "goals" in title:
                    goals = int(stat.get("value", 0))
                elif "asist" in title:
                    assists = int(stat.get("value", 0))
                elif "partidos" in title or "apps" in title or "appearances" in title:
                    matches = int(stat.get("value", 0))

    return {"goles": goals, "asistencias": assists, "partidos": matches}


def get_github_file():
    url = f"https://api.github.com/repos/{REPO}/contents/{JSON_PATH}"
    r = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if r.status_code == 200:
        data = r.json()
        content = json.loads(base64.b64decode(data["content"]).decode())
        return content, data["sha"]
    return [], None


def push_json(content, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{JSON_PATH}"
    encoded = base64.b64encode(
        json.dumps(content, ensure_ascii=False, indent=2).encode()
    ).decode()
    payload = {
        "message": f"update: goles {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
        "content": encoded,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, json=payload, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    r.raise_for_status()
    print("✓ goles.json actualizado en GitHub")


def send_telegram(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️  Sin token de Telegram, no se envía notificación")
        return
    requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        params={"chat_id": CHAT_ID, "text": msg},
        timeout=10
    )
    print(f"📢 Telegram: {msg}")


def main():
    print("⚽ Extrayendo estadísticas desde FotMob…\n")

    old_data, sha = get_github_file()
    old_goals = {}
    for item in old_data:
        if "fotmobId" in item:
            old_goals[item["fotmobId"]] = item.get("goles", 0)

    result = []
    nuevos_goles = []

    for p in PLAYERS:
        print(f"Buscando {p['name']}…")
        try:
            stats = fetch_player_stats(p["fotmobId"], p["slug"])
            goles = stats["goles"]
            print(f"  ✓ {p['name']}: {goles} goles · {stats['asistencias']} asist · {stats['partidos']} PJ")

            prev = old_goals.get(p["fotmobId"], 0)
            if goles > prev:
                nuevos_goles.append((p["name"], p["owner"], goles - prev))

        except Exception as e:
            print(f"  ✗ Error: {e} — manteniendo valor anterior")
            goles = old_goals.get(p["fotmobId"], 0)
            stats = {"goles": goles, "asistencias": 0, "partidos": 0}

        result.append({
            "owner":    p["owner"],
            "name":     p["name"],
            "fotmobId": p["fotmobId"],
            "goles":    stats["goles"],
        })
        time.sleep(1)

    result.append({"updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")})
    push_json(result, sha)

    # Notificaciones Telegram
    if nuevos_goles:
        for name, owner, n in nuevos_goles:
            mensajes = [
                f"⚽ ¡{name} ha marcado {n} gol{'es' if n > 1 else ''}! Entra a la app a ver cómo va la apuesta 👀",
                f"🔥 ¡Goool de {name}! ¿Quién va pagando la cena? Compruébalo en la app 🍽️",
                f"💥 {name} suma {n} gol{'es' if n > 1 else ''} más. La cosa se pone interesante... 👀",
            ]
            msg = mensajes[hash(name) % len(mensajes)]
            send_telegram(msg)
    else:
        print("ℹ️  Sin nuevos goles hoy, no se envía notificación.")


if __name__ == "__main__":
    main()
