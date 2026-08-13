"""문장 경계를 지키는 글자수 기준 텍스트 분할 로직.

지정한 글자수(chunk_size)로 나누되, 그 지점이 문장 중간이면
문장이 끝나는 지점(마침표/느낌표/물음표 + 이어지는 닫는 따옴표·괄호)까지
확장해서 자른다. 문장을 앞으로 당겨 짧게 자르지 않고, 항상 뒤로 늘려서
문장이 끊어지지 않게 한다.
"""

import bisect
import re

# 문장 종결부호(.!?) 뒤에 따옴표/괄호가 이어지는 것까지 하나의 경계로 인식한다.
# 사용자가 언급한 온점(.)과 큰따옴표("), 작은따옴표(')를 포함해
# 느낌표/물음표 및 자주 쓰이는 닫는 문장부호(', ", ), ], 」, 』, ’, ”)도 함께 처리한다.
_CLOSERS = "\"')\\]’”」』"
SENTENCE_END_RE = re.compile(r"[.!?]+[" + _CLOSERS + r"]*")


def find_sentence_ends(text):
    """text 안에서 문장이 끝나는 위치(그 문자 바로 다음 인덱스) 목록을 반환."""
    return [m.end() for m in SENTENCE_END_RE.finditer(text)]


def compute_chunks(text, chunk_size):
    """(start, end) 튜플 목록을 반환. text[start:end]가 한 조각이 된다.

    - chunk_size 글자를 채우는 지점이 문장 중간이면, 다음 문장 종결 지점까지
      늘려서 자른다(앞으로 당겨서 짧게 자르지 않음).
    - 이후 남은 구간에 문장 종결부호가 전혀 없으면 어쩔 수 없이 끝까지
      한 조각으로 처리한다.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size는 1 이상이어야 합니다.")

    n = len(text)
    if n == 0:
        return []

    ends = find_sentence_ends(text)
    chunks = []
    start = 0
    while start < n:
        tentative = start + chunk_size
        if tentative >= n:
            end = n
        else:
            idx = bisect.bisect_left(ends, tentative)
            end = ends[idx] if idx < len(ends) else n
        if end <= start:
            end = n
        chunks.append((start, end))
        start = end
    return chunks


def split_text(text, chunk_size):
    """text를 문장 경계를 지키며 chunk_size 기준으로 나눈 문자열 리스트를 반환."""
    return [text[s:e] for s, e in compute_chunks(text, chunk_size)]


def build_boundary_previews(text, chunk_size, context_chars=80, max_boundaries=50):
    """실제로 분할을 실행하지 않고, 각 조각이 어디서 끝나고 다음 조각이 어디서
    시작하는지 미리 볼 수 있는 정보를 만든다.

    반환: (previews, truncated, total_count)
      previews: [{"index", "start", "end", "length", "tail", "next_head", "is_last"}, ...]
      truncated: 조각 수가 max_boundaries를 넘어 일부만 담았으면 True.
      total_count: 실제로 분할했을 때 생성될 전체 조각 수.
    """
    chunks = compute_chunks(text, chunk_size)
    total_count = len(chunks)
    truncated = total_count > max_boundaries
    shown = chunks[:max_boundaries]

    previews = []
    for i, (start, end) in enumerate(shown):
        length = end - start
        if length <= context_chars * 2:
            tail = text[start:end]
        else:
            tail = "…" + text[end - context_chars:end]

        is_last = (i == len(chunks) - 1)
        next_head = ""
        if not is_last:
            next_start, next_end = chunks[i + 1]
            head_end = min(next_end, next_start + context_chars)
            next_head = text[next_start:head_end]
            if head_end < next_end:
                next_head += "…"

        previews.append(
            {
                "index": i + 1,
                "start": start,
                "end": end,
                "length": length,
                "tail": tail,
                "next_head": next_head,
                "is_last": is_last,
            }
        )

    return previews, truncated, total_count
