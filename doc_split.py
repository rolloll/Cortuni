"""단락(paragraph) + 런(run) 구조를 가진 문서(docx, hwpx 등)를
문장 경계를 지키며 여러 파일로 분할하는 공통 로직.

각 포맷은 아래 두 가지만 맞춰 구현하면 이 모듈을 그대로 재사용할 수 있다.
  - 문서를 열어 단락 어댑터 리스트를 돌려주는 함수
  - 단락 어댑터: .text / .runs(런 어댑터 리스트) / .remove()
  - 런 어댑터: .get_text() / .set_text(str) / .remove()
"""

from splitter import compute_chunks


def paragraph_spans(paragraph_texts):
    """단락 텍스트를 이어붙인(구분자 없이) 전체 텍스트 기준 각 단락의 (start, end)."""
    spans = []
    pos = 0
    for t in paragraph_texts:
        spans.append((pos, pos + len(t)))
        pos += len(t)
    return spans


def locate(spans, pos):
    """pos가 어느 단락에 속하는지, 단락 경계에 정확히 걸치는지 판정."""
    for i, (s, e) in enumerate(spans):
        if pos <= s:
            return ("boundary", i)
        if pos < e:
            return ("inside", i, pos - s)
    return ("boundary", len(spans))


def chunk_paragraph_plan(spans, start, end):
    """[start, end) 구간을 담기 위해 유지할 단락 범위와 경계 단락의 잘라낼 위치."""
    loc_s = locate(spans, start)
    loc_e = locate(spans, end)

    if loc_s[0] == "boundary":
        first_idx = loc_s[1]
        left_trim = None
    else:
        first_idx = loc_s[1]
        left_trim = loc_s[2]

    if loc_e[0] == "boundary":
        last_idx = loc_e[1] - 1
        right_trim = None
    else:
        last_idx = loc_e[1]
        right_trim = loc_e[2]

    return first_idx, last_idx, left_trim, right_trim


def trim_paragraph_runs(runs, left_trim, right_trim):
    """runs(런 어댑터 리스트)를 [left_trim, right_trim) 구간만 남도록 자른다.

    left_trim=None -> 0, right_trim=None -> 전체 길이.
    """
    texts = [r.get_text() for r in runs]
    total = sum(len(t) for t in texts)
    lo = 0 if left_trim is None else left_trim
    hi = total if right_trim is None else right_trim

    pos = 0
    for r, t in zip(runs, texts):
        r_start, r_end = pos, pos + len(t)
        pos = r_end
        keep_start = max(r_start, lo)
        keep_end = min(r_end, hi)
        if keep_start >= keep_end:
            r.remove()
        elif keep_start == r_start and keep_end == r_end:
            continue
        else:
            r.set_text(t[keep_start - r_start:keep_end - r_start])


def split_paragraph_document(source_path, chunk_size, open_doc, get_paragraphs, save_doc, make_output_path):
    """공통 분할 드라이버.

    open_doc(path) -> doc 객체 (호출할 때마다 원본을 새로 읽어 독립된 사본을 만든다)
    get_paragraphs(doc) -> 단락 어댑터 리스트 (문서 순서대로)
    save_doc(doc, path) -> 저장
    make_output_path(index) -> index번째(1부터) 출력 파일 경로

    반환값: 생성된 출력 파일 경로 리스트
    """
    probe = open_doc(source_path)
    paragraph_texts = [p.text for p in get_paragraphs(probe)]
    full_text = "".join(paragraph_texts)

    chunks = compute_chunks(full_text, chunk_size)
    spans = paragraph_spans(paragraph_texts)

    output_paths = []
    for i, (start, end) in enumerate(chunks):
        doc = open_doc(source_path)
        paragraphs = get_paragraphs(doc)

        first_idx, last_idx, left_trim, right_trim = chunk_paragraph_plan(spans, start, end)

        for idx, p in enumerate(paragraphs):
            if idx < first_idx or idx > last_idx:
                p.remove()

        if first_idx == last_idx:
            trim_paragraph_runs(paragraphs[first_idx].runs, left_trim, right_trim)
        else:
            if left_trim is not None:
                trim_paragraph_runs(paragraphs[first_idx].runs, left_trim, None)
            if right_trim is not None:
                trim_paragraph_runs(paragraphs[last_idx].runs, None, right_trim)

        out_path = make_output_path(i + 1)
        save_doc(doc, out_path)
        output_paths.append(out_path)

    return output_paths
