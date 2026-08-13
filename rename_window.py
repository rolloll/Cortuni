"""이름·호칭 바꾸기(Ctrl+H) 창.

호칭/지칭어·고유명사 사전을 관리(추가/삭제/CSV 불러오기, 작품별 그룹핑)하고,
선택한 파일(txt/docx/hwpx)에 일괄 치환(조사 자동 교정 포함)을 적용한다.
"""

import csv
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from formats import SUPPORTED_EXTS
from term_dict import TermDict, COMMON_GROUP
import rename_apply


class RenameWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.term_dict = TermDict()

        self.file_path = tk.StringVar()
        self.output_dir = tk.StringVar()

        try:
            self.iconphoto(True, master._icon_image)
        except Exception:
            pass

        self._build_widgets()
        self.refresh_dict_view()
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

    def _build_widgets(self):
        self.geometry("760x640")

        self.lbl_dict = ttk.Label(self, font=("", 10, "bold"))
        self.lbl_dict.pack(anchor="w", padx=10, pady=(10, 0))

        columns = ("old", "new", "group")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="extended", height=12)
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)
        for col in columns:
            self.tree.column(col, width=200, anchor="w")

        frm_add = ttk.Frame(self)
        frm_add.pack(fill="x", padx=10, pady=4)

        self.lbl_old = ttk.Label(frm_add, text="")
        self.lbl_old.grid(row=0, column=0, sticky="w")
        self.entry_old = ttk.Entry(frm_add, width=16)
        self.entry_old.grid(row=0, column=1, padx=4)

        self.lbl_new = ttk.Label(frm_add, text="")
        self.lbl_new.grid(row=0, column=2, sticky="w")
        self.entry_new = ttk.Entry(frm_add, width=16)
        self.entry_new.grid(row=0, column=3, padx=4)

        self.lbl_group = ttk.Label(frm_add, text="")
        self.lbl_group.grid(row=0, column=4, sticky="w")
        self.entry_group = ttk.Entry(frm_add, width=16)
        self.entry_group.grid(row=0, column=5, padx=4)

        self.btn_add = ttk.Button(frm_add, text="", command=self.on_add)
        self.btn_add.grid(row=0, column=6, padx=4)

        frm_actions = ttk.Frame(self)
        frm_actions.pack(fill="x", padx=10, pady=(0, 6))
        self.btn_delete = ttk.Button(frm_actions, text="", command=self.on_delete_selected)
        self.btn_delete.pack(side="left")
        self.btn_import = ttk.Button(frm_actions, text="", command=self.on_import_csv)
        self.btn_import.pack(side="left", padx=6)
        self.btn_example_csv = ttk.Button(frm_actions, text="", command=self.on_create_example_csv)
        self.btn_example_csv.pack(side="left", padx=6)

        ttk.Separator(self).pack(fill="x", padx=10, pady=6)

        self.lbl_groups = ttk.Label(self)
        self.lbl_groups.pack(anchor="w", padx=10)
        self.groups_list = tk.Listbox(self, selectmode="extended", height=4, exportselection=False)
        self.groups_list.pack(fill="x", padx=10, pady=(0, 6))

        frm_file = ttk.Frame(self)
        frm_file.pack(fill="x", padx=10, pady=4)
        self.lbl_file = ttk.Label(frm_file, text="")
        self.lbl_file.pack(side="left")
        ttk.Entry(frm_file, textvariable=self.file_path).pack(side="left", fill="x", expand=True, padx=6)
        self.btn_file = ttk.Button(frm_file, text="", command=self.choose_file)
        self.btn_file.pack(side="left")

        frm_out = ttk.Frame(self)
        frm_out.pack(fill="x", padx=10, pady=4)
        self.lbl_output = ttk.Label(frm_out, text="")
        self.lbl_output.pack(side="left")
        ttk.Entry(frm_out, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=6)
        self.btn_output = ttk.Button(frm_out, text="", command=self.choose_output_dir)
        self.btn_output.pack(side="left")

        self.btn_run = ttk.Button(self, text="", command=self.run_rename)
        self.btn_run.pack(pady=8)

        self.log = scrolledtext.ScrolledText(self, height=8, state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def apply_language(self):
        self.title(self.t("rename_window_title"))
        self.lbl_dict.configure(text=self.t("rename_dict_label"))
        self.tree.heading("old", text=self.t("rename_col_old"))
        self.tree.heading("new", text=self.t("rename_col_new"))
        self.tree.heading("group", text=self.t("rename_col_group"))
        self.lbl_old.configure(text=self.t("rename_add_old_label"))
        self.lbl_new.configure(text=self.t("rename_add_new_label"))
        self.lbl_group.configure(text=self.t("rename_add_group_label"))
        self.btn_add.configure(text=self.t("rename_add_button"))
        self.btn_delete.configure(text=self.t("rename_delete_button"))
        self.btn_import.configure(text=self.t("rename_import_button"))
        self.btn_example_csv.configure(text=self.t("rename_example_csv_button"))
        self.lbl_groups.configure(text=self.t("rename_groups_label"))
        self.lbl_file.configure(text=self.t("rename_file_label"))
        self.btn_file.configure(text=self.t("rename_file_button"))
        self.lbl_output.configure(text=self.t("rename_output_label"))
        self.btn_output.configure(text=self.t("rename_output_button"))
        self.btn_run.configure(text=self.t("rename_run_button"))
        self.refresh_groups_list()

    def refresh_dict_view(self):
        self.tree.delete(*self.tree.get_children())
        for entry in self.term_dict.entries:
            group_display = entry["작품"] if entry["작품"] else self.t("rename_common_group")
            self.tree.insert("", "end", values=(entry["원래단어"], entry["바꿀단어"], group_display))
        self.refresh_groups_list()

    def refresh_groups_list(self):
        selected_names = {self.groups_list.get(i) for i in self.groups_list.curselection()}
        self.groups_list.delete(0, "end")
        for g in self.term_dict.groups():
            self.groups_list.insert("end", g)
        for i in range(self.groups_list.size()):
            if self.groups_list.get(i) in selected_names:
                self.groups_list.selection_set(i)

    def selected_groups(self):
        return [self.groups_list.get(i) for i in self.groups_list.curselection()]

    def on_add(self):
        old = self.entry_old.get().strip()
        new = self.entry_new.get().strip()
        group = self.entry_group.get().strip()
        if not old:
            messagebox.showerror(self.t("err_title"), self.t("rename_add_missing_old"))
            return
        self.term_dict.add(old, new, group)
        self.entry_old.delete(0, "end")
        self.entry_new.delete(0, "end")
        self.entry_group.delete(0, "end")
        self.refresh_dict_view()

    def on_delete_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning(self.t("err_title"), self.t("rename_no_selection"))
            return
        indices = [self.tree.index(item) for item in selected_items]
        if not messagebox.askyesno(
            self.t("rename_delete_confirm_title"),
            self.t("rename_delete_confirm_body", n=len(indices)),
        ):
            return
        self.term_dict.delete(indices)
        self.refresh_dict_view()

    def on_create_example_csv(self):
        path = filedialog.asksaveasfilename(
            title=self.t("rename_choose_example_csv_title"),
            defaultextension=".csv",
            filetypes=self.t("rename_csv_filetypes"),
            initialfile="coriuni_rename_example.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["원래단어", "바꿀단어", "작품"])
            writer.writerow(["형", "언니", ""])
            writer.writerow(["철수", "영희", "작품A"])
            writer.writerow(["오빠", "언니", ""])
        messagebox.showinfo(self.t("rename_example_csv_button"), self.t("rename_example_csv_saved", path=path))

    def on_import_csv(self):
        path = filedialog.askopenfilename(
            title=self.t("rename_choose_csv_title"),
            filetypes=self.t("rename_csv_filetypes"),
        )
        if not path:
            return
        try:
            count = self.term_dict.import_csv(path)
        except Exception as e:
            messagebox.showerror(self.t("rename_error_title"), self.t("rename_error_body", err=e))
            return
        self.refresh_dict_view()
        messagebox.showinfo(self.t("rename_import_title"), self.t("rename_import_done", n=count))

    def choose_file(self):
        path = filedialog.askopenfilename(title=self.t("choose_file_title"), filetypes=self.t("filetypes"))
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if ext == ".hwp":
            messagebox.showwarning(self.t("hwp_title"), self.t("hwp_body"))
            return
        if ext not in SUPPORTED_EXTS:
            messagebox.showwarning(self.t("unsupported_title"), self.t("unsupported_body", ext=ext))
            return
        self.file_path.set(path)
        if not self.output_dir.get():
            base = os.path.splitext(os.path.basename(path))[0]
            suffix = self.t("rename_outdir_suffix")
            self.output_dir.set(os.path.join(os.path.dirname(path), f"{base}{suffix}"))

    def choose_output_dir(self):
        path = filedialog.askdirectory(title=self.t("choose_output_title"))
        if path:
            self.output_dir.set(path)

    def log_line(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def run_rename(self):
        path = self.file_path.get().strip()
        out_dir = self.output_dir.get().strip()

        if not path or not os.path.isfile(path):
            messagebox.showerror(self.t("err_title"), self.t("err_no_file"))
            return
        if not out_dir:
            messagebox.showerror(self.t("err_title"), self.t("err_no_outdir"))
            return

        groups = self.selected_groups()
        mapping = self.term_dict.active_mapping(groups)

        os.makedirs(out_dir, exist_ok=True)

        self.log_line(self.t("rename_log_start", path=path))
        group_text = ", ".join(groups) if groups else self.t("rename_log_no_active_groups")
        self.log_line(self.t("rename_log_active_groups", groups=group_text))

        if not mapping:
            self.log_line(self.t("rename_log_no_change"))
            return

        self._set_running(True)
        thread = threading.Thread(target=self._do_rename, args=(path, mapping, out_dir), daemon=True)
        thread.start()

    def _set_running(self, running):
        state = "disabled" if running else "normal"
        for btn in (
            self.btn_run, self.btn_add, self.btn_delete, self.btn_import,
            self.btn_example_csv, self.btn_file, self.btn_output,
        ):
            btn.configure(state=state)

    def _do_rename(self, path, mapping, out_dir):
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".txt":
                out_path, _encoding = rename_apply.rename_txt_file(path, mapping, out_dir)
            elif ext == ".docx":
                out_path = rename_apply.rename_docx_file(path, mapping, out_dir)
            elif ext == ".hwpx":
                out_path = rename_apply.rename_hwpx_file(path, mapping, out_dir)
            else:
                raise ValueError(self.t("unsupported_body", ext=ext))

            self.after(0, self.log_line, self.t("rename_log_done", path=out_path))
            self.after(0, lambda: messagebox.showinfo(self.t("rename_done_title"), self.t("rename_done_body", path=out_path)))
        except Exception as e:
            self.after(0, self.log_line, self.t("rename_log_error", err=e))
            self.after(0, lambda: messagebox.showerror(self.t("rename_error_title"), self.t("rename_error_body", err=e)))
        finally:
            self.after(0, self._set_running, False)
