"""분할 창.

문장이 잘리지 않는 글자수 기준으로 파일 하나를 여러 개로 나눈다.
지원 형식: .txt, .docx, .hwpx
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from formats import SUPPORTED_EXTS
from txt_handler import split_txt_file
from docx_handler import split_docx_file
from hwpx_handler import split_hwpx_file
from merge_apply import read_plain_text
import splitter
import fonts


class SplitWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master

        self.file_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.split_mode = tk.StringVar(value="chars")
        self.chunk_kb = tk.StringVar(value="100")
        self.chunk_count = tk.StringVar(value="5")
        self.chunk_size = tk.StringVar(value="3000")

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
        self.geometry("640x520")
        pad = {"padx": 10, "pady": 6}

        frm_file = ttk.Frame(self)
        frm_file.pack(fill="x", **pad)
        self.lbl_file = ttk.Label(frm_file, text="")
        self.lbl_file.pack(side="left")
        ttk.Entry(frm_file, textvariable=self.file_path).pack(side="left", fill="x", expand=True, padx=6)
        self.btn_file = ttk.Button(frm_file, text="", command=self.choose_file)
        self.btn_file.pack(side="left")

        frm_out = ttk.Frame(self)
        frm_out.pack(fill="x", **pad)
        self.lbl_output = ttk.Label(frm_out, text="")
        self.lbl_output.pack(side="left")
        ttk.Entry(frm_out, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=6)
        self.btn_output = ttk.Button(frm_out, text="", command=self.choose_output_dir)
        self.btn_output.pack(side="left")

        self.frm_mode = ttk.LabelFrame(self)
        self.frm_mode.pack(fill="x", **pad)

        row_size = ttk.Frame(self.frm_mode)
        row_size.pack(fill="x", padx=6, pady=(6, 2))
        self.radio_size = ttk.Radiobutton(
            row_size, text="", variable=self.split_mode, value="size", command=self._on_mode_changed
        )
        self.radio_size.pack(side="left")
        self.entry_kb = ttk.Entry(row_size, textvariable=self.chunk_kb, width=10)
        self.entry_kb.pack(side="left", padx=6)
        self.lbl_kb_unit = ttk.Label(row_size, text="")
        self.lbl_kb_unit.pack(side="left")

        row_count = ttk.Frame(self.frm_mode)
        row_count.pack(fill="x", padx=6, pady=2)
        self.radio_count = ttk.Radiobutton(
            row_count, text="", variable=self.split_mode, value="count", command=self._on_mode_changed
        )
        self.radio_count.pack(side="left")
        self.entry_count = ttk.Entry(row_count, textvariable=self.chunk_count, width=10)
        self.entry_count.pack(side="left", padx=6)
        self.lbl_count_unit = ttk.Label(row_count, text="")
        self.lbl_count_unit.pack(side="left")

        row_chars = ttk.Frame(self.frm_mode)
        row_chars.pack(fill="x", padx=6, pady=2)
        self.radio_chars = ttk.Radiobutton(
            row_chars, text="", variable=self.split_mode, value="chars", command=self._on_mode_changed
        )
        self.radio_chars.pack(side="left")
        self.entry_chars = ttk.Entry(row_chars, textvariable=self.chunk_size, width=10)
        self.entry_chars.pack(side="left", padx=6)
        self.lbl_chars_unit = ttk.Label(row_chars, text="")
        self.lbl_chars_unit.pack(side="left")

        self.lbl_hint = ttk.Label(self.frm_mode, text="", foreground="#555555", wraplength=580, justify="left")
        self.lbl_hint.pack(anchor="w", padx=6, pady=(2, 6))

        self._on_mode_changed()

        frm_run = ttk.Frame(self)
        frm_run.pack(pady=10)
        self.btn_preview = ttk.Button(frm_run, text="", command=self.on_preview)
        self.btn_preview.pack(side="left", padx=4)
        self.btn_run = ttk.Button(frm_run, text="", command=self.run_split)
        self.btn_run.pack(side="left", padx=4)

        self.log = scrolledtext.ScrolledText(self, height=16, state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def apply_language(self):
        self.title(self.t("split_window_title"))
        self.lbl_file.configure(text=self.t("file_label"))
        self.btn_file.configure(text=self.t("file_button"))
        self.lbl_output.configure(text=self.t("output_label"))
        self.btn_output.configure(text=self.t("output_button"))
        self.frm_mode.configure(text=self.t("split_mode_section_label"))
        self.radio_size.configure(text=self.t("split_mode_size_label"))
        self.lbl_kb_unit.configure(text=self.t("split_mode_size_unit"))
        self.radio_count.configure(text=self.t("split_mode_count_label"))
        self.lbl_count_unit.configure(text=self.t("split_mode_count_unit"))
        self.radio_chars.configure(text=self.t("split_mode_chars_label"))
        self.lbl_chars_unit.configure(text=self.t("split_mode_chars_unit"))
        self._update_hint()
        self.btn_preview.configure(text=self.t("merge_preview_button"))
        self.btn_run.configure(text=self.t("run_button"))

    def log_line(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

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
            suffix = self.t("outdir_suffix")
            self.output_dir.set(os.path.join(os.path.dirname(path), f"{base}{suffix}"))

    def choose_output_dir(self):
        path = filedialog.askdirectory(title=self.t("choose_output_title"))
        if path:
            self.output_dir.set(path)

    # ---------- 분할 단위 선택 ----------

    def _on_mode_changed(self):
        mode = self.split_mode.get()
        self.entry_kb.configure(state="normal" if mode == "size" else "disabled")
        self.entry_count.configure(state="normal" if mode == "count" else "disabled")
        self.entry_chars.configure(state="normal" if mode == "chars" else "disabled")
        self._update_hint()

    def _update_hint(self):
        key = {
            "size": "split_mode_size_hint",
            "count": "split_mode_count_hint",
            "chars": "split_mode_chars_hint",
        }[self.split_mode.get()]
        self.lbl_hint.configure(text=self.t(key))

    def _resolve_chunker(self, path):
        """현재 선택된 분할 단위를 text -> [(start, end), ...] 콜러블(또는 정수
        글자수 - splitter.resolve_chunker가 둘 다 받는다)로 환산.

        - 글자수 모드는 입력값을 그대로 정수 chunk_size로 쓴다.
        - 크기(KB) 모드는 문서 전체 글자수 대비 바이트 비율로 근사한 글자수를
          정수 chunk_size로 환산한다(문서 형식/서식에 따라 실제 파일 크기는
          지정한 값과 다를 수 있다).
        - 파일 수 모드는 compute_chunks_by_count를 쓰는 콜러블을 반환한다.
          이 함수는 조각을 만들 때마다 목표 크기를 다시 계산해 개수가
          목표에 최대한 맞도록 보정하므로(문장은 여전히 끊기지 않음),
          텍스트가 너무 짧아 그만큼 나눌 문장 경계가 없는 경우가 아니면
          실제로 정확히 그 개수가 나온다.

        반환: (chunker, None) 또는 (None, 오류메시지 번역 키).
        """
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

        # mode == "size"
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

    def _validate_file_and_size(self):
        """(path, chunker)를 반환하거나, 문제가 있으면 오류창을 띄우고 None을 반환."""
        path = self.file_path.get().strip()

        if not path or not os.path.isfile(path):
            messagebox.showerror(self.t("err_title"), self.t("err_no_file"))
            return None
        ext = os.path.splitext(path)[1].lower()
        if ext == ".hwp":
            messagebox.showwarning(self.t("hwp_title"), self.t("hwp_body"))
            return None
        if ext not in SUPPORTED_EXTS:
            messagebox.showwarning(self.t("unsupported_title"), self.t("unsupported_body", ext=ext))
            return None

        chunker, err_key = self._resolve_chunker(path)
        if chunker is None:
            messagebox.showerror(self.t("err_title"), self.t(err_key))
            return None
        return path, chunker

    def on_preview(self):
        validated = self._validate_file_and_size()
        if validated is None:
            return
        path, chunker = validated
        try:
            text = read_plain_text(path)
            previews, truncated, total_count = splitter.build_boundary_previews(text, chunker)
        except Exception as e:
            messagebox.showerror(self.t("error_title"), self.t("error_body", err=e))
            return
        SplitPreviewWindow(self, previews, truncated, total_count)

    def run_split(self):
        validated = self._validate_file_and_size()
        if validated is None:
            return
        path, chunker = validated
        out_dir = self.output_dir.get().strip()

        if not out_dir:
            messagebox.showerror(self.t("err_title"), self.t("err_no_outdir"))
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
        for btn in (
            self.btn_run, self.btn_preview, self.btn_file, self.btn_output,
            self.radio_size, self.radio_count, self.radio_chars,
        ):
            btn.configure(state=state)
        if running:
            self.entry_kb.configure(state="disabled")
            self.entry_count.configure(state="disabled")
            self.entry_chars.configure(state="disabled")
        else:
            self._on_mode_changed()

    def _do_split(self, path, chunker, out_dir):
        ext = os.path.splitext(path)[1].lower()
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

            for p in out_paths:
                try:
                    char_count = len(read_plain_text(p))
                except Exception:
                    char_count = "?"
                byte_size = os.path.getsize(p)
                self.after(
                    0, self.log_line,
                    self.t("log_generated", path=p, chars=char_count, size=f"{byte_size:,}"),
                )
            self.after(0, self.log_line, self.t("log_done", n=len(out_paths)))
            self.after(0, lambda: messagebox.showinfo(self.t("done_title"), self.t("done_body", n=len(out_paths), out=out_dir)))
        except Exception as e:
            self.after(0, self.log_line, self.t("log_error", err=e))
            self.after(0, lambda: messagebox.showerror(self.t("error_title"), self.t("error_body", err=e)))
        finally:
            self.after(0, self._set_running, False)


class SplitPreviewWindow(tk.Toplevel):
    def __init__(self, master_split_window, previews, truncated, total_count):
        super().__init__(master_split_window)
        self.master_split_window = master_split_window

        def t(key, **kwargs):
            return master_split_window.t(key, **kwargs)

        self.title(t("split_preview_window_title"))
        self.geometry("640x600")
        try:
            self.iconphoto(True, master_split_window.master_app._icon_image)
        except Exception:
            pass

        ttk.Label(self, text=t("split_preview_total_label", n=total_count)).pack(anchor="w", padx=10, pady=(10, 0))
        if truncated:
            ttk.Label(
                self,
                text=t("split_preview_truncated_note", shown=len(previews), total=total_count),
                foreground="#a05a00",
            ).pack(anchor="w", padx=10)

        text_widget = scrolledtext.ScrolledText(self, wrap="word", state="normal")
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        text_widget.tag_configure("chunk_label", font=(fonts.current_family(), 10, "bold"))
        text_widget.tag_configure("boundary", foreground="#a05a00", justify="center")
        text_widget.tag_configure("body", foreground="#333333")

        for p in previews:
            text_widget.insert(
                "end",
                t("split_preview_chunk_label", index=p["index"], start=p["start"], end=p["end"], length=p["length"])
                + "\n",
                "chunk_label",
            )
            text_widget.insert("end", p["tail"] + "\n", "body")
            if p["is_last"]:
                text_widget.insert("end", t("split_preview_last_label") + "\n\n")
            else:
                text_widget.insert("end", "\n" + t("split_preview_boundary_label") + "\n\n", "boundary")
                text_widget.insert("end", p["next_head"] + " …\n\n", "body")

        text_widget.configure(state="disabled")

        ttk.Button(self, text=t("merge_preview_close_button"), command=self.destroy).pack(pady=(0, 10))
