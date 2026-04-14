# Video Grid Compositor

一个使用 Python + PySide6 的桌面应用，把“长条视频”或“单张长条图片”按宽度切成多个片段，再按手动指定的行列网格组合成新的单文件媒体输出。视频支持三档质量导出，图片固定输出为高质量 `JPG`。

## 开发环境

- Python 3.11+
- PySide6
- FFmpeg / FFprobe 已安装，或在便携包中随程序一起提供

## 安装

建议使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 启动

```bash
python -m pyapp.main
```

## 打包便携版

推荐用脚本直接生成 one-folder 便携包，并把 `ffmpeg` / `ffprobe` 一起塞进去：

```bash
python scripts/build_portable.py --zip
```

脚本会按当前平台自动处理：

- macOS：生成 `Video Grid Compositor.app`
- Windows：默认生成 `Video Grid Compositor/` 目录；如果加 `--onefile`，会生成单文件 `Video Grid Compositor.exe`
- 可选再压成 `release/Video Grid Compositor-macos.zip` 或 `release/Video Grid Compositor-windows.zip`

如果你用 GitHub Actions 打包 Windows exe，去仓库的 `Actions` 页面打开 `Windows EXE Build` 这次运行，然后在页面底部的 `Artifacts` 里下载 `video-grid-compositor-windows-exe`。

如果系统里没有全局 `ffmpeg/ffprobe`，也可以手动指定：

```bash
python scripts/build_portable.py \
  --ffmpeg /opt/homebrew/bin/ffmpeg \
  --ffprobe /opt/homebrew/bin/ffprobe \
  --zip
```

打包脚本默认优先读取 `FFMPEG_PATH` 和 `FFPROBE_PATH`，然后再回退到 PATH 查找。

## 生成一个测试视频

如果你手头没有长条测试素材，可以先用 FFmpeg 造一个：

```bash
ffmpeg -f lavfi -i testsrc2=duration=5:size=5760x360:rate=30 -c:v libx264 -pix_fmt yuv420p test-grid.mp4
```

如果还想加一个简单音轨：

```bash
ffmpeg -f lavfi -i testsrc2=duration=5:size=5760x360:rate=30 -f lavfi -i sine=frequency=440:duration=5 -c:v libx264 -pix_fmt yuv420p -c:a aac test-grid-audio.mp4
```

## 处理规则

- 不是按时间切段，而是按画面宽度切片。
- 支持输入视频和单张图片。
- 界面采用左侧参数工具台 + 右侧单一结果舞台。
- 切片数、行数、列数都由你手动输入。
- 必须满足 `rows × cols = 切片数`。
- 导出默认保持 `16:9`，分辨率默认 `1920x1080`。
- 支持 3 种适配模式：`填满单元格（裁切）`、`完整显示（留白）`、`拉伸填满（不裁切）`。
- 视频支持 3 档导出质量：`无损`、`高质量`、`中质量`。
- 视频默认优先保留原始音轨；如果音频与当前容器不兼容，导出会直接报错提示。
- 图片不参与质量档位设置，固定导出为高质量 `JPG`。
- 视频默认输出为 `.mp4`，图片默认输出为 `.jpg`。
- 右侧舞台支持直接拖拽换序，拖拽的是“最终拼接位置”，不是原始切片编号。
- 每个格子始终保留原始编号，例如 `#3` 表示第 3 个原始切片，即使它被拖到第 1 个位置也不会改号。
- 点击“恢复默认顺序”会把舞台恢复到 `#1 -> #2 -> #3 ...` 的自然排列。
