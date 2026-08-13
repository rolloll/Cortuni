"""파일명 일괄 수정(실제 파일의 이름 자체를 바꾸는) 로직.

entries: [{"path": "C:/.../1화.txt", "new_base": "01화"}]
확장자는 항상 원본 그대로 유지되고, new_base(확장자 제외한 이름)만 바뀐다.
"""

import os


def plan_renames(entries):
    """(old_path, new_path) 목록을 반환. new_base가 비어있거나 변화가 없으면 제외."""
    planned = []
    for e in entries:
        old_path = e["path"]
        new_base = (e.get("new_base") or "").strip()
        if not new_base:
            continue
        folder = os.path.dirname(old_path)
        ext = os.path.splitext(old_path)[1]
        new_path = os.path.join(folder, new_base + ext)
        if os.path.normcase(os.path.abspath(new_path)) == os.path.normcase(os.path.abspath(old_path)):
            continue
        planned.append((old_path, new_path))
    return planned


def apply_renames(entries):
    """실제 os.rename을 수행한다.

    반환: (succeeded, failed, skipped)
      succeeded: [(old_path, new_path), ...]
      failed:    [(old_path, new_path, error_message), ...]
      skipped:   [(old_path, new_path), ...]  (다른 파일과 이름이 겹쳐서 건너뜀)
    """
    planned = plan_renames(entries)
    succeeded = []
    failed = []
    skipped = []
    reserved = set()

    for old_path, new_path in planned:
        norm_new = os.path.normcase(os.path.abspath(new_path))
        already_exists = os.path.exists(new_path) and os.path.normcase(os.path.abspath(new_path)) != os.path.normcase(
            os.path.abspath(old_path)
        )
        if norm_new in reserved or already_exists:
            skipped.append((old_path, new_path))
            continue
        try:
            os.rename(old_path, new_path)
            succeeded.append((old_path, new_path))
            reserved.add(norm_new)
        except OSError as e:
            failed.append((old_path, new_path, str(e)))

    return succeeded, failed, skipped
