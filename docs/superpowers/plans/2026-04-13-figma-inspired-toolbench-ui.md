# Figma 风格专业工具台界面重设计 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前媒体切片桌面应用重构为 Figma 风格的专业工具台界面，并支持在右侧单一网格舞台中拖拽换序后按该顺序导出。

**Architecture:** 保持现有 Electron 与媒体处理主链路不变，重点重构 `index.html`、`styles.css`、`renderer.js` 的页面结构与交互模型，同时把导出顺序从“自然索引”提升为“显式 sliceOrder”。布局数学继续集中在纯函数模块中，确保拖拽换序可被自动化测试覆盖。右侧舞台既承担预览，也承担排序，不再分出独立列表。

**Tech Stack:** Electron, Node.js CommonJS, 原生 HTML/CSS/JavaScript, `ffmpeg` / `ffprobe`, 内置 `node:test`

---

## File Map

- `docs/superpowers/specs/2026-04-13-figma-inspired-toolbench-ui-design.md`: 已确认的界面设计规范。
- `index.html`: 重新组织为顶部克制标题栏、左侧控制台、右侧单一拖拽舞台结构。
- `styles.css`: 从当前深色玻璃风切换为以黑白和灰阶为主的 Figma 风格工具台视觉系统。
- `renderer.js`: 增加舞台拖拽换序、顺序摘要、媒体感知文案，以及新的布局渲染组织。
- `src/core/layout.js`: 增加可选的 `sliceOrder` 顺序映射，让导出顺序与舞台顺序一致。
- `tests/layout.test.js`: 覆盖 `sliceOrder` 下的 filter graph 与布局输出。
- `README.md`: 补充新的界面行为和拖拽排序说明。

---

### Task 1: 为导出顺序映射补充纯函数测试和实现

**Files:**
- Modify: `src/core/layout.js`
- Test: `tests/layout.test.js`

- [ ] **Step 1: Write the failing test**

在 `tests/layout.test.js` 中新增测试，覆盖以下行为：
- `buildFilterGraph` 在传入 `sliceOrder` 时，网格位置按显式顺序映射，而不是自然顺序
- 非法 `sliceOrder`（长度不匹配、索引重复、越界）会抛出明确错误

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test:layout`
Expected: FAIL，原因是当前 `buildFilterGraph` 还不接受 `sliceOrder` 或没有按拖拽顺序生成 `xstack` 输入。

- [ ] **Step 3: Write minimal implementation**

在 `src/core/layout.js` 中：
- 为 `buildFilterGraph` 增加 `sliceOrder` 入参
- 新增顺序校验辅助函数
- 让 `row/col` 位置按“显示位置 -> 原始切片索引”映射计算
- 保持现有 `cover / contain / stretch` 行为不变

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test:layout`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add src/core/layout.js tests/layout.test.js
git commit -m "feat: support explicit slice ordering in layout graph"
```

### Task 2: 重构页面骨架为左侧控制台 + 右侧单一舞台

**Files:**
- Modify: `index.html`
- Modify: `styles.css`

- [ ] **Step 1: Write the structural expectation**

先在计划内明确最终结构必须包含：
- 顶部克制标题栏
- 左侧控制台五个区块：`Source / Slice / Output / Encode / Export`
- 右侧摘要条
- 右侧单一拖拽舞台
- 右侧底部执行反馈区

- [ ] **Step 2: Implement minimal HTML restructure**

在 `index.html` 中：
- 移除当前偏“控制面板 + 预览卡”的旧块结构
- 新建更明确的控制台区块容器和舞台容器
- 为拖拽舞台、顺序摘要、重置按钮和顶部工具标题预留稳定 ID

- [ ] **Step 3: Implement minimal CSS system**

在 `styles.css` 中：
- 切换到黑白 + 灰阶的主视觉系统
- 使用胶囊和大圆角几何
- 给焦点态加虚线轮廓
- 保留响应式双栏到单栏折叠能力

- [ ] **Step 4: Verify parsing**

Run:
```bash
node --check renderer.js
```

Expected: 语法检查通过；当前阶段即使界面还没完全联动，也不能引入解析错误。

- [ ] **Step 5: Commit**

```bash
git add index.html styles.css
git commit -m "feat: redesign app shell into toolbench layout"
```

### Task 3: 实现右侧舞台拖拽换序和媒体感知渲染

**Files:**
- Modify: `renderer.js`
- Modify: `index.html`
- Modify: `styles.css`
- Modify: `src/core/layout.js`（如导出顺序接线需要）

- [ ] **Step 1: Write the failing behavior**

先在 `renderer.js` 设计清楚最小状态模型，并让以下行为成为实现目标：
- `sliceOrder` 默认是自然顺序
- 当切片数变化时重建或重置顺序
- 舞台拖拽交换两个位置
- 顺序摘要展示当前原编号顺序
- 点击“恢复默认顺序”可还原

- [ ] **Step 2: Implement state and stage rendering**

在 `renderer.js` 中：
- 新增 `sliceOrder`
- 将右侧舞台单元改成可拖拽格子
- 每个格子显示原始编号
- 添加重置逻辑和顺序摘要渲染

- [ ] **Step 3: Wire export payload**

在 `renderer.js` 和相关导出调用中：
- 导出时把 `sliceOrder` 一并传给主进程
- 保持视频质量档位、图片导出、媒体感知文案等现有能力不回退

- [ ] **Step 4: Run manual interaction check**

Run: `npm start`
Expected:
- 选择媒体后界面结构更新为新工具台
- 拖拽两个格子时顺序摘要同步变化
- 点击恢复默认顺序后顺序恢复
- 导出按钮仍可进入导出流程

- [ ] **Step 5: Commit**

```bash
git add renderer.js index.html styles.css src/core/layout.js
git commit -m "feat: add draggable stage ordering"
```

### Task 4: 收尾文档和完整验证

**Files:**
- Modify: `README.md`
- Modify: `index.html`
- Modify: `styles.css`
- Modify: `renderer.js`
- Modify: `src/core/layout.js`
- Modify: `tests/layout.test.js`

- [ ] **Step 1: Document the new interaction model**

在 `README.md` 中补充：
- 新界面是左侧控制台 + 右侧单一舞台
- 右侧可拖拽换序
- 原编号保留规则
- “恢复默认顺序”的行为

- [ ] **Step 2: Run automated verification**

Run:
```bash
npm test
node --check main.js
node --check preload.js
node --check renderer.js
```

Expected:
- 所有测试通过
- 三个入口文件都能通过语法检查

- [ ] **Step 3: Re-package validation builds**

Run:
```bash
npm run package:mac
```

如果当前环境继续沿用离线 Windows 打包流程，则再执行对应的 `electron-packager` 命令，确认产物目录更新。

- [ ] **Step 4: Commit**

```bash
git add README.md index.html styles.css renderer.js src/core/layout.js tests/layout.test.js
git commit -m "feat: ship figma-inspired toolbench ui"
```