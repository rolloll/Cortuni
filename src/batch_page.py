"""파일명 일괄 수정 화면(디자인 시안 2e).

파일 실제 이름(확장자 제외 부분)을 CSV로 대량 편집해서 한번에 바꾼다.
확장자는 항상 원본 그대로 유지된다.

시안에 있는 패턴 바({name}/{n:02}/{ext}/{date} 토큰 + 시작 번호 + "패턴 적용")는
이전 창에는 없던 새 기능이다 - 각 행의 새 파일명(new_base)을 한 번에 채워줄
뿐, 실제 이름 변경(plan_renames/apply_renames)이나 CSV/수동 편집 경로는
그대로 둔다.
"""

import csv
import datetime
import os
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk

import batch_rename_apply as bra
import dialogs
import theme
import widgets

COLUMNS = ("current", "new")
PATTERN_TOKENS = ("{name}", "{n:02}", "{ext}", "{date}")


class BatchPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._entry_by_iid = {}
        self._next_id = 0
        self.entries = []
        self._log_visible = False

        self.pattern_var = tk.StringVar(value="{name}")
        self.start_num_var = tk.StringVar(value="1")

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
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(24, 12))
        title_col = ttk.Frame(header)
        title_col.pack(side="left")
        self.lbl_title = ttk.Label(title_col, style="Heading.TLabel")
        self.lbl_title.pack(anchor="w")
        ttk.Label(title_col, text="Rename many files at once — extension always preserved",
                  style="Caption.TLabel").pack(anchor="w")
        actions = ttk.Frame(header)
        actions.pack(side="right")
        self.btn_add_files = ttk.Button(actions, style="Secondary.TButton", command=self.on_add_files)
        self.btn_add_files.pack(side="left")
        self.btn_add_folder = ttk.Button(actions, style="Secondary.TButton", command=self.on_add_folder)
        self.btn_add_folder.pack(side="left", padx=4)
        self.btn_remove = ttk.Button(actions, style="Secondary.TButton", command=self.on_remove_selected)
        self.btn_remove.pack(side="left")
        self.btn_export_csv = ttk.Button(actions, style="Ghost.TButton", command=self.on_export_csv)
        self.btn_export_csv.pack(side="left", padx=(10, 0))
        self.btn_import_csv = ttk.Button(actions, style="Ghost.TButton", command=self.on_import_csv)
        self.btn_import_csv.pack(side="left")

        pattern_card = widgets.BlueprintFrame(self, tint=theme.tokens()["accent_100"])
        pattern_card.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 12))
        self._pattern_card = pattern_card
        row = ttk.Frame(pattern_card.content)
        row.pack(fill="x", padx=14, pady=12)
        pattern_field = ttk.Frame(row)
        pattern_field.pack(side="left", fill="x", expand=True)
        self.lbl_pattern = ttk.Label(pattern_field, style="Muted.TLabel")
        self.lbl_pattern.pack(anchor="w")
        ttk.Entry(pattern_field, textvariable=self.pattern_var).pack(fill="x", pady=(4, 0))

        tags_col = ttk.Frame(row)
        tags_col.pack(side="left", padx=14)
        for token in PATTERN_TOKENS:
            widgets.make_tag(tags_col, token, "outline").pack(side="left", padx=(0, 6))

        start_col = ttk.Frame(row)
        start_col.pack(side="left", padx=(0, 14))
        self.lbl_start_num = ttk.Label(start_col, style="Muted.TLabel")
        self.lbl_start_num.pack(anchor="w")
        ttk.Entry(start_col, textvariable=self.start_num_var, width=6, justify="center").pack(pady=(4, 0))

        self.btn_apply_pattern = ttk.Button(row, style="Secondary.TButton", command=self.on_apply_pattern)
        self.btn_apply_pattern.pack(side="left", anchor="s")

        table_frame = ttk.Frame(self)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=30)
        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", selectmode="extended")
        self.tree.pack(fill="both", expand=True)
        self.tree.column("current", width=320, anchor="w")
        self.tree.column("new", width=320, anchor="w")
        self.tree.bind("<<TreeviewSelect>>", self._on_selection_changed)

        self.lbl_ext_note = ttk.Label(self, style="Muted.TLabel", wraplength=900, justify="left")
        self.lbl_ext_note.grid(row=3, column=0, sticky="ew", padx=30, pady=(8, 0))

        edit_row = ttk.Frame(self)
        edit_row.grid(row=4, column=0, sticky="ew", padx=30, pady=(10, 0))
        self.lbl_new_name = ttk.Label(edit_row, style="Muted.TLabel")
        self.lbl_new_name.pack(side="left")
        self.entry_new_name = ttk.Entry(edit_row)
        self.entry_new_name.pack(side="left", fill="x", expand=True, padx=6)
        self.btn_apply_selected = ttk.Button(edit_row, style="Secondary.TButton", command=self.on_apply_to_selected)
        self.btn_apply_selected.pack(side="left")

        bar = ttk.Frame(self)
        bar.grid(row=5, column=0, sticky="ew", padx=30, pady=12)
        self.btn_log_toggle = ttk.Button(bar, style="Secondary.TButton", command=self._toggle_log)
        self.btn_log_toggle.pack(side="left")
        self.lbl_summary = ttk.Label(bar, style="Muted.TLabel")
        self.lbl_summary.pack(side="left", padx=(14, 0))
        self.btn_run = ttk.Button(bar, style="Primary.TButton", command=self.run_rename)
        self.btn_run.pack(side="right")

        self.log_frame = ttk.Frame(self)
        self.log = scrolledtext.ScrolledText(self.log_frame, height=6, state="disabled")
        self.log.pack(fill="both", expand=True, padx=30, pady=(0, 8))

    def apply_language(self):
        self.lbl_title.configure(text=self.t("batch_window_title"))
        self.btn_add_files.configure(text=self.t("batch_add_files_button"))
        self.btn_add_folder.configure(text=self.t("batch_add_folder_button"))
        self.btn_remove.configure(text=self.t("batch_remove_button"))
        self.btn_export_csv.configure(text=self.t("batch_export_csv_button"))
        self.btn_import_csv.configure(text=self.t("batch_import_csv_button"))
        self.lbl_pattern.configure(text="패턴 / Pattern")
        self.lbl_start_num.configure(text="시작 번호 / Start")
        self.btn_apply_pattern.configure(text="패턴 적용")
        self.lbl_ext_note.configure(text=self.t("batch_ext_note"))
        self.lbl_new_name.configure(text=self.t("batch_col_new"))
        self.btn_apply_selected.configure(text=self.t("merge_apply_to_selected_button"))
        self.btn_log_toggle.configure(text=("로그 ▼" if self._log_visible else "로그 ▲"))
        self.btn_run.configure(text=self.t("batch_run_button"))
        self.tree.heading("current", text=self.t("batch_col_current"))
        self.tree.heading("new", text=self.t("batch_col_new"))
        self._update_summary()

    def refresh_theme(self):
        t = theme.tokens()
        self._pattern_card._tint = t["accent_100"]
        self._pattern_card.refresh_theme()
        self.log.configure(
            bg=t["surface"], fg=t["text"], insertbackground=t["accent"],
            selectbackground=t["accent_200"], selectforeground=t["accent_800"],
        )

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

    def _update_summary(self):
        self.lbl_summary.configure(text=f"{len(self.entries)}개 파일")

    # ---------- 패턴 적용 (새 기능) ----------

    def on_apply_pattern(self):
        self._sync_entries_from_tree()
        if not self.entries:
            dialogs.show_warning(self, self.t("err_title"), self.t("batch_no_files"))
            return
        pattern = self.pattern_var.get()
        try:
            start = int(self.start_num_var.get().strip())
        except ValueError:
            start = 1
        date_str = datetime.date.today().isoformat()

        for i, iid in enumerate(self.tree.get_children(), start=start):
            entry = self._entry_by_iid[iid]
            base = os.path.splitext(os.path.basename(entry["path"]))[0]
            ext = os.path.splitext(entry["path"])[1].lstrip(".")
            try:
                new_base = pattern.format(name=base, n=i, ext=ext, date=date_str)
            except (KeyError, ValueError, IndexError) as e:
                dialogs.show_error(self, self.t("err_title"), f"패턴이 올바르지 않습니다: {e}")
                return
            entry["new_base"] = new_base
            self.tree.item(iid, values=self._row_values(entry))

    # ---------- 버튼 동작 ----------

    def on_add_files(self):
        paths = filedialog.askopenfilenames(title=self.t("batch_choose_files_title"))
        for path in paths:
            self._add_entry(path)
        self._update_summary()

    def on_add_folder(self):
        folder = filedialog.askdirectory(title=self.t("batch_choose_folder_title"))
        if not folder:
            return
        for name in sorted(os.listdir(folder)):
            full = os.path.join(folder, name)
            if os.path.isfile(full):
                self._add_entry(full)
        self._update_summary()

    def on_remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            dialogs.show_warning(self, self.t("err_title"), self.t("batch_no_selection"))
            return
        for iid in sel:
            self.tree.delete(iid)
            del self._entry_by_iid[iid]
        self._sync_entries_from_tree()
        self._update_summary()

    def on_apply_to_selected(self):
        sel = self.tree.selection()
        if not sel:
            dialogs.show_warning(self, self.t("err_title"), self.t("batch_no_selection"))
            return
        new_base = self.entry_new_name.get().strip()
        for iid in sel:
            entry = self._entry_by_iid[iid]
            entry["new_base"] = new_base
            self.tree.item(iid, values=self._row_values(entry))

    # ---------- CSV ----------

    def on_create_example_csv(self):
        path = filedialog.asksaveasfilename(
            title=self.t("batch_choose_example_csv_title"), defaultextension=".csv",
            filetypes=self.t("rename_csv_filetypes"), initialfile="coriuni_batch_rename_example.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["원본경로", "새파일명(확장자제외)"])
            writer.writerow([r"C:\소설\chapter1.txt", "01화"])
            writer.writerow([r"C:\소설\chapter2.txt", "02화"])
        dialogs.show_info(self, self.t("batch_example_csv_button"), self.t("batch_example_csv_saved", path=path))

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
        dialogs.show_info(self, self.t("batch_export_csv_button"), self.t("batch_export_done", path=path))

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
        dialogs.show_info(self, self.t("batch_import_csv_button"), self.t("batch_import_done", n=len(self.entries), skipped=skipped_text))
        self._update_summary()

    # ---------- 로그 서랍 ----------

    def _toggle_log(self):
        self._log_visible = not self._log_visible
        if self._log_visible:
            self.log_frame.grid(row=6, column=0, sticky="ew")
            self.btn_log_toggle.configure(text="로그 ▼")
        else:
            self.log_frame.grid_remove()
            self.btn_log_toggle.configure(text="로그 ▲")

    def log_line(self, text):
        if not self._log_visible:
            self._toggle_log()
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ---------- 실행 ----------

    def _set_running(self, running):
        state = "disabled" if running else "normal"
        for btn in (
            self.btn_run, self.btn_add_files, self.btn_add_folder, self.btn_remove,
            self.btn_export_csv, self.btn_import_csv, self.btn_apply_selected, self.btn_apply_pattern,
        ):
            btn.configure(state=state)

    def run_rename(self):
        self._sync_entries_from_tree()
        if not self.entries:
            dialogs.show_error(self, self.t("err_title"), self.t("batch_no_files"))
            return

        planned = bra.plan_renames(self.entries)
        if not planned:
            dialogs.show_info(self, self.t("batch_done_title"), self.t("batch_no_files"))
            return

        if not dialogs.ask_yes_no(self, self.t("batch_confirm_title"), self.t("batch_confirm_body", n=len(planned))):
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
                lambda: dialogs.show_info(
                    self, self.t("batch_done_title"),
                    self.t("batch_done_body", n=len(succeeded), fail_text=fail_text, skip_text=skip_text),
                ),
            )
            self.after(0, self._refresh_after_rename, succeeded)
            self.after(0, self._record_activity, succeeded)
        except Exception as e:
            self.after(0, self.log_line, self.t("batch_error_body", err=e))
            self.after(0, lambda: dialogs.show_error(self, self.t("batch_error_title"), self.t("batch_error_body", err=e)))
        finally:
            self.after(0, self._set_running, False)

    def _refresh_after_rename(self, succeeded):
        renamed_map = dict(succeeded)
        for iid, entry in list(self._entry_by_iid.items()):
            if entry["path"] in renamed_map:
                entry["path"] = renamed_map[entry["path"]]
                self.tree.item(iid, values=self._row_values(entry))

    def _record_activity(self, succeeded):
        try:
            import activity_log
            activity_log.record(self.t("batch_run_button"), f"{len(succeeded)}개 파일", "이름 변경됨")
        except Exception:
            pass

    def on_show(self):
        pass
