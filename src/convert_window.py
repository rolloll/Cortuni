"""확장자(형식) 변환 창.

txt <-> docx, txt <-> hwpx, docx <-> hwpx 변환을 지원한다. 목록에는 형식이
다른 파일이 섞여 있어도 되며, 선택한 목표 형식으로 변환할 수 없는 파일은
개별적으로 건너뛰고 로그에 남긴다.
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from formats import SUPPORTED_EXTS
import convert_apply

TARGET_EXTS = [".txt", ".docx", ".hwpx"]
COLUMNS = ("check", "filename")
CHECK_ON = "☑"
CHECK_OFF = "☐"


class ConvertWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self._entry_by_iid = {}
        self._next_id = 0
        self.entries = []
        self._filename_sort_ascending = False
        self._filename_sort_applied = False

        self.output_dir = tk.StringVar()

        try:
            self.iconphoto(True, master._icon_image)
        except Exception:
            pass

        self._build_widgets()
        self.apply_language()

        if hasattr(master, "_sub_windows"):
            master._sub_windows.append(self)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def t(self, key, **kwargs):
        return self.master_app.t(key, **kwargs)

    def _on_close(self):
        if hasattr(self.master_app, "_sub_windows"):
            try:
                self.master_app._sub_windows.remove(self)
            except ValueError:
                pass
        self.destroy()

    # ---------- UI ----------

    def _build_widgets(self):
        self.geometry("640x600")

        frm_actions = ttk.Frame(self)
        frm_actions.pack(fill="x", padx=10, pady=(10, 4))
        self.btn_add_files = ttk.Button(frm_actions, text="", command=self.on_add_files)
        self.btn_add_files.pack(side="left")
        self.btn_add_folder = ttk.Button(frm_actions, text="", command=self.on_add_folder)
        self.btn_add_folder.pack(side="left", padx=4)
        self.btn_remove = ttk.Button(frm_actions, text="", command=self.on_remove_selected)
        self.btn_remove.pack(side="left", padx=4)

        self.tree = ttk.Treeview(self, columns=COLUMNS, show="headings", selectmode="extended", height=14)
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)
        self.tree.column("check", width=36, anchor="center", stretch=False)
        self.tree.column("filename", width=520, anchor="w")
        self.tree.heading("check", text=CHECK_OFF, command=self.on_toggle_all_checkboxes)

        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_selection_changed)

        frm_target = ttk.Frame(self)
        frm_target.pack(fill="x", padx=10, pady=(0, 6))
        self.lbl_target = ttk.Label(frm_target, text="")
        self.lbl_target.pack(side="left")
        self.combo_target = ttk.Combobox(frm_target, state="readonly", width=16)
        self.combo_target.pack(side="left", padx=6)

        frm_out = ttk.Frame(self)
        frm_out.pack(fill="x", padx=10, pady=4)
        self.lbl_output = ttk.Label(frm_out, text="")
        self.lbl_output.pack(side="left")
        ttk.Entry(frm_out, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=6)
        self.btn_output = ttk.Button(frm_out, text="", command=self.choose_output)
        self.btn_output.pack(side="left")

        self.btn_run = ttk.Button(self, text="", command=self.run_convert)
        self.btn_run.pack(pady=8)

        self.log = scrolledtext.ScrolledText(self, height=8, state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def apply_language(self):
        self.title(self.t("convert_window_title"))
        self.btn_add_files.configure(text=self.t("convert_add_files_button"))
        self.btn_add_folder.configure(text=self.t("convert_add_folder_button"))
        self.btn_remove.configure(text=self.t("convert_remove_button"))
        self.lbl_target.configure(text=self.t("convert_target_label"))
        self.lbl_output.configure(text=self.t("convert_output_label"))
        self.btn_output.configure(text=self.t("convert_output_button"))
        self.btn_run.configure(text=self.t("convert_run_button"))
        self._refresh_filename_heading()
        self.tree.heading("check", text=CHECK_ON if self._all_checked() else CHECK_OFF, command=self.on_toggle_all_checkboxes)

        prev = self.combo_target.get()
        self.combo_target.configure(values=TARGET_EXTS)
        self.combo_target.set(prev if prev in TARGET_EXTS else TARGET_EXTS[0])

    # ---------- 목록 관리 ----------

    def _check_symbol(self, iid):
        return CHECK_ON if iid in self.tree.selection() else CHECK_OFF

    def _all_checked(self):
        children = self.tree.get_children()
        return bool(children) and set(self.tree.selection()) == set(children)

    def _row_values(self, iid, path):
        return (self._check_symbol(iid), os.path.basename(path))

    def _refresh_check_column(self):
        for iid in self.tree.get_children():
            vals = list(self.tree.item(iid, "values"))
            vals[0] = self._check_symbol(iid)
            self.tree.item(iid, values=vals)
        self.tree.heading("check", text=CHECK_ON if self._all_checked() else CHECK_OFF)

    def _refresh_filename_heading(self):
        text = self.t("merge_col_filename")
        if self._filename_sort_applied:
            text += " ▲" if self._filename_sort_ascending else " ▼"
        self.tree.heading("filename", text=text, command=self.on_sort_by_filename)

    def _add_file(self, path):
        iid = str(self._next_id)
        self._next_id += 1
        self._entry_by_iid[iid] = path
        self.tree.insert("", "end", iid=iid, values=self._row_values(iid, path))
        self.entries.append(path)

    def _sync_entries_from_tree(self):
        self.entries = [self._entry_by_iid[iid] for iid in self.tree.get_children()]

    # ---------- 체크박스 / 정렬 ----------

    def _on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        col = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)
        if region == "cell" and col == "#1" and row:
            self._toggle_row_check(row)
            return "break"
        return None

    def _toggle_row_check(self, iid):
        if iid in self.tree.selection():
            self.tree.selection_remove(iid)
        else:
            self.tree.selection_add(iid)

    def on_toggle_all_checkboxes(self):
        children = self.tree.get_children()
        if self._all_checked():
            self.tree.selection_remove(*children)
        elif children:
            self.tree.selection_set(children)

    def on_sort_by_filename(self):
        self._sync_entries_from_tree()
        self._filename_sort_ascending = not self._filename_sort_ascending
        self._filename_sort_applied = True
        ascending = self._filename_sort_ascending
        items = list(self.tree.get_children())
        items.sort(key=lambda iid: os.path.basename(self._entry_by_iid[iid]).lower(), reverse=not ascending)
        for index, iid in enumerate(items):
            self.tree.move(iid, "", index)
        self._refresh_filename_heading()

    def _on_selection_changed(self, _event=None):
        self._refresh_check_column()

    # ---------- 버튼 동작 ----------

    def on_add_files(self):
        paths = filedialog.askopenfilenames(title=self.t("convert_choose_files_title"), filetypes=self.t("filetypes"))
        for path in paths:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".hwp":
                messagebox.showwarning(self.t("hwp_title"), self.t("hwp_body"))
                continue
            if ext not in SUPPORTED_EXTS:
                messagebox.showwarning(self.t("unsupported_title"), self.t("unsupported_body", ext=ext))
                continue
            self._add_file(path)

    def on_add_folder(self):
        folder = filedialog.askdirectory(title=self.t("convert_choose_folder_title"))
        if not folder:
            return
        for name in sorted(os.listdir(folder)):
            full = os.path.join(folder, name)
            ext = os.path.splitext(name)[1].lower()
            if os.path.isfile(full) and ext in SUPPORTED_EXTS:
                self._add_file(full)

    def on_remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(self.t("err_title"), self.t("merge_no_selection"))
            return
        for iid in sel:
            self.tree.delete(iid)
            del self._entry_by_iid[iid]
        self._sync_entries_from_tree()

    def choose_output(self):
        path = filedialog.askdirectory(title=self.t("convert_choose_output_title"))
        if path:
            self.output_dir.set(path)

    # ---------- 실행 ----------

    def log_line(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_running(self, running):
        state = "disabled" if running else "normal"
        for btn in (self.btn_run, self.btn_add_files, self.btn_add_folder, self.btn_remove, self.btn_output):
            btn.configure(state=state)

    def run_convert(self):
        self._sync_entries_from_tree()
        if not self.entries:
            messagebox.showerror(self.t("err_title"), self.t("convert_no_files"))
            return
        out_dir = self.output_dir.get().strip()
        if not out_dir:
            messagebox.showerror(self.t("err_title"), self.t("convert_no_output"))
            return
        target_ext = self.combo_target.get()

        os.makedirs(out_dir, exist_ok=True)
        self.log_line(self.t("convert_log_start", n=len(self.entries), ext=target_ext))
        self._set_running(True)
        thread = threading.Thread(target=self._do_convert, args=(list(self.entries), target_ext, out_dir), daemon=True)
        thread.start()

    def _do_convert(self, paths, target_ext, out_dir):
        created = 0
        for path in paths:
            try:
                out_path = convert_apply.convert_file(path, target_ext, out_dir)
                self.after(0, self.log_line, self.t("convert_log_item", path=out_path))
                created += 1
            except Exception as e:
                self.after(0, self.log_line, self.t("convert_log_error_item", path=path, err=e))

        self.after(0, self.log_line, self.t("convert_log_done", n=created))
        self.after(0, lambda: messagebox.showinfo(self.t("convert_done_title"), self.t("convert_done_body", n=created, out=out_dir)))
        self.after(0, self._set_running, False)
