#!/usr/bin/env python3
"""Build the static study dataset consumed by the web app."""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
CURRENT = REPORTS / "科目1精选500题_分类学习文档.json"
ADDITIONS = REPORTS / "完整题库_补充候选分析.json"
IMAGE_SOURCE = REPORTS / "images"
WEB = ROOT / "web"
OUT = WEB / "src" / "study-data.json"
IMAGE_DEST = WEB / "public" / "images"

CATEGORY_META = {
    "事故处置与救援": {"short": "事故救援", "tone": "red"},
    "处罚扣分与法律责任": {"short": "扣分处罚", "tone": "amber"},
    "驾驶证与车辆登记": {"short": "证照登记", "tone": "blue"},
    "灯光仪表与车内装置": {"short": "灯光仪表", "tone": "cyan"},
    "标志标线与交警手势": {"short": "标志标线", "tone": "indigo"},
    "速度高速与车距车道": {"short": "速度车距", "tone": "violet"},
    "通行规则与安全驾驶": {"short": "安全通行", "tone": "green"},
    "新能源与辅助驾驶": {"short": "新能源", "tone": "teal"},
    "其他关键词技巧": {"short": "其他技巧", "tone": "gray"},
}

CATEGORY_ORDER = list(CATEGORY_META)
MNEMONIC_TYPES = ["数字记忆", "图形识别", "关键词直选", "行为原则", "法规归纳"]

ADDED_IMAGE_FILES = {
    93: "full-bank/question-1206.jpg",
    287: "full-bank/question-952.jpg",
    508: "full-bank/question-215.jpg",
    1171: "full-bank/question-1611.jpg",
    1175: "full-bank/question-1608.jpg",
    1176: "full-bank/question-1772.jpg",
    1012: "full-bank/question-708.jpg",
    181: "full-bank/question-1087.jpg",
    1528: "full-bank/question-1168.jpg",
    1529: "full-bank/question-1167.jpg",
    1530: "full-bank/question-1166.jpg",
    1531: "full-bank/question-1165.jpg",
    1532: "full-bank/question-1164.jpg",
}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\ufffc", "").replace("￼", "")).strip()


def classify_mnemonic(group: dict) -> str:
    tip = clean(group.get("tip", ""))
    category = group.get("category", "")
    items = group.get("items", [])
    joined = " ".join([tip] + [clean(item.get("question", "")) for item in items[:4]])
    if any(item.get("has_image") for item in items) or any(
        word in joined for word in ("图中", "如图", "标志", "标线", "手势", "指示灯", "颜色")
    ):
        return "图形识别"
    if re.search(r"\d|一二三四五六七八九十|公里|米|年|日|分", tip):
        return "数字记忆"
    if category in {"处罚扣分与法律责任", "驾驶证与车辆登记"}:
        return "法规归纳"
    if any(word in tip for word in ("看到", "选", "找", "直接", "关键词")):
        return "关键词直选"
    return "行为原则"


def usage_for(mnemonic_type: str) -> str:
    return {
        "数字记忆": "先认题型，再把数字与条件成组对应，注意题干中的范围和反向问法。",
        "图形识别": "先看颜色、形状和方向，再用图中细节排除相近选项。",
        "关键词直选": "先圈题干关键词，再匹配口诀；出现“错误、不得、不能”时先确认正反问法。",
        "行为原则": "先判断风险和冲突关系，优先选择减速、让行、观察和确保安全的做法。",
        "法规归纳": "先分清违法行为，再对应记分、罚款、扣留、吊销或刑事责任。",
    }[mnemonic_type]


def normalize_item(item: dict, group_id: str, index: int, source: str) -> dict:
    options = {letter: clean(value) for letter, value in item.get("options", {}).items() if clean(value)}
    image_file = item.get("image_file", "")
    return {
        "id": item.get("qid") or f"{group_id}-Q{index:02d}",
        "question": clean(item.get("question", "")),
        "options": options,
        "answer": item.get("answer", ""),
        "answerText": clean(item.get("answer_text", "")),
        "explanation": clean(item.get("explanation", "")),
        "tip": clean(item.get("tip", "")),
        "related": clean(item.get("related", "")),
        "hasImage": bool(item.get("has_image")),
        "image": f"images/{image_file}" if image_file else "",
        "source": source,
    }


