"""분할 화면(디자인 시안 2b) - 설정은 왼쪽, 미리보기는 항상 열려 있는 오른쪽 패널,
로그는 아래쪽 접이식 서랍.

문장이 잘리지 않는 글자수 기준으로 파일 하나를 여러 개로 나눈다.
지원 형식: .txt, .docx, .hwpx

실행 로직(_resolve_chunker/_do_split 등)은 이전 split_window.py와 동일하다 -
바뀐 것은 화면 배치와, 미리보기가 별도 팝업이 아니라 이 페이지에 항상
붙어 있다는 것, 그리고 로그가 접이식이라는 것뿐이다.
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk

import dialogs
import fonts
import splitter
import theme
import widgets
from docx_handler import split_docx_file
from formats import SUPPORTED_EXTS
from hwpx_handler import split_hwpx_file
from merge_apply import read_plain_text
from txt_handler import split_txt_file

QUICK_CHAR_VALUES = ("2000", "3000", "5000")


class SplitPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.file_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.split_mode = tk.StringVar(value="chars")
        self.chunk_kb = tk.StringVar(value="100")
        self.chunk_count = tk.StringVar(value="5")
        self.chunk_size = tk.StringVar(value="3000")
        self._log_visible = False

        self._build()
        self.apply_language()
        self._on_mode_changed()
        self.bind("<Destroy>", self._on_destroy)
        theme.subscribe(self)
        self.refresh_theme()

    def t(self, key, **kwargs):
        return self.app.t(key, **kwargs)

    def _on_destroy(self, _event):
        theme.unsubscribe(self)

    def refresh_theme(self):
        t = theme.tokens()
        self.lbl_file_badge.configure(bg=t["bg"], fg=t["accent_700"], highlightthickness=1, highlightbackground=t["accent"])
        card_bg = t["accent_100"]
        self.estimate_card._tint = card_bg
        self.estimate_card.refresh_theme()
        self._est_files_val.configure(bg=card_bg, fg=t["accent_700"])
        self._est_chars_val.configure(bg=card_bg, fg=t["accent_700"])
        self._configure_preview_tags()
        self.preview_text.configure(
            bg=t["bg"], fg=t["text"], insertbackground=t["accent"],
            selectbackground=t["accent_200"], selectforeground=t["accent_800"],
        )
        self.log.configure(
            bg=t["surface"], fg=t["text"], insertbackground=t["accent"],
            selectbackground=t["accent_200"], selectforeground=t["accent_800"],
        )
        # 태그(make_tag)는 ttk 스타일(TagNeutral.TLabel)을 쓰므로 theme.configure_ttk_style()에서
        # 이미 갱신된다 - 여기서 개별 처리할 필요 없음.

    # ---------- UI ----------

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=26, pady=(22, 0))
        self.lbl_title = ttk.Label(header, style="Heading.TLabel")
        self.lbl_title.pack(anchor="w")
        self.lbl_caption = ttk.Label(header, text="Split one document, never mid-sentence", style="Caption.TLabel")
        self.lbl_caption.pack(anchor="w")

        body = ttk.Frame(self)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        left = ttk.Frame(body, width=420)
        left.grid(row=0, column=0, sticky="ns", padx=(26, 18), pady=16)

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 26), pady=16)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._build_left(left)
        self._build_right(right)
        self._build_bottom()

    def _build_left(self, left):
        file_card = widgets.BlueprintFrame(left)
        file_card.pack(fill="x")
        row = ttk.Frame(file_card.content)
        row.pack(fill="x", padx=12, pady=12)
        self.lbl_file_badge = tk.Label(row, text="", width=5, font=(theme.HEADING_FONT, 9, "bold"))
        self.lbl_file_badge.pack(side="left", padx=(0, 12))
        info_col = ttk.Frame(row)
        info_col.pack(side="left", fill="x", expand=True)
        self.lbl_file_name = ttk.Label(info_col, text="", style="Heading.TLabel")
        self.lbl_file_name.pack(anchor="w")
        self.lbl_file_meta = ttk.Label(info_col, text="", style="Muted.TLabel")
        self.lbl_file_meta.pack(anchor="w")
        self.btn_file = ttk.Button(row, style="Secondary.TButton", command=self.choose_file)
        self.btn_file.pack(side="right")
        self.lbl_drop_hint = ttk.Label(left, style="Muted.TLabel", wraplength=380, justify="left")
        self.lbl_drop_hint.pack(anchor="w", pady=(6, 14))

        out_frame = ttk.Frame(left)
        out_frame.pack(fill="x", pady=(0, 14))
        self.lbl_output = ttk.Label(out_frame, style="Heading.TLabel")
        self.lbl_output.pack(anchor="w", pady=(0, 5))
        out_row = ttk.Frame(out_frame)
        out_row.pack(fill="x")
        ttk.Entry(out_row, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.btn_output = ttk.Button(out_row, style="Secondary.TButton", command=self.choose_output_dir)
        self.btn_output.pack(side="left")

        mode_frame = ttk.Frame(left)
        mode_frame.pack(fill="x", pady=(0, 14))
        self.lbl_mode_section = ttk.Label(mode_frame, style="Heading.TLabel")
        self.lbl_mode_section.pack(anchor="w", pady=(0, 7))
        self.seg_mode = widgets.Segmented(
            mode_frame,
            [("size", ""), ("count", ""), ("chars", "")],
            self.split_mode, command=lambda _v: self._on_mode_changed(),
        )
        self.seg_mode.pack(anchor="w", pady=(0, 9))

        value_row = ttk.Frame(mode_frame)
        value_row.pack(fill="x")
        self._value_vars = {"size": self.chunk_kb, "count": self.chunk_count, "chars": self.chunk_size}
        self.entry_value = ttk.Entry(value_row, width=12)
        self.entry_value.pack(side="left")
        self.lbl_unit = ttk.Label(value_row, style="Muted.TLabel")
        self.lbl_unit.pack(side="left", padx=(9, 0))

        self.tags_row = ttk.Frame(mode_frame)
        self.tags_row.pack(fill="x", pady=(8, 0))
        self._quick_tag_labels = []
        for value in QUICK_CHAR_VALUES:
            lbl = widgets.make_tag(self.tags_row, value, "neutral")
            lbl.pack(side="left", padx=(0, 6))
            lbl.bind("<Button-1>", lambda e, v=value: self._apply_quick_value(v))
            lbl.configure(cursor="hand2")
            self._quick_tag_labels.append(lbl)

        self.lbl_hint = ttk.Label(mode_frame, style="Muted.TLabel", wraplength=380, justify="left")
        self.lbl_hint.pack(anchor="w", pady=(10, 0))

        self.estimate_card = widgets.BlueprintFrame(left, tint=theme.tokens()["accent_100"])
        self.estimate_card.pack(fill="x", pady=(14, 0))
        est_row = ttk.Frame(self.estimate_card.content)
        est_row.pack(fill="x", padx=12, pady=10)
        self._est_files_val, self._est_files_lbl = self._stat_block(est_row)
        ttk.Separator(est_row, orient="vertical").pack(side="left", fill="y", padx=10)
        self._est_chars_val, self._est_chars_lbl = self._stat_block(est_row)
        self.lbl_estimate_caption = ttk.Label(est_row, style="Muted.TLabel", justify="right")
        self.lbl_estimate_caption.pack(side="right", anchor="e")

        self.entry_value.bind("<KeyRelease>", lambda e: self._update_estimate())
        self.chunk_kb.trace_add("write", lambda *a: self._sync_value_var())
        self.chunk_count.trace_add("write", lambda *a: self._sync_value_var())
        self.chunk_size.trace_add("write", lambda *a: self._sync_value_var())

    def _stat_block(self, parent):
        col = ttk.Frame(parent)
        col.pack(side="left")
        val = tk.Label(col, text="—", font=(theme.HEADING_FONT, 22, "bold"), bg=theme.tokens()["accent_100"])
        val.pack(anchor="w")
        lbl = ttk.Label(col, style="Muted.TLabel")
        lbl.pack(anchor="w")
        return val, lbl

    def _build_right(self, right):
        header = ttk.Frame(right)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.lbl_preview_title = ttk.Label(header, style="Heading.TLabel")
        self.lbl_preview_title.pack(side="left")
        self.lbl_preview_caption = ttk.Label(header, text="Preview", style="Caption.TLabel")
        self.lbl_preview_caption.pack(side="left", padx=(8, 8))
        self.tag_chunk_count = widgets.make_tag(header, "", "accent")
        self.tag_chunk_count.pack(side="left")
        self.btn_refresh = ttk.Button(header, style="Ghost.TButton", command=self.refresh_preview)
        self.btn_refresh.pack(side="right")

        self.preview_text = tk.Text(right, wrap="word", state="disabled", relief="flat", borderwidth=0)
        self.preview_text.grid(row=1, column=0, sticky="nsew")
        self._configure_preview_tags()

    def _configure_preview_tags(self):
        t = theme.tokens()
        family = fonts.current_family() or theme.BODY_FONT
        self.preview_text.tag_configure("chunk_label", font=(family, 10, "bold"), foreground=t["text"])
        self.preview_text.tag_configure("boundary", foreground=t["accent_700"], justify="center")
        self.preview_text.tag_configure("body", foreground=t["neutral_800"])

    def _build_bottom(self):
        bar = ttk.Frame(self)
        bar.grid(row=2, column=0, sticky="ew", padx=22, pady=12)
        self.btn_log_toggle = ttk.Button(bar, style="Secondary.TButton", command=self._toggle_log)
        self.btn_log_toggle.pack(side="left")
        self.lbl_last_run = ttk.Label(bar, style="Muted.TLabel")
        self.lbl_last_run.pack(side="left", padx=(14, 0))
        self.btn_open_folder = ttk.Button(bar, style="Secondary.TButton", command=self._open_output_folder)
        self.btn_open_folder.pack(side="right", padx=(8, 0))
        self.btn_run = ttk.Button(bar, style="Primary.TButton", command=self.run_split)
        self.btn_run.pack(side="right")

        self.log_frame = ttk.Frame(self)
        self.log = scrolledtext.ScrolledText(self.log_frame, height=8, state="disabled")
        self.log.pack(fill="both", expand=True, padx=22, pady=(0, 8))
        # 접힌 상태로 시작 - grid에 아직 넣지 않는다(_toggle_log가 넣는다).

    def apply_language(self):
        self.lbl_title.configure(text=self.t("split_window_title"))
        self.lbl_output.configure(text=self.t("output_label"))
        self.btn_output.configure(text=self.t("output_button"))
        self.btn_file.configure(text=self.t("file_button"))
        self.lbl_drop_hint.configure(text="창 어디로든 파일을 끌어다 놓아 바꿀 수 있습니다 / drag a file anywhere to replace")
        self.lbl_mode_section.configure(text=self.t("split_mode_section_label"))
        self.seg_mode.options = [
            ("size", self.t("split_mode_size_label")),
            ("count", self.t("split_mode_count_label")),
            ("chars", self.t("split_mode_chars_label")),
        ]
        self._rebuild_seg_labels()
        self.lbl_estimate_caption.configure(text="예상 결과\nEstimate")
        self._est_files_lbl.configure(text="파일 / files")
        self._est_chars_lbl.configure(text="평균 글자 / avg chars")
        self.lbl_preview_title.configure(text=self.t("merge_preview_button"))
        self.btn_refresh.configure(text="새로고침")
        self.btn_log_toggle.configure(text=("로그 ▼" if self._log_visible else "로그 ▲"))
        self.btn_open_folder.configure(text="폴더 열기")
        self.btn_run.configure(text=self.t("run_button"))
        self._sync_value_var()
        self._update_unit_and_hint()
        self._update_file_display()
        self._update_last_run(None)

    def _rebuild_seg_labels(self):
        # Segmented의 라벨은 생성 시 버튼 텍스트로 굳어지므로, 언어가 바뀌면 버튼 텍스트를 직접 갱신한다.
        labels = dict(self.seg_mode.options)
        for value, btn in self.seg_mode._buttons:
            btn.configure(text=labels.get(value, value))

    # ---------- 파일/출력 폴더 ----------

    def choose_file(self):
        path = filedialog.askopenfilename(title=self.t("choose_file_title"), filetypes=self.t("filetypes"))
        if not path:
            return
        self._load_file(path)

    def _load_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".hwp":
            dialogs.show_warning(self, self.t("hwp_title"), self.t("hwp_body"))
            return
        if ext not in SUPPORTED_EXTS:
            dialogs.show_warning(self, self.t("unsupported_title"), self.t("unsupported_body", ext=ext))
            return

        self.file_path.set(path)
        if not self.output_dir.get():
            base = os.path.splitext(os.path.basename(path))[0]
            suffix = self.t("outdir_suffix")
            self.output_dir.set(os.path.join(os.path.dirname(path), f"{base}{suffix}"))
        self._update_file_display()
        self._update_estimate()

    def _update_file_display(self):
        path = self.file_path.get().strip()
        if not path:
            self.lbl_file_badge.configure(text="")
            self.lbl_file_name.configure(text=self.t("err_no_file"))
            self.lbl_file_meta.configure(text="")
            return
        ext = os.path.splitext(path)[1].lstrip(".").upper()
        self.lbl_file_badge.configure(text=ext)
        self.lbl_file_name.configure(text=os.path.basename(path))
        try:
            size = os.path.getsize(path)
            self.lbl_file_meta.configure(text=f"{size:,} bytes · {os.path.dirname(path)}")
        except OSError:
            self.lbl_file_meta.configure(text=os.path.dirname(path))

    def choose_output_dir(self):
        path = filedialog.askdirectory(title=self.t("choose_output_title"))
        if path:
            self.output_dir.set(path)

    # ---------- 분할 단위 선택 ----------

    def _sync_value_var(self):
        mode = self.split_mode.get()
        var = self._value_vars[mode]
        if self.entry_value.get() != var.get():
            self.entry_value.delete(0, "end")
            self.entry_value.insert(0, var.get())

    def _on_entry_value_changed(self, _event=None):
        mode = self.split_mode.get()
        self._value_vars[mode].set(self.entry_value.get())
        self._update_estimate()

    def _on_mode_changed(self):
        mode = self.split_mode.get()
        self.tags_row.pack() if mode == "chars" else self.tags_row.pack_forget()
        self._sync_value_var()
        self._update_unit_and_hint()
        self._update_estimate()
        self.entry_value.unbind("<KeyRelease>")
        self.entry_value.bind("<KeyRelease>", self._on_entry_value_changed)

    def _apply_quick_value(self, value):
        self.chunk_size.set(value)
        self._sync_value_var()
        self._update_estimate()

    def _update_unit_and_hint(self):
        mode = self.split_mode.get()
        unit_key = {"size": "split_mode_size_unit", "count": "split_mode_count_unit", "chars": "split_mode_chars_unit"}[mode]
        hint_key = {"size": "split_mode_size_hint", "count": "split_mode_count_hint", "chars": "split_mode_chars_hint"}[mode]
        self.lbl_unit.configure(text=self.t(unit_key))
        self.lbl_hint.configure(text=self.t(hint_key))

    def _resolve_chunker(self, path):
        """현재 선택된 분할 단위를 text -> [(start, end), ...] 콜러블(또는 정수
        글자수 - splitter.resolve_chunker가 둘 다 받는다)로 환산. split_window.py와 동일한 로직."""
        mode = self.split_mode.get()

        if mode == "chars":
            try:
                chunk_size = int(self.chunk_size.get().strip())
                if chunk_size <= 0:
                    raise ValueError
            except ValueError:
                return None, "err_bad_size"
            return chunk_size, None

        try:
            full_text = read_plain_text(path)
        except Exception:
            return None, "err_bad_size"
        total_chars = len(full_text)
        if total_chars == 0:
            return None, "err_bad_size"

        if mode == "count":
            try:
                count = int(self.chunk_count.get().strip())
                if count <= 0:
                    raise ValueError
            except ValueError:
                return None, "err_bad_count"
            return (lambda text: splitter.compute_chunks_by_count(text, count)), None

        try:
            kb = float(self.chunk_kb.get().strip())
            if kb <= 0:
                raise ValueError
        except ValueError:
            return None, "err_bad_kb"
        byte_len = len(full_text.encode("utf-8"))
        avg_bytes_per_char = byte_len / total_chars
        chunk_size = max(1, int((kb * 1024) / avg_bytes_per_char))
        return chunk_size, None

    def _validate_file_and_size(self, silent=False):
        path = self.file_path.get().strip()

        if not path or not os.path.isfile(path):
            if not silent:
                dialogs.show_error(self, self.t("err_title"), self.t("err_no_file"))
            return None
        ext = os.path.splitext(path)[1].lower()
        if ext == ".hwp":
            if not silent:
                dialogs.show_warning(self, self.t("hwp_title"), self.t("hwp_body"))
            return None
        if ext not in SUPPORTED_EXTS:
            if not silent:
                dialogs.show_warning(self, self.t("unsupported_title"), self.t("unsupported_body", ext=ext))
            return None

        chunker, err_key = self._resolve_chunker(path)
        if chunker is None:
            if not silent:
                dialogs.show_error(self, self.t("err_title"), self.t(err_key))
            return None
        return path, chunker

    # ---------- 예상 결과 ----------

    def _update_estimate(self):
        validated = self._validate_file_and_size(silent=True)
        if validated is None:
            self._est_files_val.configure(text="—")
            self._est_chars_val.configure(text="—")
            return
        path, chunker = validated
        try:
            text = read_plain_text(path)
            chunks = splitter.resolve_chunker(chunker)(text)
        except Exception:
            self._est_files_val.configure(text="—")
            self._est_chars_val.configure(text="—")
            return
        if not chunks:
            self._est_files_val.configure(text="0")
            self._est_chars_val.configure(text="—")
            return
        avg = sum(e - s for s, e in chunks) // len(chunks)
        self._est_files_val.configure(text=str(len(chunks)))
        self._est_chars_val.configure(text=f"{avg:,}")

    # ---------- 미리보기(항상 열려있는 오른쪽 패널) ----------

    def refresh_preview(self):
        validated = self._validate_file_and_size()
        if validated is None:
            return
        path, chunker = validated
        try:
            text = read_plain_text(path)
            previews, truncated, total_count = splitter.build_boundary_previews(text, chunker)
        except Exception as e:
            dialogs.show_error(self, self.t("error_title"), self.t("error_body", err=e))
            return
        self._render_preview(previews, truncated, total_count)
        self._update_estimate()

    def _render_preview(self, previews, truncated, total_count):
        self.tag_chunk_count.configure(text=self.t("split_preview_total_label", n=total_count))
        tw = self.preview_text
        tw.configure(state="normal")
        tw.delete("1.0", "end")

        if truncated:
            tw.insert("end", self.t("split_preview_truncated_note", shown=len(previews), total=total_count) + "\n\n")

        for p in previews:
            tw.insert(
                "end",
                self.t("split_preview_chunk_label", index=p["index"], start=p["start"], end=p["end"], length=p["length"]) + "\n",
                "chunk_label",
            )
            tw.insert("end", p["tail"] + "\n", "body")
            if p["is_last"]:
                tw.insert("end", self.t("split_preview_last_label") + "\n\n")
            else:
                tw.insert("end", "\n" + self.t("split_preview_boundary_label") + "\n\n", "boundary")
                tw.insert("end", p["next_head"] + " …\n\n", "body")

        tw.configure(state="disabled")

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

    def _open_output_folder(self):
        out_dir = self.output_dir.get().strip()
        if out_dir and os.path.isdir(out_dir):
            os.startfile(out_dir)

    def _update_last_run(self, text):
        self.lbl_last_run.configure(text=text or "")

    # ---------- 실행 ----------

    def run_split(self):
        validated = self._validate_file_and_size()
        if validated is None:
            return
        path, chunker = validated
        out_dir = self.output_dir.get().strip()

        if not out_dir:
            dialogs.show_error(self, self.t("err_title"), self.t("err_no_outdir"))
            return

        os.makedirs(out_dir, exist_ok=True)

        self.log_line(self.t("log_start", path=path))
        self.log_line(self._mode_log_note(chunker))
        self._set_running(True)

        thread = threading.Thread(target=self._do_split, args=(path, chunker, out_dir), daemon=True)
        thread.start()

    def _mode_log_note(self, chunker):
        mode = self.split_mode.get()
        if mode == "size":
            return self.t("log_kb_note", kb=self.chunk_kb.get().strip(), n=chunker)
        if mode == "count":
            return self.t("log_count_note", count=self.chunk_count.get().strip())
        return self.t("log_size_note", n=chunker)

    def _set_running(self, running):
        state = "disabled" if running else "normal"
        for widget in (self.btn_run, self.btn_refresh, self.btn_file, self.btn_output):
            widget.configure(state=state)
        for _value, seg_btn in self.seg_mode._buttons:
            seg_btn.configure(state=state)
        self.entry_value.configure(state="disabled" if running else "normal")

    def _do_split(self, path, chunker, out_dir):
        ext = os.path.splitext(path)[1].lower()
        created = []
        try:
            if ext == ".txt":
                out_paths, encoding = split_txt_file(path, chunker, out_dir)
                self.after(0, self.log_line, self.t("log_detected_encoding", enc=encoding))
            elif ext == ".docx":
                out_paths = split_docx_file(path, chunker, out_dir)
            elif ext == ".hwpx":
                out_paths = split_hwpx_file(path, chunker, out_dir)
            else:
                raise ValueError(self.t("unsupported_body", ext=ext))
            created = out_paths

            for p in out_paths:
                try:
                    char_count = len(read_plain_text(p))
                except Exception:
                    char_count = "?"
                byte_size = os.path.getsize(p)
                self.after(0, self.log_line, self.t("log_generated", path=p, chars=char_count, size=f"{byte_size:,}"))
            self.after(0, self.log_line, self.t("log_done", n=len(out_paths)))
            self.after(0, self._update_last_run, self.t("log_done", n=len(out_paths)))
            self.after(0, lambda: dialogs.show_info(self, self.t("done_title"), self.t("done_body", n=len(out_paths), out=out_dir)))
            self.after(0, self._record_activity, path, len(out_paths))
        except Exception as e:
            self.after(0, self.log_line, self.t("log_error", err=e))
            self.after(0, lambda: dialogs.show_error(self, self.t("error_title"), self.t("error_body", err=e)))
        finally:
            self.after(0, self._set_running, False)

    def _record_activity(self, path, n):
        try:
            import activity_log
            activity_log.record(self.t("run_button"), os.path.basename(path), f"{n}개 파일")
        except Exception:
            pass

    # ---------- 드래그앤드롭 / 홈에서 넘어올 때 ----------

    def load_file_from_outside(self, path):
        """홈 화면 드롭존 등 다른 곳에서 파일을 받았을 때."""
        self._load_file(path)

    def on_show(self):
        pass
