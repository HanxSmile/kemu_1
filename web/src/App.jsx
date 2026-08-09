import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  BookOpenText,
  CaretDown,
  CaretLeft,
  CaretRight,
  Check,
  CheckCircle,
  Circle,
  Exam,
  Eye,
  Gauge,
  HashStraight,
  ImageSquare,
  Key,
  List,
  MagnifyingGlass,
  Rows,
  Scales,
  ShieldCheck,
  Sparkle,
  SquaresFour,
  UsersThree,
  X,
} from "@phosphor-icons/react";
import studyData from "./study-data.json";

const STORAGE_KEY = "kemu1-study-state-v1";

const mnemonicIcons = {
  数字记忆: HashStraight,
  图形识别: ImageSquare,
  关键词直选: Key,
  行为原则: UsersThree,
  法规归纳: Scales,
};

const categoryIcons = {
  事故处置与救援: ShieldCheck,
  处罚扣分与法律责任: Scales,
  驾驶证与车辆登记: BookOpenText,
  灯光仪表与车内装置: Gauge,
  标志标线与交警手势: ImageSquare,
  速度高速与车距车道: Rows,
  通行规则与安全驾驶: UsersThree,
  新能源与辅助驾驶: Sparkle,
  其他关键词技巧: SquaresFour,
};

function loadStudyState() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    return {
      remembered: Array.isArray(value.remembered) ? value.remembered : [],
      questions: value.questions && typeof value.questions === "object" ? value.questions : {},
    };
  } catch {
    return { remembered: [], questions: {} };
  }
}

function assetUrl(path) {
  return path ? `${import.meta.env.BASE_URL}${path}` : "";
}

function ColorizedTip({ children }) {
  const text = String(children);
  if (!text.includes("红高蓝低黄建议黑解除")) return <>{text}</>;
  const colors = { 红: "red", 蓝: "blue", 黄: "yellow", 黑: "black" };
  return (
    <>
      {text.split(/(红|蓝|黄|黑)/).map((part, index) =>
        colors[part] ? (
          <span className={`tip-color tip-color-${colors[part]}`} key={`${part}-${index}`}>
            {part}
          </span>
        ) : (
          part
        ),
      )}
    </>
  );
}

function Segmented({ mode, onChange }) {
  return (
    <div className="segmented" aria-label="学习分类方式">
      <button className={mode === "chapter" ? "active" : ""} onClick={() => onChange("chapter")}>
        按章节
      </button>
      <button className={mode === "mnemonic" ? "active" : ""} onClick={() => onChange("mnemonic")}>
        按口诀
      </button>
    </div>
  );
}

function FilterList({ mode, selected, onSelect }) {
  const items = mode === "chapter" ? studyData.categories : studyData.mnemonicTypes;
  return (
    <nav className="filter-list" aria-label={mode === "chapter" ? "章节" : "口诀分类"}>
      {items.map((item) => {
        const Icon = mode === "chapter" ? categoryIcons[item.id] || BookOpenText : mnemonicIcons[item.id] || Key;
        return (
          <button
            className={`filter-item ${selected === item.id ? "active" : ""}`}
            key={item.id}
            onClick={() => onSelect(item.id)}
          >
            <span className="filter-icon" aria-hidden="true">
              <Icon size={24} weight={selected === item.id ? "fill" : "regular"} />
            </span>
            <span className="filter-copy">
              <strong>{mode === "chapter" ? item.short : item.id}</strong>
              <small>{item.groupCount} 条口诀</small>
            </span>
          </button>
        );
      })}
    </nav>
  );
}

function QuestionStatus({ status }) {
  if (status === "mastered") return <span className="status mastered">已掌握</span>;
  if (status === "tricky") return <span className="status tricky">易混</span>;
  return <span className="status idle">未学习</span>;
}

function ProgressRing({ value }) {
  return (
    <div className="progress-ring" style={{ "--progress": `${value * 3.6}deg` }}>
      <div>
        <strong>{value}%</strong>
        <span>口诀进度</span>
      </div>
    </div>
  );
}

