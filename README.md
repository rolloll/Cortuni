# Coriuni

A Windows desktop tool for splitting, merging, and batch-editing `.txt` / `.docx` / `.hwpx` documents without cutting sentences in half.

## Features

- **Split** a document by character count, target file size (KB), or target file count. Splits always snap forward to the nearest sentence boundary, so no sentence is ever cut mid-way.
- **Merge** multiple documents into one, in a chosen order, with optional per-file titles.
- **Batch rename** many files at once via inline editing or CSV import/export.
- **Rename honorifics/terms** inside document text with Korean particle (조사) correction, so replacements like "형" → "언니" automatically fix the following "은/는", "을/를", etc.
- **Convert** between `.txt`, `.docx`, and `.hwpx`.
- Korean/English UI, selectable UI font.

Supported formats: `.txt`, `.docx`, `.hwpx`. Legacy `.hwp` (binary) is not supported — save it as `.hwpx` from Hangul first ([File > Save As] > HWPX).

## For users

Download the latest `Coriuni.exe` from the [Releases](../../releases) page and run it — no installation or Python required.

## For developers

### Project layout

```
src/        application source (flat modules, main.py is the entry point)
assets/     icon.ico / icon.png bundled into the exe
```

### Setup

```
pip install -r requirements.txt
```

Requires Python 3.9+ with Tk (standard on the python.org Windows installer).

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
pyinstaller --noconfirm --onefile --windowed --name Coriuni ^
  --icon assets/icon.ico ^
  --add-data "assets/icon.png;assets" ^
  --collect-data docx ^
  --collect-data hwpx ^
  src/main.py
```

`--collect-data docx` and `--collect-data hwpx` are required — both libraries ship non-Python template/skeleton files (`python-docx`'s default `.docx` template, `python-hwpx`'s `Skeleton.hwpx`) that PyInstaller won't pick up automatically. The output is `dist/Coriuni.exe`.

### Notes on the sentence-boundary logic

`src/splitter.py` treats `. ! ?` and their full-width CJK equivalents `。！？` (plus a following closing quote/bracket) as sentence ends. If you add support for another language's punctuation, extend `_TERMINATORS`/`_CLOSERS` there — `compute_chunks()` is the single shared function behind split, preview, and all three split modes (by size/count/characters), so a fix there applies everywhere at once.
