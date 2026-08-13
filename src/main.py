"""코리우니(Coriuni) - 문장이 잘리지 않는 글자수 기준 파일 분할/병합 도구.

지원 형식: .txt, .docx(MS Word), .hwpx(한글 최신 XML 형식)
.hwp(구버전 바이너리 한글 파일)는 공식 파서가 없어 지원하지 않는다.
한글 프로그램에서 "다른 이름으로 저장 > HWPX"로 변환한 뒤 사용해야 한다.

2.0부터는 사이드바가 있는 하나의 창(App)에서 화면만 바뀌는 구조다. 각 기능은
더 이상 별도의 팝업 창이 아니라 self._pages에 담긴 페이지(Frame)이고,
App.navigate(key)가 보여줄 페이지를 바꾼다.
"""

import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk

from tkinterdnd2 import TkinterDnD

import dialogs
import fonts
import prefs
import sidebar
import theme
import update_checker
from batch_page import BatchPage
from convert_page import ConvertPage
from i18n import STRINGS
from merge_page import MergePage
from settings_page import SettingsPage
from split_page import SplitPage
from terms_page import TermsPage
from version import __version__

DEFAULT_LANG = "ko"

_NAV_CAPTIONS_EN = {
    "home": "Home", "split": "Split", "merge": "Merge", "terms": "Terms",
    "batch": "Batch rename", "convert": "Convert", "settings": "Settings",
}
_NAV_KEYS = {
    "home": "nav_home", "split": "nav_split", "merge": "nav_merge", "terms": "nav_terms",
    "batch": "nav_batch", "convert": "nav_convert", "settings": "nav_settings",
}


