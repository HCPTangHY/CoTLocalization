#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CoT i18n 模拟替换器

从 i18n.json 的 TypeBOutputText 读取 JS 替换规则，
应用到源 JS 文件上，输出替换后的 JS 供语法检查。

用法:
  python src/verify_replace.py <source_js_dir> <i18n_json> <output_dir>

  source_js_dir: 包含原始 .js 文件的目录（从 story-export 解压得到）
  i18n_json:     translated_source/<version>/i18n.json
  output_dir:    替换后的 JS 输出目录
"""

import json
import os
import re
import sys
import logging

logger = logging.getLogger("verify_replace")
logging.basicConfig(format="[%(levelname)s] %(message)s", level=logging.INFO)


def apply_js_replacements(source_content: str, entries: list) -> tuple:
    """对 JS 源文件内容应用 i18n 替换规则。

    entries 来自 i18n.json 的 TypeBOutputText，每条包含:
      - pos: 文件内绝对位置 (0-based)
      - f:   原文 (find)
      - t:   译文 (translation)

    返回 (result_content, applied_count, skipped_count)
    """
    # 按位置排序
    sorted_entries = sorted(entries, key=lambda e: e.get("pos", 0))

    parts = []
    last_idx = 0
    applied = 0
    skipped = 0

    for entry in sorted_entries:
        pos = entry.get("pos", 0)
        original = entry.get("f", "")
        translation = entry.get("t", "")

        if not original or not translation:
            skipped += 1
            continue

        # 清理零宽空格
        translation = translation.translate(
            str.maketrans("", "", "\u200b\u200c\u200d\ufeff")
        )
        if not translation:
            skipped += 1
            continue

        if pos < last_idx:
            logger.warning(f"Overlap: pos={pos} < last_idx={last_idx}, f={original[:40]}")
            skipped += 1
            continue

        if pos > len(source_content):
            logger.warning(f"Out of bounds: pos={pos} > len={len(source_content)}")
            skipped += 1
            continue

        # 验证原文匹配
        orig_len = len(original)
        actual = source_content[pos : pos + orig_len]
        if actual != original:
            # 小范围搜索 ±10
            found = False
            for offset in range(-10, 11):
                check_pos = pos + offset
                if check_pos < last_idx or check_pos < 0:
                    continue
                if source_content[check_pos : check_pos + orig_len] == original:
                    pos = check_pos
                    found = True
                    break
            if not found:
                logger.warning(
                    f"Mismatch: pos={pos}\n"
                    f"  expect: {repr(original[:60])}\n"
                    f"  actual: {repr(actual[:60])}"
                )
                skipped += 1
                continue

        parts.append(source_content[last_idx:pos])
        parts.append(translation)
        last_idx = pos + orig_len
        applied += 1

    parts.append(source_content[last_idx:])
    return "".join(parts), applied, skipped


def main():
    if len(sys.argv) < 4:
        print(f"Usage: python {sys.argv[0]} <source_js_dir> <i18n_json> <output_dir>")
        sys.exit(1)

    source_dir = sys.argv[1]
    i18n_path = sys.argv[2]
    output_dir = sys.argv[3]

    # 读取 i18n.json
    with open(i18n_path, "r", encoding="utf-8") as f:
        i18n = json.load(f)

    typeb = i18n.get("typeB", {}).get("TypeBOutputText", [])
    if not typeb:
        logger.info("No TypeBOutputText entries found")
        sys.exit(0)

    # 按 fileName 分组
    file_groups = {}
    for entry in typeb:
        fname = entry.get("fileName", "")
        if not fname:
            continue
        file_groups.setdefault(fname, []).append(entry)

    os.makedirs(output_dir, exist_ok=True)

    total_applied = 0
    total_skipped = 0
    output_files = []

    for fname, entries in sorted(file_groups.items()):
        # 在 source_dir 里找对应文件
        source_path = os.path.join(source_dir, fname)
        if not os.path.isfile(source_path):
            logger.warning(f"Source file not found: {fname}, skipping")
            continue

        with open(source_path, "r", encoding="utf-8-sig") as f:
            content = f.read()

        result, applied, skipped = apply_js_replacements(content, entries)
        total_applied += applied
        total_skipped += skipped

        out_path = os.path.join(output_dir, fname)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(result)
        output_files.append(out_path)

        logger.info(f"  {fname}: {applied} applied, {skipped} skipped")

    logger.info(
        f"Total: {total_applied} applied, {total_skipped} skipped, "
        f"{len(output_files)} files written to {output_dir}"
    )

    # 输出文件列表供后续步骤使用
    print("\n".join(output_files))


if __name__ == "__main__":
    main()