def build_current_groups(payload: dict) -> list[dict]:
    groups = []
    for index, group in enumerate(payload["groups"], 1):
        group_id = f"K{index:03d}"
        items = [normalize_item(item, group_id, item_index, "精选500题") for item_index, item in enumerate(group["items"], 1)]
        mnemonic_type = classify_mnemonic(group)
        groups.append(
            {
                "id": group_id,
                "title": clean(group["tip"]),
                "tip": clean(group["tip"]),
                "category": group["category"],
                "mnemonicType": mnemonic_type,
                "explanation": next((item["explanation"] for item in items if item["explanation"]), usage_for(mnemonic_type)),
                "usage": usage_for(mnemonic_type),
                "kind": "精选500题",
                "isNew": False,
                "items": items,
            }
        )
    return groups


def build_added_groups(payload: dict, start_index: int) -> list[dict]:
    groups = []
    for offset, section in enumerate(payload["curated_additions"], start_index):
        group_id = f"K{offset:03d}"
        category = section["category"]
        if category == "车辆基础与安全操作":
            category = "通行规则与安全驾驶"
        raw_items = []
        for item in section["selected"]:
            capture_seq = item["capture_seq"]
            raw_items.append(
                {
                    **item,
                    "tip": section["mnemonic"],
                    "explanation": section["explanation"],
                    "qid": f"F{capture_seq}",
                    "image_file": ADDED_IMAGE_FILES.get(capture_seq, ""),
                }
            )
        provisional = {"tip": section["mnemonic"], "category": category, "items": raw_items}
        mnemonic_type = classify_mnemonic(provisional)
        items = [normalize_item(item, group_id, item_index, "完整题库增补") for item_index, item in enumerate(raw_items, 1)]
        groups.append(
            {
                "id": group_id,
                "title": clean(section["title"]),
                "tip": clean(section["mnemonic"]),
                "category": category,
                "mnemonicType": mnemonic_type,
                "explanation": clean(section["explanation"]),
                "usage": clean(section["why"]),
                "kind": section["kind"],
                "isNew": True,
                "items": items,
            }
        )
    return groups


def main() -> None:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    additions = json.loads(ADDITIONS.read_text(encoding="utf-8"))
    groups = build_current_groups(current)
    groups.extend(build_added_groups(additions, len(groups) + 1))

    IMAGE_DEST.mkdir(parents=True, exist_ok=True)
    for image in IMAGE_SOURCE.glob("*.png"):
        shutil.copy2(image, IMAGE_DEST / image.name)

    category_counts = Counter(group["category"] for group in groups)
    category_questions = Counter()
    mnemonic_counts = Counter(group["mnemonicType"] for group in groups)
    for group in groups:
        category_questions[group["category"]] += len(group["items"])

    categories = [
        {
            "id": name,
            **meta,
            "groupCount": category_counts[name],
            "questionCount": category_questions[name],
        }
        for name, meta in CATEGORY_META.items()
        if category_counts[name]
    ]
    mnemonic_types = [
        {"id": name, "groupCount": mnemonic_counts[name]}
        for name in MNEMONIC_TYPES
        if mnemonic_counts[name]
    ]
    payload = {
        "meta": {
            "title": "科目一学习册",
            "bankVersion": "2026-08 · 2328题库",
            "groupCount": len(groups),
            "questionCount": sum(len(group["items"]) for group in groups),
            "baseQuestionCount": len(current["records"]),
            "addedQuestionCount": additions["stats"]["curated_examples"],
            "imageCount": sum(1 for group in groups for item in group["items"] if item["image"]),
        },
        "categories": categories,
        "mnemonicTypes": mnemonic_types,
        "groups": groups,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(payload["meta"], ensure_ascii=False, indent=2))
    print(f"categories={len(categories)}")
    print(f"mnemonic_types={len(mnemonic_types)}")
    print(f"out={OUT}")


if __name__ == "__main__":
    main()