def resource_path(relative_path):
    """실행 파일(_MEIPASS)이든 소스에서 바로 실행하든 assets/ 아래 리소스를 찾는다.

    빌드 시 --add-data로 assets 폴더를 그대로 묶기 때문에, 소스에서 실행할 때도
    같은 구조(프로젝트 루트의 assets/)를 그대로 사용한다.
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, "assets", relative_path)


class _ComingSoonPage(ttk.Frame):
    """아직 새 디자인으로 옮기지 않은 화면의 임시 자리표시자. 포팅되면 지운다."""

    def __init__(self, parent, app, key):
        super().__init__(parent)
        self.app = app
        self.key = key
        self.lbl = ttk.Label(self, style="Heading.TLabel")
        self.lbl.place(relx=0.5, rely=0.5, anchor="center")
        self.apply_language()

    def apply_language(self):
        self.lbl.configure(text=f"{self.app.t(_NAV_KEYS[self.key])} — coming soon")


class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("1180x760")
        self.minsize(980, 640)

        try:
            self._icon_image = tk.PhotoImage(file=resource_path("icon.png"))
            self.iconphoto(True, self._icon_image)
        except Exception:
            pass

        self.lang = DEFAULT_LANG
        self._content_font_family = None
        self._active_page = None
        self._pages = {}

        ok, msg = fonts.load_brand_fonts(resource_path("fonts"))
        if not ok:
            print("[fonts] " + msg)

        theme.set_mode(prefs.load_prefs().get("theme", "system"), self)

        self._build_shell()
        self._init_font()
        self.apply_language()
        self.navigate("home")

        self.bind_all("<Control-h>", lambda e: self.navigate("terms"))

        if prefs.load_prefs().get("check_updates_on_startup", True):
            threading.Thread(target=self._check_for_update, daemon=True).start()

    # ---------- 글꼴 ----------

    def _init_font(self):
        available = fonts.list_available_fonts()
        saved = prefs.load_prefs().get("font_family")
        initial = saved if saved in available else fonts.resolve_default_font(self.lang, available)
        fonts.apply_font_family(initial)
        self._content_font_family = initial
        settings = self._pages.get("settings")
        if settings is not None:
            settings.sync_from_app()

    def on_font_selected(self, family):
        fonts.apply_font_family(family)
        prefs.set_pref("font_family", family)
        self._content_font_family = family

    def on_theme_selected(self, mode):
        prefs.set_pref("theme", mode)
        theme.set_mode(mode, self)

    def on_lang_selected(self, code):
        self.lang = code
        self.apply_language()

    def t(self, key, **kwargs):
        text = STRINGS[self.lang][key]
        return text.format(**kwargs) if kwargs else text

    def apply_language(self):
        self.title(self.t("window_title"))
        self.sidebar.apply_language()
        self._update_header_caption()
        for page in self._pages.values():
            if hasattr(page, "apply_language"):
                page.apply_language()

    # ---------- 업데이트 확인 ----------

    def _check_for_update(self):
        result = update_checker.check_for_update(__version__)
        if result is not None:
            latest_tag, url = result
            self.after(0, self._show_update_notice, latest_tag, url)

    def _show_update_notice(self, latest_tag, url):
        if dialogs.ask_yes_no(
            self, self.t("update_available_title"),
            self.t("update_available_body", latest=latest_tag, current=__version__),
        ):
            webbrowser.open(url)

    # ---------- 화면 구성 ----------

    def _build_shell(self):
        self._header = tk.Frame(self, height=38)
        self._header.pack(fill="x", side="top")
        self._header.pack_propagate(False)

        self._logo_canvas = tk.Canvas(self._header, width=18, height=24, highlightthickness=0)
        self._logo_canvas.pack(side="left", padx=(14, 8))

        self._wordmark = tk.Label(self._header, text="CORIUNI", font=(theme.HEADING_FONT, 13, "bold"))
        self._wordmark.pack(side="left")

        self._header_caption = tk.Label(self._header, text="", font=("Segoe UI", 9))
        self._header_caption.pack(side="left", padx=(12, 0))

        self._header_version = tk.Label(self._header, text=f"코리우니 {__version__}", font=("Segoe UI", 8))
        self._header_version.pack(side="right", padx=14)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        self.sidebar = sidebar.Sidebar(body, self, active="home")
        self.sidebar.pack(side="left", fill="y")

        self._content = ttk.Frame(body)
        self._content.pack(side="left", fill="both", expand=True)
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        self._build_pages()
        theme.subscribe(self)
        self.refresh_theme()

    def _build_pages(self):
        self._pages["settings"] = SettingsPage(self._content, self)
        self._pages["split"] = SplitPage(self._content, self)
        self._pages["merge"] = MergePage(self._content, self)
        self._pages["convert"] = ConvertPage(self._content, self)
        self._pages["batch"] = BatchPage(self._content, self)
        self._pages["terms"] = TermsPage(self._content, self)
        for key in ("home",):
            self._pages[key] = _ComingSoonPage(self._content, self, key)

        for page in self._pages.values():
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_remove()

    def navigate(self, key):
        if key not in self._pages or key == self._active_page:
            if key in self._pages:
                self.sidebar.set_active(key)
            return
        if self._active_page is not None:
            self._pages[self._active_page].grid_remove()
        self._pages[key].grid()
        self._active_page = key
        self.sidebar.set_active(key)
        self._update_header_caption()
        page = self._pages[key]
        if hasattr(page, "on_show"):
            page.on_show()

    def _update_header_caption(self):
        if not self._active_page:
            return
        ko = self.t(_NAV_KEYS[self._active_page])
        en = _NAV_CAPTIONS_EN[self._active_page]
        self._header_caption.configure(text=f"{ko} · {en}")

    def refresh_theme(self):
        t = theme.tokens()
        self._header.configure(bg=t["bg"], highlightthickness=1, highlightbackground=t["divider"])
        self._wordmark.configure(bg=t["bg"], fg=t["text"])
        self._header_caption.configure(bg=t["bg"], fg=t["neutral_600"])
        self._header_version.configure(bg=t["bg"], fg=t["neutral_600"])
        self._logo_canvas.configure(bg=t["bg"])
        self._logo_canvas.delete("all")
        self._logo_canvas.create_rectangle(3, 6, 15, 18, outline=t["accent"])
        self._logo_canvas.create_line(9, 1, 9, 23, fill=t["accent"])


if __name__ == "__main__":
    app = App()
    app.mainloop()
