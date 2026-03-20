const bootstrap = JSON.parse(document.getElementById("review-bootstrap").textContent);
const app = document.getElementById("app");

const state = {
  bootstrap,
  schema: null,
  overview: null,
  detail: null,
  backlog: null,
  drafts: {},
  currentIndex: 0,
  message: null,
  messageTone: "info",
  saving: false,
  queueFilters: {
    exam: "all",
    issue: "all",
    status: "all",
  },
};

void init();

async function init() {
  try {
    if (bootstrap.view === "overview") {
      state.overview = await fetchJson("/api/review/exams");
      state.schema = state.overview.schema;
      renderOverview();
      return;
    }

    if (bootstrap.view === "queue") {
      state.backlog = await fetchJson("/api/review/repair-backlog");
      state.schema = state.backlog.schema;
      renderQueue();
      return;
    }

    if (bootstrap.view === "exam") {
      state.detail = await fetchJson(`/api/review/exams/${encodeURIComponent(bootstrap.examId)}`);
      state.schema = state.detail.schema;
      for (const question of state.detail.question_views) {
        state.drafts[question.number] = cloneReview(question.review);
      }
      const requestedQuestion = Number.parseInt(new URL(window.location.href).searchParams.get("question") || "", 10);
      const startIndex = state.detail.question_views.findIndex((question) => question.number === requestedQuestion);
      state.currentIndex = startIndex >= 0 ? startIndex : findQuestionIndex(state.detail.meta.continue_question || 1);
      attachKeyboardShortcuts();
      renderExam();
      return;
    }

    renderFatal("无法识别当前审核页面类型。");
  } catch (error) {
    renderFatal(error.message || String(error));
  }
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `请求失败: ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || JSON.stringify(payload);
    } catch (_error) {
      detail = await response.text();
    }
    throw new Error(detail);
  }

  return response.json();
}

function renderOverview() {
  const { counts, exams } = state.overview;
  app.innerHTML = `
    <main class="shell">
      <section class="hero">
        <div class="hero-top">
          <div>
            <span class="eyebrow">模拟考试人工审核工作台</span>
            <h1>先逐套审核，再集中修复。</h1>
            <p>总共 ${counts.exams} 套试卷、${counts.total_questions} 道题。首轮建议按套走顺序审核，二轮再进入失败/待复查队列做修复闭环。</p>
          </div>
          <div class="button-row">
            <a class="button primary" href="/review/queue/failures">打开失败队列</a>
            <a class="ghost-button" href="/crop-review">图形框选台</a>
            <a class="ghost-button" href="/review-files/qa/index.html" target="_blank" rel="noreferrer">只读 QA 总页</a>
          </div>
        </div>

        <div class="metric-grid">
          ${metricCard("试卷总数", counts.exams, "共 16 个独立审核入口")}
          ${metricCard("题目总数", counts.total_questions, "已结构化并可逐题核对")}
          ${metricCard("已审核", counts.reviewed, `${counts.progress_percent}% 完成`)}
          ${metricCard("未审核", counts.unreviewed, "首轮审核主工作池")}
          ${metricCard("不通过", counts.failed, "需要进入修复")}
          ${metricCard("待复查", counts.follow_up, "先保留疑难题")}
        </div>

        <div class="legend">
          ${statusLegend("unreviewed")}
          ${statusLegend("passed")}
          ${statusLegend("failed")}
          ${statusLegend("follow_up")}
        </div>
      </section>

      <section class="section">
        <div class="queue-head">
          <div>
            <h2 class="section-title">16 套独立审核界面</h2>
            <p class="muted">每张卡片都支持继续上次进度、打开第一道未审题，以及跳到只读 QA 页面交叉核对。</p>
          </div>
        </div>
        <div class="card-grid">
          ${exams.map(renderExamCard).join("")}
        </div>
      </section>
    </main>
  `;
}

function renderExamCard(exam) {
  const started = exam.counts.reviewed > 0;
  const progressWidth = `${Math.max(0, Math.min(100, exam.progress_percent))}%`;
  return `
    <article class="exam-card">
      <div class="question-head">
        <div>
          <h3>${escapeHtml(exam.exam_id)}</h3>
          <div class="exam-subtitle">${escapeHtml(exam.family)} · ${escapeHtml(String(exam.year || "-"))} · ${exam.question_count} 题</div>
        </div>
        <span class="status-chip ${statusClass(cardHeadlineStatus(exam))}">${escapeHtml(cardHeadlineLabel(exam))}</span>
      </div>

      <div class="progress-track" aria-hidden="true">
        <div class="progress-bar" style="width: ${progressWidth};"></div>
      </div>

      <div class="tag-row" style="margin-top: 14px;">
        <span class="pill">已审 ${exam.counts.reviewed}</span>
        <span class="pill">未审 ${exam.counts.unreviewed}</span>
        <span class="pill">不通过 ${exam.counts.failed}</span>
        <span class="pill">待复查 ${exam.counts.follow_up}</span>
      </div>

      <div class="link-row">
        <a class="button primary" href="${escapeHtml(exam.continue_url)}">${started ? "继续上次进度" : "开始审核"}</a>
        <a class="ghost-button" href="${escapeHtml(exam.first_unreviewed_url)}">打开第一道未审题</a>
      </div>

      <div class="link-row">
        <a class="tiny-link" href="${escapeHtml(exam.review_url)}">整套题工作台</a>
        <a class="tiny-link" href="/crop-review/${escapeHtml(exam.exam_id)}">图形框选</a>
        <a class="tiny-link" href="${escapeHtml(exam.qa_page_url)}" target="_blank" rel="noreferrer">只读 QA</a>
        <a class="tiny-link" href="${escapeHtml(exam.exam_json_url)}" target="_blank" rel="noreferrer">exam.json</a>
        <a class="tiny-link" href="${escapeHtml(exam.audit_json_url)}" target="_blank" rel="noreferrer">audit.json</a>
      </div>

      <div class="exam-subtitle" style="margin-top: 16px;">
        ${exam.last_reviewed_at ? `最近更新 ${escapeHtml(formatDateTime(exam.last_reviewed_at))}` : "还没有人工审核记录"}
      </div>
    </article>
  `;
}

function renderQueue() {
  const filteredGroups = getFilteredQueueGroups();
  const totalVisible = filteredGroups.reduce((sum, group) => sum + group.items.length, 0);
  const issueOptions = state.backlog.issue_type_counts.filter((entry) => entry.count > 0);

  app.innerHTML = `
    <main class="shell">
      <section class="hero">
        <div class="hero-top">
          <div>
            <span class="eyebrow">跨试卷失败 / 待复查队列</span>
            <h1>把真正需要修的题集中处理。</h1>
            <p>这里专注于首轮审核后留下的问题题，不再重复翻通过题。可以按试卷、问题类型和状态筛选，再直接跳回对应题目。</p>
          </div>
          <div class="button-row">
            <a class="button primary" href="/review">回到总览</a>
            <a class="ghost-button" href="/review-files/qa/index.html" target="_blank" rel="noreferrer">打开只读 QA</a>
          </div>
        </div>

        <div class="metric-grid">
          ${metricCard("待处理题数", state.backlog.total_items, "所有失败与待复查题")}
          ${metricCard("当前筛选结果", totalVisible, "本页实际显示的题数")}
          ${metricCard("问题类型数", issueOptions.length, "已被人工使用过的分类")}
        </div>
      </section>

      <section class="section">
        <div class="queue-filter-bar">
          <div>
            <h2 class="section-title">修复队列</h2>
            <p class="muted">筛掉已无关的试卷或问题类型后，可以连续修同一类问题。</p>
          </div>
          <div class="button-row">
            <label>
              <span class="visually-hidden">按试卷筛选</span>
              <select class="select-input" id="queue-filter-exam">
                <option value="all">全部试卷</option>
                ${state.backlog.exams.map((exam) => `<option value="${escapeHtml(exam.exam_id)}">${escapeHtml(exam.exam_id)}</option>`).join("")}
              </select>
            </label>
            <label>
              <span class="visually-hidden">按问题类型筛选</span>
              <select class="select-input" id="queue-filter-issue">
                <option value="all">全部问题类型</option>
                ${issueOptions.map((entry) => `<option value="${escapeHtml(entry.value)}">${escapeHtml(entry.label)} (${entry.count})</option>`).join("")}
              </select>
            </label>
            <label>
              <span class="visually-hidden">按状态筛选</span>
              <select class="select-input" id="queue-filter-status">
                <option value="all">全部状态</option>
                <option value="failed">仅不通过</option>
                <option value="follow_up">仅待复查</option>
              </select>
            </label>
          </div>
        </div>

        ${filteredGroups.length ? filteredGroups.map(renderQueueGroup).join("") : renderEmptyState("当前筛选条件下没有待处理题。", "可以回到总览继续首轮审核，或者放宽筛选条件。")}
      </section>
    </main>
  `;

  document.getElementById("queue-filter-exam").value = state.queueFilters.exam;
  document.getElementById("queue-filter-issue").value = state.queueFilters.issue;
  document.getElementById("queue-filter-status").value = state.queueFilters.status;

  document.getElementById("queue-filter-exam").addEventListener("change", (event) => {
    state.queueFilters.exam = event.target.value;
    renderQueue();
  });
  document.getElementById("queue-filter-issue").addEventListener("change", (event) => {
    state.queueFilters.issue = event.target.value;
    renderQueue();
  });
  document.getElementById("queue-filter-status").addEventListener("change", (event) => {
    state.queueFilters.status = event.target.value;
    renderQueue();
  });
}

function renderQueueGroup(group) {
  return `
    <section class="queue-group">
      <div class="queue-group-head">
        <div>
          <h3 class="queue-title">${escapeHtml(group.exam_id)}</h3>
          <p class="muted">${group.items.length} 道待处理题 · ${group.question_count} 题总量</p>
        </div>
        <div class="button-row">
          <a class="ghost-button" href="${escapeHtml(group.review_url)}">整套工作台</a>
          <a class="ghost-button" href="${escapeHtml(group.qa_page_url)}" target="_blank" rel="noreferrer">只读 QA</a>
        </div>
      </div>
      ${group.items.map(renderQueueItem).join("")}
    </section>
  `;
}

function renderQueueItem(item) {
  return `
    <article class="queue-item">
      <div class="question-head">
        <div>
          <h4>第 ${item.question_number} 题</h4>
          <p class="muted">第 ${item.page} 页 · 状态 ${escapeHtml(item.status_label)} · 答案 ${escapeHtml(item.answer || "-")}</p>
        </div>
        <span class="status-chip ${statusClass(item.status)}">${escapeHtml(item.status_label)}</span>
      </div>

      <div class="tag-row" style="margin-top: 14px;">
        ${item.issue_types.map((issueType) => `<span class="pill">${escapeHtml(labelFor("issue_types", issueType))}</span>`).join("")}
        ${item.affected_areas.map((area) => `<span class="pill">${escapeHtml(labelFor("affected_areas", area))}</span>`).join("")}
      </div>

      ${item.note ? `<div class="note-text" style="margin-top: 14px;">${escapeHtml(item.note)}</div>` : `<div class="muted" style="margin-top: 14px;">暂无备注</div>`}

      <div class="tag-row" style="margin-top: 14px;">
        ${item.system_hints.map((hint) => `<span class="hint-chip">${escapeHtml(hint)}</span>`).join("")}
      </div>

      <div class="link-row">
        <a class="button primary" href="${escapeHtml(item.question_url)}">跳到题目工作台</a>
        <a class="ghost-button" href="${escapeHtml(item.qa_anchor_url)}" target="_blank" rel="noreferrer">打开只读 QA 锚点</a>
      </div>
    </article>
  `;
}

function renderExam() {
  const question = getCurrentQuestion();
  const draft = getDraft(question.number);
  const counts = state.detail.meta.counts;

  app.innerHTML = `
    <main class="shell">
      <section class="hero">
        <div class="hero-top">
          <div>
            <span class="eyebrow">${escapeHtml(state.detail.meta.exam_id)} · 单题工作台</span>
            <h1>${escapeHtml(state.detail.meta.exam_id)}</h1>
            <p>左侧看原始 PDF 裁图，中间看抽取后渲染结果，右侧直接给出人工结论与备注。默认从自然题号顺序走，尽量减少上下文切换。</p>
          </div>
          <div class="button-row">
            <a class="button primary" href="/review">回到总览</a>
            <a class="ghost-button" href="/review/queue/failures">失败队列</a>
            <a class="ghost-button" href="/crop-review/${escapeHtml(state.detail.meta.exam_id)}">图形框选台</a>
            <a class="ghost-button" href="${escapeHtml(state.detail.meta.qa_page_url)}" target="_blank" rel="noreferrer">只读 QA</a>
          </div>
        </div>

        <div class="metric-grid">
          ${metricCard("题号", `${question.number} / ${state.detail.meta.question_count}`, "当前正在审核")}
          ${metricCard("已审核", counts.reviewed, "本套卷已有人审结论")}
          ${metricCard("未审核", counts.unreviewed, "首轮主工作池")}
          ${metricCard("不通过", counts.failed, "需要修复")}
          ${metricCard("待复查", counts.follow_up, "保留疑难题")}
          ${metricCard("最近更新", state.detail.meta.last_reviewed_at ? formatDateTime(state.detail.meta.last_reviewed_at) : "暂无", "按人工保存时间统计")}
        </div>

        <div class="legend">
          <span class="pill"><span class="kbd">←</span> 上一题</span>
          <span class="pill"><span class="kbd">→</span> 下一题</span>
          <span class="pill"><span class="kbd">1</span> 通过并前进</span>
          <span class="pill"><span class="kbd">2</span> 标记不通过</span>
          <span class="pill"><span class="kbd">3</span> 标记待复查</span>
          <span class="pill"><span class="kbd">F</span> 聚焦备注框</span>
        </div>

        <div class="question-strip">
          ${state.detail.question_views.map((entry, index) => renderQuestionPill(entry, index)).join("")}
        </div>
      </section>

      <section class="exam-workspace">
        <div class="panel sticky-column">
          <h2 class="panel-title">原始 PDF 裁图</h2>
          <p class="panel-subtitle">先确认截图范围、题图是否完整，再对比中间的渲染结果。</p>
          ${
            question.reference_image_url
              ? `
                <a class="media-frame" href="${escapeHtml(question.reference_image_url)}" target="_blank" rel="noreferrer">
                  <img src="${escapeHtml(question.reference_image_url)}" alt="第 ${question.number} 题原始裁图" />
                </a>
              `
              : renderEmptyState("这道题没有参考裁图。", "可以直接打开只读 QA 页检查。")
          }

          <div class="divider"></div>
          <div class="button-row">
            <a class="ghost-button" href="${escapeHtml(question.qa_anchor_url)}" target="_blank" rel="noreferrer">打开 QA 锚点</a>
            <a class="ghost-button" href="${escapeHtml(state.detail.meta.audit_json_url)}" target="_blank" rel="noreferrer">查看 audit.json</a>
          </div>
        </div>

        <div class="panel">
          <div class="question-head">
            <div>
              <h2 class="panel-title">抽取后渲染</h2>
              <p class="panel-subtitle">${escapeHtml(question.part)} · ${question.points} 分 · 答案 ${escapeHtml(question.answer || "-")}</p>
            </div>
            <span class="status-chip ${statusClass(question.review.status)}">${escapeHtml(labelFor("statuses", question.review.status))}</span>
          </div>

          <div class="preview-block">
            <p class="preview-label">题干文本</p>
            <div class="preview-text">${escapeHtml(question.stem_text || "无题干文本")}</div>
          </div>

          <div class="preview-block">
            <p class="preview-label">题干素材</p>
            ${
              question.shared_assets.length
                ? `<div class="mini-grid">${question.shared_assets.map(renderAssetCard).join("")}</div>`
                : `<div class="muted">没有题干素材</div>`
            }
          </div>

          <div class="preview-block">
            <p class="preview-label">选项渲染</p>
            <div class="choice-grid">
              ${question.choices.map(renderChoiceCard).join("")}
            </div>
          </div>

          <div class="preview-block">
            <p class="preview-label">抽取元信息</p>
            <div class="tag-row">
              <span class="pill">页码 ${question.source.page}</span>
              <span class="pill">置信度 ${escapeHtml(String(question.source.confidence ?? "-"))}</span>
              <span class="pill">bbox ${escapeHtml(JSON.stringify(question.source.bbox || []))}</span>
              <span class="pill">文本块 ${escapeHtml(String((question.source.block_ids || []).length))}</span>
            </div>
          </div>
        </div>

        <div class="stack sticky-column">
          <section class="sidebar-card">
            <div class="question-head">
              <div>
                <h2 class="panel-title">人工审核结论</h2>
                <p class="panel-subtitle">通过后可快速前进；不通过和待复查至少选一个问题分类。</p>
              </div>
              <span class="status-chip ${statusClass(draft.status)}">${escapeHtml(labelFor("statuses", draft.status))}</span>
            </div>

            <div class="field-stack">
              <p class="field-label">状态</p>
              <div class="status-picker">
                ${renderStatusButton("passed", draft.status)}
                ${renderStatusButton("failed", draft.status)}
                ${renderStatusButton("follow_up", draft.status)}
              </div>
            </div>

            <div class="field-stack">
              <p class="field-label">问题分类</p>
              <div class="chip-grid">
                ${state.schema.issue_types.map((entry) => renderCheckChip("issue", entry.value, entry.label, draft.issue_types.includes(entry.value))).join("")}
              </div>
            </div>

            <div class="field-stack">
              <p class="field-label">影响范围</p>
              <div class="chip-grid">
                ${state.schema.affected_areas.map((entry) => renderCheckChip("area", entry.value, entry.label, draft.affected_areas.includes(entry.value))).join("")}
              </div>
            </div>

            <div class="field-stack">
              <label for="review-note" class="field-label">备注</label>
              <textarea id="review-note" class="note-input" placeholder="写下具体问题、修复思路或要回看的点...">${escapeHtml(draft.note)}</textarea>
              <div class="save-note">${question.review.reviewed_at ? `上次保存 ${escapeHtml(formatDateTime(question.review.reviewed_at))}` : "这道题还没有正式保存过人工结论"}</div>
            </div>

            ${state.message ? `<div class="message ${escapeHtml(state.messageTone)}">${escapeHtml(state.message)}</div>` : ""}

            <div class="button-row" style="margin-top: 16px;">
              <button class="button primary" id="save-review" ${state.saving ? "disabled" : ""}>${state.saving ? "保存中..." : "保存当前结论"}</button>
              <button class="ghost-button" id="reset-review" ${state.saving ? "disabled" : ""}>重置为未审核</button>
            </div>
          </section>

          <section class="sidebar-card">
            <h2 class="panel-title">系统线索</h2>
            <p class="panel-subtitle">这些信息来自现有 <code>exam.json</code> / <code>audit.json</code>，能帮助你判断问题归因。</p>
            <div class="tag-row" style="margin-top: 14px;">
              ${question.system_hints.map((hint) => `<span class="hint-chip">${escapeHtml(hint)}</span>`).join("") || `<span class="muted">暂无系统线索</span>`}
            </div>
            <div class="divider"></div>
            <div class="audit-box">
              <strong>reference_bbox</strong><br />
              ${escapeHtml(JSON.stringify(question.audit.reference_bbox || []))}
              <br /><br />
              <strong>text_bbox</strong><br />
              ${escapeHtml(JSON.stringify(question.audit.text_bbox || []))}
            </div>
          </section>

          <section class="sidebar-card">
            <div class="actions-row">
              <button class="ghost-button" id="nav-prev" ${state.currentIndex === 0 ? "disabled" : ""}>上一题</button>
              <button class="ghost-button" id="nav-next" ${state.currentIndex === state.detail.question_views.length - 1 ? "disabled" : ""}>下一题</button>
            </div>
          </section>
        </div>
      </section>
    </main>
  `;

  syncQuestionParam(question.number);
  bindExamEvents();
}

function bindExamEvents() {
  const noteInput = document.getElementById("review-note");
  if (noteInput) {
    noteInput.addEventListener("input", () => {
      const draft = getDraft(getCurrentQuestion().number);
      draft.note = noteInput.value;
    });
  }

  for (const pill of document.querySelectorAll("[data-nav-index]")) {
    pill.addEventListener("click", async () => {
      await navigateToIndex(Number.parseInt(pill.dataset.navIndex, 10));
    });
  }

  for (const button of document.querySelectorAll("[data-set-status]")) {
    button.addEventListener("click", () => {
      const draft = getDraft(getCurrentQuestion().number);
      draft.status = button.dataset.setStatus;
      if (draft.status === "passed") {
        draft.issue_types = [];
        draft.affected_areas = [];
      }
      renderExam();
    });
  }

  for (const checkbox of document.querySelectorAll("[data-chip-kind='issue']")) {
    checkbox.addEventListener("change", () => {
      toggleDraftToken("issue_types", checkbox.value, checkbox.checked);
      renderExam();
    });
  }

  for (const checkbox of document.querySelectorAll("[data-chip-kind='area']")) {
    checkbox.addEventListener("change", () => {
      toggleDraftToken("affected_areas", checkbox.value, checkbox.checked);
      renderExam();
    });
  }

  const saveButton = document.getElementById("save-review");
  if (saveButton) {
    saveButton.addEventListener("click", async () => {
      await saveCurrentDraft();
    });
  }

  const resetButton = document.getElementById("reset-review");
  if (resetButton) {
    resetButton.addEventListener("click", async () => {
      const draft = getDraft(getCurrentQuestion().number);
      Object.assign(draft, blankReview());
      await saveCurrentDraft();
    });
  }

  const prevButton = document.getElementById("nav-prev");
  if (prevButton) {
    prevButton.addEventListener("click", async () => {
      await navigateRelative(-1);
    });
  }

  const nextButton = document.getElementById("nav-next");
  if (nextButton) {
    nextButton.addEventListener("click", async () => {
      await navigateRelative(1);
    });
  }
}

function attachKeyboardShortcuts() {
  if (window.__reviewKeyboardAttached) {
    return;
  }
  window.__reviewKeyboardAttached = true;
  document.addEventListener("keydown", async (event) => {
    if (bootstrap.view !== "exam") {
      return;
    }
    if (event.metaKey || event.ctrlKey || event.altKey) {
      return;
    }

    const tagName = event.target && event.target.tagName ? event.target.tagName.toLowerCase() : "";
    const editing = tagName === "textarea" || tagName === "input" || tagName === "select";
    if (editing && event.key !== "Escape") {
      return;
    }

    if (event.key === "ArrowLeft") {
      event.preventDefault();
      await navigateRelative(-1);
      return;
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      await navigateRelative(1);
      return;
    }
    if (event.key === "1") {
      event.preventDefault();
      const draft = getDraft(getCurrentQuestion().number);
      draft.status = "passed";
      draft.issue_types = [];
      draft.affected_areas = [];
      await saveCurrentDraft({ advance: true, successMessage: "已标记为通过，并跳到下一题。" });
      return;
    }
    if (event.key === "2") {
      event.preventDefault();
      const draft = getDraft(getCurrentQuestion().number);
      draft.status = "failed";
      renderExam();
      return;
    }
    if (event.key === "3") {
      event.preventDefault();
      const draft = getDraft(getCurrentQuestion().number);
      draft.status = "follow_up";
      renderExam();
      return;
    }
    if (event.key.toLowerCase() === "f") {
      event.preventDefault();
      const textarea = document.getElementById("review-note");
      if (textarea) {
        textarea.focus();
      }
    }
  });
}

async function navigateRelative(delta) {
  await navigateToIndex(state.currentIndex + delta);
}

async function navigateToIndex(nextIndex) {
  if (!state.detail) {
    return;
  }
  if (nextIndex < 0 || nextIndex >= state.detail.question_views.length || nextIndex === state.currentIndex) {
    return;
  }
  const saved = await persistDirtyDraft();
  if (!saved) {
    return;
  }
  state.currentIndex = nextIndex;
  state.message = null;
  renderExam();
}

async function persistDirtyDraft() {
  const question = getCurrentQuestion();
  if (!question) {
    return true;
  }
  if (!isDraftDirty(question)) {
    return true;
  }
  return saveCurrentDraft({ silentSuccess: true });
}

async function saveCurrentDraft(options = {}) {
  const question = getCurrentQuestion();
  const draft = normalizeDraft(getDraft(question.number));
  const validation = validateDraft(draft);
  if (!validation.ok) {
    state.message = validation.message;
    state.messageTone = "error";
    renderExam();
    return false;
  }

  if (!isDraftDirty(question) && !options.forceSave) {
    if (options.advance) {
      if (state.currentIndex < state.detail.question_views.length - 1) {
        state.currentIndex += 1;
      }
      renderExam();
    }
    return true;
  }

  state.saving = true;
  renderExam();
  try {
    const result = await fetchJson(
      `/api/review/exams/${encodeURIComponent(state.detail.meta.exam_id)}/questions/${question.number}`,
      {
        method: "PUT",
        body: JSON.stringify(draft),
      },
    );

    question.review = result.question;
    state.detail.review.questions[String(question.number)] = result.question;
    state.drafts[question.number] = cloneReview(result.question);
    Object.assign(state.detail.meta, result.summary);

    state.saving = false;
    state.message = options.successMessage || "已保存当前题的人工结论。";
    state.messageTone = "success";
    if (options.advance && state.currentIndex < state.detail.question_views.length - 1) {
      state.currentIndex += 1;
    }
    renderExam();
    return true;
  } catch (error) {
    state.saving = false;
    state.message = error.message || String(error);
    state.messageTone = "error";
    renderExam();
    return false;
  }
}

function toggleDraftToken(key, value, enabled) {
  const draft = getDraft(getCurrentQuestion().number);
  const nextValues = new Set(draft[key]);
  if (enabled) {
    nextValues.add(value);
  } else {
    nextValues.delete(value);
  }
  draft[key] = Array.from(nextValues);
}

function getCurrentQuestion() {
  return state.detail.question_views[state.currentIndex];
}

function getDraft(questionNumber) {
  if (!state.drafts[questionNumber]) {
    const question = state.detail.question_views.find((item) => item.number === questionNumber);
    state.drafts[questionNumber] = cloneReview(question.review);
  }
  return state.drafts[questionNumber];
}

function cloneReview(review) {
  return {
    status: review.status,
    issue_types: [...(review.issue_types || [])],
    affected_areas: [...(review.affected_areas || [])],
    note: review.note || "",
  };
}

function blankReview() {
  return {
    status: "unreviewed",
    issue_types: [],
    affected_areas: [],
    note: "",
  };
}

function normalizeDraft(draft) {
  const normalized = {
    status: draft.status,
    issue_types: [...new Set(draft.issue_types)].sort(),
    affected_areas: [...new Set(draft.affected_areas)].sort(),
    note: (draft.note || "").trim(),
  };
  if (normalized.status === "unreviewed") {
    return blankReview();
  }
  if (normalized.status === "passed") {
    normalized.issue_types = [];
    normalized.affected_areas = [];
  }
  return normalized;
}

function isDraftDirty(question) {
  return JSON.stringify(normalizeDraft(getDraft(question.number))) !== JSON.stringify(normalizeDraft(question.review));
}

function validateDraft(draft) {
  if (draft.status === "failed" || draft.status === "follow_up") {
    if (!draft.issue_types.length) {
      return { ok: false, message: "不通过或待复查时，至少选择一个问题分类后才能保存。" };
    }
  }
  return { ok: true };
}

function getFilteredQueueGroups() {
  return state.backlog.exams
    .map((exam) => ({
      ...exam,
      items: exam.items.filter((item) => {
        if (state.queueFilters.exam !== "all" && item.exam_id !== state.queueFilters.exam) {
          return false;
        }
        if (state.queueFilters.issue !== "all" && !item.issue_types.includes(state.queueFilters.issue)) {
          return false;
        }
        if (state.queueFilters.status !== "all" && item.status !== state.queueFilters.status) {
          return false;
        }
        return true;
      }),
    }))
    .filter((exam) => exam.items.length > 0);
}

function renderQuestionPill(question, index) {
  const classes = ["question-pill", statusClass(getDraft(question.number).status)];
  if (index === state.currentIndex) {
    classes.push("current");
  }
  return `
    <button class="${classes.join(" ")}" data-nav-index="${index}" title="第 ${question.number} 题">
      ${question.number}
    </button>
  `;
}

function renderStatusButton(status, currentStatus) {
  const activeClass = status === currentStatus ? "active" : "";
  return `
    <button class="status-button ${activeClass}" data-set-status="${escapeHtml(status)}">
      ${escapeHtml(labelFor("statuses", status))}
    </button>
  `;
}

function renderCheckChip(kind, value, label, checked) {
  return `
    <label class="check-chip ${checked ? "active" : ""}">
      <input type="checkbox" value="${escapeHtml(value)}" data-chip-kind="${escapeHtml(kind)}" ${checked ? "checked" : ""} />
      <span>${escapeHtml(label)}</span>
    </label>
  `;
}

function renderAssetCard(asset) {
  return `
    <figure class="asset-card">
      <img src="${escapeHtml(asset.url)}" alt="${escapeHtml(asset.id)}" loading="lazy" />
      <figcaption class="asset-caption">${escapeHtml(asset.id)}</figcaption>
    </figure>
  `;
}

function renderChoiceCard(choice) {
  return `
    <article class="choice-card">
      <span class="choice-label">${escapeHtml(choice.label)}</span>
      <div class="option-text">${escapeHtml(choice.text || "(image option)")}</div>
      ${
        choice.asset_views.length
          ? `<div class="mini-grid">${choice.asset_views.map(renderAssetCard).join("")}</div>`
          : `<div class="muted">没有选项素材</div>`
      }
    </article>
  `;
}

function metricCard(label, value, detail) {
  return `
    <div class="metric-card">
      <div class="metric-label">${escapeHtml(String(label))}</div>
      <div class="metric-value">${escapeHtml(String(value))}</div>
      <div class="meta-text">${escapeHtml(String(detail))}</div>
    </div>
  `;
}

function statusLegend(status) {
  return `<span class="status-chip ${statusClass(status)}">${escapeHtml(labelFor("statuses", status))}</span>`;
}

function cardHeadlineStatus(exam) {
  if (exam.counts.failed > 0) {
    return "failed";
  }
  if (exam.counts.follow_up > 0) {
    return "follow_up";
  }
  if (exam.counts.reviewed > 0 && exam.counts.unreviewed === 0) {
    return "passed";
  }
  return "unreviewed";
}

function cardHeadlineLabel(exam) {
  if (exam.counts.failed > 0) {
    return "待修复";
  }
  if (exam.counts.follow_up > 0) {
    return "有待复查";
  }
  if (exam.counts.reviewed > 0 && exam.counts.unreviewed === 0) {
    return "首轮已完成";
  }
  if (exam.counts.reviewed > 0) {
    return "审核进行中";
  }
  return "尚未开始";
}

function renderEmptyState(title, detail) {
  return `
    <div class="empty-state">
      <div>
        <strong>${escapeHtml(title)}</strong>
        <p>${escapeHtml(detail)}</p>
      </div>
    </div>
  `;
}

function renderFatal(message) {
  app.innerHTML = `
    <main class="shell">
      ${renderEmptyState("审核台加载失败。", message)}
    </main>
  `;
}

function syncQuestionParam(questionNumber) {
  const url = new URL(window.location.href);
  url.searchParams.set("question", String(questionNumber));
  window.history.replaceState({}, "", url);
}

function findQuestionIndex(questionNumber) {
  const index = state.detail.question_views.findIndex((question) => question.number === questionNumber);
  return index >= 0 ? index : 0;
}

function labelFor(schemaKey, value) {
  const entry = (state.schema?.[schemaKey] || []).find((item) => item.value === value);
  return entry ? entry.label : value;
}

function statusClass(status) {
  return `status-${status}`;
}

function formatDateTime(value) {
  try {
    return new Date(value).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch (_error) {
    return value;
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
