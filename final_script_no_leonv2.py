import requests
import hashlib
import json
import datetime
import os

WEBHOOK_URL = "https://discord.com/api/webhooks/1440463711645990912/g__qrs1k7gpeHO9xMY0TahIYjVoA0NNTl0mGcn2us80NeTb9hly_lDI41trpuc4oumH3"

ORT = "knapp"
BASE_URL = "https://www.das-schmeckt-mir.ruhr/images/pdf/speise_{ort}/{kw}_KW_Speiseplan{year}_Knapp.jpg"

# mögliche Dateiendungen durchprobieren
EXTENSIONS = [".jpg", ".jpeg", ".png"]

# Speicherort für Dateien
SAVE_DIR = "/opt/speiseplan-bot/speiseplaene/"
LAST_HASH_FILE = "/opt/speiseplan-bot/speiseplaene/last_hash.json"

os.makedirs(SAVE_DIR, exist_ok=True)  # Ordner anlegen, falls nicht existiert

# State-Datei für den systemd hourly Timer
state_file = "/opt/speiseplan-bot/state/no_plan"

def get_current_hash():
    if not os.path.exists(LAST_HASH_FILE):
        return None
    try:
        with open(LAST_HASH_FILE, "r") as f:
            return json.load(f)["hash"]
    except:
        return None


def save_hash(h):
    with open(LAST_HASH_FILE, "w") as f:
        json.dump({"hash": h}, f)


def hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


def fetch_file(url):
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp.content
        return None
    except:
        return None


def main():
    today = datetime.date.today()
    kw = today.isocalendar().week
    year = today.year

    image_data = None
    final_url = None
    final_extension = None

    # verschiedene Dateiendungen durchprobieren
    for ext in EXTENSIONS:
        url = BASE_URL.format(ort=ORT, kw=kw, year=year, ext=ext)
        data = fetch_file(url)

        print(f"Prüfe: {url}")

        if data:
            print(f"Gefunden unter: {url}")
            image_data = data
            final_url = url
            final_extension = ext
            break


    # ----------------------------------------
    # FALL 1: KEIN ESSENSPLAN GEFUNDEN
    # ----------------------------------------
    if not image_data:
        print("Essensplan noch nicht veröffentlicht.")

        # HOURLY TIMER AKTIVIEREN
        open(state_file, "w").close()

        return

    new_hash = hash_bytes(image_data)
    old_hash = get_current_hash()

    # ----------------------------------------
    # FALL 2: ESSENSPLAN UNVERÄNDERT
    # ----------------------------------------
    if new_hash == old_hash:
        print("Essensplan unverändert.")

        # Wenn wir einen Hash von letzter Woche haben → Plan existiert → hourly AUS
        if os.path.exists(LAST_HASH_FILE):
            if os.path.exists(state_file):
                os.remove(state_file)
            return

        # Wenn wir K E I N E N gespeicherten Hash hatten → Plan existiert noch NICHT → hourly AN
        open(state_file, "w").close()
        return

    # ----------------------------------------
    # 1.) LOKAL SPEICHERN
    # ----------------------------------------
    filename = f"Speiseplan_KW{kw}_{year}{final_extension}"
    file_path = os.path.join(SAVE_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(image_data)

    print(f"Bild gespeichert unter: {file_path}")

    # ----------------------------------------
    # 2.) AUS DATEI LADEN & AN DISCORD SENDEN
    # ----------------------------------------
    with open(file_path, "rb") as f:
        requests.post(
            WEBHOOK_URL,
            data={
                "content": f"🍽️ Ein neuer Speiseplan für die Kalenderwoche {kw} ist soeben auf der Webseite eingeschlagen!"
            },
            files={
                "file": (filename, f, "image/jpeg")
            }
        )

    print("Bild erfolgreich an Discord gesendet.")

    save_hash(new_hash)


if __name__ == "__main__":
    main()
