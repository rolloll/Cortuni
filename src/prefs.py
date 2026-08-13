"""Cortuni의 사용자 환경설정(글꼴 등)을 저장/불러오는 아주 작은 저장소."""

import json
import os
import shutil

_APP_DATA_ROOT = os.environ.get("APPDATA", os.path.expanduser("~"))
APP_DATA_DIR = os.path.join(_APP_DATA_ROOT, "Cortuni")
PREFS_PATH = os.path.join(APP_DATA_DIR, "prefs.json")


def migrate_from_old_app_name(old_name="Coriuni"):
    """Coriuni -> Cortuni 개명 이전에 저장돼 있던 설정/사전/최근 작업을 한 번만 옮긴다.

    새 폴더(Cortuni)가 아직 없고 옛 폴더(Coriuni)만 있을 때만 통째로 복사한다 -
    이미 새 폴더가 생겼다면(두 번째 실행부터) 다시 손대지 않는다.
    """
    old_dir = os.path.join(_APP_DATA_ROOT, old_name)
    if os.path.isdir(old_dir) and not os.path.isdir(APP_DATA_DIR):
        try:
            shutil.copytree(old_dir, APP_DATA_DIR)
        except Exception:
            pass


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
