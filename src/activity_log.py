"""홈 화면의 "최근 작업" 기록. prefs.py와 같은 저장 방식(APPDATA의 JSON 파일)이다.

분할/병합/이름·호칭/파일명 일괄/확장자 변환이 성공적으로 끝날 때마다
record()가 한 줄 남기고, 홈 화면이 recent()로 최신순으로 읽어 보여준다.
"""

import json
import os

APP_DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Cortuni")
LOG_PATH = os.path.join(APP_DATA_DIR, "activity.json")
MAX_ENTRIES = 50


def _load(path=None):
    path = path or LOG_PATH
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(entries, path=None):
    path = path or LOG_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries[:MAX_ENTRIES], f, ensure_ascii=False, indent=2)


def record(task, target, result, path=None):
    """작업 하나를 맨 앞에 추가하고(최신이 먼저), 오래된 것은 MAX_ENTRIES개까지만 남긴다.

    시각은 실행 시점의 절대 시각(YYYY-MM-DD HH:MM)이다 - 목업의 "10분 전" 같은
    상대 시각은 보여줄 때마다 다시 계산해야 해서 여기서는 다루지 않는다.
    """
    import datetime

    entry = {
        "task": task, "target": target, "result": result,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    entries = _load(path)
    entries.insert(0, entry)
    _save(entries, path)


def recent(n=20, path=None):
    """최신순으로 최대 n개."""
    return _load(path)[:n]
