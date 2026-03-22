# -*- coding: utf-8 -*-
"""
测试入口：
- 读入 .osu 文件（绝对路径）
- keys 从 [Difficulty] CircleSize 读取，失败默认 4（按你的要求）
- 计算 Difficulty + PatternReport
- 在当前工作目录写 output.txt
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from urllib.parse import unquote
from urllib.request import urlopen

from config import BID_DOWNLOAD_TIMEOUT_SECONDS, DEFAULT_RATE
from osu_parser import parse_osu_mania
from patterns.summary import from_chart
from output_writer import render_output_lines, write_output_txt


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", name)
    return cleaned.strip() or "beatmap.osu"


def _filename_from_disposition(header_value: str | None) -> str | None:
    if not header_value:
        return None

    m = re.search(r"filename\*?=UTF-8''([^;]+)", header_value)
    if m:
        return _safe_filename(unquote(m.group(1)))

    m = re.search(r'filename="([^"]+)"', header_value)
    if m:
        return _safe_filename(unquote(m.group(1)))

    return None


def _download_osu_by_bid(bid: int, cache_dir: str) -> str:
    url = f"https://osu.ppy.sh/osu/{bid}"

    os.makedirs(cache_dir, exist_ok=True)
    with urlopen(url, timeout=BID_DOWNLOAD_TIMEOUT_SECONDS) as resp:
        status = getattr(resp, "status", 200)
        if status != 200:
            raise RuntimeError(f"下载失败，HTTP {status}")

        cd = resp.headers.get("Content-Disposition")
        filename = _filename_from_disposition(cd) or f"b{bid}.osu"
        if not filename.lower().endswith(".osu"):
            filename += ".osu"

        data = resp.read()

    out_path = os.path.abspath(os.path.join(cache_dir, filename))
    with open(out_path, "wb") as f:
        f.write(data)
    return out_path


def _resolve_input_to_osu_path(raw: str) -> str:
    s = raw.strip().strip('"')

    # 支持网址输入，例如：
    # https://osu.ppy.sh/beatmapsets/2265723#mania/4824023
    # 其中 bid=4824023（取 mania/ 后面的数字）
    url_bid_match = re.search(r"(?:#mania/|/beatmaps/)(\d+)(?:\D.*)?$", s, flags=re.IGNORECASE)
    if url_bid_match:
        bid = int(url_bid_match.group(1))
        cache_dir = os.path.join(os.getcwd(), "cache")
        return _download_osu_by_bid(bid, cache_dir)

    bid_match = re.fullmatch(r"(?:bid\s*[:=]\s*)?(\d+)", s, flags=re.IGNORECASE)
    if bid_match:
        bid = int(bid_match.group(1))
        cache_dir = os.path.join(os.getcwd(), "cache")
        return _download_osu_by_bid(bid, cache_dir)

    return s


def _ask_run_mode() -> str:
    while True:
        print("请选择运行模式：")
        print("1) 批处理 maps 文件夹")
        print("2) 输入谱面绝对路径 / bid / osu网址")
        choice = input("请输入 1 或 2: ").strip()
        if choice == "1":
            return "batch"
        if choice == "2":
            return "single"
        print("输入无效，请重试。")


@dataclass
class _BatchResult:
    FileName: str
    Category: str
    Clusters: list
    Duration: float


def _collect_maps_osu_files(cwd: str) -> list[str]:
    maps_dir = os.path.join(cwd, "maps")
    if not os.path.isdir(maps_dir):
        return []
    return sorted(
        [
            os.path.abspath(os.path.join(maps_dir, name))
            for name in os.listdir(maps_dir)
            if name.lower().endswith(".osu") and os.path.isfile(os.path.join(maps_dir, name))
        ],
        key=lambda p: os.path.basename(p).lower(),
    )


def _write_batch_output_txt(path: str, rate: float, results: list[_BatchResult], errors: list[tuple[str, str]]) -> None:
    lines: list[str] = []
    if not results and not errors:
        lines.append("maps 文件夹存在，但未找到 .osu 文件。")
    else:
        for result in results:
            lines.append(f"===== {result.FileName} =====")
            lines.extend(render_output_lines(rate, result.Category, result.Clusters, result.Duration))
            lines.append("")

        for file_name, error in errors:
            lines.append(f"===== {file_name} =====")
            lines.append(f"Error: {error}")
            lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


def main():
    cwd = os.getcwd()
    out_path = os.path.join(cwd, "output.txt")
    rate = DEFAULT_RATE

    mode = _ask_run_mode()
    if mode == "batch":
        map_files = _collect_maps_osu_files(cwd)
        maps_dir = os.path.join(cwd, "maps")
        if not os.path.isdir(maps_dir):
            print(f"错误：未找到 maps 文件夹：{maps_dir}")
            sys.exit(1)

        results: list[_BatchResult] = []
        errors: list[tuple[str, str]] = []
        for osu_path in map_files:
            file_name = os.path.basename(osu_path)
            try:
                chart = parse_osu_mania(osu_path)
                report = from_chart(chart)
                results.append(
                    _BatchResult(
                        FileName=file_name,
                        Category=report.Category,
                        Clusters=report.Clusters,
                        Duration=report.Duration,
                    )
                )
            except Exception as e:
                errors.append((file_name, str(e)))

        _write_batch_output_txt(out_path, rate, results, errors)
        print(f"已输出：{out_path}")
        print(f"批量模式：成功 {len(results)} 个，失败 {len(errors)} 个")
        return

    user_input = input("请输入 .osu 文件绝对路径、bid 或 osu 网址: ").strip()

    try:
        osu_path = _resolve_input_to_osu_path(user_input)
    except Exception as e:
        print(f"错误：下载 bid 失败：{e}")
        sys.exit(1)

    if not os.path.isabs(osu_path):
        print("错误：请提供绝对路径。")
        sys.exit(1)

    if not os.path.exists(osu_path):
        print(f"错误：文件不存在：{osu_path}")
        sys.exit(1)

    chart = parse_osu_mania(osu_path)

    report = from_chart(chart)
    write_output_txt(out_path, rate, report.Category, report.Clusters, report.Duration)

    print(f"已输出：{out_path}")
    print(f"Keys={chart.Keys}, Clusters={len(report.Clusters)}, Category={report.Category}")


if __name__ == "__main__":
    main()