# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import List

from patterns.clustering import Cluster


def format_specific_types(specific_types: List[tuple[str, float]]) -> str:
    if not specific_types:
        return ""
    parts = []
    for name, ratio in specific_types:
        parts.append(f"{ratio*100:.0f}% {name}")
    return ", ".join(parts)


def write_output_txt(path: str, rate: float, category: str, clusters: List[Cluster]) -> None:
    lines: List[str] = []
    lines.append(f"Category: {category}")
    lines.append("")

    if not clusters:
        lines.append("No clusters found.")
    else:
        for c in clusters:
            header = f"{c.Format(rate)} | Rating={c.Rating:.4f} | Amount={c.Amount/1000.0:.2f}s"
            st = format_specific_types(c.SpecificTypes)
            if st:
                header += f" | {st}"
            lines.append(header)

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))