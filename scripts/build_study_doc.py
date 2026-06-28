#!/usr/bin/env python3
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUT = ROOT / "data" / "reports" / "科目1精选500题_秒懂技巧学习文档.md"
STRUCTURED = ROOT / "data" / "reports" / "科目1精选500题_结构化技巧.json"


def clean(text: str) -> str:
    return (
        (text or "")
        .replace("\ufffc", "")
        .replace("￼", "")
        .replace("\u200b", "")
        .strip()
    )


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", clean(text))


def tip_parts(texts):
    for text in texts:
        t = clean(text)
        if any(label in t for label in ("秒懂技巧", "速记口诀", "关键字答题")) or t.startswith("秒懂"):
            m = re.match(r"^(秒懂技巧|速记口诀|关键字答题)\s*[:：]\s*(.+)$", t, re.S)
            if m:
                return m.group(1), normalize_space(m.group(2)), t
            if t.startswith("秒懂"):
                return "秒懂技巧", normalize_space(t.removeprefix("秒懂")), t
    return "未标注", "", ""


def answer_parts(texts):
    for text in texts:
        t = clean(text)
        if t.startswith("答案"):
            m = re.match(r"答案\s*([A-D])(?:[，,]\s*(.*))?$", t, re.S)
            if m:
                return m.group(1), normalize_space(m.group(2) or ""), t
            return "", "", t
    return "", "", ""


def related_topic(texts):
    for text in texts:
        t = clean(text)
        if t.startswith("相关考点"):
            parts = [p.strip() for p in t.split(",") if p.strip()]
            return parts[1] if len(parts) > 1 else "相关考点"
    return ""


def first_analysis(texts):
    for i, text in enumerate(texts):
        if clean(text) == "题目解析" and i + 1 < len(texts):
            candidate = clean(texts[i + 1])
            if candidate and not candidate.startswith(("考点", "考友互动", "板书讲题")):
                return normalize_space(candidate)
    for text in texts:
        t = clean(text)
        if len(t) > 30 and ("《" in t or "应当" in t or "不得" in t) and not t.startswith(("相关考点", "板书讲题")):
            return normalize_space(t)
    return ""


def options_for(record, texts):
    q = clean(record["questionKey"])
    try:
        start = next(i for i, t in enumerate(texts) if clean(t) == q or q in clean(t))
    except StopIteration:
        start = 0
    raw = []
    for text in texts[start + 1 :]:
        t = clean(text)
        if not t:
            continue
        if t.startswith("答案") or any(label in t for label in ("秒懂技巧", "速记口诀", "关键字答题")) or t.startswith("秒懂"):
            break
        if t in {"A", "B", "C", "D", "单选", "判断", "新规题"}:
            continue
        if t in {"test back", "答题", "背题", "question setting"}:
            continue
        raw.append(t)
    labels = ["A", "B", "C", "D"]
    return {labels[i]: raw[i] for i in range(min(len(raw), 4))}


def explain(tip, source_explanation, analysis, related, question):
    if source_explanation:
        return source_explanation
    if analysis and len(analysis) <= 180:
        return analysis
    if related:
        return f"适用于{related}相关题。做题时抓住题干关键词，按口诀定位答案。"
    if "看到" in tip or "选" in tip:
        return "这是关键词判断法：题干或选项出现对应关键词时，直接按口诀选答案。"
    if "错" in question or "错误" in question:
        return "注意题干是否问“正确/错误”。先判断口诀本身，再反向处理“错误的是”。"
    return "把口诀对应到题干关键词，优先排除与口诀相反或无关的选项。"


def category_for(tip, question, related):
    text = f"{tip} {question} {related}"
    buckets = [
        ("事故处置与救援", ["事故", "报警", "撤离", "现场", "抢救", "救援", "故障", "牵引", "伤", "危险报警", "警告标志"]),
        ("处罚扣分与法律责任", ["扣", "记", "罚", "拘役", "徒刑", "吊销", "终生", "犯罪", "处罚", "违法", "12分", "9分", "6分", "3分", "1分"]),
        ("驾驶证与车辆登记", ["驾驶证", "准驾", "审验", "换证", "补领", "登记", "实习", "身体", "年龄", "C1", "C2", "C3", "C4", "C6", "A1", "A2", "B1", "B2"]),
        ("灯光仪表与车内装置", ["灯", "雾", "远光", "近光", "仪表", "指示灯", "水温", "ABS", "安全气囊", "安全带", "头枕", "风窗", "刮水", "除霜", "踏板", "开关", "CHECK", "机油", "发动机"]),
        ("标志标线与交警手势", ["标志", "标线", "路面", "手势", "黄线", "白线", "网格", "箭头", "信号灯", "红灯", "绿灯", "黄灯"]),
        ("速度高速与车距车道", ["高速", "车速", "公里", "km", "车距", "车道", "能见度", "匝道", "加速车道", "减速车道", "应急车道"]),
        ("通行规则与安全驾驶", ["超车", "会车", "掉头", "转弯", "停车", "礼让", "行人", "校车", "公交", "铁路", "路口", "让", "减速", "避让"]),
    ]
    for name, keys in buckets:
        if any(k in text for k in keys):
            return name
    return "其他关键词技巧"


