"""병합 화면(디자인 시안 2c) - 파일 목록(드래그 순서 변경)은 왼쪽, 결과 미리보기는
항상 열려 있는 오른쪽 패널, 로그는 아래쪽 접이식 서랍.

여러 txt/docx/hwpx 파일을 원하는 순서로 배치하고, 파일별로 원하면 제목을 넣어
하나로 합친다. 실행 로직은 이전 merge_window.py와 동일하다.

디자인 시안은 제목 서식을 굵게/기울임 두 체크박스 대신 굵게·기울임·없음 중
하나만 고르는 세그먼트로 보여준다 - 그래서 이 페이지는 "굵게+기울임을 동시에"
조합은 지원하지 않는다(이전엔 가능했음). 문장을 자르지 않는 핵심 로직과는
무관한, 디자인을 따르기 위한 의도적인 단순화다.
"""

import csv
import os
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk

import dialogs
import fonts
import merge_apply
import theme
import widgets
from formats import SUPPORTED_EXTS

COLUMNS = ("check", "order", "filename", "title")
CHECK_ON = "☑"
CHECK_OFF = "☐"


class MergePage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._entry_by_iid = {}
        self._next_id = 0
        self.entries = []
        self._drag_item = None
        self._log_visible = False

        self.output_path = tk.StringVar()
        self._filename_sort_ascending = False
        self._filename_sort_applied = False
        self._header_style_var = tk.StringVar(value="bold")
        self.var_page_break = tk.BooleanVar(value=False)

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
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=26, pady=(22, 0))
        self.lbl_title = ttk.Label(header, style="Heading.TLabel")
        self.lbl_title.pack(anchor="w")
        ttk.Label(header, text="Merge in order, with optional titles", style="Caption.TLabel").pack(anchor="w")

        body = ttk.Frame(self)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        left = ttk.Frame(body, width=560)
        left.grid(row=0, column=0, sticky="nsew", padx=(26, 18), pady=16)
        left.grid_rowconfigure(1, weight=1)

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 26), pady=16)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._build_left(left)
        self._build_right(right)
        self._build_bottom()

    def _build_left(self, left):
        actions = ttk.Frame(left)
        actions.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.btn_add_files = ttk.Button(actions, style="Secondary.TButton", command=self.on_add_files)
        self.btn_add_files.pack(side="left")
        self.btn_add_folder = ttk.Button(actions, style="Secondary.TButton", command=self.on_add_folder)
        self.btn_add_folder.pack(side="left", padx=4)
        self.btn_remove = ttk.Button(actions, style="Secondary.TButton", command=self.on_remove_selected)
        self.btn_remove.pack(side="left", padx=4)
        self.btn_export_csv = ttk.Button(actions, style="Ghost.TButton", command=self.on_export_csv)
        self.btn_export_csv.pack(side="right")
        self.btn_import_csv = ttk.Button(actions, style="Ghost.TButton", command=self.on_import_csv)
        self.btn_import_csv.pack(side="right", padx=(0, 4))

        self.tree = ttk.Treeview(left, columns=COLUMNS, show="headings", selectmode="extended", height=14)
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.column("check", width=36, anchor="center", stretch=False)
        self.tree.column("order", width=44, anchor="center", stretch=False)
        self.tree.column("filename", width=300, anchor="w")
        self.tree.column("title", width=170, anchor="w")
        self.tree.heading("check", text=CHECK_OFF, command=self.on_toggle_all_checkboxes)
        self.tree.bind("<ButtonPress-1>", self._on_drag_start)
        self.tree.bind("<B1-Motion>", self._on_drag_motion)
        self.tree.bind("<<TreeviewSelect>>", self._on_selection_changed)

        self.lbl_drag_hint = ttk.Label(left, style="Muted.TLabel", wraplength=520, justify="left")
        self.lbl_drag_hint.grid(row=2, column=0, sticky="ew", pady=(8, 12))

        edit_row = ttk.Frame(left)
        edit_row.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.lbl_title_field = ttk.Label(edit_row, style="Heading.TLabel")
        self.lbl_title_field.pack(side="left")
        self.entry_title = ttk.Entry(edit_row, width=26)
        self.entry_title.pack(side="left", padx=8)
        self.btn_apply_selected = ttk.Button(edit_row, style="Secondary.TButton", command=self.on_apply_to_selected)
        self.btn_apply_selected.pack(side="left")
        self.btn_example_csv = ttk.Button(edit_row, style="Ghost.TButton", command=self.on_create_example_csv)
        self.btn_example_csv.pack(side="right")

        settings = ttk.Frame(left)
        settings.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        spacing_col = ttk.Frame(settings)
        spacing_col.pack(side="left")
        self.lbl_spacing = ttk.Label(spacing_col, style="Muted.TLabel")
        self.lbl_spacing.pack(side="left")
        self.spin_spacing = ttk.Spinbox(spacing_col, from_=0, to=10, width=4)
        self.spin_spacing.set(str(merge_apply.DEFAULT_BLANK_LINES))
        self.spin_spacing.pack(side="left", padx=(6, 0))

        header_col = ttk.Frame(settings)
        header_col.pack(side="left", padx=(20, 0))
        self.lbl_header_style = ttk.Label(header_col, style="Muted.TLabel")
        self.lbl_header_style.pack(side="left", padx=(0, 8))
        self.seg_header_style = widgets.Segmented(
            header_col, [("bold", ""), ("italic", ""), ("none", "")], self._header_style_var,
        )
        self.seg_header_style.pack(side="left")

        pgbreak_row = ttk.Frame(left)
        pgbreak_row.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        self.chk_page_break = ttk.Checkbutton(pgbreak_row, variable=self.var_page_break)
        self.chk_page_break.pack(side="left")
        self.lbl_page_break_hint = ttk.Label(pgbreak_row, style="Muted.TLabel", wraplength=480, justify="left")
        self.lbl_page_break_hint.pack(side="left", padx=(6, 0))

    def _build_right(self, right):
        header = ttk.Frame(right)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.lbl_preview_title = ttk.Label(header, style="Heading.TLabel")
        self.lbl_preview_title.pack(side="left")
        ttk.Label(header, text="Result preview", style="Caption.TLabel").pack(side="left", padx=(8, 8))
        self.tag_preview_summary = widgets.make_tag(header, "", "accent")
        self.tag_preview_summary.pack(side="left")
        self.btn_refresh = ttk.Button(header, style="Ghost.TButton", command=self.refresh_preview)
        self.btn_refresh.pack(side="right")

        self.preview_text = tk.Text(right, wrap="word", state="disabled", relief="flat", borderwidth=0)
        self.preview_text.grid(row=1, column=0, sticky="nsew")

        self.lbl_hwpx_note = ttk.Label(right, style="Muted.TLabel", wraplength=420, justify="left")
        self.lbl_hwpx_note.grid(row=2, column=0, sticky="ew", pady=(8, 0))

    def _configure_preview_tags(self):
        t = theme.tokens()
        family = fonts.current_family() or theme.BODY_FONT
        self.preview_text.tag_configure("bold", font=(family, 10, "bold"))
        self.preview_text.tag_configure("italic", font=(family, 10, "italic"))
        self.preview_text.tag_configure("bold_italic", font=(family, 10, "bold italic"))
        self.preview_text.tag_configure("page_break", foreground=t["accent_700"], justify="center")

    def _build_bottom(self):
        bar = ttk.Frame(self)
        bar.grid(row=2, column=0, sticky="ew", padx=22, pady=12)
        self.btn_log_toggle = ttk.Button(bar, style="Secondary.TButton", command=self._toggle_log)
        self.btn_log_toggle.pack(side="left")
        out_col = ttk.Frame(bar)
        out_col.pack(side="left", padx=(14, 0), fill="x", expand=True)
        self.lbl_output = ttk.Label(out_col, style="Muted.TLabel")
        self.lbl_output.pack(side="left")
        ttk.Entry(out_col, textvariable=self.output_path).pack(side="left", fill="x", expand=True, padx=(6, 6))
        self.btn_output = ttk.Button(out_col, style="Secondary.TButton", command=self.choose_output)
        self.btn_output.pack(side="left")
        self.btn_run = ttk.Button(bar, style="Primary.TButton", command=self.run_merge)
        self.btn_run.pack(side="right")

        self.log_frame = ttk.Frame(self)
        self.log = scrolledtext.ScrolledText(self.log_frame, height=6, state="disabled")
        self.log.pack(fill="both", expand=True, padx=22, pady=(0, 8))

    def apply_language(self):
        self.lbl_title.configure(text=self.t("merge_window_title"))
        self.btn_add_files.configure(text=self.t("merge_add_files_button"))
        self.btn_add_folder.configure(text=self.t("merge_add_folder_button"))
        self.btn_remove.configure(text=self.t("merge_remove_button"))
        self.btn_export_csv.configure(text=self.t("merge_export_csv_button"))
        self.btn_import_csv.configure(text=self.t("merge_import_csv_button"))
        self.btn_example_csv.configure(text=self.t("merge_example_csv_button"))
        self.lbl_drag_hint.configure(text=self.t("merge_drag_hint"))
        self.lbl_title_field.configure(text=self.t("merge_title_label"))
        self.btn_apply_selected.configure(text=self.t("merge_apply_to_selected_button"))
        self.lbl_spacing.configure(text=self.t("merge_spacing_label"))
        self.lbl_header_style.configure(text=self.t("merge_header_style_label"))
        self.seg_header_style.options = [
            ("bold", self.t("merge_bold_label")), ("italic", self.t("merge_italic_label")), ("none", "없음 / None"),
        ]
        for value, btn in self.seg_header_style._buttons:
            btn.configure(text=dict(self.seg_header_style.options)[value])
        self.chk_page_break.configure(text=self.t("merge_page_break_label"))
        self.lbl_page_break_hint.configure(text=self.t("merge_page_break_hint"))
        self.lbl_output.configure(text=self.t("merge_output_label"))
        self.btn_output.configure(text=self.t("merge_output_button"))
        self.lbl_hwpx_note.configure(text=self.t("merge_hwpx_note"))
        self.lbl_preview_title.configure(text=self.t("merge_preview_button"))
        self.btn_refresh.configure(text="새로고침")
        self.btn_log_toggle.configure(text=("로그 ▼" if self._log_visible else "로그 ▲"))
        self.btn_run.configure(text=self.t("merge_run_button"))

        self.tree.heading("order", text=self.t("merge_col_order"))
        self.tree.heading("title", text=self.t("merge_col_title"))
        self._refresh_filename_heading()
        self.tree.heading("check", text=CHECK_ON if self._all_checked() else CHECK_OFF, command=self.on_toggle_all_checkboxes)

    def refresh_theme(self):
        self._configure_preview_tags()
        t = theme.tokens()
        self.preview_text.configure(
            bg=t["bg"], fg=t["text"], insertbackground=t["accent"],
            selectbackground=t["accent_200"], selectforeground=t["accent_800"],
        )
        self.log.configure(
            bg=t["surface"], fg=t["text"], insertbackground=t["accent"],
            selectbackground=t["accent_200"], selectforeground=t["accent_800"],
        )

    # ---------- 목록 관리 (merge_window.py와 동일한 로직) ----------

    def _check_symbol(self, iid):
        return CHECK_ON if iid in self.tree.selection() else CHECK_OFF

    def _all_checked(self):
        children = self.tree.get_children()
        return bool(children) and set(self.tree.selection()) == set(children)

    def _row_values(self, iid, order, entry):
        return (self._check_symbol(iid), order, os.path.basename(entry["path"]), entry.get("title", ""))

    def _update_row(self, iid, entry):
        order = self.tree.index(iid) + 1
        self.tree.item(iid, values=self._row_values(iid, order, entry))

    def _add_entry(self, entry):
        iid = str(self._next_id)
        self._next_id += 1
        self._entry_by_iid[iid] = entry
        order = len(self.tree.get_children()) + 1
        self.tree.insert("", "end", iid=iid, values=self._row_values(iid, order, entry))
        self.entries.append(entry)

    def _add_file_path(self, path):
        self._add_entry({"path": path, "title": ""})

    def _sync_entries_from_tree(self):
        self.entries = [self._entry_by_iid[iid] for iid in self.tree.get_children()]
        self._renumber()

    def _renumber(self):
        for i, iid in enumerate(self.tree.get_children(), start=1):
            entry = self._entry_by_iid[iid]
            self.tree.item(iid, values=self._row_values(iid, i, entry))

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

    # ---------- 드래그로 순서 변경 / 체크박스 ----------

    def _on_drag_start(self, event):
        region = self.tree.identify_region(event.x, event.y)
        col = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)
        if region == "cell" and col == "#1" and row:
            self._toggle_row_check(row)
            self._drag_item = None
            return "break"
        self._drag_item = row or None
        return None

    def _on_drag_motion(self, event):
        if not self._drag_item:
            return
        target = self.tree.identify_row(event.y)
        if target and target != self._drag_item:
            self.tree.move(self._drag_item, "", self.tree.index(target))
            self._renumber()

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
        items.sort(key=lambda iid: os.path.basename(self._entry_by_iid[iid]["path"]).lower(), reverse=not ascending)
        for index, iid in enumerate(items):
            self.tree.move(iid, "", index)
        self._renumber()
        self._refresh_filename_heading()

    def _on_selection_changed(self, _event=None):
        self._refresh_check_column()
        sel = self.tree.selection()
        if len(sel) == 1:
            entry = self._entry_by_iid[sel[0]]
            self.entry_title.delete(0, "end")
            self.entry_title.insert(0, entry.get("title", ""))

    # ---------- 버튼 동작 ----------

    def on_add_files(self):
        paths = filedialog.askopenfilenames(title=self.t("merge_choose_files_title"), filetypes=self.t("filetypes"))
        for path in paths:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".hwp":
                dialogs.show_warning(self, self.t("hwp_title"), self.t("hwp_body"))
                continue
            if ext not in SUPPORTED_EXTS:
                dialogs.show_warning(self, self.t("unsupported_title"), self.t("unsupported_body", ext=ext))
                continue
            self._add_file_path(path)

    def on_add_folder(self):
        folder = filedialog.askdirectory(title=self.t("merge_choose_folder_title"))
        if not folder:
            return
        for name in sorted(os.listdir(folder)):
            ext = os.path.splitext(name)[1].lower()
            if ext in SUPPORTED_EXTS:
                self._add_file_path(os.path.join(folder, name))

    def on_remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            dialogs.show_warning(self, self.t("err_title"), self.t("merge_no_selection"))
            return
        for iid in sel:
            self.tree.delete(iid)
            del self._entry_by_iid[iid]
        self._sync_entries_from_tree()

    def on_apply_to_selected(self):
        sel = self.tree.selection()
        if not sel:
            dialogs.show_warning(self, self.t("err_title"), self.t("merge_no_selection"))
            return
        title = self.entry_title.get()
        for iid in sel:
            entry = self._entry_by_iid[iid]
            entry["title"] = title
            self._update_row(iid, entry)

    def choose_output(self):
        self._sync_entries_from_tree()
        ext = ".txt"
        if self.entries:
            try:
                ext = merge_apply.common_extension(self.entries)
            except merge_apply.MixedExtensionError:
                ext = os.path.splitext(self.entries[0]["path"])[1].lower()
        path = filedialog.asksaveasfilename(
            title=self.t("merge_choose_save_title"), defaultextension=ext, filetypes=self.t("filetypes")
        )
        if path:
            self.output_path.set(path)

    # ---------- 설정값 읽기 ----------

    def _get_spacing(self):
        try:
            return max(0, int(self.spin_spacing.get()))
        except ValueError:
            return merge_apply.DEFAULT_BLANK_LINES

    def _get_header_style(self):
        style = self._header_style_var.get()
        return style == "bold", style == "italic"

    def _get_page_break(self):
        return bool(self.var_page_break.get())

    # ---------- CSV ----------

    def on_create_example_csv(self):
        path = filedialog.asksaveasfilename(
            title=self.t("merge_choose_example_csv_title"), defaultextension=".csv",
            filetypes=self.t("rename_csv_filetypes"), initialfile="coriuni_merge_example.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["파일경로", "제목"])
            writer.writerow([r"C:\소설\1화.txt", "프롤로그"])
            writer.writerow([r"C:\소설\2화.txt", "1화"])
            writer.writerow([r"C:\소설\3화.txt", ""])
        dialogs.show_info(self, self.t("merge_example_csv_button"), self.t("merge_example_csv_saved", path=path))

    def on_export_csv(self):
        self._sync_entries_from_tree()
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=self.t("rename_csv_filetypes"))
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["파일경로", "제목"])
            for e in self.entries:
                writer.writerow([e["path"], e.get("title", "")])
        dialogs.show_info(self, self.t("merge_export_csv_button"), self.t("merge_export_done", path=path))

    def _read_merge_csv(self, path, encoding="utf-8-sig"):
        with open(path, newline="", encoding=encoding) as f:
            return list(csv.DictReader(f))

    def on_import_csv(self):
        path = filedialog.askopenfilename(title=self.t("rename_choose_csv_title"), filetypes=self.t("rename_csv_filetypes"))
        if not path:
            return
        try:
            rows = self._read_merge_csv(path)
        except UnicodeDecodeError:
            rows = self._read_merge_csv(path, encoding="cp949")

        self.tree.delete(*self.tree.get_children())
        self._entry_by_iid = {}
        self.entries = []

        skipped = 0
        for row in rows:
            file_path = (row.get("파일경로") or "").strip()
            if not file_path or not os.path.isfile(file_path):
                skipped += 1
                continue
            entry = {"path": file_path, "title": row.get("제목", "") or ""}
            self._add_entry(entry)

        skipped_text = self.t("merge_import_skipped", n=skipped) if skipped else ""
        dialogs.show_info(self, self.t("merge_import_csv_button"), self.t("merge_import_done", n=len(self.entries), skipped=skipped_text))

    # ---------- 로그 서랍 ----------

    def _toggle_log(self):
        self._log_visible = not self._log_visible
        if self._log_visible:
            self.log_frame.grid(row=3, column=0, sticky="ew")
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
            self.btn_run, self.btn_refresh, self.btn_add_files, self.btn_add_folder,
            self.btn_remove, self.btn_export_csv, self.btn_import_csv,
            self.btn_example_csv, self.btn_apply_selected, self.btn_output,
        ):
            btn.configure(state=state)

    def run_merge(self):
        self._sync_entries_from_tree()
        if not self.entries:
            dialogs.show_error(self, self.t("err_title"), self.t("merge_no_files"))
            return
        output_path = self.output_path.get().strip()
        if not output_path:
            dialogs.show_error(self, self.t("err_title"), self.t("merge_no_output"))
            return

        spacing = self._get_spacing()
        bold, italic = self._get_header_style()
        page_break = self._get_page_break()

        self.log_line(self.t("merge_log_start", n=len(self.entries)))
        self._set_running(True)
        thread = threading.Thread(
            target=self._do_merge, args=(list(self.entries), output_path, spacing, bold, italic, page_break), daemon=True
        )
        thread.start()

    def _do_merge(self, entries, output_path, spacing, bold, italic, page_break):
        try:
            merge_apply.merge_files(
                entries, output_path, blank_lines=spacing, header_bold=bold, header_italic=italic,
                page_break=page_break,
            )
            self.after(0, self.log_line, self.t("merge_log_done", path=output_path))
            self.after(0, lambda: dialogs.show_info(self, self.t("merge_done_title"), self.t("merge_done_body", path=output_path)))
            self.after(0, self._record_activity, entries, output_path)
        except merge_apply.MixedExtensionError as e:
            msg = self.t("merge_mixed_ext_error", exts=", ".join(e.exts))
            self.after(0, self.log_line, self.t("merge_log_error", err=msg))
            self.after(0, lambda: dialogs.show_error(self, self.t("merge_error_title"), msg))
        except Exception as e:
            self.after(0, self.log_line, self.t("merge_log_error", err=e))
            self.after(0, lambda: dialogs.show_error(self, self.t("merge_error_title"), self.t("merge_error_body", err=e)))
        finally:
            self.after(0, self._set_running, False)

    def _record_activity(self, entries, output_path):
        try:
            import activity_log
            activity_log.record(self.t("merge_run_button"), f"{len(entries)}개 파일", os.path.basename(output_path))
        except Exception:
            pass

    # ---------- 미리보기(항상 열려있는 오른쪽 패널) ----------

    def refresh_preview(self):
        self._sync_entries_from_tree()
        if not self.entries:
            dialogs.show_error(self, self.t("err_title"), self.t("merge_no_files"))
            return
        try:
            ext = merge_apply.common_extension(self.entries)
        except merge_apply.MixedExtensionError as e:
            dialogs.show_error(self, self.t("merge_error_title"), self.t("merge_mixed_ext_error", exts=", ".join(e.exts)))
            return

        spacing = self._get_spacing()
        bold, italic = self._get_header_style()
        page_break = self._get_page_break() and ext in (".docx", ".hwpx")
        try:
            segments, truncated = merge_apply.build_preview_segments(
                self.entries, blank_lines=spacing, header_bold=bold, header_italic=italic, page_break=page_break
            )
        except Exception as e:
            dialogs.show_error(self, self.t("merge_error_title"), self.t("merge_error_body", err=e))
            return

        self._render_preview(segments, truncated)

    def _render_preview(self, segments, truncated):
        total_chars = sum(len(s[0]) for s in segments)
        self.tag_preview_summary.configure(text=f"{len(self.entries)}개 파일 · 약 {total_chars:,}자")

        tw = self.preview_text
        tw.configure(state="normal")
        tw.delete("1.0", "end")
        if truncated:
            tw.insert("end", self.t("merge_preview_truncated_note") + "\n\n")

        for content, _is_header, bold, italic, is_page_break in segments:
            if is_page_break:
                tw.insert("end", "\n" + self.t("merge_preview_page_break_label") + "\n\n", "page_break")
                continue
            if bold and italic:
                tag = "bold_italic"
            elif bold:
                tag = "bold"
            elif italic:
                tag = "italic"
            else:
                tag = ""
            if tag:
                tw.insert("end", content, tag)
            else:
                tw.insert("end", content)

        tw.configure(state="disabled")

    def on_show(self):
        pass

    # ---------- 홈 화면 드롭존 등 다른 곳에서 파일을 받았을 때 ----------

    def add_paths_from_outside(self, paths):
        for path in paths:
            ext = os.path.splitext(path)[1].lower()
            if ext in SUPPORTED_EXTS:
                self._add_file_path(path)
