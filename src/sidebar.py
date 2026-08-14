"""왼쪽 고정 사이드바 - CoriuniNav.dc.html의 포팅.

3개 그룹(분할·병합 / 파일 편집 / 설정)에 항목이 있고, 각 항목은
한글자 표식 + 한글 이름 + (항상 영문인) 소캡션으로 구성된다. 활성 항목은
왼쪽에 accent 색 띠 + 옅은 배경 틴트로 표시한다.
"""

import tkinter as tk

import theme

WIDTH = 208

GROUP_A = (("home", "H"), ("split", "S"), ("merge", "M"))
# GROUP_B에는 원래 ("terms", "T")가 맨 앞에 있었다 - 이름·호칭 기능 비활성화.
GROUP_B = (("batch", "B"), ("convert", "C"))
GROUP_C = (("settings", "⚙"),)

_NAV_KEYS = {
    "home": "nav_home", "split": "nav_split", "merge": "nav_merge",
    "batch": "nav_batch", "convert": "nav_convert",
    "settings": "nav_settings",
    # "terms": "nav_terms",  # 이름·호칭 기능 비활성화
}
# 항상 영어인 장식용 소캡션 - 언어 설정과 무관하게 디자인 시스템 고유의 표기.
_NAV_CAPTIONS = {
    "home": "Home", "split": "Split", "merge": "Merge",
    "batch": "Batch rename", "convert": "Convert",
    "settings": "Settings",
    # "terms": "Terms",  # 이름·호칭 기능 비활성화
}


class Sidebar(tk.Frame):
    def __init__(self, parent, app, active="home", **kwargs):
        kwargs.setdefault("width", WIDTH)
        kwargs.setdefault("highlightthickness", 1)
        super().__init__(parent, **kwargs)
        self.app = app
        self.active = active
        self._rows = {}  # key -> dict(row, bar, mark, title, caption)
        self._section_labels = []
        self.pack_propagate(False)
        self._build()
        theme.subscribe(self)
        self.bind("<Destroy>", lambda e: theme.unsubscribe(self))
        self.refresh_theme()

    def t(self, key, **kwargs):
        return self.app.t(key, **kwargs)

    # ---------- 구성 ----------

    def _build(self):
        self._section_label(self.t("nav_group_split_merge"))
        for key, mark in GROUP_A:
            self._row(key, mark)

        self._section_label(self.t("nav_group_edit"), pady=(18, 6))
        for key, mark in GROUP_B:
            self._row(key, mark)

        bottom = tk.Frame(self)
        bottom.pack(side="bottom", fill="x", pady=(10, 12))
        sep = tk.Frame(bottom, height=1)
        sep.pack(fill="x", padx=16, pady=(0, 10))
        self._separator = sep
        for key, mark in GROUP_C:
            self._row(key, mark, container=bottom)

    def _section_label(self, text, pady=(0, 8)):
        lbl = tk.Label(self, text=text, anchor="w", font=("Segoe UI", 8))
        lbl.pack(fill="x", padx=16, pady=pady)
        self._section_labels.append(lbl)

    def _row(self, key, mark, container=None):
        container = container or self
        row = tk.Frame(container, cursor="hand2")
        row.pack(fill="x")

        bar = tk.Frame(row, width=2)
        bar.pack(side="left", fill="y")

        inner = tk.Frame(row)
        inner.pack(side="left", fill="both", expand=True, padx=(14, 10), pady=8)

        mark_box = tk.Label(inner, text=mark, width=2, font=(theme.HEADING_FONT, 10, "bold"))
        mark_box.pack(side="left", padx=(0, 11))

        text_col = tk.Frame(inner)
        text_col.pack(side="left", fill="x", expand=True)
        title = tk.Label(text_col, text=self.t(_NAV_KEYS[key]), anchor="w", font=(theme.HEADING_FONT, 13, "bold"))
        title.pack(fill="x")
        caption = tk.Label(text_col, text=_NAV_CAPTIONS[key], anchor="w", font=("Segoe UI", 7))
        caption.pack(fill="x")

        for widget in (row, bar, inner, mark_box, text_col, title, caption):
            widget.bind("<Button-1>", lambda e, k=key: self.app.navigate(k))

        self._rows[key] = {"row": row, "bar": bar, "mark": mark_box, "title": title, "caption": caption}

    # ---------- 상태 갱신 ----------

    def set_active(self, key):
        self.active = key
        self._recolor()

    def apply_language(self):
        for key, widgets in self._rows.items():
            widgets["title"].configure(text=self.t(_NAV_KEYS[key]))
        # 섹션 소제목도 다시 그려야 하므로 통째로 재구성.
        for lbl in self._section_labels:
            lbl.destroy()
        self._section_labels = []
        for row_widgets in self._rows.values():
            row_widgets["row"].destroy()
        self._rows = {}
        for child in self.winfo_children():
            child.destroy()
        self._build()
        self._recolor()

    def refresh_theme(self):
        t = theme.tokens()
        self.configure(bg=t["bg"], highlightbackground=t["divider"], highlightcolor=t["divider"])
        for lbl in self._section_labels:
            lbl.configure(bg=t["bg"], fg=t["neutral_600"])
        if hasattr(self, "_separator"):
            self._separator.configure(bg=t["divider"])
        self._recolor()

    def _recolor(self):
        t = theme.tokens()
        for key, widgets in self._rows.items():
            active = key == self.active
            bg = t["accent_200"] if active else t["bg"]
            fg = t["accent_800"] if active else t["text"]
            mk_border = t["accent"] if active else t["divider"]
            bar_color = t["accent"] if active else t["bg"]

            for name in ("row", "bar", "mark", "title", "caption"):
                pass
            widgets["row"].configure(bg=bg)
            widgets["bar"].configure(bg=bar_color)
            for child in widgets["row"].winfo_children():
                if child is widgets["bar"]:
                    continue
                child.configure(bg=bg)
                for grandchild in child.winfo_children():
                    grandchild.configure(bg=bg)
            widgets["mark"].configure(
                bg=bg, fg=fg, highlightthickness=1, highlightbackground=mk_border, highlightcolor=mk_border,
            )
            widgets["title"].configure(bg=bg, fg=fg)
            widgets["caption"].configure(bg=bg, fg=t["neutral_600"])
