"""텍스트(.txt) 파일 인코딩 자동 감지 및 문장 경계 안전 분할."""

import os

from splitter import resolve_chunker

# 흔히 쓰이는 한국어 인코딩 순서대로 시도한다. BOM이 있으면 utf-8-sig가 우선 처리된다.
_ENCODING_CANDIDATES = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]


def read_text_auto(path):
    """인코딩을 자동 감지해서 읽는다. 실패 시 chardet로 추정 후, 그래도 안되면 대체 문자로 읽는다."""
    with open(path, "rb") as f:
        raw = f.read()

    for enc in _ENCODING_CANDIDATES:
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue

    try:
        import chardet
        guess = chardet.detect(raw)
        enc = guess.get("encoding")
        if enc:
            return raw.decode(enc, errors="strict"), enc
    except Exception:
        pass

    return raw.decode("utf-8", errors="replace"), "utf-8(대체문자 포함)"


def split_txt_file(path, chunker, output_dir):
    text, used_encoding = read_text_auto(path)

    base = os.path.splitext(os.path.basename(path))[0]
    parts = [text[s:e] for s, e in resolve_chunker(chunker)(text)]

    output_paths = []
    for i, part in enumerate(parts, start=1):
        out_path = os.path.join(output_dir, f"{base}_{i}.txt")
        with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(part)
        output_paths.append(out_path)

    return output_paths, used_encoding
