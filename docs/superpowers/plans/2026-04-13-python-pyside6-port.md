# Python PySide6 Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the current Electron-based media grid compositor to a Python + PySide6 portable desktop application that keeps width-based slicing, drag-to-reorder staging, video quality presets, JPG image export, and bundled ffmpeg/ffprobe support.

**Architecture:** Keep the migration intentionally layered. First port the pure ordering/layout/media logic into small testable Python modules, then build a PySide6 Widgets shell around those modules, and finally package the app as a PyInstaller `onedir` bundle with bundled ffmpeg binaries for macOS and Windows. The UI should preserve the current left-toolbench/right-stage structure, but the business logic must remain isolated so the application can be tested without launching a GUI.

**Tech Stack:** Python 3.11+, PySide6 Qt Widgets, PyInstaller `onedir`, `pytest`, `pytest-qt`, native `ffmpeg` / `ffprobe`

---

## File Map

- `pyproject.toml`: Python packaging metadata, runtime dependencies, dev dependencies, and test configuration.
- `pyapp/main.py`: Python entrypoint for development and packaged execution.
- `pyapp/app.py`: application bootstrap, resource initialization, and top-level window creation.
- `pyapp/core/order.py`: default order, swap/reorder helpers, order summary formatting.
- `pyapp/core/layout.py`: slice width math, grid math, validation, and ffmpeg filter graph generation.
- `pyapp/core/media.py`: ffprobe probe helpers, media type detection, metadata normalization.
- `pyapp/core/export.py`: ffmpeg command builder, export runner, progress parsing, cancellation.
- `pyapp/core/paths.py`: packaged vs development resource path resolution for ffmpeg binaries.
- `pyapp/core/app_state.py`: validation, output path suggestion, and media-aware label/state helpers.
- `pyapp/ui/main_window.py`: main window, toolbench layout, stage panel, progress, logs, and signals.
- `pyapp/ui/stage_grid.py`: drag-and-drop stage cards and swap behavior for the right-side grid.
- `pyapp/ui/theme.qss`: Qt stylesheet that keeps the current monochrome Figma-inspired look.
- `pyapp/resources/bin/<platform>/`: bundled ffmpeg/ffprobe binaries by platform.
- `tests/test_*.py`: Python unit tests for pure logic, state helpers, media probing, export command generation, resource resolution, and smoke coverage.
- `tests/test_paths.py`: checks that packaged and development resource resolution work for bundled ffmpeg binaries.
- `pyinstaller.spec`: one-folder packaging entry for macOS and Windows release builds.
- `README.md`: Python setup, run, test, and packaging instructions.

### Task 1: Bootstrap the Python project skeleton

**Files:**
- Create `pyproject.toml`
- Create `pyapp/__init__.py`
- Create `pyapp/main.py`
- Create `pyapp/app.py`
- Create `tests/test_bootstrap.py`

- [ ] **Step 1: Write the failing test**

Create a bootstrap test that imports the Python entrypoint and app bootstrap layer and asserts the package does not exist yet. Keep the test narrow, for example by checking that `import pyapp.main` and `import pyapp.app` currently fail.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_bootstrap.py -q
```

Expected: fail with `ModuleNotFoundError` because the Python package has not been created yet.

- [ ] **Step 3: Write minimal implementation**

Add a minimal Python package layout and entrypoint:

- `pyapp/main.py` should call a `main()` function and start the Qt app.
- `pyapp/app.py` should create the application object and main window placeholder.
- `pyproject.toml` should declare `PySide6`, `pytest`, `pytest-qt`, and `PyInstaller`.

Keep the first version intentionally tiny. Do not implement business logic in this task.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_bootstrap.py -q
python -m py_compile pyapp/main.py pyapp/app.py
```

Expected: the bootstrap test passes and both Python files compile cleanly.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml pyapp/__init__.py pyapp/main.py pyapp/app.py tests/test_bootstrap.py
git commit -m "feat: bootstrap python pyside6 app"
```

### Task 2: Port the pure order and layout logic

**Files:**
- Create `pyapp/core/order.py`
- Create `pyapp/core/layout.py`
- Create `tests/test_order.py`
- Create `tests/test_layout.py`

- [ ] **Step 1: Write the failing tests**

Write tests that lock in the current behavior:

- default order is `0..N-1`
- swapping two positions preserves original slice numbers
- order summary renders as `#1 -> #3 -> #2`
- slice widths distribute remainder pixels left to right
- single-slice input does not emit a split label
- explicit `slice_order` changes the final `xstack` input order
- invalid `slice_order` length, duplicates, or out-of-range values raise clear errors

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_order.py tests/test_layout.py -q
```

Expected: fail because the new Python modules do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implement in `pyapp/core/order.py`:

- `build_default_order(slice_count)`
- `normalize_order(order, slice_count)`
- `swap_order(order, from_index, to_index)`
- `is_default_order(order)`
- `format_order_summary(order)`

Implement in `pyapp/core/layout.py`:

- slice width distribution
- slice plan creation
- grid validation
- output cell size derivation
- `build_filter_graph(..., slice_order=None)`

Keep the same behavior as the current app: width-based slicing, `cover / contain / stretch`, and explicit `slice_order` support.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_order.py tests/test_layout.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyapp/core/order.py pyapp/core/layout.py tests/test_order.py tests/test_layout.py
git commit -m "feat: port python order and layout logic"
```