def load_records():
    out = []
    for paper in range(1, 6):
        for line in (RAW_DIR / f"paper{paper}.jsonl").read_text().splitlines():
            record = json.loads(line)
            texts = [clean(item["text"]) for item in record["texts"]]
            tip_type, tip, tip_raw = tip_parts(texts)
            answer, answer_explanation, answer_raw = answer_parts(texts)
            options = options_for(record, texts)
            correct = options.get(answer, "")
            related = related_topic(texts)
            analysis = first_analysis(texts)
            out.append(
                {
                    "paper": paper,
                    "index": record["index"],
                    "qid": f"P{paper}-{record['index']:03d}",
                    "question": clean(record["questionKey"]),
                    "tip_type": tip_type,
                    "tip": tip or "未提取到技巧",
                    "tip_raw": tip_raw,
                    "answer": answer,
                    "answer_text": correct,
                    "answer_raw": answer_raw,
                    "explanation": explain(tip, answer_explanation, analysis, related, clean(record["questionKey"])),
                    "related": related,
                    "options": options,
                    "has_image": bool(record.get("hasImageCandidate")),
                }
            )
    return out


def entry_key(item):
    return item["tip"].strip()


def example_line(item):
    answer = item["answer"]
    if item["answer_text"]:
        answer = f"{answer}（{item['answer_text']}）"
    image = "【图题】" if item["has_image"] else ""
    return f"{item['qid']}{image}：{item['question']} 答案：{answer}"


def write_doc(records):
    groups = defaultdict(list)
    for item in records:
        groups[entry_key(item)].append(item)

    category_groups = defaultdict(list)
    for tip, items in groups.items():
        category = category_for(tip, items[0]["question"], items[0]["related"])
        category_groups[category].append((tip, items))

    category_order = [
        "事故处置与救援",
        "处罚扣分与法律责任",
        "驾驶证与车辆登记",
        "灯光仪表与车内装置",
        "标志标线与交警手势",
        "速度高速与车距车道",
        "通行规则与安全驾驶",
        "其他关键词技巧",
    ]

    lines = []
    lines.append("# 科目1精选500题：秒懂技巧与口诀学习文档")
    lines.append("")
    lines.append("来源：驾校一点通「科一精选500题」背题模式。")
    lines.append("")
    lines.append(f"- 覆盖题目：{len(records)} 题")
    lines.append(f"- 归并技巧：{len(groups)} 条")
    lines.append(f"- 图题标记：{sum(1 for r in records if r['has_image'])} 题")
    lines.append("")
    lines.append("## 使用方法")
    lines.append("")
    lines.append("先背“高频速背”，再按主题查漏补缺。每条技巧后面的题号可回到题库定位复习；标有【图题】的题建议结合题图记视觉特征。")
    lines.append("")

    counter = Counter({tip: len(items) for tip, items in groups.items()})
    lines.append("## 高频速背")
    lines.append("")
    lines.append("| 出现 | 口诀/技巧 | 核心用法 | 代表题 |")
    lines.append("|---:|---|---|---|")
    for tip, count in counter.most_common(40):
        items = groups[tip]
        explanation = items[0]["explanation"]
        rep = example_line(items[0]).replace("|", "｜")
        lines.append(f"| {count} | {tip.replace('|', '｜')} | {explanation.replace('|', '｜')} | {rep} |")
    lines.append("")

    lines.append("## 全部技巧索引")
    lines.append("")
    for category in category_order:
        entries = category_groups.get(category, [])
        if not entries:
            continue
        entries.sort(key=lambda pair: (-len(pair[1]), pair[0]))
        lines.append(f"## {category}")
        lines.append("")
        for idx, (tip, items) in enumerate(entries, 1):
            first = items[0]
            type_counts = Counter(item["tip_type"] for item in items)
            type_text = "、".join(f"{k}×{v}" for k, v in type_counts.items())
            ids = "、".join(item["qid"] for item in items[:12])
            if len(items) > 12:
                ids += f" 等{len(items)}题"
            image = "；含图题" if any(item["has_image"] for item in items) else ""
            lines.append(f"### {idx}. {tip}")
            lines.append("")
            lines.append(f"- 类型/频次：{type_text}；出现 {len(items)} 题{image}")
            lines.append(f"- 题号：{ids}")
            lines.append(f"- 解释：{first['explanation']}")
            lines.append("- 代表题：")
            for ex in items[:3]:
                lines.append(f"  - {example_line(ex)}")
            lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    STRUCTURED.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    records = load_records()
    write_doc(records)
    print(f"records={len(records)}")
    print(f"output={OUT}")
    print(f"structured={STRUCTURED}")


if __name__ == "__main__":
    main()
