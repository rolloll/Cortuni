"""파일 병합 창.

여러 txt/docx/hwpx 파일을 원하는 순서로(마우스 드래그) 배치하고,
파일별로 원하면 제목을 넣어 하나로 합친다(제목을 비워두면 그 파일 앞에 아무것도
넣지 않는다). 파일이 많을 때는 CSV로 내보내 제목을 한번에 편집한 뒤 다시 불러올 수 있다.
"""

import csv
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from formats import SUPPORTED_EXTS
import merge_apply
import fonts

COLUMNS = ("check", "order", "filename", "title")
CHECK_ON = "☑"
CHECK_OFF = "☐"


class MergeWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self._entry_by_iid = {}
        self._next_id = 0
        self.entries = []
        self._drag_item = None

        self.output_path = tk.StringVar()
        self._filename_sort_ascending = False
        self._filename_sort_applied = False

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
        self.geometry("760x740")

        frm_actions = ttk.Frame(self)
        frm_actions.pack(fill="x", padx=10, pady=(10, 4))
        self.btn_add_files = ttk.Button(frm_actions, text="", command=self.on_add_files)
        self.btn_add_files.pack(side="left")
        self.btn_add_folder = ttk.Button(frm_actions, text="", command=self.on_add_folder)
        self.btn_add_folder.pack(side="left", padx=4)
        self.btn_remove = ttk.Button(frm_actions, text="", command=self.on_remove_selected)
        self.btn_remove.pack(side="left", padx=4)

        self.lbl_drag_hint = ttk.Label(self, foreground="#555555", wraplength=720, justify="left")
        self.lbl_drag_hint.pack(anchor="w", padx=10)

        self.tree = ttk.Treeview(self, columns=COLUMNS, show="headings", selectmode="extended", height=14)
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)
        self.tree.column("check", width=36, anchor="center", stretch=False)
        self.tree.column("order", width=50, anchor="center", stretch=False)
        self.tree.column("filename", width=340, anchor="w")
        self.tree.column("title", width=280, anchor="w")
        self.tree.heading("check", text=CHECK_OFF, command=self.on_toggle_all_checkboxes)

        self.tree.bind("<ButtonPress-1>", self._on_drag_start)
        self.tree.bind("<B1-Motion>", self._on_drag_motion)
        self.tree.bind("<<TreeviewSelect>>", self._on_selection_changed)

        frm_edit = ttk.LabelFrame(self)
        frm_edit.pack(fill="x", padx=10, pady=6)
        self.lbl_edit_panel = frm_edit

        self.lbl_title = ttk.Label(frm_edit, text="")
        self.lbl_title.grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.entry_title = ttk.Entry(frm_edit, width=30)
        self.entry_title.grid(row=0, column=1, padx=4, sticky="we")
        frm_edit.columnconfigure(1, weight=1)

        self.btn_apply_selected = ttk.Button(frm_edit, text="", command=self.on_apply_to_selected)
        self.btn_apply_selected.grid(row=0, column=2, padx=6)

        self.lbl_title_hint = ttk.Label(frm_edit, foreground="#555555", wraplength=700, justify="left")
        self.lbl_title_hint.grid(row=1, column=0, columnspan=3, sticky="w", padx=4, pady=(0, 4))

        self.frm_csv = ttk.LabelFrame(self)
        self.frm_csv.pack(fill="x", padx=10, pady=(0, 6))
        self.lbl_csv_section = self.frm_csv
        frm_csv_buttons = ttk.Frame(self.frm_csv)
        frm_csv_buttons.pack(fill="x", padx=4, pady=4)
        self.btn_export_csv = ttk.Button(frm_csv_buttons, text="", command=self.on_export_csv)
        self.btn_export_csv.pack(side="left")
        self.btn_import_csv = ttk.Button(frm_csv_buttons, text="", command=self.on_import_csv)
        self.btn_import_csv.pack(side="left", padx=4)
        self.btn_example_csv = ttk.Button(frm_csv_buttons, text="", command=self.on_create_example_csv)
        self.btn_example_csv.pack(side="left", padx=4)
        self.lbl_csv_hint = ttk.Label(self.frm_csv, foreground="#555555", wraplength=700, justify="left")
        self.lbl_csv_hint.pack(anchor="w", padx=4, pady=(0, 4))

        frm_settings = ttk.Frame(self)
        frm_settings.pack(fill="x", padx=10, pady=(6, 6))
        self.lbl_spacing = ttk.Label(frm_settings, text="")
        self.lbl_spacing.pack(side="left")
        self.spin_spacing = ttk.Spinbox(frm_settings, from_=0, to=10, width=4)
        self.spin_spacing.set(str(merge_apply.DEFAULT_BLANK_LINES))
        self.spin_spacing.pack(side="left", padx=(4, 16))

        self.lbl_header_style = ttk.Label(frm_settings, text="")
        self.lbl_header_style.pack(side="left")
        self.var_bold = tk.BooleanVar(value=True)
        self.var_italic = tk.BooleanVar(value=False)
        self.chk_bold = ttk.Checkbutton(frm_settings, variable=self.var_bold, text="")
        self.chk_bold.pack(side="left", padx=(4, 8))
        self.chk_italic = ttk.Checkbutton(frm_settings, variable=self.var_italic, text="")
        self.chk_italic.pack(side="left")

        frm_page_break = ttk.Frame(self)
        frm_page_break.pack(fill="x", padx=10, pady=(0, 6))
        self.var_page_break = tk.BooleanVar(value=False)
        self.chk_page_break = ttk.Checkbutton(frm_page_break, variable=self.var_page_break, text="")
        self.chk_page_break.pack(side="left")
        self.lbl_page_break_hint = ttk.Label(frm_page_break, foreground="#555555", wraplength=600, justify="left")
        self.lbl_page_break_hint.pack(side="left", padx=(6, 0))

        ttk.Separator(self).pack(fill="x", padx=10, pady=4)

        frm_out = ttk.Frame(self)
        frm_out.pack(fill="x", padx=10, pady=4)
        self.lbl_output = ttk.Label(frm_out, text="")
        self.lbl_output.pack(side="left")
        ttk.Entry(frm_out, textvariable=self.output_path).pack(side="left", fill="x", expand=True, padx=6)
        self.btn_output = ttk.Button(frm_out, text="", command=self.choose_output)
        self.btn_output.pack(side="left")

        self.lbl_hwpx_note = ttk.Label(self, foreground="#555555", wraplength=720, justify="left")
        self.lbl_hwpx_note.pack(anchor="w", padx=10)

        frm_run = ttk.Frame(self)
        frm_run.pack(pady=8)
        self.btn_preview = ttk.Button(frm_run, text="", command=self.on_preview)
        self.btn_preview.pack(side="left", padx=4)
        self.btn_run = ttk.Button(frm_run, text="", command=self.run_merge)
        self.btn_run.pack(side="left", padx=4)

        self.log = scrolledtext.ScrolledText(self, height=6, state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def apply_language(self):
        self.title(self.t("merge_window_title"))
        self.btn_add_files.configure(text=self.t("merge_add_files_button"))
        self.btn_add_folder.configure(text=self.t("merge_add_folder_button"))
        self.btn_remove.configure(text=self.t("merge_remove_button"))
        self.btn_export_csv.configure(text=self.t("merge_export_csv_button"))
        self.btn_import_csv.configure(text=self.t("merge_import_csv_button"))
        self.btn_example_csv.configure(text=self.t("merge_example_csv_button"))
        self.lbl_drag_hint.configure(text=self.t("merge_drag_hint"))
        self.lbl_edit_panel.configure(text=self.t("merge_edit_panel_label"))
        self.lbl_title.configure(text=self.t("merge_title_label"))
        self.btn_apply_selected.configure(text=self.t("merge_apply_to_selected_button"))
        self.lbl_title_hint.configure(text=self.t("merge_title_hint"))
        self.lbl_csv_section.configure(text=self.t("merge_csv_section_label"))
        self.lbl_csv_hint.configure(text=self.t("merge_csv_section_hint"))
        self.lbl_spacing.configure(text=self.t("merge_spacing_label"))
        self.lbl_header_style.configure(text=self.t("merge_header_style_label"))
        self.chk_bold.configure(text=self.t("merge_bold_label"))
        self.chk_italic.configure(text=self.t("merge_italic_label"))
        self.chk_page_break.configure(text=self.t("merge_page_break_label"))
        self.lbl_page_break_hint.configure(text=self.t("merge_page_break_hint"))
        self.lbl_output.configure(text=self.t("merge_output_label"))
        self.btn_output.configure(text=self.t("merge_output_button"))
        self.lbl_hwpx_note.configure(text=self.t("merge_hwpx_note"))
        self.btn_preview.configure(text=self.t("merge_preview_button"))
        self.btn_run.configure(text=self.t("merge_run_button"))

        self.tree.heading("order", text=self.t("merge_col_order"))
        self.tree.heading("title", text=self.t("merge_col_title"))
        self._refresh_filename_heading()
        self.tree.heading("check", text=CHECK_ON if self._all_checked() else CHECK_OFF, command=self.on_toggle_all_checkboxes)

    # ---------- 목록 관리 ----------

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
        entry = {"path": path, "title": ""}
        self._add_entry(entry)

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
                messagebox.showwarning(self.t("hwp_title"), self.t("hwp_body"))
                continue
            if ext not in SUPPORTED_EXTS:
                messagebox.showwarning(self.t("unsupported_title"), self.t("unsupported_body", ext=ext))
                continue
            self._add_file_path(path)

    def on_add_folder(self):
        folder = filedialog.askdirectory(title=self.t("merge_choose_folder_title"))
        if not folder:
            return
        names = sorted(os.listdir(folder))
        for name in names:
            ext = os.path.splitext(name)[1].lower()
            if ext in SUPPORTED_EXTS:
                self._add_file_path(os.path.join(folder, name))

    def on_remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(self.t("err_title"), self.t("merge_no_selection"))
            return
        for iid in sel:
            self.tree.delete(iid)
            del self._entry_by_iid[iid]
        self._sync_entries_from_tree()

    def on_apply_to_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(self.t("err_title"), self.t("merge_no_selection"))
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
        return bool(self.var_bold.get()), bool(self.var_italic.get())

    def _get_page_break(self):
        return bool(self.var_page_break.get())

    # ---------- CSV ----------

    def on_create_example_csv(self):
        path = filedialog.asksaveasfilename(
            title=self.t("merge_choose_example_csv_title"),
            defaultextension=".csv",
            filetypes=self.t("rename_csv_filetypes"),
            initialfile="coriuni_merge_example.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["파일경로", "제목"])
            writer.writerow([r"C:\소설\1화.txt", "프롤로그"])
            writer.writerow([r"C:\소설\2화.txt", "1화"])
            writer.writerow([r"C:\소설\3화.txt", ""])
        messagebox.showinfo(self.t("merge_example_csv_button"), self.t("merge_example_csv_saved", path=path))

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
        messagebox.showinfo(self.t("merge_export_csv_button"), self.t("merge_export_done", path=path))

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
        messagebox.showinfo(self.t("merge_import_csv_button"), self.t("merge_import_done", n=len(self.entries), skipped=skipped_text))

    # ---------- 실행 ----------

    def log_line(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_running(self, running):
        state = "disabled" if running else "normal"
        for btn in (
            self.btn_run, self.btn_preview, self.btn_add_files, self.btn_add_folder,
            self.btn_remove, self.btn_export_csv, self.btn_import_csv,
            self.btn_example_csv, self.btn_apply_selected, self.btn_output,
        ):
            btn.configure(state=state)

    def run_merge(self):
        self._sync_entries_from_tree()
        if not self.entries:
            messagebox.showerror(self.t("err_title"), self.t("merge_no_files"))
            return
        output_path = self.output_path.get().strip()
        if not output_path:
            messagebox.showerror(self.t("err_title"), self.t("merge_no_output"))
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
            self.after(0, lambda: messagebox.showinfo(self.t("merge_done_title"), self.t("merge_done_body", path=output_path)))
        except merge_apply.MixedExtensionError as e:
            msg = self.t("merge_mixed_ext_error", exts=", ".join(e.exts))
            self.after(0, self.log_line, self.t("merge_log_error", err=msg))
            self.after(0, lambda: messagebox.showerror(self.t("merge_error_title"), msg))
        except Exception as e:
            self.after(0, self.log_line, self.t("merge_log_error", err=e))
            self.after(0, lambda: messagebox.showerror(self.t("merge_error_title"), self.t("merge_error_body", err=e)))
        finally:
            self.after(0, self._set_running, False)

    # ---------- 미리보기 ----------

    def on_preview(self):
        self._sync_entries_from_tree()
        if not self.entries:
            messagebox.showerror(self.t("err_title"), self.t("merge_no_files"))
            return
        try:
            ext = merge_apply.common_extension(self.entries)
        except merge_apply.MixedExtensionError as e:
            messagebox.showerror(self.t("merge_error_title"), self.t("merge_mixed_ext_error", exts=", ".join(e.exts)))
            return

        spacing = self._get_spacing()
        bold, italic = self._get_header_style()
        page_break = self._get_page_break() and ext in (".docx", ".hwpx")
        try:
            segments, truncated = merge_apply.build_preview_segments(
                self.entries, blank_lines=spacing, header_bold=bold, header_italic=italic, page_break=page_break
            )
        except Exception as e:
            messagebox.showerror(self.t("merge_error_title"), self.t("merge_error_body", err=e))
            return

        PreviewWindow(self, segments, truncated)


class PreviewWindow(tk.Toplevel):
    def __init__(self, master_merge_window, segments, truncated):
        super().__init__(master_merge_window)
        self.master_merge_window = master_merge_window

        def t(key, **kwargs):
            return master_merge_window.t(key, **kwargs)

        self.title(t("merge_preview_window_title"))
        self.geometry("640x600")
        try:
            self.iconphoto(True, master_merge_window.master_app._icon_image)
        except Exception:
            pass

        if truncated:
            ttk.Label(self, text=t("merge_preview_truncated_note"), foreground="#a05a00").pack(
                anchor="w", padx=10, pady=(10, 0)
            )

        text_widget = scrolledtext.ScrolledText(self, wrap="word", state="normal")
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)

        family = fonts.current_family()
        text_widget.tag_configure("bold", font=(family, 10, "bold"))
        text_widget.tag_configure("italic", font=(family, 10, "italic"))
        text_widget.tag_configure("bold_italic", font=(family, 10, "bold italic"))
        text_widget.tag_configure("page_break", foreground="#a05a00", justify="center")

        for content, _is_header, bold, italic, is_page_break in segments:
            if is_page_break:
                text_widget.insert("end", "\n" + t("merge_preview_page_break_label") + "\n\n", "page_break")
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
                text_widget.insert("end", content, tag)
            else:
                text_widget.insert("end", content)

        text_widget.configure(state="disabled")

        ttk.Button(self, text=t("merge_preview_close_button"), command=self.destroy).pack(pady=(0, 10))
