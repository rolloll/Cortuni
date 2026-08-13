"""프로그램 전체에 적용되는 글꼴 관리.

Tk의 "이름있는 폰트"(TkDefaultFont 등)를 재설정하는 방식이라, 이미 열려 있는
창을 포함해 프로그램 전체에 즉시 반영된다(개별 위젯을 순회할 필요가 없다).
"""

import tkinter.font as tkfont

DEFAULT_FONTS = {
    "ko": "맑은 고딕",
    "en": "Helvetica",
    "zh": "Noto Sans SC",
    "ja": "Noto Sans JP",
}

# 프로그램에서 쓰이는 위젯들이 실제로 참조하는 이름있는 폰트 전부.
# (ttk 위젯 대부분 TkDefaultFont, Treeview 헤더는 TkHeadingFont,
#  Text/ScrolledText/Spinbox 등은 TkFixedFont/TkTextFont를 사용한다.)
_NAMED_FONTS = (
    "TkDefaultFont",
    "TkTextFont",
    "TkFixedFont",
    "TkMenuFont",
    "TkHeadingFont",
    "TkCaptionFont",
    "TkSmallCaptionFont",
    "TkIconFont",
    "TkTooltipFont",
)


def list_available_fonts():
    """사용자 시스템에 설치된 폰트 이름을 정렬해서 반환.

    Windows는 세로쓰기(수직) 렌더링용으로 이름 앞에 "@"가 붙은 폰트를
    같이 등록해 둔다(예: "@맑은 고딕"). 이걸 그대로 적용하면 가로쓰기
    위젯에서도 글자가 90도 회전해서 출력되므로 목록에서 제외한다.
    """
    return sorted({f for f in tkfont.families() if not f.startswith("@")}, key=str.lower)


def resolve_default_font(lang, available=None):
    """lang에 대한 기본 폰트 이름. available에 없으면 그래도 시도해볼 값을 반환한다
    (Helvetica처럼 Tk가 내부적으로 대체해 주는 논리 폰트도 있기 때문)."""
    preferred = DEFAULT_FONTS.get(lang, DEFAULT_FONTS["en"])
    if available is not None and preferred not in available:
        return DEFAULT_FONTS["en"]
    return preferred


def current_family():
    return tkfont.nametofont("TkDefaultFont").actual("family")


def apply_font_family(family):
    """family를 프로그램 전체 기본 글꼴로 적용."""
    if not family:
        return
    family = family.lstrip("@")
    for name in _NAMED_FONTS:
        try:
            tkfont.nametofont(name).configure(family=family)
        except Exception:
            pass
