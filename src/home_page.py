"""홈 화면(디자인 시안 2a) - 무엇을 할지 고르는 진입점.

이전 앱에는 없던 화면이다. 파일을 드롭존에 놓으면(tkinterdnd2) 한 개면 분할,
여러 개면 병합으로 바로 넘어가고, 카드를 누르면 해당 화면으로 이동한다.
아래쪽 "최근 작업"은 activity_log.py가 남긴 기록을 최신순으로 보여준다.
"""

import os

import tkinter as tk
from tkinter import ttk

from tkinterdnd2 import DND_FILES

import activity_log
import theme
import widgets
from formats import SUPPORTED_EXTS

_CARD_KEYS = ("split", "merge", "terms", "batch", "convert")
_CARD_CAPTIONS = {
    "split": ("Split", "문장을 자르지 않고 글자 수·크기·개수로 나눕니다."),
    "merge": ("Merge", "순서를 정하고 제목을 붙여 하나로 합칩니다."),
    "terms": ("Terms", "조사까지 자동 교정하며 호칭을 바꿉니다."),
    "batch": ("Batch rename", "패턴이나 CSV로 파일명을 한 번에 바꿉니다."),
    "convert": ("Convert", "txt · docx · hwpx 사이를 오갑니다."),
}
_NAV_KEYS = {
    "split": "nav_split", "merge": "nav_merge", "terms": "nav_terms",
    "batch": "nav_batch", "convert": "nav_convert",
}


