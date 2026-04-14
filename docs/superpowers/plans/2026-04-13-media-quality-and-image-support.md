# 媒体质量档位与图片拼接支持 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add selectable video export quality presets and single-image slice/recompose export support to the desktop app.

**Architecture:** Keep the existing Electron UI and the pure grid-layout layer, then extend the FFmpeg orchestration to become media-aware so both video and image exports reuse the same slice and grid math. UI behavior changes based on detected media type, while the main process keeps one export pipeline with per-media argument branches.

**Tech Stack:** Electron, Node.js CommonJS, `ffmpeg` / `ffprobe`, native HTML/CSS/JavaScript, built-in `node:test`

---

## File Map

- `docs/superpowers/specs/2026-04-13-media-quality-and-image-support-design.md`: enhancement spec for media support and quality presets.
- `package.json`: add any packaging or helper scripts if implementation needs them.
- `main.js`: broaden file pickers, default output extension selection, and main-process validation around media type.
- `preload.js`: keep the renderer bridge aligned with the broader media-oriented IPC calls.
- `index.html`: add the quality selector and media-aware labels.
- `styles.css`: support hiding and showing media-specific controls cleanly.
- `renderer.js`: manage media type state, quality state, dynamic labels, and export payload branching.
- `src/core/ffmpeg.js`: extend probing and export command generation for video and image paths.
- `tests/ffmpeg.test.js`: cover quality presets and image export command generation.
- `README.md`: document the new media support and export quality behavior.

---

### Task 1: Extend FFmpeg Helpers for Media-Aware Probing and Export

**Files:**
- Modify `src/core/ffmpeg.js`
- Modify `tests/ffmpeg.test.js`

- [ ] **Step 1: Write the failing tests**

Add tests for:
- video export commands in `lossless`, `high`, and `medium` quality modes
- image export command generation that outputs a single `JPG` frame without audio mapping
- media probing helpers that distinguish image-oriented defaults from video-oriented defaults

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test tests/ffmpeg.test.js`
Expected: fail because the new media-aware helpers and command branches do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement:
- `probeMedia(filePath)`
- media-type inference helpers
- image-specific export command branch
- video quality preset mapping for `lossless / high / medium`

- [ ] **Step 4: Run the tests to verify they pass**

Run: `node --test tests/ffmpeg.test.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/core/ffmpeg.js tests/ffmpeg.test.js
git commit -m "feat: add media-aware ffmpeg export modes"
```

### Task 2: Wire Main Process and Preload to the Broader Media Flow

**Files:**
- Modify `main.js`
- Modify `preload.js`

- [ ] **Step 1: Broaden input and output handling**

Update the open/save dialogs to:
- accept both video and image inputs
- select `.mp4` for video outputs
- select `.jpg` for image outputs

- [ ] **Step 2: Route probing and export through media-aware helpers**

Replace video-specific assumptions with media-aware ones while preserving the current IPC surface or safely evolving it in lockstep with the renderer.

- [ ] **Step 3: Verify the bridge behavior**

Run: `node --check main.js && node --check preload.js`
Expected: both files parse cleanly.

- [ ] **Step 4: Commit**

```bash
git add main.js preload.js
git commit -m "feat: support image-aware desktop export flow"
```

### Task 3: Add Media-Aware UI State and Quality Controls

**Files:**
- Modify `index.html`
- Modify `styles.css`
- Modify `renderer.js`

- [ ] **Step 1: Add the failing behavior expectation**

Define renderer expectations in code and logs:
- selecting a video shows the quality selector
- selecting an image hides it
- output file suggestions switch extension based on media type

- [ ] **Step 2: Implement the UI updates**

Add:
- “选择文件”入口
- quality selector for video
- dynamic button and hint text
- media-aware metadata chips
- image-safe validation rules

- [ ] **Step 3: Verify the UI flow manually**

Run: `npm start`
Expected:
- video selection shows quality controls
- image selection hides quality controls
- output path suggestions use `.mp4` or `.jpg` correctly

- [ ] **Step 4: Commit**

```bash
git add index.html styles.css renderer.js
git commit -m "feat: add media-aware quality controls"
```

### Task 4: Update Documentation and Final Verification

**Files:**
- Modify `README.md`

- [ ] **Step 1: Document the new media matrix**

Document:
- supported video and image input types
- video quality presets
- fixed `JPG` output for images
- shared slice/grid behavior

- [ ] **Step 2: Run full verification**

Run:
```bash
npm test
```

Expected:
- all automated tests pass

- [ ] **Step 3: Package the desktop targets needed for validation**

Run the platform packaging commands needed for the current environment and confirm the updated app bundles exist.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/superpowers/specs/2026-04-13-media-quality-and-image-support-design.md docs/superpowers/plans/2026-04-13-media-quality-and-image-support.md
git commit -m "docs: add media quality and image support plan"
```