"""설정 화면(디자인 시안 2g) - 언어 / 테마 / 글꼴 / 업데이트를 한 화면에서 관리."""

import threading
import webbrowser
import tkinter as tk
from tkinter import ttk

import dialogs
import fonts
import prefs
import theme
import update_checker
import widgets
from i18n import LANGUAGES
from version import __version__


class SettingsPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()
        self.apply_language()
        self.bind("<Destroy>", self._on_destroy)

    def t(self, key, **kwargs):
        return self.app.t(key, **kwargs)

    # ---------- 구성 ----------

    def _build(self):
        self.lbl_title = ttk.Label(self, style="Heading.TLabel")
        self.lbl_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=30, pady=(26, 2))
        ttk.Label(self, text="Settings", style="Caption.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=30, pady=(0, 20)
        )

        grid = ttk.Frame(self)
        grid.grid(row=2, column=0, columnspan=2, sticky="nw", padx=30)

        lang_names = [name for name, _ in LANGUAGES]
        self._lang_var = tk.StringVar(value=lang_names[0])
        self.lbl_lang_row = ttk.Label(grid, style="Heading.TLabel")
        self.lbl_lang_row.grid(row=0, column=0, sticky="w", pady=10, padx=(0, 24))
        self.seg_lang = widgets.Segmented(
            grid, [(n, n) for n in lang_names], self._lang_var, command=self._on_lang_selected
        )
        self.seg_lang.grid(row=0, column=1, sticky="w", pady=10)

        self._theme_var = tk.StringVar(value=theme.current_mode())
        self.lbl_theme_row = ttk.Label(grid, style="Heading.TLabel")
        self.lbl_theme_row.grid(row=1, column=0, sticky="w", pady=10, padx=(0, 24))
        self.seg_theme = widgets.Segmented(
            grid,
            [("light", "밝게 / Light"), ("dark", "어둡게 / Dark"), ("system", "시스템 / System")],
            self._theme_var, command=self._on_theme_selected,
        )
        self.seg_theme.grid(row=1, column=1, sticky="w", pady=10)

        self.lbl_font_row = ttk.Label(grid, style="Heading.TLabel")
        self.lbl_font_row.grid(row=2, column=0, sticky="w", pady=10, padx=(0, 24))
        font_row = ttk.Frame(grid)
        font_row.grid(row=2, column=1, sticky="w", pady=10)
        self._font_var = tk.StringVar()
        self.combo_font = ttk.Combobox(
            font_row, textvariable=self._font_var, values=fonts.list_available_fonts(),
            state="readonly", width=28,
        )
        self.combo_font.pack(side="left")
        self.combo_font.bind("<<ComboboxSelected>>", self._on_font_selected)
        self.lbl_font_preview = ttk.Label(font_row, style="Muted.TLabel")
        self.lbl_font_preview.pack(side="left", padx=(14, 0))

        self.lbl_update_row = ttk.Label(grid, style="Heading.TLabel")
        self.lbl_update_row.grid(row=3, column=0, sticky="w", pady=10, padx=(0, 24))
        update_row = ttk.Frame(grid)
        update_row.grid(row=3, column=1, sticky="w", pady=10)
        self._check_startup_var = tk.BooleanVar(value=prefs.load_prefs().get("check_updates_on_startup", True))
        self.chk_startup = ttk.Checkbutton(
            update_row, variable=self._check_startup_var, command=self._on_check_startup_toggled,
        )
        self.chk_startup.pack(side="left")
        self.btn_check_now = ttk.Button(update_row, style="Ghost.TButton", command=self._on_check_now)
        self.btn_check_now.pack(side="left", padx=(14, 14))
        self.lbl_version_tag = ttk.Label(update_row, style="Muted.TLabel")
        self.lbl_version_tag.pack(side="left")

        self.note = widgets.BlueprintFrame(self)
        self.note.grid(row=4, column=0, columnspan=2, sticky="ew", padx=30, pady=(30, 20))
        self.lbl_note = ttk.Label(self.note.content, style="Muted.TLabel", wraplength=680, justify="left")
        self.lbl_note.pack(anchor="w", padx=12, pady=10)

    # ---------- App -> 페이지 동기화 ----------

    def sync_from_app(self):
        family = getattr(self.app, "_content_font_family", "") or ""
        if family:
            self._font_var.set(family)
        self._theme_var.set(theme.current_mode())
        self._update_font_preview()

    # ---------- 이벤트 ----------

    def _on_lang_selected(self, name):
        code = dict(LANGUAGES).get(name)
        if code:
            self.app.on_lang_selected(code)

    def _on_theme_selected(self, mode):
        self.app.on_theme_selected(mode)

    def _on_font_selected(self, _event=None):
        family = self._font_var.get()
        self.app.on_font_selected(family)
        self._update_font_preview()

    def _on_check_startup_toggled(self):
        prefs.set_pref("check_updates_on_startup", bool(self._check_startup_var.get()))

    def _on_check_now(self):
        self.btn_check_now.configure(state="disabled")
        threading.Thread(target=self._do_check_now, daemon=True).start()

    def _do_check_now(self):
        result = update_checker.check_for_update(__version__)
        self.after(0, self._show_check_now_result, result)

    def _show_check_now_result(self, result):
        self.btn_check_now.configure(state="normal")
        if result is not None:
            latest_tag, url = result
            if dialogs.ask_yes_no(
                self, self.t("update_available_title"),
                self.t("update_available_body", latest=latest_tag, current=__version__),
            ):
                webbrowser.open(url)
        else:
            dialogs.show_info(
                self, self.t("settings_up_to_date_title"), self.t("settings_up_to_date_body", version=__version__)
            )

    # ---------- 언어/테마/폰트 표시 갱신 ----------

    def apply_language(self):
        self.lbl_title.configure(text=self.t("settings_window_title"))
        self.lbl_lang_row.configure(text=self.t("lang_label"))
        self.lbl_theme_row.configure(text=self.t("settings_theme_label"))
        self.lbl_font_row.configure(text=self.t("font_label"))
        self.lbl_update_row.configure(text=self.t("settings_update_label"))
        self.chk_startup.configure(text=self.t("settings_check_on_startup"))
        self.btn_check_now.configure(text=self.t("settings_check_now_button"))
        self.lbl_version_tag.configure(text=self.t("settings_current_version", version=__version__))
        self.lbl_note.configure(text=self.t("settings_hwp_note"))
        self._update_font_preview()

    def _update_font_preview(self):
        family = self._font_var.get() or theme.BODY_FONT
        self.lbl_font_preview.configure(text=self.t("settings_font_preview"), font=(family, 10))

    def _on_destroy(self, _event):
        pass
