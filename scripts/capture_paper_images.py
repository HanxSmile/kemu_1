#!/usr/bin/env python3
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MODULE_CACHE = ROOT / ".swift-module-cache"
AX_DUMP = ROOT / "scripts" / "ax_dump.swift"
DRAG = ROOT / "scripts" / "drag_once.swift"
WINDOW_ID = ROOT / "scripts" / "window_id.swift"
OUT_DIR = ROOT / "data" / "reports" / "images"
TMP_DIR = ROOT / "data" / "tmp"


def run(args, *, text=True):
    return subprocess.run(args, cwd=ROOT, check=True, text=text, capture_output=True).stdout


def swift(script, *args):
    return run(["swift", "-module-cache-path", str(MODULE_CACHE), str(script), *map(str, args)])


def dump_ax(pid):
    return json.loads(swift(AX_DUMP, pid))


def window_info(pid):
    out = swift(WINDOW_ID, pid).strip().splitlines()
    if not out:
        raise RuntimeError(f"window not found for pid {pid}")
    parts = out[0].split("\t", 3)
    window_id = parts[0]
    bounds = {}
    for key, value in re.findall(r"([A-Za-z]+) = \"?(-?[0-9.]+)\"?;", parts[3]):
        bounds[key] = float(value)
    return window_id, bounds


def clean(text):
    return (text or "").replace("\ufffc", "").replace("￼", "").strip()


def all_texts(node):
    values = []
    for key in ("description", "title", "value"):
        if node.get(key):
            values.append(clean(node[key]))
    for child in node.get("children", []):
        values.extend(all_texts(child))
    return [v for v in values if v]


def question_key(root):
    ignored = {
        "test back",
        "答题",
        "背题",
        "question setting",
        "试题详解",
        "题目解析",
        "点击或上拉加载更多",
    }
    for text in all_texts(root):
        if text in ignored:
            continue
        if text.startswith(("答案 ", "秒懂技巧", "速记口诀", "关键字答题", "相关考点", "板书讲题")):
            continue
        if "？" in text or "?" in text or "。" in text:
            return text
    return ""


def answer_top(node):
    if any(clean(node.get(k, "")).startswith("答案 ") for k in ("description", "title", "value")):
        pos = node.get("position") or []
        if len(pos) > 1:
            return pos[1]
    values = [answer_top(child) for child in node.get("children", [])]
    values = [v for v in values if v is not None]
    return min(values) if values else None


def image_candidates(node, before_y):
    found = []
    desc = clean(node.get("description", "")) or clean(node.get("title", "")) or clean(node.get("value", ""))
    role = node.get("role")
    pos = node.get("position") or []
    size = node.get("size") or []
    if (
        role == "AXButton"
        and not desc
        and len(pos) >= 2
        and len(size) >= 2
        and pos[1] < before_y
        and size[0] >= 70
        and size[1] >= 50
    ):
        found.append((pos, size))
    for child in node.get("children", []):
        found.extend(image_candidates(child, before_y))
    return found


def question_image_box(root):
    top = answer_top(root)
    if top is None:
        return None
    candidates = image_candidates(root, top)
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[1][0] * item[1][1])


def capture_window(window_id, path):
    subprocess.run(["screencapture", "-x", "-l", str(window_id), str(path)], cwd=ROOT, check=True)


def crop_image(root, box, full_path, out_path):
    im = Image.open(full_path)
    root_pos = root.get("position") or [0, 0]
    root_size = root.get("size") or [im.width, im.height]
    margin_x = max(0, (im.width - root_size[0]) / 2)
    margin_y = max(0, (im.height - root_size[1]) / 2)
    pos, size = box
    left = int(round(pos[0] - root_pos[0] + margin_x))
    top = int(round(pos[1] - root_pos[1] + margin_y))
    right = int(round(left + size[0]))
    bottom = int(round(top + size[1]))
    pad = 3
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(im.width, right + pad)
    bottom = min(im.height, bottom + pad)
    if right - left < 40 or bottom - top < 40:
        return False
    cropped = im.crop((left, top, right, bottom))
    cropped.save(out_path)
    return True


def drag_next(root):
    win_x = (root.get("position") or [556, -999])[0]
    win_y = (root.get("position") or [556, -999])[1]
    has_image = question_image_box(root) is not None
    y = win_y + (650 if has_image else 330)
    swift(DRAG, win_x + 520, y, win_x + 120, y)


def main():
    if len(sys.argv) != 4:
        print("Usage: capture_paper_images.py <pid> <paper> <count>", file=sys.stderr)
        raise SystemExit(2)
    pid = int(sys.argv[1])
    paper = int(sys.argv[2])
    count = int(sys.argv[3])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    window_id, _ = window_info(pid)
    manifest = []
    for index in range(1, count + 1):
        root = dump_ax(pid)
        q = question_key(root)
        box = question_image_box(root)
        saved = None
        if box is not None:
            full = TMP_DIR / f"window_P{paper}-{index:03d}.png"
            out = OUT_DIR / f"P{paper}-{index:03d}.png"
            capture_window(window_id, full)
            if crop_image(root, box, full, out):
                saved = str(out.relative_to(ROOT))
        manifest.append({"paper": paper, "index": index, "question": q, "image": saved})
        print(f"P{paper}-{index:03d} {'image' if saved else 'no-image'} {q}", flush=True)
        if index < count:
            drag_next(root)
            time.sleep(0.2)
    manifest_path = TMP_DIR / f"image_manifest_paper{paper}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest={manifest_path}")


if __name__ == "__main__":
    main()