export function App() {
  const initialGroup = studyData.groups.find((group) => group.tip.includes("红高蓝低黄建议黑解除")) || studyData.groups[0];
  const [mode, setMode] = useState("mnemonic");
  const [filter, setFilter] = useState(initialGroup.mnemonicType);
  const [groupId, setGroupId] = useState(initialGroup.id);
  const [questionId, setQuestionId] = useState(initialGroup.items[0]?.id || "");
  const [rightView, setRightView] = useState("questions");
  const [practiceMode, setPracticeMode] = useState("study");
  const [selectedOption, setSelectedOption] = useState("");
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);
  const [studyState, setStudyState] = useState(loadStudyState);
  const searchRef = useRef(null);

  const currentGroup = studyData.groups.find((group) => group.id === groupId) || initialGroup;
  const currentQuestion = currentGroup.items.find((item) => item.id === questionId) || currentGroup.items[0];
  const filteredGroups = useMemo(
    () =>
      studyData.groups.filter((group) =>
        mode === "chapter" ? group.category === filter : group.mnemonicType === filter,
      ),
    [mode, filter],
  );
  const groupIndex = Math.max(
    0,
    filteredGroups.findIndex((group) => group.id === currentGroup.id),
  );
  const questionIndex = Math.max(
    0,
    currentGroup.items.findIndex((item) => item.id === currentQuestion?.id),
  );
  const rememberedSet = useMemo(() => new Set(studyState.remembered), [studyState.remembered]);
  const progress = Math.round((rememberedSet.size / studyData.groups.length) * 100);

  const searchResults = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return [];
    return studyData.groups
      .filter((group) =>
        [group.title, group.tip, group.explanation, ...group.items.map((item) => item.question)]
          .join(" ")
          .toLowerCase()
          .includes(keyword),
      )
      .slice(0, 10);
  }, [query]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(studyState));
  }, [studyState]);

  useEffect(() => {
    setSelectedOption("");
  }, [groupId, questionId, practiceMode]);

  useEffect(() => {
    const close = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) setSearchOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);

  function selectGroup(group, view = "questions") {
    setGroupId(group.id);
    setQuestionId(group.items[0]?.id || "");
    setFilter(mode === "chapter" ? group.category : group.mnemonicType);
    setRightView(view);
    setSearchOpen(false);
    setQuery("");
    setLeftOpen(false);
  }

  function selectFilter(nextFilter) {
    setFilter(nextFilter);
    const first = studyData.groups.find((group) =>
      mode === "chapter" ? group.category === nextFilter : group.mnemonicType === nextFilter,
    );
    if (first) selectGroup(first, "groups");
  }

  function changeMode(nextMode) {
    setMode(nextMode);
    setFilter(nextMode === "chapter" ? currentGroup.category : currentGroup.mnemonicType);
    setRightView("groups");
  }

  function stepGroup(delta) {
    if (!filteredGroups.length) return;
    const next = filteredGroups[(groupIndex + delta + filteredGroups.length) % filteredGroups.length];
    selectGroup(next);
  }

  function selectQuestion(item) {
    setQuestionId(item.id);
    setRightView("questions");
    setRightOpen(false);
  }

  function toggleRemembered() {
    setStudyState((current) => {
      const set = new Set(current.remembered);
      if (set.has(currentGroup.id)) set.delete(currentGroup.id);
      else set.add(currentGroup.id);
      return { ...current, remembered: [...set] };
    });
  }

  function markQuestion(status) {
    if (!currentQuestion) return;
    setStudyState((current) => ({
      ...current,
      questions: { ...current.questions, [currentQuestion.id]: status },
    }));
  }

  function chooseOption(letter) {
    if (practiceMode !== "quiz" || selectedOption) return;
    setSelectedOption(letter);
    markQuestion(letter === currentQuestion.answer ? "mastered" : "tricky");
  }

  function stepQuestion(delta) {
    const items = currentGroup.items;
    const next = items[(questionIndex + delta + items.length) % items.length];
    selectQuestion(next);
  }

  const showAnswer = practiceMode === "study" || Boolean(selectedOption);
  const correctAnswer = currentQuestion?.answer;
  const currentQuestionStatus = currentQuestion ? studyState.questions[currentQuestion.id] : "";

  return (
    <div className="study-shell">
      <div className={`scrim ${leftOpen || rightOpen ? "visible" : ""}`} onClick={() => { setLeftOpen(false); setRightOpen(false); }} />

      <aside className={`left-sidebar ${leftOpen ? "open" : ""}`}>
        <div className="brand-row">
          <BookOpenText size={27} weight="fill" />
          <strong>{studyData.meta.title}</strong>
          <button className="icon-button mobile-only" onClick={() => setLeftOpen(false)} aria-label="关闭分类">
            <X size={20} />
          </button>
        </div>
        <Segmented mode={mode} onChange={changeMode} />
        <FilterList mode={mode} selected={filter} onSelect={selectFilter} />
        <div className="sidebar-meta">
          <span>{studyData.meta.bankVersion}</span>
          <strong>{studyData.meta.groupCount} 条口诀 · {studyData.meta.questionCount} 道代表题</strong>
        </div>
      </aside>

      <main className="study-main">
        <header className="topbar">
          <button className="icon-button nav-trigger" onClick={() => setLeftOpen(true)} aria-label="打开分类">
            <List size={21} />
          </button>
          <div className="breadcrumbs">
            <span>{mode === "chapter" ? "按章节" : "按口诀"}</span>
            <CaretRight size={14} />
            <span>{filter}</span>
            <CaretRight size={14} />
            <strong>{currentGroup.title}</strong>
          </div>
          <div className="top-actions">
            <div className="search" ref={searchRef}>
              <MagnifyingGlass size={18} />
              <input
                value={query}
                onChange={(event) => { setQuery(event.target.value); setSearchOpen(true); }}
                onFocus={() => setSearchOpen(true)}
                placeholder="搜索口诀或题目"
                aria-label="搜索口诀或题目"
              />
              {query && (
                <button onClick={() => setQuery("")} aria-label="清空搜索">
                  <X size={16} />
                </button>
              )}
              {searchOpen && query && (
                <div className="search-results">
                  {searchResults.length ? (
                    searchResults.map((group) => (
                      <button key={group.id} onClick={() => selectGroup(group)}>
                        <span>{group.tip}</span>
                        <small>{group.category} · {group.items.length}题</small>
                      </button>
                    ))
                  ) : (
                    <div className="search-empty">没有找到相关口诀</div>
                  )}
                </div>
              )}
            </div>
            <button className="icon-button right-trigger" onClick={() => setRightOpen(true)} aria-label="打开关联题目">
              <Rows size={21} />
            </button>
          </div>
        </header>

        <article className="lesson">
          <div className="lesson-heading">
            <div className="eyebrow-row">
              <span className="source-badge">{currentGroup.kind}</span>
              <span>{currentGroup.mnemonicType}</span>
              <span>{currentGroup.items.length} 道关联题</span>
            </div>
            <h1><ColorizedTip>{currentGroup.tip}</ColorizedTip></h1>
          </div>

          <section className="explanation-block">
            <h2>怎么用</h2>
            <p>{currentGroup.explanation}</p>
            <div className="usage-line">
              <span>答题方法</span>
              <p>{currentGroup.usage}</p>
            </div>
          </section>

          <section className="question-section">
            <div className="question-toolbar">
              <button className="linked-count" onClick={() => { setRightView("questions"); setRightOpen(true); }}>
                关联原题 {currentGroup.items.length} 道
              </button>
              <div className="question-mode" aria-label="答题模式">
                <button className={practiceMode === "study" ? "active" : ""} onClick={() => setPracticeMode("study")}>
                  <Eye size={17} /> 背题
                </button>
                <button className={practiceMode === "quiz" ? "active" : ""} onClick={() => setPracticeMode("quiz")}>
                  <Exam size={17} /> 练习
                </button>
              </div>
              <div className="question-pager">
                <button className="icon-button" onClick={() => stepQuestion(-1)} aria-label="上一题">
                  <CaretLeft size={20} />
                </button>
                <span>{questionIndex + 1} / {currentGroup.items.length}</span>
                <button className="icon-button" onClick={() => stepQuestion(1)} aria-label="下一题">
                  <CaretRight size={20} />
                </button>
              </div>
            </div>

            {currentQuestion && (
              <div className={`question-layout ${currentQuestion.image ? "has-image" : ""}`}>
                <div className="question-copy">
                  <div className="question-source">
                    <span>{currentQuestion.id}</span>
                    <QuestionStatus status={currentQuestionStatus} />
                  </div>
                  <h2>{currentQuestion.question}</h2>
                  {currentQuestion.image && (
                    <img className="question-image" src={assetUrl(currentQuestion.image)} alt={`${currentQuestion.id} 题图`} />
                  )}
                </div>

                <div className="answer-panel">
                  {Object.keys(currentQuestion.options).length ? (
                    <div className="options" role="group" aria-label="答案选项">
                      {Object.entries(currentQuestion.options).map(([letter, text]) => {
                        const isCorrect = showAnswer && letter === correctAnswer;
                        const isWrong = showAnswer && selectedOption === letter && letter !== correctAnswer;
                        return (
                          <button
                            key={letter}
                            className={`option ${isCorrect ? "correct" : ""} ${isWrong ? "wrong" : ""}`}
                            onClick={() => chooseOption(letter)}
                            disabled={practiceMode === "study"}
                          >
                            <span className="option-marker">
                              {isCorrect ? <Check size={15} weight="bold" /> : letter}
                            </span>
                            <span>{text}</span>
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="answer-only">答案：{currentQuestion.answerText || currentQuestion.answer}</div>
                  )}

                  {showAnswer && (
                    <div className="answer-result">
                      <strong>正确答案：{currentQuestion.answer}</strong>
                      <span>{currentQuestion.answerText}</span>
                    </div>
                  )}

                  {!showAnswer && <div className="answer-pending">请选择一个答案</div>}

                  <details className="details" key={`${currentGroup.id}-${currentQuestion.id}`}>
                    <summary>
                      <BookOpenText size={18} />
                      查看解释
                      <CaretDown className="details-caret" size={18} />
                    </summary>
                    <div>
                      <p>{currentQuestion.explanation || currentGroup.explanation}</p>
                      {currentQuestion.related && <span>相关考点：{currentQuestion.related}</span>}
                    </div>
                  </details>
                </div>
              </div>
            )}
          </section>

          <footer className="lesson-footer">
            <button className="outline-button" onClick={() => stepGroup(-1)}>
              <CaretLeft size={19} /> 上一个口诀
            </button>
            <button className={`remember-button ${rememberedSet.has(currentGroup.id) ? "active" : ""}`} onClick={toggleRemembered}>
              {rememberedSet.has(currentGroup.id) ? <CheckCircle size={23} weight="fill" /> : <Circle size={23} />}
              {rememberedSet.has(currentGroup.id) ? "已记住" : "记住了"}
            </button>
            <button className="outline-button" onClick={() => stepGroup(1)}>
              下一个口诀 <CaretRight size={19} />
            </button>
          </footer>
        </article>
      </main>

      <aside className={`right-sidebar ${rightOpen ? "open" : ""}`}>
        <div className="right-header">
          <div>
            <span>{rightView === "questions" ? "当前口诀" : mode === "chapter" ? "本章口诀" : "本类口诀"}</span>
            <strong>{rightView === "questions" ? `${questionIndex + 1} / ${currentGroup.items.length}` : `${groupIndex + 1} / ${filteredGroups.length}`}</strong>
          </div>
          <button className="icon-button mobile-only" onClick={() => setRightOpen(false)} aria-label="关闭关联题目">
            <X size={20} />
          </button>
        </div>

        {rightView === "questions" ? (
          <>
            <div className="current-tip">
              <i />
              <span>{currentGroup.tip}</span>
              <button onClick={() => setRightView("groups")}>
                <ArrowLeft size={16} /> 返回本类口诀
              </button>
            </div>
            <div className="rail-title">
              <h2>关联题目 {currentGroup.items.length} 道</h2>
            </div>
            <div className="question-list">
              {currentGroup.items.map((item, index) => {
                const status = studyState.questions[item.id];
                return (
                  <button className={`question-card ${item.id === currentQuestion?.id ? "active" : ""}`} key={item.id} onClick={() => selectQuestion(item)}>
                    <span className="question-number">{index + 1}</span>
                    {item.image ? (
                      <img src={assetUrl(item.image)} alt="" />
                    ) : (
                      <span className="question-thumb"><BookOpenText size={23} /></span>
                    )}
                    <span className="question-card-copy">
                      <strong>{item.question}</strong>
                      <QuestionStatus status={status} />
                    </span>
                    {item.id === currentQuestion?.id && <CheckCircle className="selected-check" size={19} weight="fill" />}
                  </button>
                );
              })}
            </div>
          </>
        ) : (
          <>
            <div className="rail-title rail-title-groups">
              <h2>{filter}</h2>
              <span>{filteredGroups.length} 条口诀</span>
            </div>
            <div className="group-list">
              {filteredGroups.map((group) => (
                <button className={group.id === currentGroup.id ? "active" : ""} key={group.id} onClick={() => selectGroup(group)}>
                  <i />
                  <span>
                    <strong>{group.tip}</strong>
                    <small>{group.items.length}题 · {group.category}</small>
                  </span>
                  {group.isNew && <em>新增</em>}
                </button>
              ))}
            </div>
          </>
        )}

        <div className="progress-panel">
          <ProgressRing value={progress} />
          <div>
            <span>已记住</span>
            <strong>{rememberedSet.size} / {studyData.groups.length}</strong>
          </div>
        </div>
      </aside>
    </div>
  );
}
