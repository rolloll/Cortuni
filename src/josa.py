# 이름·호칭(Terms) 기능이 UI에서 빠지면서 이 파일 전체를 주석 처리했다.
# 되살리려면: 이 파일의 '# ' 접두어를 전부 지우고, main.py/home_page.py/
# sidebar.py에서 '이름·호칭 기능 비활성화' 주석이 붙은 줄들을 되돌리면 된다.
#
# """한글 받침 유무에 따라 조사(은/는, 이/가 등)를 자동으로 맞바꾸는 로직.
# 
# 이름/호칭어를 다른 단어로 치환할 때, 그 뒤에 붙어 있던 조사도
# 새 단어의 받침 유무에 맞게 함께 바뀌도록 하기 위한 모듈이다.
# 예) 형은 -> (형을 언니로 바꾸면) 언니는
# """
# 
# import re
# 
# _HANGUL_BASE = 0xAC00
# _HANGUL_LAST = 0xD7A3
# _JONGSUNG_COUNT = 28
# _RIEUL_JONGSUNG_INDEX = 8  # 종성 'ㄹ'의 인덱스
# 
# 
# def _final_consonant_index(word):
#     """word 마지막 글자의 종성(받침) 인덱스. 한글 음절이 아니면 None."""
#     if not word:
#         return None
#     code = ord(word[-1])
#     if _HANGUL_BASE <= code <= _HANGUL_LAST:
#         return (code - _HANGUL_BASE) % _JONGSUNG_COUNT
#     return None
# 
# 
# def has_batchim(word):
#     """word가 받침 있는 한글 음절로 끝나면 True. 한글 음절이 아니면 받침 없다고 간주."""
#     idx = _final_consonant_index(word)
#     if idx is None:
#         return False
#     return idx != 0
# 
# 
# def _ends_with_rieul(word):
#     return _final_consonant_index(word) == _RIEUL_JONGSUNG_INDEX
# 
# 
# # (받침 있을 때 형태, 받침 없을 때 형태)
# PARTICLE_GROUPS = [
#     ("은", "는"),
#     ("이", "가"),
#     ("을", "를"),
#     ("과", "와"),
#     ("아", "야"),
#     ("이나", "나"),
#     ("이랑", "랑"),
#     ("이라도", "라도"),
#     ("이며", "며"),
#     ("이라", "라"),
# ]
# 
# _LO_GROUP = ("으로", "로")  # 받침 없음/ㄹ받침 -> 로, 그 외 받침 -> 으로
# 
# # 조사 문자열 -> 그룹 인덱스 (PARTICLE_GROUPS의 인덱스, "으로/로"는 -1로 특수 표시)
# _PARTICLE_TO_GROUP = {}
# for _idx, (_cons, _vowel) in enumerate(PARTICLE_GROUPS):
#     _PARTICLE_TO_GROUP[_cons] = _idx
#     _PARTICLE_TO_GROUP[_vowel] = _idx
# _PARTICLE_TO_GROUP[_LO_GROUP[0]] = -1
# _PARTICLE_TO_GROUP[_LO_GROUP[1]] = -1
# 
# # 매칭 시 긴 조사부터 시도해야 "이라도"가 "이"로 잘못 잘리지 않는다.
# ALL_PARTICLES = sorted(_PARTICLE_TO_GROUP.keys(), key=len, reverse=True)
# 
# 
# def correct_particle(original_particle, new_word):
#     """new_word 뒤에 와야 할, original_particle과 같은 계열의 조사를 반환."""
#     group_idx = _PARTICLE_TO_GROUP.get(original_particle)
#     if group_idx is None:
#         return original_particle
#     if group_idx == -1:
#         if has_batchim(new_word) and not _ends_with_rieul(new_word):
#             return _LO_GROUP[0]
#         return _LO_GROUP[1]
#     cons, vowel = PARTICLE_GROUPS[group_idx]
#     return cons if has_batchim(new_word) else vowel
# 
# 
# _PARTICLE_ALTERNATION = "|".join(re.escape(p) for p in ALL_PARTICLES)
# _HANGUL_CHAR = r"[가-힣]"
# 
# 
# def build_word_pattern(word):
#     """word(+선택적 조사) 하나만 찾는 정규식. 앞뒤로 한글 음절이 이어지면(더 긴 단어의 일부로 보고) 매칭하지 않는다."""
#     return re.compile(
#         r"(?<!" + _HANGUL_CHAR + r")(" + re.escape(word) + r")(" + _PARTICLE_ALTERNATION + r")?(?!" + _HANGUL_CHAR + r")"
#     )
# 
# 
# def build_combined_pattern(words):
#     """여러 단어를 한 번에 찾는 정규식. 긴 단어를 먼저 시도하도록 정렬해서 넘겨야 한다."""
#     word_alt = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
#     return re.compile(
#         r"(?<!" + _HANGUL_CHAR + r")(" + word_alt + r")(" + _PARTICLE_ALTERNATION + r")?(?!" + _HANGUL_CHAR + r")"
#     )
