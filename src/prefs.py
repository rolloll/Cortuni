"""코리우니의 사용자 환경설정(글꼴 등)을 저장/불러오는 아주 작은 저장소."""

import json
import os

APP_DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Coriuni")
PREFS_PATH = os.path.join(APP_DATA_DIR, "prefs.json")


def load_prefs(path=None):
    path = path or PREFS_PATH
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_prefs(prefs, path=None):
    path = path or PREFS_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(prefs, f, ensure_ascii=False, indent=2)


def set_pref(key, value, path=None):
    prefs = load_prefs(path)
    prefs[key] = value
    save_prefs(prefs, path)
