# 视频网格重排桌面应用 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows/macOS desktop app that splits a long-strip video by width into configurable slices, arranges them into a manually specified grid, and exports a single 16:9 video file.

**Architecture:** Use Electron as the desktop shell, plain HTML/CSS/JavaScript for the renderer, and system `ffmpeg`/`ffprobe` for video processing. Keep all grid math and FFmpeg filter construction in pure CommonJS modules so they can be unit tested without launching Electron.

**Tech Stack:** Electron, Node.js CommonJS, native `ffmpeg`/`ffprobe`, built-in `node:test` and `assert`

---

## File Map

- `package.json`: app metadata, Electron dependency, scripts for `start`, `test`, and future packaging.
- `main.js`: Electron main process, window creation, IPC handlers, export job orchestration.
- `preload.js`: safe bridge from renderer to main process.
- `index.html`: app shell and layout containers.
- `styles.css`: desktop UI styling and visual polish.
- `renderer.js`: form state, previews, user interactions, progress UI.
- `src/core/layout.js`: slice width distribution, grid validation, output sizing, FFmpeg filter graph generation.
- `src/core/ffmpeg.js`: `ffprobe` metadata lookup, export process launch, progress parsing, cancel handling.
- `tests/layout.test.js`: pure-function unit tests for grid math and filter generation.
- `tests/ffmpeg.test.js`: pure-function unit tests for progress parsing and command-building helpers.

---

### Task 1: Build the Pure Grid Math Layer

**Files:**
- Create `src/core/layout.js`
- Create `tests/layout.test.js`

- [ ] **Step 1: Write the failing test**

Write tests for:
- even distribution of slice widths when `sourceWidth % sliceCount != 0`
- row/column validation where `rows * cols` must equal `sliceCount`
- cell size calculation from `outputWidth`, `outputHeight`, `rows`, and `cols`
- filter graph output for a small known case like `5760x360`, `sliceCount=3`, `rows=3`, `cols=1`

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test tests/layout.test.js`
Expected: fail with `Cannot find module` or missing export errors because `src/core/layout.js` does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement the pure helpers in `src/core/layout.js`:
- `distributeSliceWidths(sourceWidth, sliceCount)`
- `buildSlicePlan(sourceWidth, sliceCount)`
- `validateGridConfig({ sliceCount, rows, cols, outputWidth, outputHeight })`
- `buildFilterGraph({ sourceWidth, sourceHeight, sliceCount, rows, cols, outputWidth, outputHeight, fitMode })`

- [ ] **Step 4: Run the test to verify it passes**

Run: `node --test tests/layout.test.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/core/layout.js tests/layout.test.js
git commit -m "feat: add grid layout math"
```

### Task 2: Bootstrap the Electron App Shell

**Files:**
- Create `package.json`
- Create `main.js`
- Create `preload.js`
- Create `index.html`
- Create `styles.css`
- Create `renderer.js`

- [ ] **Step 1: Write the failing integration check**

Create a minimal smoke test or start script expectation by adding the Electron entrypoints and a placeholder renderer state. The goal is to make `npm start` fail until Electron is installed and the window bootstrap is wired.

- [ ] **Step 2: Install and wire the runtime**

Add `electron` as a dependency and scripts for:
- `start`: launch Electron against `main.js`
- `test`: run `node --test`

Implement:
- `main.js` creates a single BrowserWindow.
- `preload.js` exposes a small API surface.
- `index.html` loads `renderer.js`.
- `renderer.js` renders the first version of the form and preview layout.

- [ ] **Step 3: Verify the app starts**

Run: `npm start`
Expected: Electron window opens with the initial UI shell.

- [ ] **Step 4: Commit**

```bash
git add package.json main.js preload.js index.html styles.css renderer.js
git commit -m "feat: bootstrap electron shell"
```

### Task 3: Implement FFmpeg Probe and Export Helpers

**Files:**
- Create `src/core/ffmpeg.js`
- Create `tests/ffmpeg.test.js`
- Modify `main.js`

- [ ] **Step 1: Write the failing tests**

Write tests for:
- parsing FFmpeg progress lines into a numeric percentage
- building a safe export command object from a known job config
- rejecting invalid input when `ffprobe` metadata is missing

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test tests/ffmpeg.test.js`
Expected: fail because `src/core/ffmpeg.js` is missing.

- [ ] **Step 3: Write the minimal implementation**

Implement helpers in `src/core/ffmpeg.js`:
- `probeVideo(filePath)`
- `runExport(jobConfig, handlers)`
- `parseProgressLine(line, durationSeconds)`

Wire the main process to call these helpers and emit IPC progress updates.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `node --test tests/ffmpeg.test.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/core/ffmpeg.js tests/ffmpeg.test.js main.js
git commit -m "feat: add ffmpeg export helpers"
```

### Task 4: Wire the Renderer UI to the Processing Pipeline

**Files:**
- Modify `index.html`
- Modify `styles.css`
- Modify `renderer.js`
- Modify `preload.js`
- Modify `main.js`

- [ ] **Step 1: Add the interaction test plan**

No automated DOM test framework is required in the MVP. Instead, define the renderer state transitions clearly in code comments and keep the UI logic split into small functions:
- file selection
- metadata display
- grid preview rendering
- export start/cancel
- progress and error display

- [ ] **Step 2: Implement the UI state and IPC bridge**

Add:
- file picker button
- numeric inputs for slice count, rows, cols
- output aspect/resolution fields
- fit mode selector
- preview grid
- progress bar and status text
- export and cancel actions

Use the preload bridge so the renderer never calls Node APIs directly.

- [ ] **Step 3: Verify the user flow manually**

Run: `npm start`
Expected:
- selecting a file shows its metadata
- invalid `rows * cols != sliceCount` is blocked
- export button becomes enabled only when the config is valid
- progress updates appear during export

- [ ] **Step 4: Commit**

```bash
git add index.html styles.css renderer.js preload.js main.js
git commit -m "feat: connect renderer to export flow"
```

### Task 5: Polish Validation, Defaults, and Documentation

**Files:**
- Modify `src/core/layout.js`
- Modify `renderer.js`
- Create `README.md`

- [ ] **Step 1: Add any missing validation**

Tighten rules for:
- even output dimensions
- `sliceCount <= sourceWidth`
- readable error text for invalid aspect ratios or output sizes

- [ ] **Step 2: Improve the default UX**

Add sensible defaults:
- `sliceCount = 3`
- `rows = 3`
- `cols = 1`
- `outputWidth = 1920`
- `outputHeight = 1080`
- `fitMode = cover`

- [ ] **Step 3: Document the workflow**

Document:
- how to install dependencies
- how to launch the app
- how to prepare a test video
- how the slice/grid math works

- [ ] **Step 4: Final verification**

Run:
```bash
npm test
npm start
```

Expected:
- tests pass
- app launches
- export pipeline works on a synthetic sample video

- [ ] **Step 5: Commit**

```bash
git add src/core/layout.js renderer.js README.md
git commit -m "docs: polish video grid compositor"
```