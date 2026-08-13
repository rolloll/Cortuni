"""'Industry' 디자인 시스템 토큰 + ttk 스타일 적용.

이 모듈은 색/폭/폰트 "토큰"과, 그 토큰으로 ttk.Style을 구성하는 로직만 담는다.
실제로 어떤 모드(light/dark/system)를 쓸지는 prefs.py에 저장되고, 최초 적용은
main.py가 시작할 때 담당한다(이 모듈은 저장을 직접 하지 않는다 - fonts.py가
글꼴 선택을 직접 저장하지 않는 것과 같은 이유).

라이트/다크 전환 시 ttk 위젯은 스타일 재설정만으로 자동 갱신되지만, 다음은
ttk.Style을 따르지 않아 별도로 손대야 한다:
  - ttk.Combobox의 팝다운 목록(진짜 ttk가 아니라 순수 Tk Listbox) - root.option_add로 처리.
  - BlueprintFrame/Segmented 등 직접 그리는 위젯 - subscribe()로 등록해서 set_mode()가
    호출될 때마다 각자의 refresh_theme()을 부르게 한다.
  - ScrolledText, Treeview.tag_configure 색 등 - 각 페이지가 스스로 갱신해야 한다
    (이 모듈은 존재를 알 수 없는 위젯이므로).
"""

import sys
import tkinter as tk
from tkinter import ttk

import fonts as _fonts

HEADING_FONT = _fonts.BRAND_HEADING_FAMILY
BODY_FONT = _fonts.BRAND_BODY_FAMILY

LIGHT_TOKENS = {
    "bg": "#f2f2f3",
    "surface": "#e9e9ea",
    "text": "#1d1f20",
    "accent": "#5980a6",
    "divider": "#d1d2d3",
    "neutral_100": "#f5f5f8",
    "neutral_200": "#e7e7ea",
    "neutral_300": "#d4d4d7",
    "neutral_400": "#b7b7ba",
    "neutral_500": "#98989b",
    "neutral_600": "#7a7a7d",
    "neutral_700": "#5d5d60",
    "neutral_800": "#424244",
    "neutral_900": "#2b2b2d",
    "accent_100": "#eef6ff",
    "accent_200": "#d6ebff",
    "accent_300": "#b5d9fd",
    "accent_400": "#94bce3",
    "accent_500": "#749dc4",
    "accent_600": "#597ea3",
    "accent_700": "#416180",
    "accent_800": "#2c455d",
    "accent_900": "#1d2d3d",
}

DARK_TOKENS = {
    "bg": "#141618",
    "surface": "#1d2124",
    "text": "#e8e9eb",
    "accent": "#8fb3d6",
    "divider": "#33373a",
    "neutral_100": "#2b2e31",
    "neutral_200": "#33373a",
    "neutral_300": "#404448",
    "neutral_400": "#54585c",
    "neutral_500": "#6e7174",
    "neutral_600": "#83868a",
    "neutral_700": "#9a9da1",
    "neutral_800": "#b5b8bb",
    "neutral_900": "#d3d5d8",
    "accent_100": "#1d2d3d",
    "accent_200": "#2c455d",
    "accent_300": "#416180",
    "accent_400": "#597ea3",
    "accent_500": "#749dc4",
    "accent_600": "#94bce3",
    "accent_700": "#b9d0e8",
    "accent_800": "#d6e5f2",
    "accent_900": "#eef6ff",
}

SPACE_1, SPACE_2, SPACE_3, SPACE_4, SPACE_6, SPACE_8 = 3, 7, 10, 14, 20, 27

_mode = "light"
_tokens = LIGHT_TOKENS
_subscribers = []
_style = None


def tokens():
    """현재 적용 중인 토큰 dict(light 또는 dark로 이미 해석된 것)."""
    return _tokens


def current_mode():
    return _mode


def subscribe(widget):
    """widget은 refresh_theme() 메서드를 가져야 한다. set_mode()가 호출될 때마다 불린다."""
    _subscribers.append(widget)


def unsubscribe(widget):
    try:
        _subscribers.remove(widget)
    except ValueError:
        pass


def _resolve_system_mode():
    """Windows의 현재 라이트/다크 앱 테마를 한 번 읽는다. 실패하면 light로 간주."""
    if sys.platform != "win32":
        return "light"
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return "light" if value else "dark"
    except Exception:
        return "light"


