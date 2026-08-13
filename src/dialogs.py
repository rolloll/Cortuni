"""tkinter.messagebox 대신 쓰는, 디자인 토큰을 따르는 대화상자(.dialog).

네이티브 messagebox는 서식을 전혀 바꿀 수 없어서(글꼴/테두리/색 고정) 이 앱의
청사진 톤과 항상 어긋난다. 여기 있는 네 함수가 그 자리를 대신한다:

    dialogs.show_info(self, title, message)
    dialogs.show_warning(self, title, message)
    dialogs.show_error(self, title, message)
    dialogs.ask_yes_no(self, title, message)  # -> bool

parent는 페이지(Frame)든 루트든 아무 위젯이나 된다 - winfo_toplevel()로 실제
최상위 창을 찾아 그 자식으로 모달을 띄운다.
"""

import tkinter as tk
from tkinter import ttk

import theme
import widgets

_ICONS = {"info": "✓", "warn": "!", "error": "!", "question": "?"}


class _MessageDialog(tk.Toplevel):
    def __init__(self, parent, title, message, icon="info", mode="ok", ok_label="닫기",
                 yes_label="예", no_label="아니요"):
        master = parent.winfo_toplevel()
        super().__init__(master)
        self.withdraw()
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.result = None

        t = theme.tokens()
        self.configure(bg=t["bg"])

        card = widgets.BlueprintFrame(self, tint=t["surface"])
        card.pack(fill="both", expand=True, padx=14, pady=14)
        body = card.content

        header = tk.Frame(body, bg=t["surface"])
        header.pack(fill="x", padx=18, pady=(16, 8))
        icon_color = t["accent"]
        icon_box = tk.Label(
            header, text=_ICONS.get(icon, "i"), width=2, height=1,
            font=(theme.HEADING_FONT, 13, "bold"), fg=t["accent_700"], bg=t["surface"],
            highlightthickness=1, highlightbackground=icon_color, highlightcolor=icon_color,
        )
        icon_box.pack(side="left", padx=(0, 11))
        title_label = tk.Label(
            header, text=title, font=(theme.HEADING_FONT, 15, "bold"),
            fg=t["text"], bg=t["surface"], anchor="w", justify="left",
        )
        title_label.pack(side="left", fill="x", expand=True)

        body_label = tk.Label(
            body, text=message, font=(theme.BODY_FONT, 10), fg=t["text"], bg=t["surface"],
            justify="left", anchor="w", wraplength=380,
        )
        body_label.pack(fill="x", padx=18, pady=(0, 14))

        actions = tk.Frame(body, bg=t["surface"])
        actions.pack(fill="x", padx=18, pady=(0, 16))

        if mode == "yesno":
            ttk.Button(actions, text=no_label, style="Secondary.TButton", command=self._on_no).pack(
                side="right", padx=(8, 0)
            )
            ttk.Button(actions, text=yes_label, style="Primary.TButton", command=self._on_yes).pack(side="right")
        else:
            ttk.Button(actions, text=ok_label, style="Primary.TButton", command=self._on_ok).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())

        self.update_idletasks()
        self._center_on(master)
        self.deiconify()
        self.grab_set()
        self.focus_set()

    def _center_on(self, master):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        mx, my = master.winfo_rootx(), master.winfo_rooty()
        mw, mh = master.winfo_width(), master.winfo_height()
        x = mx + max(0, (mw - w) // 2)
        y = my + max(0, (mh - h) // 3)
        self.geometry(f"+{x}+{y}")

    def _on_ok(self):
        self.result = True
        self.destroy()

    def _on_yes(self):
        self.result = True
        self.destroy()

    def _on_no(self):
        self.result = False
        self.destroy()

    def _on_close(self):
        self.result = False
        self.destroy()

    def show(self):
        self.wait_window(self)
        return self.result


def show_info(parent, title, message, ok_label="닫기"):
    _MessageDialog(parent, title, message, icon="info", ok_label=ok_label).show()


def show_warning(parent, title, message, ok_label="닫기"):
    _MessageDialog(parent, title, message, icon="warn", ok_label=ok_label).show()


def show_error(parent, title, message, ok_label="닫기"):
    _MessageDialog(parent, title, message, icon="error", ok_label=ok_label).show()


def ask_yes_no(parent, title, message, yes_label="예", no_label="아니요"):
    return bool(
        _MessageDialog(
            parent, title, message, icon="question", mode="yesno", yes_label=yes_label, no_label=no_label
        ).show()
    )
