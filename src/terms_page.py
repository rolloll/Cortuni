# 이름·호칭(Terms) 기능이 UI에서 빠지면서 이 파일 전체를 주석 처리했다.
# 되살리려면: 이 파일의 '# ' 접두어를 전부 지우고, main.py/home_page.py/
# sidebar.py에서 '이름·호칭 기능 비활성화' 주석이 붙은 줄들을 되돌리면 된다.
#
# """이름·호칭 바꾸기 화면(디자인 시안 2d, 이전 Ctrl+H 창).
# 
# 호칭/지칭어·고유명사 사전을 관리(추가/삭제/CSV 불러오기, 작품별 그룹핑)하고,
# 선택한 파일(txt/docx/hwpx)에 일괄 치환(조사 자동 교정 포함)을 적용한다.
# 
# "치환 미리보기" 오른쪽 패널은 이전 창에는 없던 새 기능이다 - 실행 로직
# (compute_replacements)은 이미 rename_apply.py에 있던 것을 그대로 재사용해서,
# 실제로 바뀔 지점들을 실행 전에 앞뒤 문맥과 함께 보여준다.
# """
# 
# import csv
# import os
# import threading
# import tkinter as tk
# from tkinter import filedialog, scrolledtext, ttk
# 
# import dialogs
# import rename_apply
# import theme
# import widgets
# from formats import SUPPORTED_EXTS
# from merge_apply import read_plain_text
# from term_dict import TermDict
# 
# DIFF_CONTEXT_CHARS = 20
# DIFF_MAX_ITEMS = 50
# 
# 
# class TermsPage(ttk.Frame):
#     def __init__(self, parent, app):
#         super().__init__(parent)
#         self.app = app
#         self.term_dict = TermDict()
#         self._log_visible = False
# 
#         self.file_path = tk.StringVar()
#         self.output_dir = tk.StringVar()
# 
#         self._build()
#         self.refresh_dict_view()
#         self.apply_language()
#         self.bind("<Destroy>", self._on_destroy)
#         theme.subscribe(self)
#         self.refresh_theme()
# 
#     def t(self, key, **kwargs):
#         return self.app.t(key, **kwargs)
# 
#     def _on_destroy(self, _event):
#         theme.unsubscribe(self)
# 
#     # ---------- UI ----------
# 
#     def _build(self):
#         self.grid_rowconfigure(1, weight=1)
#         self.grid_columnconfigure(0, weight=1)
# 
#         header = ttk.Frame(self)
#         header.grid(row=0, column=0, sticky="ew", padx=26, pady=(22, 0))
#         self.lbl_title = ttk.Label(header, style="Heading.TLabel")
#         self.lbl_title.pack(anchor="w")
#         ttk.Label(header, text="Replace names & honorifics, particles corrected", style="Caption.TLabel").pack(anchor="w")
# 
#         body = ttk.Frame(self)
#         body.grid(row=1, column=0, sticky="nsew")
#         body.grid_rowconfigure(0, weight=1)
#         body.grid_columnconfigure(1, weight=1)
# 
#         left = ttk.Frame(body, width=540)
#         left.grid(row=0, column=0, sticky="nsew", padx=(26, 18), pady=16)
#         left.grid_rowconfigure(1, weight=1)
# 
#         right = ttk.Frame(body)
#         right.grid(row=0, column=1, sticky="nsew", padx=(0, 26), pady=16)
#         right.grid_rowconfigure(1, weight=1)
#         right.grid_columnconfigure(0, weight=1)
# 
#         self._build_left(left)
#         self._build_right(right)
#         self._build_bottom()
# 
#     def _build_left(self, left):
#         self._group_tags_row = ttk.Frame(left)
#         self._group_tags_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
# 
#         columns = ("old", "new", "group")
#         self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="extended")
#         self.tree.grid(row=1, column=0, sticky="nsew")
#         for col in columns:
#             self.tree.column(col, width=170, anchor="w")
# 
#         add_row = ttk.Frame(left)
#         add_row.grid(row=2, column=0, sticky="ew", pady=(10, 4))
#         self.lbl_old = ttk.Label(add_row, style="Muted.TLabel")
#         self.lbl_old.grid(row=0, column=0, sticky="w")
#         self.entry_old = ttk.Entry(add_row, width=12)
#         self.entry_old.grid(row=0, column=1, padx=4)
#         self.lbl_new = ttk.Label(add_row, style="Muted.TLabel")
#         self.lbl_new.grid(row=0, column=2, sticky="w")
#         self.entry_new = ttk.Entry(add_row, width=12)
#         self.entry_new.grid(row=0, column=3, padx=4)
#         self.lbl_group = ttk.Label(add_row, style="Muted.TLabel")
#         self.lbl_group.grid(row=0, column=4, sticky="w")
#         self.entry_group = ttk.Entry(add_row, width=12)
#         self.entry_group.grid(row=0, column=5, padx=4)
#         self.btn_add = ttk.Button(add_row, style="Secondary.TButton", command=self.on_add)
#         self.btn_add.grid(row=0, column=6, padx=(6, 0))
# 
#         actions_row = ttk.Frame(left)
#         actions_row.grid(row=3, column=0, sticky="ew", pady=(0, 10))
#         self.btn_delete = ttk.Button(actions_row, style="Ghost.TButton", command=self.on_delete_selected)
#         self.btn_delete.pack(side="left")
#         self.btn_import = ttk.Button(actions_row, style="Ghost.TButton", command=self.on_import_csv)
#         self.btn_import.pack(side="left", padx=4)
#         self.btn_example_csv = ttk.Button(actions_row, style="Ghost.TButton", command=self.on_create_example_csv)
#         self.btn_example_csv.pack(side="left")
# 
#         ttk.Separator(left).grid(row=4, column=0, sticky="ew", pady=(0, 10))
# 
#         self.lbl_groups = ttk.Label(left, style="Heading.TLabel")
#         self.lbl_groups.grid(row=5, column=0, sticky="w", pady=(0, 4))
#         self.groups_list = tk.Listbox(left, selectmode="extended", height=4, exportselection=False, relief="flat", borderwidth=1)
#         self.groups_list.grid(row=6, column=0, sticky="ew", pady=(0, 10))
# 
#         file_row = ttk.Frame(left)
#         file_row.grid(row=7, column=0, sticky="ew", pady=(0, 6))
#         self.lbl_file = ttk.Label(file_row, style="Muted.TLabel")
#         self.lbl_file.pack(side="left")
#         ttk.Entry(file_row, textvariable=self.file_path).pack(side="left", fill="x", expand=True, padx=6)
#         self.btn_file = ttk.Button(file_row, style="Secondary.TButton", command=self.choose_file)
#         self.btn_file.pack(side="left")
# 
#         out_row = ttk.Frame(left)
#         out_row.grid(row=8, column=0, sticky="ew")
#         self.lbl_output = ttk.Label(out_row, style="Muted.TLabel")
#         self.lbl_output.pack(side="left")
#         ttk.Entry(out_row, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=6)
#         self.btn_output = ttk.Button(out_row, style="Secondary.TButton", command=self.choose_output_dir)
#         self.btn_output.pack(side="left")
# 
#     def _build_right(self, right):
#         header = ttk.Frame(right)
#         header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
#         self.lbl_preview_title = ttk.Label(header, style="Heading.TLabel")
#         self.lbl_preview_title.pack(side="left")
#         ttk.Label(header, text="Preview", style="Caption.TLabel").pack(side="left", padx=(8, 8))
#         self.tag_diff_summary = widgets.make_tag(header, "", "accent")
#         self.tag_diff_summary.pack(side="left")
#         self.btn_refresh = ttk.Button(header, style="Ghost.TButton", command=self.refresh_preview)
#         self.btn_refresh.pack(side="right")
# 
#         self.diff_text = tk.Text(right, wrap="word", state="disabled", relief="flat", borderwidth=0)
#         self.diff_text.grid(row=1, column=0, sticky="nsew")
# 
#         self.note = widgets.BlueprintFrame(right)
#         self.note.grid(row=2, column=0, sticky="ew", pady=(10, 0))
#         self.lbl_note = ttk.Label(self.note.content, style="Muted.TLabel", wraplength=380, justify="left")
#         self.lbl_note.pack(anchor="w", padx=10, pady=8)
# 
#     def _configure_diff_tags(self):
#         t = theme.tokens()
#         self.diff_text.tag_configure("loc", foreground=t["neutral_600"], font=("Segoe UI", 8))
#         self.diff_text.tag_configure("before", foreground=t["neutral_500"], overstrike=True)
#         self.diff_text.tag_configure("after", foreground=t["text"])
# 
#     def _build_bottom(self):
#         bar = ttk.Frame(self)
#         bar.grid(row=2, column=0, sticky="ew", padx=22, pady=12)
#         self.btn_log_toggle = ttk.Button(bar, style="Secondary.TButton", command=self._toggle_log)
#         self.btn_log_toggle.pack(side="left")
#         self.btn_run = ttk.Button(bar, style="Primary.TButton", command=self.run_rename)
#         self.btn_run.pack(side="right")
# 
#         self.log_frame = ttk.Frame(self)
#         self.log = scrolledtext.ScrolledText(self.log_frame, height=6, state="disabled")
#         self.log.pack(fill="both", expand=True, padx=22, pady=(0, 8))
# 
#     def apply_language(self):
#         self.lbl_title.configure(text=self.t("rename_window_title"))
#         self.tree.heading("old", text=self.t("rename_col_old"))
#         self.tree.heading("new", text=self.t("rename_col_new"))
#         self.tree.heading("group", text=self.t("rename_col_group"))
#         self.lbl_old.configure(text=self.t("rename_add_old_label"))
#         self.lbl_new.configure(text=self.t("rename_add_new_label"))
#         self.lbl_group.configure(text=self.t("rename_add_group_label"))
#         self.btn_add.configure(text=self.t("rename_add_button"))
#         self.btn_delete.configure(text=self.t("rename_delete_button"))
#         self.btn_import.configure(text=self.t("rename_import_button"))
#         self.btn_example_csv.configure(text=self.t("rename_example_csv_button"))
#         self.lbl_groups.configure(text=self.t("rename_groups_label"))
#         self.lbl_file.configure(text=self.t("rename_file_label"))
#         self.btn_file.configure(text=self.t("rename_file_button"))
#         self.lbl_output.configure(text=self.t("rename_output_label"))
#         self.btn_output.configure(text=self.t("rename_output_button"))
#         self.lbl_preview_title.configure(text="치환 미리보기")
#         self.btn_refresh.configure(text="새로고침")
#         self.lbl_note.configure(text="조사(은/는, 을/를, 이/가)는 바뀐 단어의 받침에 맞춰 자동으로 고쳐집니다.")
#         self.btn_log_toggle.configure(text=("로그 ▼" if self._log_visible else "로그 ▲"))
#         self.btn_run.configure(text=self.t("rename_run_button"))
#         self.refresh_groups_list()
#         self._refresh_group_tags()
#         self._update_diff_summary(0, 0)
# 
#     def refresh_theme(self):
#         t = theme.tokens()
#         self._configure_diff_tags()
#         self.diff_text.configure(
#             bg=t["bg"], fg=t["text"], insertbackground=t["accent"],
#             selectbackground=t["accent_200"], selectforeground=t["accent_800"],
#         )
#         self.groups_list.configure(
#             bg=t["surface"], fg=t["text"], selectbackground=t["accent"], selectforeground=t["bg"],
#             highlightbackground=t["divider"], highlightcolor=t["divider"],
#         )
#         self.log.configure(
#             bg=t["surface"], fg=t["text"], insertbackground=t["accent"],
#             selectbackground=t["accent_200"], selectforeground=t["accent_800"],
#         )
# 
#     # ---------- 사전 관리 ----------
# 
#     def refresh_dict_view(self):
#         self.tree.delete(*self.tree.get_children())
#         for entry in self.term_dict.entries:
#             group_display = entry["작품"] if entry["작품"] else self.t("rename_common_group")
#             self.tree.insert("", "end", values=(entry["원래단어"], entry["바꿀단어"], group_display))
#         self.refresh_groups_list()
#         self._refresh_group_tags()
# 
#     def refresh_groups_list(self):
#         selected_names = {self.groups_list.get(i) for i in self.groups_list.curselection()}
#         self.groups_list.delete(0, "end")
#         for g in self.term_dict.groups():
#             self.groups_list.insert("end", g)
#         for i in range(self.groups_list.size()):
#             if self.groups_list.get(i) in selected_names:
#                 self.groups_list.selection_set(i)
# 
#     def _refresh_group_tags(self):
#         for child in self._group_tags_row.winfo_children():
#             child.destroy()
#         common_count = sum(1 for e in self.term_dict.entries if not e["작품"])
#         widgets.make_tag(self._group_tags_row, f"{self.t('rename_common_group')} · {common_count}", "neutral").pack(
#             side="left", padx=(0, 6)
#         )
#         for g in self.term_dict.groups():
#             count = sum(1 for e in self.term_dict.entries if e["작품"] == g)
#             widgets.make_tag(self._group_tags_row, f"{g} · {count}", "outline").pack(side="left", padx=(0, 6))
# 
#     def selected_groups(self):
#         return [self.groups_list.get(i) for i in self.groups_list.curselection()]
# 
#     def on_add(self):
#         old = self.entry_old.get().strip()
#         new = self.entry_new.get().strip()
#         group = self.entry_group.get().strip()
#         if not old:
#             dialogs.show_error(self, self.t("err_title"), self.t("rename_add_missing_old"))
#             return
#         self.term_dict.add(old, new, group)
#         self.entry_old.delete(0, "end")
#         self.entry_new.delete(0, "end")
#         self.entry_group.delete(0, "end")
#         self.refresh_dict_view()
# 
#     def on_delete_selected(self):
#         selected_items = self.tree.selection()
#         if not selected_items:
#             dialogs.show_warning(self, self.t("err_title"), self.t("rename_no_selection"))
#             return
#         indices = [self.tree.index(item) for item in selected_items]
#         if not dialogs.ask_yes_no(
#             self, self.t("rename_delete_confirm_title"), self.t("rename_delete_confirm_body", n=len(indices)),
#         ):
#             return
#         self.term_dict.delete(indices)
#         self.refresh_dict_view()
# 
#     def on_create_example_csv(self):
#         path = filedialog.asksaveasfilename(
#             title=self.t("rename_choose_example_csv_title"), defaultextension=".csv",
#             filetypes=self.t("rename_csv_filetypes"), initialfile="coriuni_rename_example.csv",
#         )
#         if not path:
#             return
#         with open(path, "w", newline="", encoding="utf-8-sig") as f:
#             writer = csv.writer(f)
#             writer.writerow(["원래단어", "바꿀단어", "작품"])
#             writer.writerow(["형", "언니", ""])
#             writer.writerow(["철수", "영희", "작품A"])
#             writer.writerow(["오빠", "언니", ""])
#         dialogs.show_info(self, self.t("rename_example_csv_button"), self.t("rename_example_csv_saved", path=path))
# 
#     def on_import_csv(self):
#         path = filedialog.askopenfilename(title=self.t("rename_choose_csv_title"), filetypes=self.t("rename_csv_filetypes"))
#         if not path:
#             return
#         try:
#             count = self.term_dict.import_csv(path)
#         except Exception as e:
#             dialogs.show_error(self, self.t("rename_error_title"), self.t("rename_error_body", err=e))
#             return
#         self.refresh_dict_view()
#         dialogs.show_info(self, self.t("rename_import_title"), self.t("rename_import_done", n=count))
# 
#     # ---------- 파일/출력 ----------
# 
#     def choose_file(self):
#         path = filedialog.askopenfilename(title=self.t("choose_file_title"), filetypes=self.t("filetypes"))
#         if not path:
#             return
#         ext = os.path.splitext(path)[1].lower()
#         if ext == ".hwp":
#             dialogs.show_warning(self, self.t("hwp_title"), self.t("hwp_body"))
#             return
#         if ext not in SUPPORTED_EXTS:
#             dialogs.show_warning(self, self.t("unsupported_title"), self.t("unsupported_body", ext=ext))
#             return
#         self.file_path.set(path)
#         if not self.output_dir.get():
#             base = os.path.splitext(os.path.basename(path))[0]
#             suffix = self.t("rename_outdir_suffix")
#             self.output_dir.set(os.path.join(os.path.dirname(path), f"{base}{suffix}"))
# 
#     def choose_output_dir(self):
#         path = filedialog.askdirectory(title=self.t("choose_output_title"))
#         if path:
#             self.output_dir.set(path)
# 
#     # ---------- 치환 미리보기 (새 기능) ----------
# 
#     def _build_diff_previews(self, text, mapping):
#         replacements = rename_apply.compute_replacements(text, mapping)
#         total = len(replacements)
#         shown = replacements[:DIFF_MAX_ITEMS]
#         previews = []
#         for start, end, new_text in shown:
#             line_no = text.count("\n", 0, start) + 1
#             ctx_start = max(0, start - DIFF_CONTEXT_CHARS)
#             ctx_end = min(len(text), end + DIFF_CONTEXT_CHARS)
#             before = text[ctx_start:start] + text[start:end] + text[end:ctx_end]
#             after = text[ctx_start:start] + new_text + text[end:ctx_end]
#             previews.append({"line": line_no, "before": before, "after": after})
#         return previews, total
# 
#     def refresh_preview(self):
#         path = self.file_path.get().strip()
#         if not path or not os.path.isfile(path):
#             dialogs.show_error(self, self.t("err_title"), self.t("err_no_file"))
#             return
#         mapping = self.term_dict.active_mapping(self.selected_groups())
#         try:
#             text = read_plain_text(path)
#         except Exception as e:
#             dialogs.show_error(self, self.t("error_title"), self.t("error_body", err=e))
#             return
#         previews, total = self._build_diff_previews(text, mapping)
#         self._render_diff(previews, total)
# 
#     def _render_diff(self, previews, total):
#         self._update_diff_summary(total, len(previews))
#         tw = self.diff_text
#         tw.configure(state="normal")
#         tw.delete("1.0", "end")
#         for p in previews:
#             tw.insert("end", f"{p['line']}행 · Line {p['line']}\n", "loc")
#             tw.insert("end", p["before"] + "\n", "before")
#             tw.insert("end", p["after"] + "\n\n", "after")
#         if not previews:
#             tw.insert("end", "표시할 치환 지점이 없습니다. / No replacements to preview.")
#         tw.configure(state="disabled")
# 
#     def _update_diff_summary(self, total, shown):
#         if total > shown:
#             self.tag_diff_summary.configure(text=f"{total}곳 (처음 {shown}개 표시)")
#         else:
#             self.tag_diff_summary.configure(text=f"{total}곳")
# 
#     # ---------- 로그 서랍 ----------
# 
#     def _toggle_log(self):
#         self._log_visible = not self._log_visible
#         if self._log_visible:
#             self.log_frame.grid(row=3, column=0, sticky="ew")
#             self.btn_log_toggle.configure(text="로그 ▼")
#         else:
#             self.log_frame.grid_remove()
#             self.btn_log_toggle.configure(text="로그 ▲")
# 
#     def log_line(self, text):
#         if not self._log_visible:
#             self._toggle_log()
#         self.log.configure(state="normal")
#         self.log.insert("end", text + "\n")
#         self.log.see("end")
#         self.log.configure(state="disabled")
# 
#     # ---------- 실행 ----------
# 
#     def _set_running(self, running):
#         state = "disabled" if running else "normal"
#         for btn in (
#             self.btn_run, self.btn_refresh, self.btn_add, self.btn_delete, self.btn_import,
#             self.btn_example_csv, self.btn_file, self.btn_output,
#         ):
#             btn.configure(state=state)
# 
#     def run_rename(self):
#         path = self.file_path.get().strip()
#         out_dir = self.output_dir.get().strip()
# 
#         if not path or not os.path.isfile(path):
#             dialogs.show_error(self, self.t("err_title"), self.t("err_no_file"))
#             return
#         if not out_dir:
#             dialogs.show_error(self, self.t("err_title"), self.t("err_no_outdir"))
#             return
# 
#         groups = self.selected_groups()
#         mapping = self.term_dict.active_mapping(groups)
# 
#         os.makedirs(out_dir, exist_ok=True)
# 
#         self.log_line(self.t("rename_log_start", path=path))
#         group_text = ", ".join(groups) if groups else self.t("rename_log_no_active_groups")
#         self.log_line(self.t("rename_log_active_groups", groups=group_text))
# 
#         if not mapping:
#             self.log_line(self.t("rename_log_no_change"))
#             return
# 
#         self._set_running(True)
#         thread = threading.Thread(target=self._do_rename, args=(path, mapping, out_dir), daemon=True)
#         thread.start()
# 
#     def _do_rename(self, path, mapping, out_dir):
#         ext = os.path.splitext(path)[1].lower()
#         try:
#             if ext == ".txt":
#                 out_path, _encoding = rename_apply.rename_txt_file(path, mapping, out_dir)
#             elif ext == ".docx":
#                 out_path = rename_apply.rename_docx_file(path, mapping, out_dir)
#             elif ext == ".hwpx":
#                 out_path = rename_apply.rename_hwpx_file(path, mapping, out_dir)
#             else:
#                 raise ValueError(self.t("unsupported_body", ext=ext))
# 
#             self.after(0, self.log_line, self.t("rename_log_done", path=out_path))
#             self.after(0, lambda: dialogs.show_info(self, self.t("rename_done_title"), self.t("rename_done_body", path=out_path)))
#             self.after(0, self._record_activity, path, out_path)
#         except Exception as e:
#             self.after(0, self.log_line, self.t("rename_log_error", err=e))
#             self.after(0, lambda: dialogs.show_error(self, self.t("rename_error_title"), self.t("rename_error_body", err=e)))
#         finally:
#             self.after(0, self._set_running, False)
# 
#     def _record_activity(self, path, out_path):
#         try:
#             import activity_log
#             activity_log.record(self.t("rename_run_button"), os.path.basename(path), os.path.basename(out_path))
#         except Exception:
#             pass
# 
#     def on_show(self):
#         pass
