#!/usr/bin/env python3
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
REPORT_DIR = ROOT / "data" / "reports"
IMAGE_DIR = REPORT_DIR / "images"
OUT_DIR = REPORT_DIR / "科目1精选500题_分类学习文档"
STRUCTURED = REPORT_DIR / "科目1精选500题_分类学习文档.json"

PAPER_NAMES = {
    1: "试卷1 高频100题",
    2: "试卷2 高频100题",
    3: "试卷3 高频100题",
    4: "试卷4 易错100题",
    5: "试卷5 冲刺100题",
}

CATEGORIES = [
    {
        "slug": "01_事故处置与救援",
        "title": "事故处置与救援",
        "focus": "先保命、再报警、再按规定设置警告和撤离。",
        "keys": ["事故", "报警", "撤离", "现场", "抢救", "救援", "故障", "牵引", "伤", "危险报警", "警告标志", "逃逸", "爆胎"],
    },
    {
        "slug": "02_处罚扣分与法律责任",
        "title": "处罚扣分与法律责任",
        "focus": "数字题先认违法类型，再背分值、罚款、拘留、吊销和刑责。",
        "keys": ["扣", "记", "罚", "拘役", "徒刑", "吊销", "终生", "犯罪", "处罚", "违法", "12分", "9分", "6分", "3分", "1分", "拘留", "罚款", "满分"],
    },
    {
        "slug": "03_驾驶证与车辆登记",
        "title": "驾驶证与车辆登记",
        "focus": "围绕人和车的资格：申领、换证、审验、登记、备案和准驾。",
        "keys": ["驾驶证", "准驾", "审验", "换证", "补领", "登记", "备案", "实习", "身体", "年龄", "C1", "C2", "C3", "C4", "C6", "A1", "A2", "B1", "B2", "车辆管理所"],
    },
    {
        "slug": "04_灯光仪表与车内装置",
        "title": "灯光仪表与车内装置",
        "focus": "图像题看形状、颜色、箭头方向和部件位置。",
        "keys": ["灯", "雾", "远光", "近光", "仪表", "指示灯", "水温", "ABS", "安全气囊", "安全带", "头枕", "风窗", "刮水", "除霜", "踏板", "开关", "CHECK", "机油", "发动机", "油箱", "制动系统", "转向"],
    },
    {
        "slug": "05_标志标线与交警手势",
        "title": "标志标线与交警手势",
        "focus": "识别颜色、形状、线型、箭头和交警身体朝向。",
        "keys": ["标志", "标线", "路面", "手势", "黄线", "白线", "网格", "箭头", "信号灯", "红灯", "绿灯", "黄灯", "虚线", "实线", "导流线"],
    },
    {
        "slug": "06_速度高速与车距车道",
        "title": "速度高速与车距车道",
        "focus": "把速度、能见度、车距、车道和高速场景连成一套数字表。",
        "keys": ["高速", "车速", "公里", "km", "车距", "车道", "能见度", "匝道", "加速车道", "减速车道", "应急车道", "限速", "速度"],
    },
    {
        "slug": "07_通行规则与安全驾驶",
        "title": "通行规则与安全驾驶",
        "focus": "遇到路口、转弯、会车、超车、行人和特殊车辆，默认减速让行、保证安全。",
        "keys": ["超车", "会车", "掉头", "转弯", "停车", "礼让", "行人", "校车", "公交", "铁路", "路口", "让", "减速", "避让", "依次", "变更车道", "靠边"],
    },
    {
        "slug": "08_其他关键词技巧",
        "title": "其他关键词技巧",
        "focus": "收纳跨主题关键词、判断题陷阱和少量不易归类的口诀。",
        "keys": [],
    },
]

CATEGORY_BY_TITLE = {item["title"]: item for item in CATEGORIES}


def clean(text: str) -> str:
    return (
        (text or "")
        .replace("\ufffc", "")
        .replace("￼", "")
        .replace("\u200b", "")
        .strip()
    )


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", clean(text)).strip()


