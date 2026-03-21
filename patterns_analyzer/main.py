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
import sys

from osu_parser import parse_osu_mania
from calculator.difficulty import calculate as calc_difficulty
from patterns.summary import from_chart
from output_writer import write_output_txt


def main():
    if len(sys.argv) >= 2:
        osu_path = sys.argv[1]
    else:
        osu_path = input("请输入 .osu 文件绝对路径: ").strip().strip('"')

    if not os.path.isabs(osu_path):
        print("错误：请提供绝对路径。")
        sys.exit(1)

    if not os.path.exists(osu_path):
        print(f"错误：文件不存在：{osu_path}")
        sys.exit(1)

    chart = parse_osu_mania(osu_path)

    # 目前测试只用 rate=1.0（Interlude 内部会支持变速；你后续接 Nonebot 时也可做参数）
    rate = 1.0

    diff = calc_difficulty(rate, chart.Notes)
    report = from_chart(diff, chart)

    out_path = os.path.join(os.getcwd(), "output.txt")
    write_output_txt(out_path, rate, report.Category, report.Clusters, report.Duration)

    print(f"已输出：{out_path}")
    print(f"Keys={chart.Keys}, Clusters={len(report.Clusters)}, Category={report.Category}")


if __name__ == "__main__":
    main()