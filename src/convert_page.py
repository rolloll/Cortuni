"""확장자 변환 화면(디자인 시안 2f).

txt <-> docx, txt <-> hwpx, docx <-> hwpx 변환을 지원한다. 목록에는 형식이
다른 파일이 섞여 있어도 되며, 선택한 목표 형식으로 변환할 수 없는 파일은
개별적으로 건너뛰고 로그에 남긴다. 대상 형식이 바뀔 때마다 표의 상태 칸을
convert_apply.supported_targets()로 미리 계산해서 보여준다(이전 창에는
없던, 시안에 있는 작은 개선).
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk

import convert_apply
import dialogs
import theme
import widgets
from formats import SUPPORTED_EXTS

TARGET_EXTS = [".txt", ".docx", ".hwpx"]
COLUMNS = ("check", "filename", "from", "arrow", "to", "status")
CHECK_ON = "☑"
CHECK_OFF = "☐"


class ConvertPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._entry_by_iid = {}
        self._next_id = 0
        self.entries = []
        self._filename_sort_ascending = False
        self._filename_sort_applied = False
        self._log_visible = False

        self.output_dir = tk.StringVar()
        self.target_ext = tk.StringVar(value=TARGET_EXTS[0])

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
        ttk.Label(title_col, text="Convert between txt · docx · hwpx", style="Caption.TLabel").pack(anchor="w")
        actions = ttk.Frame(header)
        actions.pack(side="right")
        self.btn_add_files = ttk.Button(actions, style="Secondary.TButton", command=self.on_add_files)
        self.btn_add_files.pack(side="left")
        self.btn_add_folder = ttk.Button(actions, style="Secondary.TButton", command=self.on_add_folder)
        self.btn_add_folder.pack(side="left", padx=4)
        self.btn_remove = ttk.Button(actions, style="Secondary.TButton", command=self.on_remove_selected)
        self.btn_remove.pack(side="left")

        settings_row = ttk.Frame(self)
        settings_row.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 12))
        self.lbl_target = ttk.Label(settings_row, style="Caption.TLabel")
        self.lbl_target.pack(side="left")
        self.seg_target = widgets.Segmented(
            settings_row, [(ext, ext) for ext in TARGET_EXTS], self.target_ext, command=self._on_target_changed,
        )
        self.seg_target.pack(side="left", padx=(10, 24))
        self.lbl_output = ttk.Label(settings_row, style="Muted.TLabel")
        self.lbl_output.pack(side="left")
        ttk.Entry(settings_row, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=6)
        self.btn_output = ttk.Button(settings_row, style="Secondary.TButton", command=self.choose_output)
        self.btn_output.pack(side="left")

        table_frame = ttk.Frame(self)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=30)
        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", selectmode="extended")
        self.tree.pack(fill="both", expand=True)
        self.tree.column("check", width=36, anchor="center", stretch=False)
        self.tree.column("filename", width=340, anchor="w")
        self.tree.column("from", width=70, anchor="center", stretch=False)
        self.tree.column("arrow", width=26, anchor="center", stretch=False)
        self.tree.column("to", width=70, anchor="center", stretch=False)
        self.tree.column("status", width=130, anchor="w")
        self.tree.heading("check", text=CHECK_OFF, command=self.on_toggle_all_checkboxes)
        self.tree.heading("arrow", text="→")
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_selection_changed)
        self.lbl_note = ttk.Label(self, style="Muted.TLabel", wraplength=900, justify="left")
        self.lbl_note.grid(row=3, column=0, sticky="ew", padx=30, pady=(8, 0))

        bar = ttk.Frame(self)
        bar.grid(row=4, column=0, sticky="ew", padx=30, pady=12)
        self.btn_log_toggle = ttk.Button(bar, style="Secondary.TButton", command=self._toggle_log)
        self.btn_log_toggle.pack(side="left")
        self.lbl_summary = ttk.Label(bar, style="Muted.TLabel")
        self.lbl_summary.pack(side="left", padx=(14, 0))
        self.btn_run = ttk.Button(bar, style="Primary.TButton", command=self.run_convert)
        self.btn_run.pack(side="right")

        self.log_frame = ttk.Frame(self)
        self.log = scrolledtext.ScrolledText(self.log_frame, height=6, state="disabled")
        self.log.pack(fill="both", expand=True, padx=30, pady=(0, 8))

    def apply_language(self):
        self.lbl_title.configure(text=self.t("convert_window_title"))
        self.btn_add_files.configure(text=self.t("convert_add_files_button"))
        self.btn_add_folder.configure(text=self.t("convert_add_folder_button"))
        self.btn_remove.configure(text=self.t("convert_remove_button"))
        self.lbl_target.configure(text=self.t("convert_target_label"))
        self.lbl_output.configure(text=self.t("convert_output_label"))
        self.btn_output.configure(text=self.t("convert_output_button"))
        self.btn_log_toggle.configure(text=("로그 ▼" if self._log_visible else "로그 ▲"))
        self.btn_run.configure(text=self.t("convert_run_button"))
        self.tree.heading("filename", text=self.t("merge_col_filename"))
        self.tree.heading("from", text="원본 · From")
        self.tree.heading("to", text="대상 · To")
        self.tree.heading("status", text="상태 · Status")
        self.tree.heading("check", text=CHECK_ON if self._all_checked() else CHECK_OFF, command=self.on_toggle_all_checkboxes)
        self.lbl_note.configure(text=(
            "※ 지원하지 않는 조합은 건너뛰고 로그에 남깁니다. .hwp(구버전)는 한글에서 .hwpx로 저장한 뒤 사용하세요.\n"
            "Unsupported pairs are skipped and logged; legacy .hwp must be saved as .hwpx first."
        ))
        self._refresh_status_column()
        self._update_summary()

    def refresh_theme(self):
        t = theme.tokens()
        self.log.configure(
            bg=t["surface"], fg=t["text"], insertbackground=t["accent"],
            selectbackground=t["accent_200"], selectforeground=t["accent_800"],
        )

    # ---------- 목록 관리 ----------

    def _check_symbol(self, iid):
        return CHECK_ON if iid in self.tree.selection() else CHECK_OFF

    def _all_checked(self):
        children = self.tree.get_children()
        return bool(children) and set(self.tree.selection()) == set(children)

    def _row_status(self, path):
        ext = os.path.splitext(path)[1].lower()
        target = self.target_ext.get()
        if ext == target:
            return ext.lstrip("."), "—", "건너뜀 · same format"
        if target in convert_apply.supported_targets(ext):
            return ext.lstrip("."), target.lstrip("."), "대기 · ready"
        return ext.lstrip("."), target.lstrip("."), "건너뜀 · skipped"

    def _row_values(self, iid, path):
        src, dst, status = self._row_status(path)
        return (self._check_symbol(iid), os.path.basename(path), src, "→", dst, status)

    def _refresh_check_column(self):
        for iid in self.tree.get_children():
            vals = list(self.tree.item(iid, "values"))
            vals[0] = self._check_symbol(iid)
            self.tree.item(iid, values=vals)
        self.tree.heading("check", text=CHECK_ON if self._all_checked() else CHECK_OFF)

    def _refresh_status_column(self):
        for iid, path in self._entry_by_iid.items():
            self.tree.item(iid, values=self._row_values(iid, path))
        self._update_summary()

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

    def _update_summary(self):
        target = self.target_ext.get()
        ready = sum(1 for p in self.entries if target in convert_apply.supported_targets(os.path.splitext(p)[1].lower()))
        total = len(self.entries)
        skipped = total - ready
        self.lbl_summary.configure(text=f"{total}개 선택 · {ready}개 변환 가능, {skipped}개 건너뜀")

    # ---------- 체크박스 / 정렬 / 대상 형식 ----------

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

    def _on_target_changed(self, _value):
        self._refresh_status_column()

    # ---------- 버튼 동작 ----------

    def on_add_files(self):
        paths = filedialog.askopenfilenames(title=self.t("convert_choose_files_title"), filetypes=self.t("filetypes"))
        for path in paths:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".hwp":
                dialogs.show_warning(self, self.t("hwp_title"), self.t("hwp_body"))
                continue
            if ext not in SUPPORTED_EXTS:
                dialogs.show_warning(self, self.t("unsupported_title"), self.t("unsupported_body", ext=ext))
                continue
            self._add_file(path)
        self._update_summary()

    def on_add_folder(self):
        folder = filedialog.askdirectory(title=self.t("convert_choose_folder_title"))
        if not folder:
            return
        for name in sorted(os.listdir(folder)):
            full = os.path.join(folder, name)
            ext = os.path.splitext(name)[1].lower()
            if os.path.isfile(full) and ext in SUPPORTED_EXTS:
                self._add_file(full)
        self._update_summary()

    def on_remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            dialogs.show_warning(self, self.t("err_title"), self.t("merge_no_selection"))
            return
        for iid in sel:
            self.tree.delete(iid)
            del self._entry_by_iid[iid]
        self._sync_entries_from_tree()
        self._update_summary()

    def choose_output(self):
        path = filedialog.askdirectory(title=self.t("convert_choose_output_title"))
        if path:
            self.output_dir.set(path)

    # ---------- 로그 서랍 ----------

    def _toggle_log(self):
        self._log_visible = not self._log_visible
        if self._log_visible:
            self.log_frame.grid(row=5, column=0, sticky="ew")
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
        for btn in (self.btn_run, self.btn_add_files, self.btn_add_folder, self.btn_remove, self.btn_output):
            btn.configure(state=state)

    def run_convert(self):
        self._sync_entries_from_tree()
        if not self.entries:
            dialogs.show_error(self, self.t("err_title"), self.t("convert_no_files"))
            return
        out_dir = self.output_dir.get().strip()
        if not out_dir:
            dialogs.show_error(self, self.t("err_title"), self.t("convert_no_output"))
            return
        target_ext = self.target_ext.get()

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
        self.after(0, lambda: dialogs.show_info(self, self.t("convert_done_title"), self.t("convert_done_body", n=created, out=out_dir)))
        self.after(0, self._record_activity, created, target_ext)
        self.after(0, self._set_running, False)

    def _record_activity(self, created, target_ext):
        try:
            import activity_log
            activity_log.record(self.t("convert_run_button"), f"{len(self.entries)}개 파일 → {target_ext}", f"{created}개 생성")
        except Exception:
            pass

    def on_show(self):
        pass
