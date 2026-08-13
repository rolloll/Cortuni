"""한글(.hwpx, XML 기반) 문장 경계 안전 분할.

본문 단락 텍스트만 대상으로 한다(표/이미지 등은 분할 대상에서 제외되며,
표가 있는 경우 모든 결과 파일에 표 전체가 그대로 남는다).
"""

import os

from adapters import open_hwpx, hwpx_paragraphs, save_hwpx
from doc_split import split_paragraph_document


def split_hwpx_file(path, chunk_size, output_dir):
    base = os.path.splitext(os.path.basename(path))[0]

    def make_output_path(index):
        return os.path.join(output_dir, f"{base}_{index}.hwpx")

    return split_paragraph_document(
        source_path=path,
        chunk_size=chunk_size,
        open_doc=open_hwpx,
        get_paragraphs=hwpx_paragraphs,
        save_doc=save_hwpx,
        make_output_path=make_output_path,
    )
