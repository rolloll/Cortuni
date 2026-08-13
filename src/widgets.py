"""'Industry' 디자인 시스템의 재사용 위젯: BlueprintFrame(청사진 테두리+귀퉁이 표식),
Segmented(분할 선택 버튼), make_tag(작은 라벨 칩).

전부 theme.py의 토큰을 쓰고, theme.subscribe()로 등록해서 라이트/다크 전환 시
스스로 다시 그린다.
"""

import tkinter as tk
from tkinter import ttk

import theme


class BlueprintFrame(tk.Canvas):
    """헤어라인 테두리 + 네 귀퉁이 '+' 등록 마크가 있는 프레임(디자인의 .blueprint).

    실제 내용은 .content(평범한 tk.Frame)에 얹는다:
        bp = BlueprintFrame(parent)
        bp.pack(...)
        ttk.Label(bp.content, text="...").pack(...)

    tint을 주면 여백/내용 배경이 그 색이 된다(디자인에서 옅은 accent 틴트를 쓰는
    카드/드롭존/통계 카드 등). 기본은 현재 테마의 bg.
    """

    MARGIN = 7
    TICK = 6

    def __init__(self, parent, tint=None, dashed=False, **kwargs):
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("bd", 0)
        super().__init__(parent, **kwargs)
        self._tint = tint
        self._dashed = dashed
        self._border_id = None
        self._corner_ids = []
        self.content = tk.Frame(self, bd=0, highlightthickness=0)
        self._window_id = self.create_window(0, 0, anchor="nw", window=self.content)
        self.bind("<Configure>", self._on_configure)
        self.bind("<Destroy>", lambda e: theme.unsubscribe(self))
        theme.subscribe(self)
        self.refresh_theme()

    def _on_configure(self, event):
        m = self.MARGIN
        inner_w = max(0, event.width - 2 * m)
        inner_h = max(0, event.height - 2 * m)
        self.coords(self._window_id, m, m)
        self.itemconfig(self._window_id, width=inner_w, height=inner_h)
        self._redraw(event.width, event.height)

    def _bg_color(self):
        t = theme.tokens()
        return self._tint or t["bg"]

    def _redraw(self, w=None, h=None):
        w = w if w is not None else self.winfo_width()
        h = h if h is not None else self.winfo_height()
        m = self.MARGIN
        t = theme.tokens()
        bg = self._bg_color()

        self.configure(bg=bg)
        self.content.configure(bg=bg)

        for item in filter(None, [self._border_id, *self._corner_ids]):
            self.delete(item)
        self._corner_ids = []
        self._border_id = None

        if w <= 2 * m or h <= 2 * m:
            return

        dash = (4, 3) if self._dashed else None
        self._border_id = self.create_rectangle(
            m, m, w - m, h - m, outline=t["divider"], width=1, dash=dash
        )
        corner_color = t["neutral_500"]
        tick = self.TICK
        for cx, cy in ((m, m), (w - m, m), (m, h - m), (w - m, h - m)):
            self._corner_ids.append(self.create_line(cx - tick, cy, cx + tick, cy, fill=corner_color))
            self._corner_ids.append(self.create_line(cx, cy - tick, cx, cy + tick, fill=corner_color))

    def refresh_theme(self):
        self._redraw()


class Segmented(tk.Frame):
    """단일 선택 세그먼트 버튼 그룹(디자인의 .seg / .seg-opt).

    options: [(value, label), ...]. variable: tk.StringVar - 바깥에서 값을 바꿔도
    자동으로 다시 그려진다.
    """

    def __init__(self, parent, options, variable, command=None, **kwargs):
        kwargs.setdefault("bd", 0)
        kwargs.setdefault("highlightthickness", 1)
        super().__init__(parent, **kwargs)
        self.options = list(options)
        self.variable = variable
        self.command = command
        self._buttons = []

        for i, (value, label) in enumerate(self.options):
            if i > 0:
                ttk.Separator(self, orient="vertical").pack(side="left", fill="y")
            btn = ttk.Button(self, text=label, style="SegOff.TButton", command=lambda v=value: self._select(v))
            btn.pack(side="left")
            btn.bind("<Left>", lambda e, idx=i: self._move(idx, -1))
            btn.bind("<Right>", lambda e, idx=i: self._move(idx, 1))
            self._buttons.append((value, btn))

        self._trace_id = self.variable.trace_add("write", lambda *a: self._sync())
        self.bind("<Destroy>", self._on_destroy)
        theme.subscribe(self)
        self._sync()
        self.refresh_theme()

    def _select(self, value):
        self.variable.set(value)
        if self.command:
            self.command(value)

    def _move(self, idx, delta):
        new_idx = max(0, min(len(self._buttons) - 1, idx + delta))
        value, btn = self._buttons[new_idx]
        self._select(value)
        btn.focus_set()

    def _sync(self):
        current = self.variable.get()
        for value, btn in self._buttons:
            btn.configure(style="SegOn.TButton" if value == current else "SegOff.TButton")

    def refresh_theme(self):
        t = theme.tokens()
        self.configure(bg=t["divider"], highlightbackground=t["divider"], highlightcolor=t["divider"])
        self._sync()

    def _on_destroy(self, _event):
        theme.unsubscribe(self)
        try:
            self.variable.trace_remove("write", self._trace_id)
        except Exception:
            pass


_TAG_STYLES = {
    "accent": "TagAccent.TLabel",
    "neutral": "TagNeutral.TLabel",
    "outline": "TagOutline.TLabel",
}


def make_tag(parent, text, variant="accent"):
    """작은 라벨 칩(디자인의 .tag-accent/-neutral/-outline)을 만든다."""
    style = _TAG_STYLES.get(variant, _TAG_STYLES["accent"])
    return ttk.Label(parent, text=text, style=style)
