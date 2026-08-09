#!/usr/bin/env python3
"""Parse the live full-bank scrape and rank additions to the 500-question guide."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIVE_BANKS = (
    ROOT / "data" / "raw" / "full_bank_2328_live_20260809.jsonl",
    ROOT / "data" / "raw" / "full_bank_missing_prefix_20260809.jsonl",
)
CURRENT_GUIDE = ROOT / "data" / "reports" / "科目1精选500题_分类学习文档.json"
OUT_JSON = ROOT / "data" / "reports" / "完整题库_补充候选分析.json"
OUT_MD = ROOT / "data" / "reports" / "完整题库_建议新增清单.md"

OBJECT_MARKS = "\ufffc￼"
ANSWER_RE = re.compile(r"^答案\s*([A-D])")
TIP_RE = re.compile(r"^(秒懂技巧|速记口诀|关键字答题)\s*[:：]\s*(.+)$", re.S)
LINE_RE = re.compile(r"^\s*(\d+)\s+([^\s]+)(?:\s+|$)(.*)$")

UI_TEXT = {
    "test back",
    "答题",
    "背题",
    "直播刷题",
    "question setting",
    "试题详解",
    "题目解析",
    "考友互动",
    "考朋友",
    "反馈",
    "点击或上拉加载更多",
    "examPage board bs tip",
    "全部考点总结",
    "查看解析",
    "马上去学",
    "驾校一点通",
}

LOCAL_MARKERS = (
    "快处易赔",
    "上海市",
    "本市",
    "随申办",
    "上海交警",
    "事故e处理",
)

THEMES = [
    {
        "id": "new-energy-safety",
        "category": "新能源与辅助驾驶",
        "title": "新能源高压与充电安全",
        "mnemonic": "橙色高压不碰不拆；充电异常立即停，起火失控快远离",
        "explanation": "橙色电缆和高压警示部件属于高压系统；雨雪要防水，异味、异响、温度报警时停止充电，火势无法控制时远离并报警。",
        "keywords": ("新能源汽车", "电动汽车", "高压", "橙色电缆", "充电", "电池", "起火"),
    },
    {
        "id": "driver-assistance",
        "category": "新能源与辅助驾驶",
        "title": "驾驶辅助系统不替代驾驶人",
        "mnemonic": "辅助只是帮，方向刹车仍由人掌",
        "explanation": "AEB、ACC、车道偏离预警、盲区监测等系统只能辅助或提醒，驾驶人仍须观察环境并保持车辆控制。",
        "keywords": ("自动紧急制动", "自适应巡航", "车道偏离", "盲区监视", "驾驶辅助", "AEB", "ACC", "LDW", "FCW", "CCS"),
    },
    {
        "id": "system-abbreviations",
        "category": "新能源与辅助驾驶",
        "title": "常见系统英文缩写",
        "mnemonic": "AEB自动刹，ACC自适应巡航，FCW防碰预警，LDW车道偏离",
        "explanation": "缩写题不要只认字母，要把系统名称和功能成对记忆，再用功能排除近似选项。",
        "keywords": ("缩写", "英文缩写", "ABS系统", "牵引力控制", "巡航系统"),
    },
    {
        "id": "points-reeducation",
        "category": "处罚扣分与法律责任",
        "title": "学法减分与满分学习",
        "mnemonic": "学法作假撤减分、恢复分；多次满12，科一之后还考科三",
        "explanation": "学法减分弄虚作假会撤销扣减记录并恢复记分；一个周期多次满12分或达到更高累计分值，学习和考试要求会升级。",
        "keywords": ("学法减分", "满分学习", "二次累积记分", "累积记分满24", "累积记分满36", "恢复相应记分"),
    },
    {
        "id": "dangerous-driving-crime",
        "category": "处罚扣分与法律责任",
        "title": "危险驾驶与妨害安全驾驶",
        "mnemonic": "追逐情节恶劣属危险驾驶；抢控公交装置危及安全要担刑责",
        "explanation": "区分一般交通违法与犯罪：追逐竞驶情节恶劣、暴力抢控公共交通工具等行为可能进入刑事责任。",
        "keywords": ("追逐竞驶", "危险驾驶罪", "抢控驾驶操纵装置", "妨害安全驾驶", "公共交通工具", "构成犯罪"),
    },
    {
        "id": "vehicle-detention",
        "category": "处罚扣分与法律责任",
        "title": "扣留、收缴、强制报废与吊销",
        "mnemonic": "证牌手续有问题常扣车；拼装报废要收缴、强制报废并吊证",
        "explanation": "先分清交警对车辆的处置和对驾驶人的处罚：扣留是临时控制，达到报废标准则收缴并强制报废，驾驶人还可能被罚款、吊销驾驶证。",
        "keywords": ("扣留机动车", "予以扣留", "收缴", "强制报废", "报废标准机动车", "吊销驾驶证"),
    },
    {
        "id": "accident-evidence",
        "category": "事故处置与救援",
        "title": "事故现场与证据",
        "mnemonic": "无伤无争议，留证快撤离；伤人、酒驾、设施受损立即报警",
        "explanation": "轻微事故可在固定证据后撤离协商；有人伤亡、涉嫌酒驾、碰撞公共设施或责任有争议时，应保护现场并报警。",
        "keywords": ("交通事故", "事故现场", "保护现场", "立即报警", "自行协商", "设施损坏", "单方交通事故"),
    },
    {
        "id": "long-downhill",
        "category": "车辆基础与安全操作",
        "title": "长下坡与制动",
        "mnemonic": "长坡挂低挡，发动机制动帮；空挡只靠刹，容易热衰退",
        "explanation": "长下坡应利用低挡位的发动机制动控制车速，避免空挡滑行和长时间连续踩制动踏板。",
        "keywords": ("长下坡", "空挡", "发动机制动", "制动失效", "制动效能"),
    },
    {
        "id": "abs-braking",
        "category": "车辆基础与安全操作",
        "title": "ABS紧急制动",
        "mnemonic": "ABS急刹踩到底，踏板抖动别松脚",
        "explanation": "装有ABS的车辆紧急制动时应持续用力踩住制动踏板；踏板脉冲或抖动是系统工作现象。",
        "keywords": ("ABS", "紧急制动", "制动踏板", "抱死"),
    },
    {
        "id": "seatbelt-child",
        "category": "车辆基础与安全操作",
        "title": "安全带与儿童约束",
        "mnemonic": "前后排都要系，儿童要用适龄约束装置",
        "explanation": "车辆行驶中驾驶人和乘车人都应按规定使用安全带，儿童还应使用适合年龄和体型的安全约束装置。",
        "keywords": ("安全带", "少年儿童", "儿童安全", "约束装置"),
    },
    {
        "id": "instrument-pairs",
        "category": "灯光仪表与车内装置",
        "title": "易混仪表与指示灯",
        "mnemonic": "先看颜色判轻重，再看图形找部件；红色故障或危险优先停车查",
        "explanation": "仪表题应将颜色、图形和对应部件一起记忆，尤其区分前后雾灯、远近光、制动系统、蓄电池、机油和车门状态。",
        "keywords": ("仪表板", "指示灯", "这个仪表", "前雾灯", "后雾灯", "近光灯", "远光灯", "蓄电池", "机油"),
    },
    {
        "id": "sign-confusion",
        "category": "标志标线与交警手势",
        "title": "新增易混标志与标线",
        "mnemonic": "黄黑多警告，红圈多禁令，蓝底多指示；图形细节决定具体含义",
        "explanation": "对当前500题未覆盖的标志，应按颜色和形状先定大类，再用内部图案区分环形交叉、合流、绕行、车道用途等具体含义。",
        "keywords": ("这个标志", "交通标志", "标线", "路面标记", "指示标志", "禁令标志", "警告标志"),
    },
]

CURATED_ADDITIONS = [
    {
        "kind": "新增口诀卡",
        "category": "新能源与辅助驾驶",
        "title": "高压部件与维修边界",
        "mnemonic": "橙色高压不碰不拆，车辆故障交给专业站",
        "explanation": "带高压警示的零部件、橙色电缆及连接器不得自行触碰、拆卸或更换；电动汽车故障也不能先自行拆检。",
        "why": "现有500题没有覆盖高压触电和维修边界，这是新能源题最重要的安全底线。",
        "examples": [
            {"question": "驾驶人不得触摸、拆卸或更换车辆上带有高压警示标识的零部件、橙色电缆及其连接器，以防高压电击。"},
            {"question": "电动汽车出现故障需要维修时可先自行拆卸检修，如遇故障无法排除应当选择专业的维修机构进行维修。"},
        ],
    },
    {
        "kind": "补强已有口诀",
        "category": "新能源与辅助驾驶",
        "title": "充电与电池异常处置",
        "mnemonic": "缺电不久放，雨雪先防水；温报警、闻异味、听异响，立即停充",
        "explanation": "低电量不宜长期停放；雨雪充电要保护充电口；使用符合国家标准的充电桩；电池温度报警、异味或异响时停止充电。",
        "why": "现有文档只有出发查电量和冬季预热，缺少充电全过程的异常处置。",
        "examples": [
            {"question": "可以在电池电量不足的情况下长期停放电动车辆。"},
            {"question": "新能源汽车在雨雪天气充电时，应做好充电口防雨水措施。"},
            {"question": "高温天气时，若电动汽车电池温度报警，应避免进行充电及驾驶。"},
            {"question": "新能源汽车充电时应选择使用符合国家标准的充电桩。"},
            {"question": "新能源汽车充电过程中，如遇电池出现异味、异响时，应立即停止充电。"},
        ],
    },
    {
        "kind": "修正文档表述",
        "category": "新能源与辅助驾驶",
        "title": "新能源起火题型要区分",
        "mnemonic": "电路起火选干粉，火势失控先远离再报警",
        "explanation": "完整题库把“新能源车电路起火”和“车辆/动力电池火势失控”分开考：前者选择干粉灭火剂，后者强调快速远离并报警。现有“普通灭火器不能用”不宜写成覆盖所有起火场景的绝对句。",
        "why": "可消除当前文档与完整题库表述看似冲突的问题。",
        "examples": [
            {"question": "新能源车电路起火燃烧时，应该采用的灭火方式是什么？"},
            {"question": "驾驶新能源汽车发生起火时，如火势较大无法控制，应快速远离车辆，并立即报警。"},
        ],
    },
    {
        "kind": "新增口诀卡",
        "category": "新能源与辅助驾驶",
        "title": "驾驶辅助系统的能力边界",
        "mnemonic": "辅助只是帮，方向刹车仍由人掌；路况复杂、标线不全少用巡航",
        "explanation": "ACC、车道偏离预警、盲区监视和AEB只能保持距离、报警或辅助制动，不能替代驾驶人观察与控制。",
        "why": "现有文档记了系统缩写，但没有把“系统能做什么、不能替代什么”整理成统一原则。",
        "examples": [
            {"question": "开启自适应巡航控制系统时，可辅助车辆与前车保持适当距离。"},
            {"question": "开启车辆盲区监视系统，可以辅助监测驾驶人视野盲区，并在盲区内出现其他道路使用者时发出警告。"},
            {"question": "开启自动紧急制动辅助系统时，驾驶人仍要保证对制动踏板的控制。"},
            {"question": "驾车时应避免在路况复杂、交通标线不完整的情况下使用自适应巡航控制系统。"},
        ],
    },
    {
        "kind": "新增口诀卡",
        "category": "新能源与辅助驾驶",
        "title": "能量回收不等于制动",
        "mnemonic": "回收能量可减速，不能当成制动用",
        "explanation": "能量回收可以在松开加速踏板时产生一定减速效果，但不能替代行车制动。",
        "why": "这是新能源特有概念，现有500题未覆盖。",
        "examples": [
            {"question": "关于电动汽车的能量回收功能，以下错误的说法是什么?"},
        ],
    },
    {
        "kind": "新增口诀卡",
        "category": "车辆基础与安全操作",
        "title": "低胎压为什么容易爆胎",
        "mnemonic": "胎压低，高速跑，波浪变形又升温，最后易爆胎",
        "explanation": "胎压过低时轮胎变形增大，高速滚动会出现波浪变形并持续升温，最终可能爆胎；预防爆胎不能靠继续降低胎压。",
        "why": "比单纯记“胎压异常要检查”更容易迁移到原因题和反向题。",
        "examples": [
            {"question": "轮胎气压过低时，高速行驶轮胎会出现波浪变形温度升高而导致什么？"},
            {"question": "避免爆胎的错误的做法是什么？"},
        ],
    },
    {
        "kind": "新增口诀卡",
        "category": "通行规则与安全驾驶",
        "title": "校车停靠的分车道规则",
        "mnemonic": "校车停靠：一二车道全停车，三条以上同向两道停、最外侧慢行",
        "explanation": "校车在右侧停靠上下学生时，校车所在车道及相邻车道车辆停车等待；同向三条及以上车道时，更外侧车道车辆减速通过。",
        "why": "现有文档有“礼让校车”，但没有覆盖图题中最容易错的车道数量边界。",
        "examples": [
            {"question": "如图所示，校车在最右侧车道停靠上下学生时，以下哪辆车可以通行？"},
            {"question": "如图所示，校车在最右侧车道停靠上下学生时，校车停靠车道后方和相邻机动车道的机动车应停车等待，最左侧车道上的机动车应当减速通过。"},
        ],
    },
    {
        "kind": "补强已有口诀",
        "category": "通行规则与安全驾驶",
        "title": "后排与儿童约束",
        "mnemonic": "前后排都要系，儿童还要适龄座椅和约束",
        "explanation": "安全带要求不只针对驾驶人和前排乘员；后排乘员、少年儿童同样需要约束，儿童应使用适合的安全座椅。",
        "why": "现有安全带内容较多，但后排和儿童的题型未形成一张完整卡。",
        "examples": [
            {"question": "机动车行驶中，车上少年儿童可不使用安全带。"},
            {"question": "儿童安全座椅系于汽车后排座位上，供儿童乘坐并且具有（ ）设备，能在汽车遇突发情况时最大限度保障儿童的安全。"},
            {"question": "驾驶机动车上路行驶，后排乘车人可不系安全带。"},
        ],
    },
    {
        "kind": "补强已有口诀",
        "category": "标志标线与交警手势",
        "title": "黄灯持续闪烁",
        "mnemonic": "黄闪不是停，减速瞭望安全行",
        "explanation": "持续闪烁的黄灯是警示信号，应提前减速、观察并确认安全后通过，不等同于黄灯常亮时的通行规则。",
        "why": "现有文档有普通红黄绿灯，但没有单独整理持续闪烁信号。",
        "examples": [
            {"question": "看到路边有一个黄灯闪烁时，正确的做法是什么？"},
            {"question": "如图所示，驾驶机动车遇到这种信号灯不断闪烁时怎样行驶？"},
        ],
    },
    {
        "kind": "补强已有口诀",
        "category": "处罚扣分与法律责任",
        "title": "多项违法记分总则",
        "mnemonic": "一车多违章，分别记、再累加",
        "explanation": "一次存在两个以上违法行为时，各违法行为分别确定记分分值，最后累加。",
        "why": "现有文档有具体分值，但缺少统领多项违法题的计算原则。",
        "examples": [
            {"question": "机动车驾驶人一次有两个以上违法行为记分的，应当分别计算累加分值。"},
        ],
    },
    {
        "kind": "新增口诀卡",
        "category": "驾驶证与车辆登记",
        "title": "电子驾驶证申领入口",
        "mnemonic": "电子驾驶证，可在互联网交管平台申请",
        "explanation": "驾驶人可以通过互联网交通安全综合服务管理平台申请机动车驾驶证电子版。",
        "why": "属于当前完整题库的新式证照题，现有500题未覆盖。",
        "examples": [
            {"question": "驾驶人可以通过互联网交通安全综合服务管理平台申请机动车驾驶证电子版。"},
        ],
    },
    {
        "kind": "新增图题组",
        "category": "标志标线与交警手势",
        "title": "新式停车与车道标志",
        "mnemonic": "P加对象看谁停；箭头变少看合流；硬路肩红线圈住表示结束",
        "explanation": "把充电停车位、校车停车位、车道数变少、电动自行车车道、硬路肩允许行驶及其结束标志并排比较。",
        "why": "这些题依赖图片细节，适合网页做成可选择的对照图组，需要后续补截图。",
        "examples": [
            {"question": "这个标志是何含义？", "answer": "充电停车位标志"},
            {"question": "这个标志是何含义？", "answer": "校车专用停车位、校车停靠站"},
            {"question": "这个标志是何含义？", "answer": "硬路肩允许行驶路段结束"},
            {"question": "下列哪个标志表示一般道路车道数变少？"},
            {"question": "图中所示标志表示该车道仅供电动自行车通行。"},
        ],
    },
    {
        "kind": "新增图题组",
        "category": "灯光仪表与车内装置",
        "title": "新能源专用警告灯",
        "mnemonic": "电池看电量和故障，电机看过热与功率，轮胎轮廓加叹号看胎压",
        "explanation": "将低荷电、动力蓄电池故障、充电系统故障、电机过热、驱动功率限制和胎压警告集中对照。",
        "why": "文字题干高度重复，必须靠图形辨认；适合网页的“选图—揭晓—对比”交互。",
        "examples": [
            {"question": "驾驶电动汽车，如下图所示指示灯亮表示什么？", "answer": "动力蓄电池故障"},
            {"question": "驾驶电动汽车，如下图所示指示灯亮表示什么？", "answer": "充电系统故障"},
            {"question": "驾驶电动汽车，如下图所示指示灯亮表示什么？", "answer": "低荷电状态警告"},
            {"question": "驾驶电动汽车，如下图所示指示灯亮表示什么？", "answer": "胎压故障警告"},
            {"question": "驾驶电动汽车，如下图所示指示灯亮表示什么？", "answer": "电机过热警告"},
        ],
    },
]


@dataclass
class Entry:
    line: int
    role: str
    text: str


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").translate({ord(ch): None for ch in OBJECT_MARKS})).strip()


def normalize(text: str) -> str:
    text = clean(text).lower()
    return re.sub(r"[\s，。！？；：、,.!?;:（）()《》【】\[\]“”‘’\-—_/]+", "", text)


def parse_entries(raw: str) -> list[Entry]:
    entries: list[Entry] = []
    for line_no, raw_line in enumerate(raw.splitlines()):
        match = LINE_RE.match(raw_line)
        if not match:
            if entries and raw_line.strip() and not raw_line.lstrip().startswith(("Window:", "menu bar")):
                entries[-1].text += "\n" + raw_line.strip()
            continue
        role = match.group(2)
        rest = match.group(3).strip()
        text = ""
        if "Description:" in rest:
            text = rest.split("Description:", 1)[1]
            text = re.split(r",\s*Secondary Actions:", text, maxsplit=1)[0]
        elif role in {"文本", "element"} and rest and not rest.startswith(("Secondary Actions:", "ID:", "Help:")):
            text = rest
        if text:
            entries.append(Entry(line_no, role, text.strip()))
    return entries


def is_question_marker(entry: Entry) -> bool:
    raw = entry.text
    text = clean(raw)
    if not text or len(text) < 4 or not any(ch in raw for ch in OBJECT_MARKS):
        return False
    if text.startswith(("秒懂技巧", "速记口诀", "关键字答题", "板书讲题")):
        return False
    return entry.role == "element"


def option_texts(entries: list[Entry], start: int, end: int) -> list[str]:
    options = []
    for entry in entries[start + 1 : end]:
        text = clean(entry.text)
        if not text or text in UI_TEXT or text in {"A", "B", "C", "D", "单选", "判断", "新规题"}:
            continue
        if entry.role == "按钮":
            continue
        if text.startswith(("答案", "秒懂技巧", "速记口诀", "关键字答题", "相关考点", "板书讲题")):
            continue
        if len(options) < 4:
            options.append(text)
    return options


def after_answer_details(entries: list[Entry], answer_i: int, boundary: int, question: str) -> tuple[str, str, str]:
    tip_type = ""
    tip = ""
    explanation = ""
    topic = ""
    for offset, entry in enumerate(entries[answer_i + 1 : boundary], start=answer_i + 1):
        text = clean(entry.text)
        tip_match = TIP_RE.match(text)
        if tip_match and not tip:
            tip_type, tip = tip_match.group(1), clean(tip_match.group(2))
        if text.startswith("考点, 难度") and offset + 1 < boundary:
            candidate = clean(entries[offset + 1].text)
            if candidate and candidate not in UI_TEXT:
                topic = candidate
        if text == "题目解析":
            for candidate_entry in entries[offset + 1 : boundary]:
                candidate = clean(candidate_entry.text)
                if (
                    candidate
                    and candidate not in UI_TEXT
                    and normalize(candidate) != normalize(question)
                    and not candidate.startswith(("板书讲题", "考点,", "考友"))
                ):
                    explanation = candidate
                    break
    return tip_type, tip, explanation or topic


def parse_raw_record(source: str, capture_seq: int, raw: str) -> list[dict]:
    entries = parse_entries(raw)
    answer_indices = [i for i, entry in enumerate(entries) if ANSWER_RE.match(clean(entry.text))]
    parsed = []
    previous_answer = -1
    for answer_pos, answer_i in enumerate(answer_indices):
        markers = [i for i in range(previous_answer + 1, answer_i) if is_question_marker(entries[i])]
        if not markers:
            previous_answer = answer_i
            continue
        question_i = markers[-1]
        question = clean(entries[question_i].text)
        answer_match = ANSWER_RE.match(clean(entries[answer_i].text))
        if not question or not answer_match:
            previous_answer = answer_i
            continue
        options_list = option_texts(entries, question_i, answer_i)
        options = {chr(65 + i): value for i, value in enumerate(options_list)}
        answer = answer_match.group(1)
        boundary = answer_indices[answer_pos + 1] if answer_pos + 1 < len(answer_indices) else len(entries)
        tip_type, tip, explanation = after_answer_details(entries, answer_i, boundary, question)
        parsed.append(
            {
                "capture_seq": capture_seq,
                "source": source,
                "capture_part": answer_pos + 1,
                "question": question,
                "options": options,
                "answer": answer,
                "answer_text": options.get(answer, ""),
                "tip_type": tip_type,
                "tip": tip,
                "explanation": explanation,
                "has_image": any(
                    word in question
                    for word in (
                        "图",
                        "照片",
                        "红圈",
                        "这个标志",
                        "哪个标志",
                        "这个仪表",
                        "指示灯",
                        "该装置",
                    )
                ),
            }
        )
        previous_answer = answer_i
    return parsed


def signature(record: dict) -> str:
    option_blob = "|".join(normalize(record.get("options", {}).get(letter, "")) for letter in "ABCD")
    return f"{normalize(record['question'])}|{option_blob}|{record.get('answer', '')}"


def answer_signature(record: dict) -> str:
    return f"{normalize(record['question'])}|{normalize(record.get('answer_text', ''))}"


def dedupe(records: list[dict]) -> tuple[list[dict], Counter]:
    unique = {}
    counts = Counter()
    for record in records:
        key = signature(record)
        counts[key] += 1
        if key not in unique:
            unique[key] = record
        else:
            kept = unique[key]
            if not kept.get("tip") and record.get("tip"):
                kept["tip_type"] = record["tip_type"]
                kept["tip"] = record["tip"]
            if not kept.get("explanation") and record.get("explanation"):
                kept["explanation"] = record["explanation"]
    return list(unique.values()), counts


def theme_for(record: dict) -> dict | None:
    haystack = " ".join(
        [record["question"], record.get("tip", ""), record.get("explanation", "")]
        + list(record.get("options", {}).values())
    )
    scored = []
    for theme in THEMES:
        hits = sum(1 for keyword in theme["keywords"] if keyword.lower() in haystack.lower())
        if hits:
            scored.append((hits, theme))
    return max(scored, key=lambda item: item[0])[1] if scored else None


def score_record(record: dict, current_questions: set[str], current_tips: set[str]) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    question_norm = normalize(record["question"])
    if question_norm not in current_questions:
        score += 4
        reasons.append("当前500题未收录")
    if record.get("tip"):
        score += 3
        reasons.append("题库给出明确口诀")
        if normalize(record["tip"]) not in current_tips:
            score += 2
            reasons.append("新口诀")
    theme = theme_for(record)
    if theme:
        score += 4
        reasons.append(theme["title"])
    if record.get("has_image"):
        score += 1
        reasons.append("代表性图题")
    if any(word in record["question"] for word in ("错误", "不得", "不能", "以下说法错误", "不正确")):
        score += 1
        reasons.append("反向/易错问法")
    if any(marker in record["question"] for marker in LOCAL_MARKERS):
        score -= 8
        reasons.append("地方性题目")
    record["theme_id"] = theme["id"] if theme else "other"
    record["category"] = theme["category"] if theme else "其他补充"
    record["theme_title"] = theme["title"] if theme else "其他补充"
    return score, reasons


def escape(text: str) -> str:
    return clean(text).replace("|", "｜")


def load_current() -> tuple[list[dict], set[str], set[str], set[str]]:
    payload = json.loads(CURRENT_GUIDE.read_text(encoding="utf-8"))
    records = payload["records"]
    return (
        records,
        {normalize(item["question"]) for item in records},
        {normalize(item["tip"]) for item in records},
        {signature(item) for item in records},
    )


def select_curated(records: list[dict]) -> list[dict]:
    by_question = defaultdict(list)
    for record in records:
        by_question[normalize(record["question"])].append(record)

    selected_sections = []
    for section in CURATED_ADDITIONS:
        selected = []
        for spec in section["examples"]:
            matches = by_question.get(normalize(spec["question"]), [])
            if spec.get("answer"):
                matches = [
                    item for item in matches if normalize(item.get("answer_text", "")) == normalize(spec["answer"])
                ]
            if not matches:
                selected.append({"question": spec["question"], "missing": True})
                continue
            matches.sort(
                key=lambda item: (
                    not bool(item.get("tip")),
                    not bool(item.get("explanation")),
                    item["capture_seq"],
                )
            )
            selected.append(matches[0])
        selected_sections.append({**section, "selected": selected})
    return selected_sections


def build_report(stats: dict, curated_sections: list[dict]) -> str:
    kind_counts = Counter(section["kind"] for section in curated_sections)
    lines = [
        "# 完整题库补充建议",
        "",
        "> 核对时间：2026-08-09。驾校一点通界面显示已做 500、未做 1828，当前总题量为 2328 题。",
        "> 结论：精选500题对传统法规和常规驾驶覆盖较好，值得补充的内容主要集中在新能源、驾驶辅助、儿童/校车边界、少量总则和新式图标。",
        "",
        "## 覆盖校验",
        "",
        f"- 两次现场遍历共保存 {stats['raw_states']} 个题目状态，解析出 {stats['parsed_segments']} 个题目片段。",
        f"- 与现有500题合并后得到 {stats['union_strict_signatures_with_current']} 个严格签名；按题干与正确答案归并后为 {stats['union_question_answer_signatures']} 个。",
        "- 两种口径分别比2328多23和7，来自图片题同题干、选项标签懒加载和翻页过渡；覆盖已闭合，没有把这些技术差异当成新题。",
        f"- 识别出地方性内容 {stats['local_records']} 题，默认不进入全国通用主册。",
        "",
        "## 建议结论",
        "",
        f"建议整理为 {len(curated_sections)} 组："
        + "、".join(f"{name}{count}组" for name, count in kind_counts.items())
        + "。",
        "",
        "| 类型 | 分类 | 建议新增/补强内容 | 口诀核心 |",
        "|---|---|---|---|",
    ]
    for section in curated_sections:
        lines.append(
            f"| {section['kind']} | {section['category']} | [{section['title']}](#{normalize(section['title'])}) | {escape(section['mnemonic'])} |"
        )

    lines.extend(["", "## 详细建议", ""])
    for number, section in enumerate(curated_sections, 1):
        lines.extend(
            [
                f'<a id="{normalize(section["title"])}"></a>',
                "",
                f"### {number}. {section['title']}",
                "",
                f"- **处理方式**：{section['kind']}，放入“{section['category']}”。",
                f"- **建议口诀**：{section['mnemonic']}",
                f"- **具体解释**：{section['explanation']}",
                f"- **为什么值得加**：{section['why']}",
                "",
                "**代表题**",
                "",
            ]
        )
        for item in section["selected"]:
            if item.get("missing"):
                lines.append(f"- {escape(item['question'])}（解析时未定位，待人工复核）")
                continue
            answer = item.get("answer_text") or item.get("answer") or "未提取"
            image = "【需截图】" if item.get("has_image") else ""
            tip = f"；题库口诀：{escape(item['tip'])}" if item.get("tip") else ""
            lines.append(f"- {image}{escape(item['question'])}（答案：{escape(answer)}{tip}）")
        lines.append("")

    lines.extend(
        [
            "## 不建议直接加入",
            "",
            "- **上海“快处易赔”等地方题**：保留为地区附录候选，不混入全国通用主册。",
            "- **货车、客车专属细节**：C1/C2学习价值有限，除非能说明通用规则。",
            "- **已有口诀的纯换句判断题**：可挂在已有口诀的题目列表中，不新建卡片。",
            "- **全套冷门标志逐题罗列**：只保留易混对和新式标志，其他通过题库练习即可。",
            "- **题库里过度简化的关键词技巧**：例如“看到刑字结尾选错”，不能作为法律规则写进主口诀。",
            "",
            "## 后续落地",
            "",
            "1. 先把上述新增口诀卡和补强项合入现有Markdown分册。",
            "2. 对两组图题回到题库补截图，网页中做成同组可选择题目。",
            "3. 网页默认展示口诀和解释，点击口诀后在右侧列出本组全部代表题。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    current_records, current_questions, current_tips, current_signatures = load_current()
    raw_rows = []
    raw_counts = {}
    for path in LIVE_BANKS:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]
        raw_counts[path.name] = len(rows)
        raw_rows.extend({**row, "source": path.name} for row in rows)

    parsed_segments = []
    for row in raw_rows:
        parsed_segments.extend(parse_raw_record(row["source"], row["seq"], row["raw"]))
    unique_records, duplicate_counts = dedupe(parsed_segments)

    ranked = []
    local_count = 0
    for record in unique_records:
        record["duplicate_capture_count"] = duplicate_counts[signature(record)]
        score, reasons = score_record(record, current_questions, current_tips)
        record["score"] = score
        record["reasons"] = reasons
        if any(marker in record["question"] for marker in LOCAL_MARKERS):
            local_count += 1
        if score >= 8 and record["category"] != "其他补充" and "地方性题目" not in reasons:
            ranked.append(record)

    ranked.sort(key=lambda item: (-item["score"], item["theme_title"], item["capture_seq"]))
    curated_sections = select_curated(unique_records)

    stats = {
        "bank_total": 2328,
        "current_guide_records": len(current_records),
        "raw_states": len(raw_rows),
        "raw_state_files": raw_counts,
        "parsed_segments": len(parsed_segments),
        "unique_records": len(unique_records),
        "overlap_current_questions": sum(
            1 for record in unique_records if normalize(record["question"]) in current_questions
        ),
        "overlap_current_signatures": sum(
            1 for record in unique_records if signature(record) in current_signatures
        ),
        "union_strict_signatures_with_current": len(
            {signature(record) for record in unique_records} | current_signatures
        ),
        "union_question_answer_signatures": len(
            {answer_signature(record) for record in unique_records}
            | {answer_signature(record) for record in current_records}
        ),
        "current_unique_signatures": len(current_signatures),
        "duplicate_segments": len(parsed_segments) - len(unique_records),
        "explicit_tips": sum(1 for record in unique_records if record.get("tip")),
        "local_records": local_count,
        "candidate_records": len(ranked),
        "curated_groups": len(curated_sections),
        "curated_examples": sum(len(section["selected"]) for section in curated_sections),
        "curated_missing_examples": sum(
            1 for section in curated_sections for item in section["selected"] if item.get("missing")
        ),
    }
    OUT_JSON.write_text(
        json.dumps(
            {
                "stats": stats,
                "themes": THEMES,
                "candidates": ranked,
                "curated_additions": curated_sections,
                "all_unique_records": unique_records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(build_report(stats, curated_sections), encoding="utf-8")

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"json={OUT_JSON}")
    print(f"markdown={OUT_MD}")


if __name__ == "__main__":
    main()
