# Cortuni

A Windows desktop tool for splitting, merging, and batch-editing `.txt` / `.docx` / `.hwpx` documents without cutting sentences in half.

## Features

- **Home** — drop a file to jump straight in (one file → Split, several → Merge), quick-access cards, and a log of recent actions.
- **Split** a document by character count, target file size (KB), or target file count. Splits always snap forward to the nearest sentence boundary, so no sentence is ever cut mid-way; the "by file count" mode recomputes the target size per remaining piece so the count matches the request exactly in the normal case. The output pieces can be saved as a different format than the source (e.g. split one `.hwpx` into 10 `.docx` files).
- **Merge** multiple documents into one, in a chosen order, with optional per-file titles and an optional page break between files (`.docx`/`.hwpx` only). The merged result can be saved as a different format than the inputs (e.g. merge 20 `.txt` files into one `.hwpx`) — just pick that extension in the save dialog.
<!-- Terms (names/honorifics + particle correction) is disabled and hidden from the UI — little use. The code (terms_page.py, term_dict.py, rename_apply.py, josa.py) is still in the repo, commented out, in case it comes back. -->
- **Batch rename** many files at once via a pattern (`{name}`/`{n:02}`/`{ext}`/`{date}`), inline editing, or CSV import/export.
- **Convert** between `.txt`, `.docx`, and `.hwpx`, with a per-file status column showing what's actually convertible.
- Korean/English UI, light/dark/system theme, selectable content font.

Supported formats: `.txt`, `.docx`, `.hwpx`. Legacy `.hwp` (binary) is not supported — save it as `.hwpx` from Hangul first ([File > Save As] > HWPX).

## For users

Download the latest `Cortuni.zip` from the [Releases](../../releases) page, extract it, and run `Cortuni.exe` inside the extracted folder — no installation or Python required. (It ships as a folder rather than a single `.exe` because unsigned single-file PyInstaller executables get flagged as malware by some antivirus software more often than the folder form does.)

## For developers

### Project layout

```
src/        application source (flat modules, main.py is the entry point)
assets/     icon.ico / icon.png, icons/ (multi-resolution 16-256px taskbar/titlebar icons), and fonts/ (bundled Barlow / Barlow Condensed)
```

`main.py` is a single persistent window (`App`) with a left `Sidebar` and a content area holding one `*_page.py` `Frame` per feature, swapped via `App.navigate(key)`. All the actual split/merge/convert/batch-rename logic lives in plain modules with no UI code (`splitter.py`, `merge_apply.py`, `convert_apply.py`, `batch_rename_apply.py`, plus their `*_handler.py`/`adapters.py` format glue) — the `*_page.py` files only build widgets and call into those. Split and Merge can output a different format than the source: both always run the actual split/merge in the source format first, then hand off to `convert_apply.CONVERTERS` to produce the requested extension — see `split_page.py`'s `_convert_outputs` and `merge_apply.merge_files`.

The visual design ("Industry" — flat, square-cornered, hairline-bordered, steel-blue accent) lives in `theme.py` (color/spacing tokens + the `ttk.Style` built from them, with light/dark/system switching) and `widgets.py` (`BlueprintFrame` — the hairline-plus-corner-marks card/panel primitive; `Segmented` — the pill-style single-choice control used instead of radio buttons). `dialogs.py` replaces `tkinter.messagebox` (which can't be restyled at all) with themed equivalents. `fonts.py` handles two independent things: the user-selectable content font (`apply_font_family`, unchanged since 1.x) and the fixed brand chrome font (`load_brand_fonts`, registers the bundled Barlow files with Windows at runtime via `AddFontResourceExW`). `winchrome.py` repaints the OS-drawn title bar (the minimize/maximize/close strip tkinter can't touch directly) via undocumented-but-stable DWM window attributes, so it follows the app's light/dark/system theme instead of staying stuck on the OS default; `main.App.refresh_theme()` calls it on every theme change.

### Setup

```
pip install -r requirements.txt
```

Requires Python 3.9+ with Tk (standard on the python.org Windows installer). Drag-and-drop on the Home page needs `tkinterdnd2`, which ships its own native component — nothing extra to install manually, but see the build note below.

### Run from source

```
python src/main.py
```

### Run the self-test

Exercises the split/merge/rename/convert logic end-to-end (no GUI needed):

```
python src/selftest.py
```

### Build the Windows exe

```
pyinstaller --noconfirm Cortuni.spec
```

`Cortuni.spec` is the tracked, authoritative build config (originally generated from a `pyinstaller --onefile --windowed --name Cortuni --icon assets/icon.ico --add-data ... --collect-data docx --collect-data hwpx --collect-all tkinterdnd2 src/main.py` command, then hand-edited — see below). `--collect-data docx`/`--collect-data hwpx` pick up non-Python template/skeleton files (`python-docx`'s default `.docx` template, `python-hwpx`'s `Skeleton.hwpx`) that PyInstaller won't bundle automatically; `--collect-all tkinterdnd2` does the same for its native `tkdnd` component; the two `--add-data` flags for `assets/icons`/`assets/fonts` ship the window/taskbar icon set and brand fonts that `main.py` loads via `resource_path()`.

The build is **onedir**, not `--onefile`: the output is a `dist/Cortuni/` folder (zip it for distribution) rather than a single exe. An unsigned single-file PyInstaller exe self-extracts to a temp folder on every launch, which looks enough like dropper/loader behavior that some antivirus engines flag it as malware even though nothing's wrong with it; shipping the already-extracted folder avoids that specific false-positive path. This doesn't replace code signing — that's the only real fix for Windows SmartScreen's reputation warning on a brand-new unsigned binary — but it does help with heuristic AV detections.

### Notes on the sentence-boundary logic

`src/splitter.py` treats `. ! ?` and their full-width CJK equivalents `。！？` (plus a following closing quote/bracket) as sentence ends. If you add support for another language's punctuation, extend `_TERMINATORS`/`_CLOSERS` there — `compute_chunks()`/`compute_chunks_by_count()` are the shared functions behind split, preview, and all three split modes (by size/count/characters), so a fix there applies everywhere at once.

### Notes on the design system

Colors, spacing, and font-family names are tokens in `theme.py` (`LIGHT_TOKENS`/`DARK_TOKENS`) — never hardcode a hex or a font name in a page file. Any raw `tk` widget a page creates directly (a `scrolledtext.ScrolledText` log, a `tk.Text` preview pane, a `tk.Listbox`) doesn't follow `ttk.Style` automatically and must be recolored by hand in that page's `refresh_theme()`; every page that has one already does this, so copy an existing one rather than re-deriving it. `BlueprintFrame`/`Segmented` instances register themselves with `theme.subscribe()` and repaint on their own — but if you give a `BlueprintFrame` a fixed `tint=` at construction (rather than leaving it `None` to just track the ground color), that tint is a snapshot, not a live reference: recompute it from `theme.tokens()` and call `.refresh_theme()` on the frame explicitly inside the *page's* `refresh_theme()`, the same way `split_page.py`'s estimate card and `batch_page.py`'s pattern card do — this bit `home_page.py`'s drop zone once already.
