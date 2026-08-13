"""프로그램 전체에 적용되는 글꼴 관리.

Tk의 "이름있는 폰트"(TkDefaultFont 등)를 재설정하는 방식이라, 이미 열려 있는
창을 포함해 프로그램 전체에 즉시 반영된다(개별 위젯을 순회할 필요가 없다).

이 모듈은 두 가지 서로 다른 글꼴 개념을 다룬다:
  - "내용 글꼴": 사용자가 설정 화면에서 직접 고르는, 본문/미리보기에 쓰이는 글꼴
    (apply_font_family 등 이 파일의 원래 기능).
  - "브랜드 글꼴": 2.0 리디자인의 청사진 디자인이 요구하는 고정 글꼴(Barlow /
    Barlow Condensed) - 사용자가 바꿀 수 없고, 앱에 내장된 폰트 파일을 실행 시
    등록해서 쓴다(load_brand_fonts).
"""

import ctypes
import os
import sys
import tkinter.font as tkfont

BRAND_HEADING_FAMILY = "Barlow Condensed SemiBold"  # Windows GDI가 실제로 이렇게 등록한다 -
# BarlowCondensed-SemiBold.ttf는 Regular/Bold 짝이 없는 단일 굵기라, GDI의 4단계
# 스타일 모델(Regular/Bold/Italic/BoldItalic)에 안 맞는 굵기 이름("SemiBold")이
# 패밀리명 뒤에 그대로 붙어서 열거된다. 실행 시 load_brand_fonts()가 이 이름이
# 실제로 존재하는지 확인하니, 폰트 파일을 바꾸면 이 상수도 다시 확인해야 한다.
BRAND_BODY_FAMILY = "Barlow"

_BRAND_FONT_FILES = ("Barlow-Regular.ttf", "Barlow-Bold.ttf", "BarlowCondensed-SemiBold.ttf")
_brand_fonts_loaded = False

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


def load_brand_fonts(assets_fonts_dir):
    """assets_fonts_dir(예: resource_path("assets/fonts"))에 있는 Barlow 폰트 파일들을
    이 프로세스에만 적용되는 방식(FR_PRIVATE)으로 등록한다.

    Windows가 아니거나, 파일이 없거나, 등록에 실패해도 예외를 던지지 않는다 -
    실패하면 그냥 시스템 대체 글꼴로 보이는 것뿐이지 앱이 죽을 이유는 아니다.
    Tk 루트가 생성된 뒤 호출해야 하며(그래야 tkfont.families()로 결과를 확인할
    수 있다), 위젯을 만들기 전에 호출해야 한다.

    반환값: (성공 여부: bool, 진단 메시지: str) - 호출하는 쪽이 로그에 남기고
    싶을 때 쓰라고 메시지도 함께 돌려준다.
    """
    global _brand_fonts_loaded

    if sys.platform != "win32":
        return False, "브랜드 글꼴 등록은 Windows에서만 지원합니다(다른 OS는 대체 글꼴로 표시됨)."

    registered = []
    for filename in _BRAND_FONT_FILES:
        path = os.path.join(assets_fonts_dir, filename)
        if not os.path.isfile(path):
            continue
        try:
            FR_PRIVATE = 0x10
            n = ctypes.windll.gdi32.AddFontResourceExW(str(path), FR_PRIVATE, 0)
            if n:
                registered.append(filename)
        except Exception:
            continue

    if not registered:
        return False, "브랜드 글꼴 파일을 찾지 못했거나 등록에 실패했습니다: " + assets_fonts_dir

    _brand_fonts_loaded = True
    available = set(tkfont.families())
    missing = [f for f in (BRAND_HEADING_FAMILY, BRAND_BODY_FAMILY) if f not in available]
    if missing:
        return False, f"폰트 파일은 등록됐지만 Tk가 다음 글꼴명을 인식하지 못했습니다: {missing}"
    return True, f"브랜드 글꼴 등록 완료: {registered}"
