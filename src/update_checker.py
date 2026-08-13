"""GitHub Releases를 확인해서 더 새로운 버전이 있는지 알아내는 로직.

네트워크가 없거나 저장소에 릴리즈가 아직 없어도 예외를 던지지 않고
그냥 "새 버전 없음"으로 조용히 처리한다(앱 시작을 막으면 안 되므로).
"""

import json
import urllib.error
import urllib.request

GITHUB_REPO = "rolloll/Cortuni"
REQUEST_TIMEOUT = 4


def _parse_version(tag):
    tag = (tag or "").strip()
    if tag[:1].lower() == "v":
        tag = tag[1:]
    parts = []
    for piece in tag.split("."):
        digits = ""
        for ch in piece:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer(latest_tag, current_version):
    return _parse_version(latest_tag) > _parse_version(current_version)


def fetch_latest_release(repo=GITHUB_REPO, timeout=REQUEST_TIMEOUT):
    """(tag_name, html_url)을 반환. 실패하면(오프라인, 릴리즈 없음 등) None."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Cortuni-UpdateChecker"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    tag = data.get("tag_name")
    html_url = data.get("html_url")
    if not tag or not html_url:
        return None
    return tag, html_url


def check_for_update(current_version, repo=GITHUB_REPO, timeout=REQUEST_TIMEOUT):
    """새 버전이 있으면 (latest_tag, html_url)을, 없거나 확인할 수 없으면 None을 반환."""
    result = fetch_latest_release(repo=repo, timeout=timeout)
    if result is None:
        return None
    latest_tag, url = result
    if is_newer(latest_tag, current_version):
        return latest_tag, url
    return None
