from __future__ import annotations

import signal
import subprocess
import threading
from dataclasses import dataclass

from .layout import build_filter_graph
from .paths import resolve_tool_path


def parse_progress_line(line: str, duration_seconds: float | None) -> dict[str, object] | None:
    if not isinstance(line, str):
        return None

    trimmed = line.strip()
    if not trimmed or "=" not in trimmed:
        return None

    key, value = trimmed.split("=", 1)

    if key == "out_time_ms":
        try:
            seconds = float(value) / 1_000_000
        except ValueError:
            return None

        percent = _progress_percent(seconds, duration_seconds)
        return {
            "type": "progress",
            "seconds": seconds,
            "percent": percent,
        }

    if key == "out_time":
        seconds = _parse_timecode(value)
        if seconds is None:
            return None

        percent = _progress_percent(seconds, duration_seconds)
        return {
            "type": "progress",
            "seconds": seconds,
            "percent": percent,
        }

    if key == "progress":
        return {
            "type": "state",
            "state": value,
            "finished": value == "end",
        }

    return {
        "type": "kv",
        "key": key,
        "value": value,
    }


def _parse_timecode(value: str) -> float | None:
    parts = value.strip().split(":")
    if len(parts) != 3:
        return None

    try:
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
    except ValueError:
        return None

    return (hours * 3600) + (minutes * 60) + seconds


def _progress_percent(seconds: float, duration_seconds: float | None) -> float | None:
    if not isinstance(duration_seconds, (int, float)) or duration_seconds <= 0:
        return None

    percent = (seconds / duration_seconds) * 100
    return min(100.0, round(percent, 2))


def build_export_command(job_config: dict[str, object]) -> dict[str, object]:
    media_type = job_config.get("media_type", "video")
    source_path = job_config["source_path"]
    output_path = job_config["output_path"]
    source_width = job_config["source_width"]
    source_height = job_config["source_height"]
    slice_count = job_config["slice_count"]
    rows = job_config["rows"]
    cols = job_config["cols"]
    slice_order = job_config.get("slice_order")
    output_width = job_config["output_width"]
    output_height = job_config["output_height"]
    fit_mode = job_config.get("fit_mode", "cover")
    export_mode = job_config.get("export_mode", "lossless")
    audio_mode = job_config.get("audio_mode", "copy")
    ffmpeg_path = job_config.get("ffmpeg_path", "ffmpeg")

    graph = build_filter_graph(
        {
            "source_width": source_width,
            "source_height": source_height,
            "slice_count": slice_count,
            "rows": rows,
            "cols": cols,
            "output_width": output_width,
            "output_height": output_height,
            "fit_mode": fit_mode,
            "slice_order": slice_order,
        }
    )

    resolved_ffmpeg = resolve_tool_path(
        str(ffmpeg_path),
        env=job_config.get("env"),
        extra_search_dirs=job_config.get("extra_search_dirs"),
    )

    args: list[str] = [
        "-hide_banner",
        "-y",
        "-i",
        str(source_path),
        "-filter_complex",
        graph["filter_complex"],
        "-map",
        graph["output_label"],
    ]

    if media_type == "image":
        args.extend(
            [
                "-frames:v",
                "1",
                "-c:v",
                "mjpeg",
                "-q:v",
                "1",
            ]
        )
    else:
        args.extend(["-map", "0:a?"])

        if export_mode == "lossless":
            args.extend(["-c:v", "libx264", "-preset", "veryslow", "-crf", "0"])
        elif export_mode == "high":
            args.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "slow", "-crf", "12"])
        else:
            args.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20"])

        if audio_mode == "copy":
            args.extend(["-c:a", "copy"])
        else:
            args.extend(["-c:a", "aac", "-b:a", "192k"])

    if media_type == "video":
        args.extend(["-movflags", "+faststart"])

    args.extend(["-progress", "pipe:1", "-nostats", str(output_path)])

    return {
        "ffmpeg_path": resolved_ffmpeg,
        "args": args,
        "filter_complex": graph["filter_complex"],
        "output_label": graph["output_label"],
        "layout": graph["layout"],
    }


@dataclass
class ExportJob:
    process: subprocess.Popen[str]
    command: dict[str, object]
    stdout_thread: threading.Thread | None
    stderr_thread: threading.Thread | None

    def cancel(self) -> None:
        if self.process.poll() is not None:
            return

        if hasattr(self.process, "send_signal"):
            try:
                self.process.send_signal(signal.SIGINT)
                return
            except Exception:
                pass

        if hasattr(self.process, "terminate"):
            self.process.terminate()

    def wait(self) -> int | None:
        return self.process.wait()


def run_export(job_config: dict[str, object], handlers: dict[str, object] | None = None) -> ExportJob:
    command = build_export_command(job_config)
    handlers = handlers or {}
    duration_seconds = job_config.get("duration_seconds")

    process = subprocess.Popen(
        [command["ffmpeg_path"], *command["args"]],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    stdout_thread = _start_stdout_thread(process, duration_seconds, handlers)
    stderr_thread = _start_stderr_thread(process, handlers)

    return ExportJob(
        process=process,
        command=command,
        stdout_thread=stdout_thread,
        stderr_thread=stderr_thread,
    )


def _start_stdout_thread(process: subprocess.Popen[str], duration_seconds: float | None, handlers: dict[str, object]) -> threading.Thread | None:
    if process.stdout is None:
        return None

    def pump_stdout() -> None:
        for line in iter(process.stdout.readline, ""):
            parsed = parse_progress_line(line, duration_seconds)
            if not parsed:
                continue

            if parsed["type"] == "progress":
                callback = handlers.get("on_progress")
                if callback:
                    callback(parsed)
            elif parsed["type"] == "state":
                callback = handlers.get("on_state")
                if callback:
                    callback(parsed)

    thread = threading.Thread(target=pump_stdout, daemon=True)
    thread.start()
    return thread


def _start_stderr_thread(process: subprocess.Popen[str], handlers: dict[str, object]) -> threading.Thread | None:
    if process.stderr is None:
        return None

    def pump_stderr() -> None:
        for line in iter(process.stderr.readline, ""):
            if not line:
                continue

            callback = handlers.get("on_stderr")
            if callback:
                callback(line)

    thread = threading.Thread(target=pump_stderr, daemon=True)
    thread.start()
    return thread
