"""파일명 일괄 수정 창.

파일 실제 이름(확장자 제외 부분)을 CSV로 대량 편집해서 한번에 바꾼다.
확장자는 항상 원본 그대로 유지된다.
"""

import csv
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import batch_rename_apply as bra

COLUMNS = ("current", "new")


class BatchRenameWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self._entry_by_iid = {}
        self._next_id = 0
        self.entries = []

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
        self.geometry("700x640")

        frm_actions = ttk.Frame(self)
        frm_actions.pack(fill="x", padx=10, pady=(10, 4))
        self.btn_add_files = ttk.Button(frm_actions, text="", command=self.on_add_files)
        self.btn_add_files.pack(side="left")
        self.btn_add_folder = ttk.Button(frm_actions, text="", command=self.on_add_folder)
        self.btn_add_folder.pack(side="left", padx=4)
        self.btn_remove = ttk.Button(frm_actions, text="", command=self.on_remove_selected)
        self.btn_remove.pack(side="left", padx=4)
        self.btn_export_csv = ttk.Button(frm_actions, text="", command=self.on_export_csv)
        self.btn_export_csv.pack(side="left", padx=4)
        self.btn_import_csv = ttk.Button(frm_actions, text="", command=self.on_import_csv)
        self.btn_import_csv.pack(side="left", padx=4)
        self.btn_example_csv = ttk.Button(frm_actions, text="", command=self.on_create_example_csv)
        self.btn_example_csv.pack(side="left", padx=4)

        self.lbl_ext_note = ttk.Label(self, foreground="#555555", wraplength=660, justify="left")
        self.lbl_ext_note.pack(anchor="w", padx=10)

        self.tree = ttk.Treeview(self, columns=COLUMNS, show="headings", selectmode="extended", height=16)
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)
        self.tree.column("current", width=280, anchor="w")
        self.tree.column("new", width=280, anchor="w")
        self.tree.bind("<<TreeviewSelect>>", self._on_selection_changed)

        frm_edit = ttk.Frame(self)
        frm_edit.pack(fill="x", padx=10, pady=(0, 6))
        self.lbl_new_name = ttk.Label(frm_edit, text="")
        self.lbl_new_name.pack(side="left")
        self.entry_new_name = ttk.Entry(frm_edit)
        self.entry_new_name.pack(side="left", fill="x", expand=True, padx=6)
        self.btn_apply_selected = ttk.Button(frm_edit, text="", command=self.on_apply_to_selected)
        self.btn_apply_selected.pack(side="left")

        self.btn_run = ttk.Button(self, text="", command=self.run_rename)
        self.btn_run.pack(pady=8)

        self.log = scrolledtext.ScrolledText(self, height=8, state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def apply_language(self):
        self.title(self.t("batch_window_title"))
        self.btn_add_files.configure(text=self.t("batch_add_files_button"))
        self.btn_add_folder.configure(text=self.t("batch_add_folder_button"))
        self.btn_remove.configure(text=self.t("batch_remove_button"))
        self.btn_export_csv.configure(text=self.t("batch_export_csv_button"))
        self.btn_import_csv.configure(text=self.t("batch_import_csv_button"))
        self.btn_example_csv.configure(text=self.t("batch_example_csv_button"))
        self.lbl_ext_note.configure(text=self.t("batch_ext_note"))
        self.lbl_new_name.configure(text=self.t("batch_col_new"))
        self.btn_apply_selected.configure(text=self.t("merge_apply_to_selected_button"))
        self.btn_run.configure(text=self.t("batch_run_button"))
        self.tree.heading("current", text=self.t("batch_col_current"))
        self.tree.heading("new", text=self.t("batch_col_new"))

    # ---------- 목록 관리 ----------

    def _row_values(self, entry):
        return (os.path.basename(entry["path"]), entry.get("new_base", ""))

    def _add_entry(self, path):
        base = os.path.splitext(os.path.basename(path))[0]
        entry = {"path": path, "new_base": base}
        iid = str(self._next_id)
        self._next_id += 1
        self._entry_by_iid[iid] = entry
        self.tree.insert("", "end", iid=iid, values=self._row_values(entry))
        self.entries.append(entry)

    def _sync_entries_from_tree(self):
        self.entries = [self._entry_by_iid[iid] for iid in self.tree.get_children()]

    def _on_selection_changed(self, _event=None):
        sel = self.tree.selection()
        if len(sel) == 1:
            entry = self._entry_by_iid[sel[0]]
            self.entry_new_name.delete(0, "end")
            self.entry_new_name.insert(0, entry.get("new_base", ""))

    # ---------- 버튼 동작 ----------

    def on_add_files(self):
        paths = filedialog.askopenfilenames(title=self.t("batch_choose_files_title"))
        for path in paths:
            self._add_entry(path)

    def on_add_folder(self):
        folder = filedialog.askdirectory(title=self.t("batch_choose_folder_title"))
        if not folder:
            return
        for name in sorted(os.listdir(folder)):
            full = os.path.join(folder, name)
            if os.path.isfile(full):
                self._add_entry(full)

    def on_remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(self.t("err_title"), self.t("batch_no_selection"))
            return
        for iid in sel:
            self.tree.delete(iid)
            del self._entry_by_iid[iid]
        self._sync_entries_from_tree()

    def on_apply_to_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(self.t("err_title"), self.t("batch_no_selection"))
            return
        new_base = self.entry_new_name.get().strip()
        for iid in sel:
            entry = self._entry_by_iid[iid]
            entry["new_base"] = new_base
            self.tree.item(iid, values=self._row_values(entry))

    # ---------- CSV ----------

    def on_create_example_csv(self):
        path = filedialog.asksaveasfilename(
            title=self.t("batch_choose_example_csv_title"),
            defaultextension=".csv",
            filetypes=self.t("rename_csv_filetypes"),
            initialfile="coriuni_batch_rename_example.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["원본경로", "새파일명(확장자제외)"])
            writer.writerow([r"C:\소설\chapter1.txt", "01화"])
            writer.writerow([r"C:\소설\chapter2.txt", "02화"])
        messagebox.showinfo(self.t("batch_example_csv_button"), self.t("batch_example_csv_saved", path=path))

    def on_export_csv(self):
        self._sync_entries_from_tree()
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=self.t("rename_csv_filetypes"))
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["원본경로", "새파일명(확장자제외)"])
            for e in self.entries:
                writer.writerow([e["path"], e.get("new_base", "")])
        messagebox.showinfo(self.t("batch_export_csv_button"), self.t("batch_export_done", path=path))

    def _read_csv(self, path, encoding="utf-8-sig"):
        with open(path, newline="", encoding=encoding) as f:
            return list(csv.DictReader(f))

    def on_import_csv(self):
        path = filedialog.askopenfilename(title=self.t("rename_choose_csv_title"), filetypes=self.t("rename_csv_filetypes"))
        if not path:
            return
        try:
            rows = self._read_csv(path)
        except UnicodeDecodeError:
            rows = self._read_csv(path, encoding="cp949")

        self.tree.delete(*self.tree.get_children())
        self._entry_by_iid = {}
        self.entries = []

        skipped = 0
        for row in rows:
            file_path = (row.get("원본경로") or "").strip()
            if not file_path or not os.path.isfile(file_path):
                skipped += 1
                continue
            new_base = (row.get("새파일명(확장자제외)") or "").strip()
            entry = {"path": file_path, "new_base": new_base}
            iid = str(self._next_id)
            self._next_id += 1
            self._entry_by_iid[iid] = entry
            self.tree.insert("", "end", iid=iid, values=self._row_values(entry))
            self.entries.append(entry)

        skipped_text = self.t("batch_import_skipped", n=skipped) if skipped else ""
        messagebox.showinfo(self.t("batch_import_csv_button"), self.t("batch_import_done", n=len(self.entries), skipped=skipped_text))

    # ---------- 실행 ----------

    def log_line(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_running(self, running):
        state = "disabled" if running else "normal"
        for btn in (
            self.btn_run, self.btn_add_files, self.btn_add_folder, self.btn_remove,
            self.btn_export_csv, self.btn_import_csv, self.btn_example_csv, self.btn_apply_selected,
        ):
            btn.configure(state=state)

    def run_rename(self):
        self._sync_entries_from_tree()
        if not self.entries:
            messagebox.showerror(self.t("err_title"), self.t("batch_no_files"))
            return

        planned = bra.plan_renames(self.entries)
        if not planned:
            messagebox.showinfo(self.t("batch_done_title"), self.t("batch_no_files"))
            return

        if not messagebox.askyesno(self.t("batch_confirm_title"), self.t("batch_confirm_body", n=len(planned))):
            return

        self.log_line(self.t("batch_log_start", n=len(planned)))
        self._set_running(True)
        thread = threading.Thread(target=self._do_rename, args=(list(self.entries),), daemon=True)
        thread.start()

    def _do_rename(self, entries):
        try:
            succeeded, failed, skipped = bra.apply_renames(entries)

            for old_path, new_path in succeeded:
                self.after(0, self.log_line, self.t("batch_log_item", old=os.path.basename(old_path), new=os.path.basename(new_path)))
            for old_path, new_path, err in failed:
                self.after(0, self.log_line, self.t("batch_log_fail_item", old=os.path.basename(old_path), err=err))
            for old_path, new_path in skipped:
                self.after(0, self.log_line, self.t("batch_log_skip_item", old=os.path.basename(old_path), new=os.path.basename(new_path)))
            self.after(0, self.log_line, self.t("batch_log_done"))

            fail_text = self.t("batch_fail_text", n=len(failed)) if failed else ""
            skip_text = self.t("batch_skip_text", n=len(skipped)) if skipped else ""
            self.after(
                0,
                lambda: messagebox.showinfo(
                    self.t("batch_done_title"),
                    self.t("batch_done_body", n=len(succeeded), fail_text=fail_text, skip_text=skip_text),
                ),
            )
            self.after(0, self._refresh_after_rename, succeeded)
        except Exception as e:
            self.after(0, self.log_line, self.t("batch_error_body", err=e))
            self.after(0, lambda: messagebox.showerror(self.t("batch_error_title"), self.t("batch_error_body", err=e)))
        finally:
            self.after(0, self._set_running, False)

    def _refresh_after_rename(self, succeeded):
        renamed_map = dict(succeeded)
        for iid, entry in list(self._entry_by_iid.items()):
            if entry["path"] in renamed_map:
                entry["path"] = renamed_map[entry["path"]]
                self.tree.item(iid, values=self._row_values(entry))