### Task 3: Port media probing and export command construction

**Files:**
- Create `pyapp/core/paths.py`
- Create `pyapp/core/media.py`
- Create `pyapp/core/export.py`
- Create `tests/test_media.py`
- Create `tests/test_export.py`

- [ ] **Step 1: Write the failing tests**

Write tests for:

- detecting video vs image from file extension
- parsing `ffprobe` JSON into normalized metadata
- resolving bundled ffmpeg/ffprobe paths versus development PATH lookup
- building video export commands for lossless/high/medium quality
- building a single-frame JPG export command for images
- parsing ffmpeg progress lines into percentages
- propagating cancellation and subprocess errors

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_media.py tests/test_export.py -q
```

Expected: fail because the media/export modules are missing.

- [ ] **Step 3: Write minimal implementation**

Implement Python subprocess-based helpers that mirror the current Electron behavior:

- probe media with `ffprobe`
- build export commands with `ffmpeg`
- keep audio copy-first behavior for video
- export a single JPG frame for images
- accept `slice_order` and pass it into the filter graph
- use bundled ffmpeg binaries when available

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_media.py tests/test_export.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyapp/core/paths.py pyapp/core/media.py pyapp/core/export.py tests/test_media.py tests/test_export.py
git commit -m "feat: add python media export engine"
```

### Task 4: Add app state helpers for validation and output paths

**Files:**
- Create `pyapp/core/app_state.py`
- Create `tests/test_app_state.py`
- Modify `pyapp/app.py`

- [ ] **Step 1: Write the failing tests**

Cover the state rules that the UI needs:

- validation rejects `rows × cols != slice_count`
- validation rejects odd output dimensions
- validation rejects unsupported aspect ratio combinations
- output path suggestions preserve the source basename and append the current slice/grid suffix
- media-aware text changes correctly for video versus image
- resetting order restores the default sequence

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_app_state.py -q
```

Expected: fail because the state helpers do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Move the reusable validation and suggestion logic into `pyapp/core/app_state.py` so the UI can stay thin. Keep the functions pure where possible.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_app_state.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyapp/core/app_state.py tests/test_app_state.py pyapp/app.py
git commit -m "feat: add python app state helpers"
```

### Task 5: Build the PySide6 toolbench UI and drag stage

**Files:**
- Create `pyapp/ui/main_window.py`
- Create `pyapp/ui/stage_grid.py`
- Create `pyapp/ui/theme.qss`
- Create `tests/test_main_window_smoke.py`
- Modify `pyapp/app.py`

- [ ] **Step 1: Write the failing smoke test**

Write a smoke test that instantiates the main window offscreen and checks that the core UI pieces exist:

- left toolbench sections
- right stage grid
- order summary
- progress and log areas
- reset order action

Use `pytest-qt` or an offscreen `QApplication` harness so the test can run headlessly.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_main_window_smoke.py -q
```

Expected: fail because the Qt window classes do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implement the Qt UI:

- `QMainWindow` with a `QSplitter`
- left control groups for `Source / Slice / Output / Export`
- a right-side single draggable stage
- path display that wraps instead of truncating
- reset-order button
- media-aware button labels and validation text
- drag/drop swapping that preserves original numbering

Keep UI behavior thin and route all logic through the pure helpers from earlier tasks.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_main_window_smoke.py -q
python -m pyapp.main
```

Expected: the smoke test passes and the app window opens in manual testing.

- [ ] **Step 5: Commit**

```bash
git add pyapp/ui/main_window.py pyapp/ui/stage_grid.py pyapp/ui/theme.qss tests/test_main_window_smoke.py pyapp/app.py
git commit -m "feat: build python pyside6 ui shell"
```

### Task 6: Package the portable app and update docs

**Files:**
- Create `pyinstaller.spec`
- Create `pyapp/resources/bin/darwin/`
- Create `pyapp/resources/bin/win32/`
- Modify `README.md`
- Modify any build scripts needed for packaging

- [ ] **Step 1: Write the failing packaging check**

Add a packaging smoke test or build expectation that exercises resource resolution and bundle entrypoints. The goal is to make sure the app can discover bundled ffmpeg binaries and start from the packaged path.

- [ ] **Step 2: Run the check to verify it fails**

Run:

```bash
pytest tests/test_paths.py -q
```

Expected: fail if the resource path resolver or bundle assumptions are not in place yet.

- [ ] **Step 3: Write minimal implementation**

Implement:

- bundled ffmpeg/ffprobe resource lookup
- `PyInstaller --onedir` spec
- macOS packaging command
- Windows packaging command
- README updates for install, run, test, and packaging

Keep the Electron files in the repo until the Python build is verified, then decide whether to retire or archive them separately.

- [ ] **Step 4: Run final verification**

Run:

```bash
pytest -q
python -m PyInstaller pyinstaller.spec
```

Expected:

- all Python tests pass
- the portable bundle is produced successfully

- [ ] **Step 5: Commit**

```bash
git add pyinstaller.spec pyapp/resources/bin README.md
git commit -m "feat: package portable python app"
```