class HomePage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()
        self.apply_language()
        self.bind("<Destroy>", self._on_destroy)
        theme.subscribe(self)
        self.refresh_theme()

    def t(self, key, **kwargs):
        return self.app.t(key, **kwargs)

    def _on_destroy(self, _event):
        theme.unsubscribe(self)

    # ---------- UI ----------

    def _build(self):
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(26, 16))
        self.lbl_title = ttk.Label(header, style="Heading.TLabel")
        self.lbl_title.pack(anchor="w")
        ttk.Label(header, text="What do you want to do", style="Caption.TLabel").pack(anchor="w")

        self.drop_zone = widgets.BlueprintFrame(self, tint=theme.tokens()["accent_100"], dashed=True, height=118)
        self.drop_zone.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 18))
        dz = self.drop_zone.content
        self.lbl_drop_title = tk.Label(dz, font=(theme.HEADING_FONT, 17, "bold"))
        self.lbl_drop_title.pack(pady=(18, 2))
        self.lbl_drop_body = tk.Label(dz, font=("Segoe UI", 9))
        self.lbl_drop_body.pack()
        self.lbl_drop_formats = tk.Label(dz, font=("Segoe UI", 8))
        self.lbl_drop_formats.pack(pady=(2, 0))

        self.drop_zone.drop_target_register(DND_FILES)
        self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)

        cards_row = ttk.Frame(self)
        cards_row.grid(row=2, column=0, sticky="ew", padx=30, pady=(0, 18))
        for i in range(len(_CARD_KEYS)):
            cards_row.grid_columnconfigure(i, weight=1, uniform="cards")
        self._cards = {}
        for i, key in enumerate(_CARD_KEYS):
            card = widgets.BlueprintFrame(cards_row, height=132)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            card.bind("<Button-1>", lambda e, k=key: self.app.navigate(k))
            card.content.bind("<Button-1>", lambda e, k=key: self.app.navigate(k))
            card.configure(cursor="hand2")
            kicker = tk.Label(card.content, font=("Segoe UI", 8))
            kicker.pack(anchor="w", padx=10, pady=(10, 0))
            title = tk.Label(card.content, font=(theme.HEADING_FONT, 15, "bold"))
            title.pack(anchor="w", padx=10)
            body = tk.Label(card.content, font=("Segoe UI", 8), wraplength=160, justify="left")
            body.pack(anchor="w", padx=10, pady=(4, 10))
            for w in (kicker, title, body):
                w.bind("<Button-1>", lambda e, k=key: self.app.navigate(k))
                w.configure(cursor="hand2")
            self._cards[key] = {"card": card, "kicker": kicker, "title": title, "body": body}

        recent_frame = ttk.Frame(self)
        recent_frame.grid(row=3, column=0, sticky="nsew", padx=30, pady=(0, 20))
        recent_frame.grid_rowconfigure(1, weight=1)
        recent_frame.grid_columnconfigure(0, weight=1)
        recent_header = ttk.Frame(recent_frame)
        recent_header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.lbl_recent = ttk.Label(recent_header, style="Heading.TLabel")
        self.lbl_recent.pack(side="left")
        ttk.Label(recent_header, text="Recent", style="Caption.TLabel").pack(side="left", padx=(8, 0))
        self.btn_refresh_recent = ttk.Button(recent_header, style="Ghost.TButton", command=self.refresh_recent)
        self.btn_refresh_recent.pack(side="right")

        columns = ("task", "target", "result", "time")
        self.recent_tree = ttk.Treeview(recent_frame, columns=columns, show="headings", height=6)
        self.recent_tree.grid(row=1, column=0, sticky="nsew")
        self.recent_tree.column("task", width=140, anchor="w")
        self.recent_tree.column("target", width=260, anchor="w")
        self.recent_tree.column("result", width=200, anchor="w")
        self.recent_tree.column("time", width=120, anchor="center", stretch=False)

    def apply_language(self):
        self.lbl_title.configure(text="무엇을 할까요?")
        self.lbl_drop_title.configure(text="여기에 파일을 놓으세요")
        self.lbl_drop_body.configure(
            text="Drop files here — 한 개면 분할, 여러 개면 병합·일괄 작업으로 이어집니다"
        )
        self.lbl_drop_formats.configure(text=".txt · .docx · .hwpx")
        for key, widgets_ in self._cards.items():
            en, desc = _CARD_CAPTIONS[key]
            widgets_["kicker"].configure(text=en)
            widgets_["title"].configure(text=self.t(_NAV_KEYS[key]))
            widgets_["body"].configure(text=desc)
        self.lbl_recent.configure(text="최근 작업")
        self.btn_refresh_recent.configure(text="새로고침")
        self.recent_tree.heading("task", text="작업 · Task")
        self.recent_tree.heading("target", text="대상 · Target")
        self.recent_tree.heading("result", text="결과 · Result")
        self.recent_tree.heading("time", text="시각 · Time")
        self.refresh_recent()

    def refresh_theme(self):
        t = theme.tokens()
        for key, widgets_ in self._cards.items():
            card = widgets_["card"]
            for w in (widgets_["kicker"], widgets_["title"], widgets_["body"]):
                w.configure(bg=card._bg_color())
            widgets_["kicker"].configure(fg=t["accent"])
            widgets_["title"].configure(fg=t["text"])
            widgets_["body"].configure(fg=t["neutral_700"])
        for w in (self.lbl_drop_title, self.lbl_drop_body, self.lbl_drop_formats):
            w.configure(bg=self.drop_zone._bg_color())
        self.lbl_drop_title.configure(fg=t["accent_700"])
        self.lbl_drop_body.configure(fg=t["neutral_700"])
        self.lbl_drop_formats.configure(fg=t["neutral_600"])

    # ---------- 드래그앤드롭 ----------

    def _on_drop(self, event):
        try:
            paths = list(self.tk.splitlist(event.data))
        except Exception:
            paths = [event.data]
        valid = [p for p in paths if os.path.isfile(p) and os.path.splitext(p)[1].lower() in SUPPORTED_EXTS]
        if not valid:
            return
        if len(valid) == 1:
            self.app.navigate("split")
            self.app._pages["split"].load_file_from_outside(valid[0])
        else:
            self.app.navigate("merge")
            self.app._pages["merge"].add_paths_from_outside(valid)

    # ---------- 최근 작업 ----------

    def refresh_recent(self):
        self.recent_tree.delete(*self.recent_tree.get_children())
        for entry in activity_log.recent():
            self.recent_tree.insert("", "end", values=(entry["task"], entry["target"], entry["result"], entry["time"]))

    def on_show(self):
        self.refresh_recent()