def escape_table(text: str) -> str:
    return normalize_space(text).replace("|", "｜")


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
    if analysis and len(analysis) <= 220:
        return analysis
    if related:
        return f"适用于{related}相关题。做题时先抓题干关键词，再按口诀定位答案。"
    if "看到" in tip or "找" in tip or "选" in tip:
        return "这是关键词判断法：题干或选项出现对应词时，按口诀直接定位或排除。"
    if "错" in question or "错误" in question:
        return "先判断口诀本身，再处理题干里的“正确/错误”问法，避免反向掉坑。"
    return "把口诀对应到题干关键词，优先排除与口诀相反或无关的选项。"


def usage_note(tip, explanation, items):
    joined_questions = " ".join(item["question"] for item in items[:5])
    if "看到" in tip or "找" in tip:
        return "先圈出题干关键词，再到选项里找口诀提示的答案词。"
    if "选" in tip:
        return "这类题适合快速直选；但遇到“错误的是、不能、不得”要先看清正反问法。"
    if any(word in tip for word in ["扣", "分", "罚", "吊销", "拘留"]):
        return "把违法行为和数字绑定记忆，题干变换时只要认出行为即可。"
    if any(word in joined_questions for word in ["如图", "图所示", "指示灯", "标线", "标志", "手势"]):
        return "先看图形特征，再回到题干确认问的是名称、含义还是操作。"
    if explanation:
        return explanation
    return "把这句口诀当作判断锚点，先排除明显违背安全原则的选项。"


def score_category(item):
    text = f"{item['tip']} {item['question']} {item['related']} {item['explanation']}"
    scores = {}
    for category in CATEGORIES[:-1]:
        score = 0
        for key in category["keys"]:
            if key in item["tip"]:
                score += 3
            if key in item["question"]:
                score += 2
            if key in item["related"] or key in item["explanation"]:
                score += 1
            if key and key in text:
                score += 1
        scores[category["title"]] = score
    best_title, best_score = max(scores.items(), key=lambda pair: pair[1])
    return best_title if best_score > 0 else "其他关键词技巧"


def category_for_group(items):
    votes = Counter()
    for item in items:
        votes[score_category(item)] += 1
    return votes.most_common(1)[0][0] if votes else "其他关键词技巧"


def load_records():
    records = []
    for paper in range(1, 6):
        path = RAW_DIR / f"paper{paper}.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            texts = [clean(item["text"]) for item in record["texts"]]
            tip_type, tip, tip_raw = tip_parts(texts)
            answer, answer_explanation, answer_raw = answer_parts(texts)
            options = options_for(record, texts)
            correct = options.get(answer, "")
            related = related_topic(texts)
            analysis = first_analysis(texts)
            qid = f"P{paper}-{record['index']:03d}"
            image_path = IMAGE_DIR / f"{qid}.png"
            records.append(
                {
                    "paper": paper,
                    "paper_name": PAPER_NAMES[paper],
                    "index": record["index"],
                    "qid": qid,
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
                    "image_file": image_path.name if image_path.exists() else "",
                }
            )
    return records


def group_records(records):
    groups = defaultdict(list)
    for item in records:
        groups[item["tip"].strip()].append(item)

    grouped = []
    for tip, items in groups.items():
        items.sort(key=lambda row: (row["paper"], row["index"]))
        category = category_for_group(items)
        grouped.append(
            {
                "tip": tip,
                "category": category,
                "items": items,
                "count": len(items),
                "image_count": sum(1 for item in items if item["has_image"]),
                "type_counts": Counter(item["tip_type"] for item in items),
            }
        )
    grouped.sort(key=lambda group: (-group["count"], group["tip"]))
    return grouped


def representative_items(items, limit=3):
    image_items = [item for item in items if item["image_file"]]
    plain_items = [item for item in items if not item["image_file"]]
    selected = []
    for item in image_items + plain_items:
        if item["qid"] not in {row["qid"] for row in selected}:
            selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def answer_text(item):
    if item["answer_text"]:
        return f"{item['answer']}（{item['answer_text']}）"
    return item["answer"] or "未提取"


