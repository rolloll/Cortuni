"""코리우니(Coriuni) - 문장이 잘리지 않는 글자수 기준 파일 분할/병합 도구.

지원 형식: .txt, .docx(MS Word), .hwpx(한글 최신 XML 형식)
.hwp(구버전 바이너리 한글 파일)는 공식 파서가 없어 지원하지 않는다.
한글 프로그램에서 "다른 이름으로 저장 > HWPX"로 변환한 뒤 사용해야 한다.

분할/병합/이름·호칭 바꾸기는 각각 별도의 창에서 이루어지며, 이 창은 그 창들을
여는 진입점 역할만 한다.
"""

import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox, ttk

from i18n import STRINGS, LANGUAGES
from rename_window import RenameWindow
from merge_window import MergeWindow
from split_window import SplitWindow
from batch_rename_window import BatchRenameWindow
from convert_window import ConvertWindow
from version import __version__
import update_checker
import fonts
import prefs

DEFAULT_LANG = "ko"


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


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.resizable(True, True)

        try:
            self._icon_image = tk.PhotoImage(file=resource_path("icon.png"))
            self.iconphoto(True, self._icon_image)
        except Exception:
            pass

        self.lang = DEFAULT_LANG
        self._sub_windows = []
        self._rename_window = None
        self._merge_window = None
        self._split_window = None
        self._batch_rename_window = None
        self._convert_window = None
        self.edit_section_expanded = False

        self._build_widgets()
        self.apply_language()
        self._init_font()

        self.bind_all("<Control-h>", self._open_rename_window_event)
        self.bind_all("<Control-H>", self._open_rename_window_event)

        threading.Thread(target=self._check_for_update, daemon=True).start()

    def _init_font(self):
        available = fonts.list_available_fonts()
        saved = prefs.load_prefs().get("font_family")
        initial = saved if saved in available else fonts.resolve_default_font(self.lang, available)
        fonts.apply_font_family(initial)
        if initial in available:
            self.combo_font.set(initial)

    def _on_font_selected(self, _event=None):
        family = self.combo_font.get()
        fonts.apply_font_family(family)
        prefs.set_pref("font_family", family)

    def _check_for_update(self):
        result = update_checker.check_for_update(__version__)
        if result is not None:
            latest_tag, url = result
            self.after(0, self._show_update_notice, latest_tag, url)

    def _show_update_notice(self, latest_tag, url):
        if messagebox.askyesno(
            self.t("update_available_title"),
            self.t("update_available_body", latest=latest_tag, current=__version__),
        ):
            webbrowser.open(url)

    def t(self, key, **kwargs):
        text = STRINGS[self.lang][key]
        return text.format(**kwargs) if kwargs else text

    def _build_widgets(self):
        frm_lang = ttk.Frame(self)
        frm_lang.pack(fill="x", padx=10, pady=(10, 0))
        self.lbl_lang = ttk.Label(frm_lang, text="")
        self.lbl_lang.pack(side="left")
        lang_names = [name for name, _ in LANGUAGES]
        self.combo_lang = ttk.Combobox(frm_lang, values=lang_names, state="readonly", width=12)
        self.combo_lang.current(0)
        self.combo_lang.pack(side="left", padx=6)
        self.combo_lang.bind("<<ComboboxSelected>>", self._on_lang_selected)

        self.lbl_font = ttk.Label(frm_lang, text="")
        self.lbl_font.pack(side="left", padx=(16, 0))
        self.combo_font = ttk.Combobox(frm_lang, values=fonts.list_available_fonts(), state="readonly", width=24)
        self.combo_font.pack(side="left", padx=6)
        self.combo_font.bind("<<ComboboxSelected>>", self._on_font_selected)

        self.frm_split_section = ttk.LabelFrame(self, text="")
        self.frm_split_section.pack(fill="x", padx=10, pady=10)
        frm_split_buttons = ttk.Frame(self.frm_split_section)
        frm_split_buttons.pack(pady=14)
        self.btn_split = ttk.Button(frm_split_buttons, text="", command=self.open_split_window, width=14)
        self.btn_split.pack(side="left", padx=8)
        self.btn_merge = ttk.Button(frm_split_buttons, text="", command=self.open_merge_window, width=14)
        self.btn_merge.pack(side="left", padx=8)

        self.frm_edit_outer = ttk.Frame(self)
        self.frm_edit_outer.pack(fill="x", padx=10, pady=(0, 10))

        frm_edit_header = ttk.Frame(self.frm_edit_outer)
        frm_edit_header.pack(fill="x")
        self.btn_edit_toggle = ttk.Button(frm_edit_header, text="▶", width=3, command=self.toggle_edit_section)
        self.btn_edit_toggle.pack(side="left")
        self.lbl_edit_section = ttk.Label(frm_edit_header, text="", font=("", 10, "bold"))
        self.lbl_edit_section.pack(side="left", padx=6)

        self.frm_edit_content = ttk.Frame(self.frm_edit_outer)
        frm_edit_buttons = ttk.Frame(self.frm_edit_content)
        frm_edit_buttons.pack(pady=14)
        self.btn_rename = ttk.Button(frm_edit_buttons, text="", command=self.open_rename_window)
        self.btn_rename.pack(side="left", padx=6)
        self.btn_batch_rename = ttk.Button(frm_edit_buttons, text="", command=self.open_batch_rename_window)
        self.btn_batch_rename.pack(side="left", padx=6)
        self.btn_convert = ttk.Button(frm_edit_buttons, text="", command=self.open_convert_window)
        self.btn_convert.pack(side="left", padx=6)

        if self.edit_section_expanded:
            self.frm_edit_content.pack(fill="x")

    def _on_lang_selected(self, _event=None):
        name = self.combo_lang.get()
        code = dict((n, c) for n, c in LANGUAGES).get(name, DEFAULT_LANG)
        self.lang = code
        self.apply_language()

    def apply_language(self):
        self.title(self.t("window_title"))
        self.lbl_lang.configure(text=self.t("lang_label"))
        self.lbl_font.configure(text=self.t("font_label"))
        self.frm_split_section.configure(text=self.t("section_split_label"))
        self.btn_split.configure(text=self.t("run_button"))
        self.btn_merge.configure(text=self.t("merge_button"))
        self.lbl_edit_section.configure(text=self.t("section_edit_label"))
        self.btn_rename.configure(text=self.t("rename_menu_button"))
        self.btn_batch_rename.configure(text=self.t("batch_rename_button"))
        self.btn_convert.configure(text=self.t("convert_button"))

        for win in list(self._sub_windows):
            if win.winfo_exists():
                win.apply_language()
            else:
                self._sub_windows.remove(win)

    def toggle_edit_section(self):
        self.edit_section_expanded = not self.edit_section_expanded
        if self.edit_section_expanded:
            self.frm_edit_content.pack(fill="x")
            self.btn_edit_toggle.configure(text="▼")
        else:
            self.frm_edit_content.pack_forget()
            self.btn_edit_toggle.configure(text="▶")

    def _open_rename_window_event(self, _event=None):
        self.open_rename_window()

    def open_rename_window(self):
        if self._rename_window is not None and self._rename_window.winfo_exists():
            self._rename_window.lift()
            self._rename_window.focus_force()
            return
        self._rename_window = RenameWindow(self)

    def open_merge_window(self):
        if self._merge_window is not None and self._merge_window.winfo_exists():
            self._merge_window.lift()
            self._merge_window.focus_force()
            return
        self._merge_window = MergeWindow(self)

    def open_split_window(self):
        if self._split_window is not None and self._split_window.winfo_exists():
            self._split_window.lift()
            self._split_window.focus_force()
            return
        self._split_window = SplitWindow(self)

    def open_batch_rename_window(self):
        if self._batch_rename_window is not None and self._batch_rename_window.winfo_exists():
            self._batch_rename_window.lift()
            self._batch_rename_window.focus_force()
            return
        self._batch_rename_window = BatchRenameWindow(self)

    def open_convert_window(self):
        if self._convert_window is not None and self._convert_window.winfo_exists():
            self._convert_window.lift()
            self._convert_window.focus_force()
            return
        self._convert_window = ConvertWindow(self)


if __name__ == "__main__":
    app = App()
    app.mainloop()
