# 이름·호칭(Terms) 기능이 UI에서 빠지면서 이 파일 전체를 주석 처리했다.
# 되살리려면: 이 파일의 '# ' 접두어를 전부 지우고, main.py/home_page.py/
# sidebar.py에서 '이름·호칭 기능 비활성화' 주석이 붙은 줄들을 되돌리면 된다.
#
# """이름/호칭어 일괄 치환 + 조사 자동 교정을 실제 텍스트/문서에 적용하는 로직.
# 
# mapping(원래단어 -> 바꿀단어) 하나로 여러 단어를 한 번에 치환한다.
# 치환된 단어 뒤에 조사가 붙어 있었다면, 새 단어의 받침 유무에 맞는 조사로 바꾼다.
# """
# 
# import os
# 
# from josa import build_combined_pattern, correct_particle
# from adapters import open_docx, docx_paragraphs, save_docx
# from adapters import open_hwpx, hwpx_paragraphs, save_hwpx
# from txt_handler import read_text_auto
# 
# 
# def compute_replacements(text, mapping):
#     """text 안에서 mapping에 해당하는 치환 지점들을 (start, end, new_text) 리스트로 반환."""
#     if not mapping:
#         return []
#     pattern = build_combined_pattern(mapping.keys())
#     replacements = []
#     for m in pattern.finditer(text):
#         old_word, particle = m.group(1), m.group(2)
#         new_word = mapping[old_word]
#         new_text = new_word + correct_particle(particle, new_word) if particle else new_word
#         replacements.append((m.start(), m.end(), new_text))
#     return replacements
# 
# 
# def apply_to_text(text, mapping):
#     """일반 문자열에 치환을 적용한 결과를 반환."""
#     replacements = compute_replacements(text, mapping)
#     if not replacements:
#         return text
#     pieces = []
#     cursor = 0
#     for start, end, new_text in replacements:
#         pieces.append(text[cursor:start])
#         pieces.append(new_text)
#         cursor = end
#     pieces.append(text[cursor:])
#     return "".join(pieces)
# 
# 
# def apply_to_runs(runs, mapping):
#     """단락 하나에 속한 런(run) 리스트에 치환을 적용한다. 실제로 바뀐 것이 있으면 True."""
#     texts = [r.get_text() for r in runs]
#     full_text = "".join(texts)
#     replacements = compute_replacements(full_text, mapping)
#     if not replacements:
#         return False
# 
#     spans = []
#     pos = 0
#     for t in texts:
#         spans.append((pos, pos + len(t)))
#         pos += len(t)
# 
#     # 각 치환의 "앵커" 런(치환 시작 위치를 포함하는 런) - 새 텍스트는 여기에만 삽입한다.
#     anchor_of = []
#     for start, _end, _new_text in replacements:
#         anchor_idx = len(spans) - 1
#         for i, (rs, re_) in enumerate(spans):
#             if rs <= start < re_:
#                 anchor_idx = i
#                 break
#         anchor_of.append(anchor_idx)
# 
#     changed = False
#     for i, (run, text, (rs, re_)) in enumerate(zip(runs, texts, spans)):
#         overlapping = [
#             (start, end, new_text, anchor_of[j])
#             for j, (start, end, new_text) in enumerate(replacements)
#             if not (end <= rs or start >= re_)
#         ]
#         if not overlapping:
#             continue
# 
#         pieces = []
#         cursor = rs
#         for start, end, new_text, anchor_idx in overlapping:
#             if start > cursor:
#                 pieces.append(text[cursor - rs:start - rs])
#             if anchor_idx == i:
#                 pieces.append(new_text)
#             cursor = max(cursor, min(end, re_))
#         if cursor < re_:
#             pieces.append(text[cursor - rs:])
# 
#         new_run_text = "".join(pieces)
#         if new_run_text != text:
#             changed = True
#             if new_run_text == "":
#                 run.remove()
#             else:
#                 run.set_text(new_run_text)
# 
#     return changed
# 
# 
# def rename_txt_file(path, mapping, output_dir):
#     text, encoding = read_text_auto(path)
#     new_text = apply_to_text(text, mapping)
#     base = os.path.splitext(os.path.basename(path))[0]
#     out_path = os.path.join(output_dir, f"{base}_변경.txt")
#     with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
#         f.write(new_text)
#     return out_path, encoding
# 
# 
# def rename_docx_file(path, mapping, output_dir):
#     doc = open_docx(path)
#     for p in docx_paragraphs(doc):
#         apply_to_runs(p.runs, mapping)
#     base = os.path.splitext(os.path.basename(path))[0]
#     out_path = os.path.join(output_dir, f"{base}_변경.docx")
#     save_docx(doc, out_path)
#     return out_path
# 
# 
# def rename_hwpx_file(path, mapping, output_dir):
#     doc = open_hwpx(path)
#     for p in hwpx_paragraphs(doc):
#         apply_to_runs(p.runs, mapping)
#     base = os.path.splitext(os.path.basename(path))[0]
#     out_path = os.path.join(output_dir, f"{base}_변경.hwpx")
#     save_hwpx(doc, out_path)
#     return out_path