def image_markdown(item):
    if not item["image_file"]:
        return []
    return ["", f"![{item['qid']}题图](../images/{item['image_file']})", ""]


def write_question_card(lines, item, heading_level=4):
    hashes = "#" * heading_level
    lines.append(f"{hashes} {item['qid']}｜{item['paper_name']}")
    lines.append("")
    lines.append(f"**原题**：{item['question']}")
    lines.extend(image_markdown(item))
    if item["options"]:
        lines.append("")
        lines.append("**选项**")
        for label in ["A", "B", "C", "D"]:
            if label in item["options"]:
                lines.append(f"- {label}. {item['options'][label]}")
    lines.append("")
    lines.append(f"**答案**：{answer_text(item)}")
    lines.append(f"**秒懂技巧**：{item['tip']}")
    lines.append(f"**解释**：{item['explanation']}")
    if item["related"]:
        lines.append(f"**相关考点**：{item['related']}")
    lines.append("")


def group_anchor(category_slug, number):
    return f"{category_slug}-tip-{number:03d}"


def write_category_doc(category, groups):
    title = category["title"]
    path = OUT_DIR / f"{category['slug']}.md"
    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"学习重点：{category['focus']}")
    lines.append("")
    lines.append(f"- 覆盖口诀：{len(groups)} 条")
    lines.append(f"- 覆盖原题：{sum(group['count'] for group in groups)} 题")
    lines.append(f"- 含图原题：{sum(group['image_count'] for group in groups)} 题")
    lines.append("")

    lines.append("## 本章速背")
    lines.append("")
    lines.append("| 出现 | 口诀/技巧 | 怎么用 | 代表原题 |")
    lines.append("|---:|---|---|---|")
    for number, group in enumerate(groups, 1):
        rep = group["items"][0]
        link = f"#{group_anchor(category['slug'], number)}"
        how = usage_note(group["tip"], rep["explanation"], group["items"])
        lines.append(
            f"| {group['count']} | [{escape_table(group['tip'])}]({link}) | {escape_table(how)} | {rep['qid']}：{escape_table(rep['question'])} |"
        )
    lines.append("")

    lines.append("## 口诀卡片")
    lines.append("")
    for number, group in enumerate(groups, 1):
        anchor = group_anchor(category["slug"], number)
        first = group["items"][0]
        type_text = "、".join(f"{name}×{count}" for name, count in group["type_counts"].items())
        qids = "、".join(item["qid"] for item in group["items"])
        image_note = f"；含图 {group['image_count']} 题" if group["image_count"] else ""

        lines.append(f'<a id="{anchor}"></a>')
        lines.append("")
        lines.append(f"### {number}. {group['tip']}")
        lines.append("")
        lines.append(f"> 记忆核心：{first['explanation']}")
        lines.append(f"> 使用方法：{usage_note(group['tip'], first['explanation'], group['items'])}")
        lines.append("")
        lines.append(f"- 类型/频次：{type_text}；共 {group['count']} 题{image_note}")
        lines.append(f"- 对应题号：{qids}")
        lines.append("")
        lines.append("#### 代表原题")
        lines.append("")
        reps = representative_items(group["items"])
        for item in reps:
            write_question_card(lines, item, heading_level=5)

        rep_ids = {item["qid"] for item in reps}
        remaining = [item for item in group["items"] if item["qid"] not in rep_ids]
        if remaining:
            lines.append(f"<details>")
            lines.append(f"<summary>展开其余 {len(remaining)} 道对应原题</summary>")
            lines.append("")
            for item in remaining:
                write_question_card(lines, item, heading_level=5)
            lines.append("</details>")
            lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_overview(records, groups, category_groups):
    path = OUT_DIR / "00_总览与速背目录.md"
    image_expected = sum(1 for item in records if item["has_image"])
    image_ready = sum(1 for item in records if item["image_file"])
    lines = []
    lines.append("# 科目1精选500题分类学习文档")
    lines.append("")
    lines.append("来源：驾校一点通「科一精选500题」背题模式。本文档按口诀和题型重新组织，适合先背技巧、再看原题巩固。")
    lines.append("")
    lines.append("## 覆盖情况")
    lines.append("")
    lines.append(f"- 原题总数：{len(records)} 题")
    lines.append(f"- 归并口诀：{len(groups)} 条")
    lines.append(f"- 图题收录：{image_ready}/{image_expected} 张")
    lines.append("")
    lines.append("## 分册目录")
    lines.append("")
    for category in CATEGORIES:
        cgroups = category_groups.get(category["title"], [])
        question_count = sum(group["count"] for group in cgroups)
        image_count = sum(group["image_count"] for group in cgroups)
        lines.append(
            f"- [{category['title']}]({category['slug']}.md)：{len(cgroups)} 条口诀，{question_count} 道原题，{image_count} 道图题。{category['focus']}"
        )
    lines.append("")

    lines.append("## 最高频速背")
    lines.append("")
    lines.append("| 出现 | 口诀/技巧 | 所在分册 | 快速用法 |")
    lines.append("|---:|---|---|---|")
    for group in sorted(groups, key=lambda row: (-row["count"], row["tip"]))[:50]:
        category = CATEGORY_BY_TITLE[group["category"]]
        number = category_groups[group["category"]].index(group) + 1
        link = f"{category['slug']}.md#{group_anchor(category['slug'], number)}"
        how = usage_note(group["tip"], group["items"][0]["explanation"], group["items"])
        lines.append(
            f"| {group['count']} | [{escape_table(group['tip'])}]({link}) | {category['title']} | {escape_table(how)} |"
        )
    lines.append("")

    lines.append("## 复习路线")
    lines.append("")
    lines.append("1. 先读本页“最高频速背”，把出现多次的口诀背熟。")
    lines.append("2. 再按分册阅读“本章速背”，把同类题放在一起记。")
    lines.append("3. 最后展开每条口诀下的原题，重点看自己容易混淆的题图、数字和反向问法。")
    lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_index(records, groups_by_qid):
    path = OUT_DIR / "09_题号索引.md"
    lines = ["# 题号索引", "", "按原始试卷顺序列出 500 道题，方便回到题库定位。", ""]
    for paper in range(1, 6):
        lines.append(f"## {PAPER_NAMES[paper]}")
        lines.append("")
        lines.append("| 题号 | 原题 | 技巧 | 分册 |")
        lines.append("|---|---|---|---|")
        for item in [row for row in records if row["paper"] == paper]:
            group = groups_by_qid[item["qid"]]
            category = CATEGORY_BY_TITLE[group["category"]]
            number = group["_number"]
            link = f"{category['slug']}.md#{group_anchor(category['slug'], number)}"
            image_tag = "【图】" if item["has_image"] else ""
            lines.append(
                f"| {item['qid']} | {image_tag}{escape_table(item['question'])} | [{escape_table(item['tip'])}]({link}) | {category['title']} |"
            )
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def main():
    records = load_records()
    groups = group_records(records)

    category_groups = {category["title"]: [] for category in CATEGORIES}
    for group in groups:
        category_groups[group["category"]].append(group)
    for category in CATEGORIES:
        category_groups[category["title"]].sort(key=lambda group: (-group["count"], group["tip"]))
        for number, group in enumerate(category_groups[category["title"]], 1):
            group["_number"] = number

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = [write_overview(records, groups, category_groups)]
    for category in CATEGORIES:
        written.append(write_category_doc(category, category_groups[category["title"]]))

    groups_by_qid = {}
    for group in groups:
        for item in group["items"]:
            groups_by_qid[item["qid"]] = group
    written.append(write_index(records, groups_by_qid))

    STRUCTURED.write_text(
        json.dumps({"records": records, "groups": groups}, ensure_ascii=False, indent=2, default=dict),
        encoding="utf-8",
    )

    print(f"records={len(records)}")
    print(f"groups={len(groups)}")
    print(f"docs={len(written)}")
    print(f"out_dir={OUT_DIR}")
    print(f"images={sum(1 for item in records if item['image_file'])}/{sum(1 for item in records if item['has_image'])}")


if __name__ == "__main__":
    main()