def set_mode(mode, root=None):
    """mode: "light" | "dark" | "system". ttk 스타일을 다시 구성하고 모든 구독자를 갱신."""
    global _mode, _tokens
    _mode = mode
    resolved = _resolve_system_mode() if mode == "system" else mode
    _tokens = DARK_TOKENS if resolved == "dark" else LIGHT_TOKENS

    configure_ttk_style(root)
    for widget in list(_subscribers):
        try:
            widget.refresh_theme()
        except tk.TclError:
            # 위젯이 이미 파괴된 경우 - 구독 목록에서 제거.
            unsubscribe(widget)


def configure_ttk_style(root=None):
    """토큰으로 ttk.Style을 구성한다. 시작 시 한 번, 테마 전환마다 다시 호출된다."""
    global _style
    t = _tokens
    style = ttk.Style(root) if root is not None else ttk.Style()
    style.theme_use("clam")
    _style = style

    heading = (HEADING_FONT, 11, "normal")
    heading_bold = (HEADING_FONT, 11, "bold")
    body = (BODY_FONT, 10, "normal")
    small_tracked = (BODY_FONT, 8, "normal")

    style.configure(".", background=t["bg"], foreground=t["text"], font=body, borderwidth=0)

    # 일반 프레임/라벨 - 기본 배경(bg) 계열
    style.configure("TFrame", background=t["bg"])
    style.configure("TLabel", background=t["bg"], foreground=t["text"], font=body)
    style.configure("Heading.TLabel", background=t["bg"], foreground=t["text"], font=heading_bold)
    style.configure("Caption.TLabel", background=t["bg"], foreground=t["neutral_600"], font=small_tracked)
    style.configure("Muted.TLabel", background=t["bg"], foreground=t["neutral_700"], font=body)

    # 표면(입력창/카드 등) 배경 계열
    style.configure("Surface.TFrame", background=t["surface"])
    style.configure("Surface.TLabel", background=t["surface"], foreground=t["text"], font=body)

    # 버튼
    style.configure(
        "TButton", font=heading_bold, padding=(12, 6), borderwidth=1,
        background=t["bg"], foreground=t["text"], relief="flat",
    )
    style.map(
        "TButton",
        background=[("disabled", t["neutral_100"]), ("active", t["neutral_200"])],
        foreground=[("disabled", t["neutral_500"])],
    )

    style.configure(
        "Primary.TButton", font=heading_bold, padding=(16, 7), borderwidth=1,
        background=t["accent"], foreground=t["bg"], bordercolor=t["accent"], relief="flat",
    )
    style.map(
        "Primary.TButton",
        background=[("disabled", t["neutral_200"]), ("pressed", t["accent_800"]), ("active", t["accent_600"])],
        foreground=[("disabled", t["neutral_500"])],
        bordercolor=[("disabled", t["divider"]), ("!disabled", t["accent"])],
    )

    style.configure(
        "Secondary.TButton", font=heading_bold, padding=(12, 6), borderwidth=1,
        background=t["bg"], foreground=t["text"], bordercolor=t["divider"], relief="flat",
    )
    style.map(
        "Secondary.TButton",
        background=[("disabled", t["neutral_100"]), ("pressed", t["neutral_300"]), ("active", t["neutral_200"])],
        foreground=[("disabled", t["neutral_500"])],
    )

    style.configure(
        "Ghost.TButton", font=heading_bold, padding=(6, 6), borderwidth=0,
        background=t["bg"], foreground=t["accent"], relief="flat",
    )
    style.map(
        "Ghost.TButton",
        background=[("disabled", t["bg"]), ("pressed", t["accent_200"]), ("active", t["accent_100"])],
        foreground=[("disabled", t["neutral_500"])],
    )

    # 세그먼트 컨트롤(widgets.Segmented)이 켜짐/꺼짐 상태를 토글하는 버튼 스타일
    style.configure(
        "SegOn.TButton", font=body, padding=(10, 6), borderwidth=0,
        background=t["accent"], foreground=t["bg"], relief="flat",
    )
    style.map(
        "SegOn.TButton",
        background=[("disabled", t["neutral_300"]), ("active", t["accent"])],
        foreground=[("disabled", t["neutral_600"])],
    )

    style.configure(
        "SegOff.TButton", font=body, padding=(10, 6), borderwidth=0,
        background=t["bg"], foreground=t["text"], relief="flat",
    )
    style.map(
        "SegOff.TButton",
        background=[("disabled", t["bg"]), ("active", t["neutral_200"])],
        foreground=[("disabled", t["neutral_500"])],
    )

    # 입력창
    style.configure(
        "TEntry", font=body, padding=4, foreground=t["text"], fieldbackground=t["surface"],
        bordercolor=t["divider"], insertcolor=t["accent"], lightcolor=t["surface"], darkcolor=t["surface"],
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", t["accent"]), ("!focus", t["divider"])],
        fieldbackground=[("disabled", t["bg"])],
        foreground=[("disabled", t["neutral_500"])],
    )

    style.configure(
        "TCombobox", font=body, padding=4, foreground=t["text"], fieldbackground=t["surface"],
        background=t["surface"], bordercolor=t["divider"], arrowcolor=t["neutral_700"],
    )
    style.map(
        "TCombobox",
        bordercolor=[("focus", t["accent"]), ("!focus", t["divider"])],
        fieldbackground=[("readonly", t["surface"])],
        foreground=[("disabled", t["neutral_500"])],
    )
    # 팝다운 목록은 ttk가 아니라 순수 Tk Listbox라 option_add로만 색이 먹는다.
    if root is not None:
        root.option_add("*TCombobox*Listbox.background", t["surface"])
        root.option_add("*TCombobox*Listbox.foreground", t["text"])
        root.option_add("*TCombobox*Listbox.selectBackground", t["accent"])
        root.option_add("*TCombobox*Listbox.selectForeground", t["bg"])

    style.configure(
        "TSpinbox", font=body, padding=4, foreground=t["text"], fieldbackground=t["surface"],
        bordercolor=t["divider"], arrowcolor=t["neutral_700"], insertcolor=t["accent"],
    )
    style.map("TSpinbox", bordercolor=[("focus", t["accent"]), ("!focus", t["divider"])])

    # 라디오/체크박스 - 배경은 부모 프레임을 따르도록 bg 기본값
    style.configure(
        "TRadiobutton", font=body, background=t["bg"], foreground=t["text"], focuscolor=t["accent"],
    )
    style.map("TRadiobutton", foreground=[("disabled", t["neutral_500"])])
    style.configure(
        "TCheckbutton", font=body, background=t["bg"], foreground=t["text"], focuscolor=t["accent"],
    )
    style.map("TCheckbutton", foreground=[("disabled", t["neutral_500"])])

    # 구분선
    style.configure("TSeparator", background=t["divider"])

    # 스크롤바 - 최대한 얇고 평평하게
    style.configure(
        "Vertical.TScrollbar", background=t["surface"], troughcolor=t["bg"],
        bordercolor=t["divider"], arrowcolor=t["neutral_600"], relief="flat",
    )
    style.configure(
        "Horizontal.TScrollbar", background=t["surface"], troughcolor=t["bg"],
        bordercolor=t["divider"], arrowcolor=t["neutral_600"], relief="flat",
    )

    # LabelFrame(merge 창의 편집 패널 등)
    style.configure("TLabelframe", background=t["bg"], bordercolor=t["divider"], relief="flat", borderwidth=1)
    style.configure("TLabelframe.Label", background=t["bg"], foreground=t["neutral_700"], font=body)

    # 표(Treeview)
    style.configure(
        "Treeview", font=body, background=t["bg"], fieldbackground=t["bg"], foreground=t["text"],
        borderwidth=0, rowheight=26,
    )
    style.map(
        "Treeview",
        background=[("selected", t["accent_200"])],
        foreground=[("selected", t["accent_800"])],
    )
    style.configure(
        "Treeview.Heading", font=small_tracked, background=t["bg"], foreground=t["neutral_600"],
        relief="flat", borderwidth=0,
    )
    style.map("Treeview.Heading", background=[("active", t["bg"])])

    # 탭 형태는 쓰지 않지만, 혹시 남는 기본 Notebook 스타일도 톤을 맞춰둔다.
    style.configure("TNotebook", background=t["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=t["surface"], foreground=t["text"], font=body)

    # 태그(작은 라벨 칩) - widgets.make_tag가 사용
    tag_font = (BODY_FONT, 9, "normal")
    style.configure("TagAccent.TLabel", background=t["accent_100"], foreground=t["accent_800"], font=tag_font, padding=(8, 2))
    style.configure("TagNeutral.TLabel", background=t["neutral_100"], foreground=t["neutral_800"], font=tag_font, padding=(8, 2))
    style.configure(
        "TagOutline.TLabel", background=t["bg"], foreground=t["accent"], font=tag_font, padding=(7, 1),
        borderwidth=1, relief="solid", bordercolor=t["accent"],
    )

    return style
