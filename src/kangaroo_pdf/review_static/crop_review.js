const bootstrap = JSON.parse(document.getElementById("crop-review-bootstrap").textContent);
const app = document.getElementById("app");
const OPTION_LABELS = ["A", "B", "C", "D", "E"];

const state = {
  bootstrap,
  overview: null,
  detail: null,
  drafts: {},
  currentIndex: 0,
  currentPage: null,
  onlyLikelyVisual: true,
  selectedSlot: "stem",
  selectedRegionKey: null,
  drag: null,
  saving: false,
  message: null,
  messageTone: "info",
};

void init();

async function init() {
  try {
    if (bootstrap.view === "overview") {
      state.overview = await fetchJson("/api/crop-review/exams");
      renderOverview();
      return;
    }

    if (bootstrap.view === "exam") {
      state.detail = await fetchJson(`/api/crop-review/exams/${encodeURIComponent(bootstrap.examId)}`);
      for (const question of state.detail.question_views) {
        state.drafts[question.number] = cloneDraft(question.manual);
      }
      const requestedQuestion = Number.parseInt(new URL(window.location.href).searchParams.get("question") || "", 10);
      if (requestedQuestion) {
        const requestedIndex = state.detail.question_views.findIndex((question) => question.number === requestedQuestion);
        if (requestedIndex >= 0) {
          state.currentIndex = requestedIndex;
          if (state.onlyLikelyVisual && !state.detail.question_views[requestedIndex].likely_visual) {
            state.onlyLikelyVisual = false;
          }
        }
      } else {
        state.currentIndex = findInitialIndex();
      }
      state.currentPage = getCurrentQuestion().page;
      bindGlobalPointerEvents();
      attachKeyboardShortcuts();
      renderExam();
      return;
    }

    renderFatal("无法识别当前框选页面类型。");
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
  const { counts, exams, likely_visual_questions, stale_question_count } = state.overview;
  app.innerHTML = `
    <main class="crop-shell">
      <section class="crop-hero">
        <div class="hero-copy">
          <span class="eyebrow">整页 PDF 人工图形框选</span>
          <h1>先把题图边界框准，再让后续 JSON 生成稳定下来。</h1>
          <p>这个工作台会在整页视图里带出系统当前识别到的题干图和选项图，你只需要修正范围、补漏、或确认无图。保存后会直接导出人工裁图资产，并写入后续 agent 可直接消费的结构化标注。</p>
        </div>
        <div class="button-row">
          <a class="button primary" href="${escapeHtml(exams[0]?.continue_url || "/crop-review")}">继续框选</a>
          <a class="ghost-button" href="/review">打开原审核台</a>
          <a class="ghost-button" href="/review-files/qa/index.html" target="_blank" rel="noreferrer">只读 QA 总页</a>
        </div>
        <div class="metric-grid">
          ${metricCard("试卷总数", counts.exams, "每套卷都有独立框选入口")}
          ${metricCard("题目总数", counts.total_questions, "人工可逐题修正图形范围")}
          ${metricCard("疑似有图", likely_visual_questions, "默认优先展示这些题")}
          ${metricCard("已就绪", counts.ready, `${counts.progress_percent}% 可供下游直接使用`)}
          ${metricCard("待处理", counts.pending, "仍未确认最终图形范围")}
          ${metricCard("需复看", stale_question_count, "源数据变化后要再次确认")}
        </div>
      </section>

      <section class="crop-section">
        <div class="section-head">
          <div>
            <h2>试卷入口</h2>
            <p class="muted">默认从疑似有图的未完成题开始。即使系统没识别到图，也可以在单卷页切到“显示全部题目”手动补框。</p>
          </div>
        </div>
        <div class="exam-grid">
          ${exams.map(renderExamCard).join("")}
        </div>
      </section>
    </main>
  `;
}

function renderExamCard(exam) {
  return `
    <article class="exam-card">
      <div class="exam-card-head">
        <div>
          <h3>${escapeHtml(exam.exam_id)}</h3>
          <p class="muted">${escapeHtml(exam.family)} · ${escapeHtml(String(exam.year || "-"))} · ${exam.question_count} 题</p>
        </div>
        <span class="status-pill ${statusClass(summaryStatus(exam))}">${escapeHtml(summaryLabel(exam))}</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" style="width:${Math.max(0, Math.min(100, exam.progress_percent))}%"></div>
      </div>
      <div class="tag-row">
        <span class="tiny-pill">已就绪 ${exam.counts.ready}</span>
        <span class="tiny-pill">待处理 ${exam.counts.pending}</span>
        <span class="tiny-pill">疑似有图 ${exam.likely_visual_questions}</span>
        ${exam.stale_question_count ? `<span class="tiny-pill warn">需复看 ${exam.stale_question_count}</span>` : ""}
      </div>
      <div class="button-row">
        <a class="button primary" href="${escapeHtml(exam.continue_url)}">继续框选</a>
        <a class="ghost-button" href="${escapeHtml(exam.crop_review_url)}">打开整卷</a>
      </div>
      <div class="link-row">
        <a class="tiny-link" href="${escapeHtml(exam.review_url)}">原审核页</a>
        <a class="tiny-link" href="/review-files/qa/${escapeHtml(exam.exam_id)}/index.html" target="_blank" rel="noreferrer">只读 QA</a>
      </div>
      <div class="muted footnote">${exam.updated_at ? `最近保存 ${escapeHtml(formatDateTime(exam.updated_at))}` : "还没有人工框选记录"}</div>
    </article>
  `;
}

function renderExam() {
  ensureCurrentQuestionVisible();
  const question = getCurrentQuestion();
  const draft = getDraft(question.number);
  const visibleEntries = getVisibleQuestionEntries();
  const counts = state.detail.meta.counts;
  const currentPageMeta = getCurrentPageMeta();
  const staleBanner = state.detail.meta.stale_question_count
    ? `<div class="warning-banner">这套卷已有 ${state.detail.meta.stale_question_count} 道题的人工框选基于旧版 source revision，请留意右侧“需复看”提示。</div>`
    : "";

  app.innerHTML = `
    <main class="crop-shell">
      <section class="crop-hero compact">
        <div class="hero-copy">
          <span class="eyebrow">${escapeHtml(state.detail.meta.exam_id)} · 整页框选工作台</span>
          <h1>${escapeHtml(state.detail.meta.exam_id)}</h1>
          <p>左侧在整页 PDF 上框选，中间管理题干和 A-E 槽位，右侧确认状态并保存导出。保存后的人工裁图会覆盖自动结果，成为后续 JSON 生成的权威来源。</p>
        </div>
        <div class="button-row">
          <a class="button primary" href="/crop-review">回到总览</a>
          <a class="ghost-button" href="${escapeHtml(question.review_url)}">原审核页</a>
          <a class="ghost-button" href="${escapeHtml(question.qa_anchor_url)}" target="_blank" rel="noreferrer">QA 锚点</a>
        </div>
        <div class="metric-grid">
          ${metricCard("当前题号", `${question.number} / ${state.detail.meta.question_count}`, question.likely_visual ? "系统认为这题疑似有图" : "当前题默认不在疑似有图集合")}
          ${metricCard("已就绪", counts.ready, "completed + confirmed_no_visual")}
          ${metricCard("待处理", counts.pending, "还不能直接下游使用")}
          ${metricCard("疑似有图", state.detail.meta.likely_visual_questions, "默认过滤视图会优先显示")}
          ${metricCard("当前页", currentPageMeta ? `P${currentPageMeta.number}` : "-", "整页视图可切页")}
          ${metricCard("最近保存", question.manual.updated_at ? formatDateTime(question.manual.updated_at) : "暂无", question.manual.stale ? "当前题需复看" : "当前题与现有 source revision 一致")}
        </div>
        ${staleBanner}
        <div class="toolbar-row">
          <label class="toggle">
            <input type="checkbox" id="toggle-likely-visual" ${state.onlyLikelyVisual ? "checked" : ""} />
            <span>只显示疑似有图 / 已有人工结果的题</span>
          </label>
          <div class="button-row">
            <button class="ghost-button" id="nav-prev" ${visibleEntries.length <= 1 ? "disabled" : ""}>上一题</button>
            <button class="ghost-button" id="nav-next" ${visibleEntries.length <= 1 ? "disabled" : ""}>下一题</button>
          </div>
        </div>
        <div class="question-strip">
          ${visibleEntries.map(({ question: item, index }) => renderQuestionPill(item, index)).join("")}
        </div>
      </section>

      <section class="workspace-grid">
        <div class="workspace-panel">
          <div class="panel-head">
            <div>
              <h2>整页框选</h2>
              <p class="muted">选中中间的槽位后，直接在页面上拖拽新增矩形；点选已有框可以拖动或缩放。</p>
            </div>
            <span class="status-pill ${statusClass(draft.status)}">${escapeHtml(labelForStatus(draft.status))}</span>
          </div>
          <div class="page-switcher">
            ${state.detail.pages.map((page) => renderPageButton(page)).join("")}
          </div>
          <div class="canvas-card">
            <div id="page-canvas-host"></div>
          </div>
          <div class="tag-row">
            <span class="tiny-pill">当前槽位 ${escapeHtml(slotDisplayLabel(state.selectedSlot))}</span>
            <span class="tiny-pill">当前页 P${escapeHtml(String(state.currentPage))}</span>
            <span class="tiny-pill">${question.manual.stale ? "需复看" : "source revision 已对齐"}</span>
          </div>
        </div>

        <div class="workspace-panel">
          <div class="panel-head">
            <div>
              <h2>槽位与裁切预览</h2>
              <p class="muted">题干支持多框，A-E 每个选项也都支持多框。顺序会写入最终导出命名。</p>
            </div>
            <button class="ghost-button" id="clear-current-slot">清空当前槽位</button>
          </div>
          <div id="slot-list-host"></div>
        </div>

        <div class="sidebar-stack">
          <section class="sidebar-card">
            <div class="panel-head">
              <div>
                <h2>保存状态</h2>
                <p class="muted"><code>completed</code> 会作为人工权威结果，<code>confirmed_no_visual</code> 表示整题已确认没有图。</p>
              </div>
            </div>
            <div class="status-grid">
              ${renderStatusButton("pending", draft.status)}
              ${renderStatusButton("completed", draft.status)}
              ${renderStatusButton("confirmed_no_visual", draft.status)}
            </div>
            ${state.message ? `<div class="message ${escapeHtml(state.messageTone)}">${escapeHtml(state.message)}</div>` : ""}
            <div class="button-row" style="margin-top: 14px;">
              <button class="button primary" id="save-question" ${state.saving ? "disabled" : ""}>${state.saving ? "保存中..." : "保存当前题"}</button>
              <button class="ghost-button" id="mark-no-visual" ${state.saving ? "disabled" : ""}>一键确认本题无图</button>
            </div>
          </section>

          <section class="sidebar-card">
            <h2>当前题信息</h2>
            <div class="info-list">
              <div><strong>题号</strong><span>${question.number}</span></div>
              <div><strong>分值</strong><span>${escapeHtml(String(question.points))}</span></div>
              <div><strong>答案</strong><span>${escapeHtml(question.answer || "-")}</span></div>
              <div><strong>题干页</strong><span>P${escapeHtml(String(question.page))}</span></div>
              <div><strong>question_bbox</strong><span>${escapeHtml(JSON.stringify(question.question_bbox || []))}</span></div>
              <div><strong>text_bbox</strong><span>${escapeHtml(JSON.stringify(question.text_bbox || []))}</span></div>
            </div>
            <div class="divider"></div>
            <div class="preview-text">${escapeHtml(question.stem_text || "无题干文本")}</div>
            <div class="divider"></div>
            <div class="tag-row">
              ${question.system_hints.length ? question.system_hints.map((hint) => `<span class="tiny-pill">${escapeHtml(hint)}</span>`).join("") : `<span class="muted">暂无系统线索</span>`}
            </div>
          </section>

          <section class="sidebar-card">
            <h2>下游契约</h2>
            <p class="muted">这里展示当前题最终会被后续 agent 看到的是自动结果还是人工覆盖结果。</p>
            <div class="contract-card ${escapeHtml(question.effective_assets.mode)}">
              <strong>${escapeHtml(question.effective_assets.mode === "manual_override" ? "人工覆盖生效中" : "当前仍使用自动结果")}</strong>
              <p>${escapeHtml(question.effective_assets.stale ? "但人工结果基于旧版 source revision，需要复看。" : "当前 source revision 已一致。")}</p>
              <div class="tag-row">
                <span class="tiny-pill">mode ${escapeHtml(question.effective_assets.mode)}</span>
                <span class="tiny-pill">agent_ready ${escapeHtml(String(question.effective_assets.agent_ready))}</span>
              </div>
            </div>
          </section>
        </div>
      </section>
    </main>
  `;

  syncQuestionParam(question.number);
  renderCanvas();
  renderSlotList();
  bindExamEvents();
}

function renderCanvas() {
  const host = document.getElementById("page-canvas-host");
  if (!host) {
    return;
  }
  const question = getCurrentQuestion();
  const pageMeta = getCurrentPageMeta();
  const regions = getDisplayRegions(question.number, state.currentPage);
  host.innerHTML = `
    <div class="page-frame" id="page-frame">
      <img class="page-image" src="${escapeHtml(pageMeta.image_url)}" alt="Page ${pageMeta.number}" draggable="false" />
      <svg class="page-overlay" id="page-overlay" viewBox="0 0 ${pageMeta.pdf_width} ${pageMeta.pdf_height}" preserveAspectRatio="none">
        ${renderQuestionHighlight(question)}
        ${regions.map(renderRegionOverlay).join("")}
      </svg>
    </div>
  `;
  bindCanvasEvents();
}

function renderQuestionHighlight(question) {
  if (question.page !== state.currentPage || !question.question_bbox?.length) {
    return "";
  }
  const [x0, y0, x1, y1] = question.question_bbox;
  return `
    <rect class="question-focus" x="${x0}" y="${y0}" width="${x1 - x0}" height="${y1 - y0}"></rect>
  `;
}

function renderRegionOverlay(region) {
  const [x0, y0, x1, y1] = region.bbox;
  const width = Math.max(0.5, x1 - x0);
  const height = Math.max(0.5, y1 - y0);
  const selected = state.selectedRegionKey === region.key;
  const labelX = x0 + 6;
  const labelY = y0 + 18;
  return `
    <g class="overlay-group ${selected ? "selected" : ""}" data-region-key="${escapeHtml(region.key)}">
      <rect
        class="overlay-rect slot-${escapeHtml(region.slotColor)}"
        x="${x0}"
        y="${y0}"
        width="${width}"
        height="${height}"
        data-region-key="${escapeHtml(region.key)}"
        data-region-role="body"
      ></rect>
      <text class="overlay-label" x="${labelX}" y="${labelY}" data-region-key="${escapeHtml(region.key)}" data-region-role="body">
        ${escapeHtml(region.display)}
      </text>
      ${selected ? renderOverlayHandles(region.bbox, region.key) : ""}
    </g>
  `;
}

function renderOverlayHandles(bbox, key) {
  const [x0, y0, x1, y1] = bbox;
  const points = {
    nw: [x0, y0],
    ne: [x1, y0],
    sw: [x0, y1],
    se: [x1, y1],
  };
  return Object.entries(points)
    .map(
      ([handle, [cx, cy]]) => `
        <rect
          class="overlay-handle"
          x="${cx - 4}"
          y="${cy - 4}"
          width="8"
          height="8"
          data-region-key="${escapeHtml(key)}"
          data-region-role="handle"
          data-handle="${handle}"
        ></rect>
      `
    )
    .join("");
}

function renderSlotList() {
  const host = document.getElementById("slot-list-host");
  if (!host) {
    return;
  }
  const question = getCurrentQuestion();
  const draft = getDraft(question.number);
  const saved = question.manual;
  host.innerHTML = `
    ${renderSlotCard("stem", draft.stem_regions, saved.resolved_exports.stem)}
    ${OPTION_LABELS.map((label) => renderSlotCard(`option:${label}`, draft.option_regions[label], saved.resolved_exports.options[label])).join("")}
  `;
  bindSlotEvents();
}

function renderSlotCard(slotKey, regions, savedExports) {
  const active = state.selectedSlot === slotKey;
  return `
    <section class="slot-card ${active ? "active" : ""}">
      <button class="slot-card-head" data-slot-select="${escapeHtml(slotKey)}">
        <div>
          <strong>${escapeHtml(slotDisplayLabel(slotKey))}</strong>
          <div class="muted">${regions.length ? `当前 ${regions.length} 个框` : "当前为空，可直接在左侧拖拽新增"}</div>
        </div>
        <span class="tiny-pill">${regions.length}</span>
      </button>
      <div class="slot-note">选中这个槽位后，在左侧整页画布拖拽即可新增矩形。</div>
      <div class="region-list">
        ${regions.length ? regions.map((region, index) => renderRegionRow(slotKey, region, index, savedExports[index])).join("") : `<div class="empty-box">这个槽位还没有框。</div>`}
      </div>
    </section>
  `;
}

function renderRegionRow(slotKey, region, index, savedExport) {
  const key = buildRegionKey(slotKey, index);
  const active = state.selectedRegionKey === key;
  const pageMeta = getPageMeta(region.page);
  const preview = pageMeta ? renderRegionPreview(pageMeta, region) : `<div class="crop-thumb missing">没有对应页图</div>`;
  return `
    <article class="region-row ${active ? "active" : ""}">
      <button class="region-main" data-region-select="${escapeHtml(key)}" data-region-page="${escapeHtml(String(region.page))}">
        ${preview}
        <div class="region-copy">
          <strong>${escapeHtml(slotDisplayLabel(slotKey))} · #${index + 1}</strong>
          <div class="muted">P${escapeHtml(String(region.page))} · ${escapeHtml(formatBBox(region.bbox))}</div>
          <div class="seed-text">${region.seed_asset_id ? `seed ${escapeHtml(region.seed_asset_id)}` : "人工新增"}</div>
          ${savedExport?.url ? `<a class="tiny-link inline" href="${escapeHtml(savedExport.url)}" target="_blank" rel="noreferrer">查看已导出裁图</a>` : `<span class="seed-text">尚未导出或待保存</span>`}
        </div>
      </button>
      <div class="row-actions">
        <button class="ghost-button small" data-region-move="${escapeHtml(key)}" data-direction="up" ${index === 0 ? "disabled" : ""}>上移</button>
        <button class="ghost-button small" data-region-move="${escapeHtml(key)}" data-direction="down" ${index === getRegionsForSlot(getDraft(getCurrentQuestion().number), slotKey).length - 1 ? "disabled" : ""}>下移</button>
        <button class="ghost-button small warn" data-region-delete="${escapeHtml(key)}">删除</button>
      </div>
    </article>
  `;
}

function renderRegionPreview(pageMeta, region) {
  const [x0, y0, x1, y1] = region.bbox;
  const width = Math.max(1, x1 - x0);
  const height = Math.max(1, y1 - y0);
  const imageWidth = (pageMeta.pdf_width / width) * 100;
  const imageHeight = (pageMeta.pdf_height / height) * 100;
  const left = -(x0 / width) * 100;
  const top = -(y0 / height) * 100;
  return `
    <div class="crop-thumb">
      <img
        src="${escapeHtml(pageMeta.image_url)}"
        alt="Crop preview"
        draggable="false"
        style="width:${imageWidth}%;height:${imageHeight}%;left:${left}%;top:${top}%"
      />
    </div>
  `;
}

function bindExamEvents() {
  const likelyVisualToggle = document.getElementById("toggle-likely-visual");
  if (likelyVisualToggle) {
    likelyVisualToggle.addEventListener("change", () => {
      state.onlyLikelyVisual = likelyVisualToggle.checked;
      renderExam();
    });
  }

  for (const button of document.querySelectorAll("[data-nav-question]")) {
    button.addEventListener("click", async () => {
      await navigateToIndex(Number.parseInt(button.dataset.navQuestion, 10));
    });
  }

  for (const button of document.querySelectorAll("[data-page-select]")) {
    button.addEventListener("click", () => {
      state.currentPage = Number.parseInt(button.dataset.pageSelect, 10);
      renderCanvas();
      renderSlotList();
    });
  }

  for (const button of document.querySelectorAll("[data-set-status]")) {
    button.addEventListener("click", () => {
      const draft = getDraft(getCurrentQuestion().number);
      draft.status = button.dataset.setStatus;
      if (draft.status === "confirmed_no_visual") {
        clearAllRegions(draft);
      }
      renderExam();
    });
  }

  const clearCurrentSlotButton = document.getElementById("clear-current-slot");
  if (clearCurrentSlotButton) {
    clearCurrentSlotButton.addEventListener("click", () => {
      clearSlot(getDraft(getCurrentQuestion().number), state.selectedSlot);
      renderCanvas();
      renderSlotList();
    });
  }

  const saveButton = document.getElementById("save-question");
  if (saveButton) {
    saveButton.addEventListener("click", async () => {
      await saveCurrentDraft();
    });
  }

  const markNoVisualButton = document.getElementById("mark-no-visual");
  if (markNoVisualButton) {
    markNoVisualButton.addEventListener("click", () => {
      const draft = getDraft(getCurrentQuestion().number);
      draft.status = "confirmed_no_visual";
      clearAllRegions(draft);
      renderExam();
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

function bindCanvasEvents() {
  const overlay = document.getElementById("page-overlay");
  if (!overlay) {
    return;
  }

  overlay.addEventListener("mousedown", (event) => {
    if (event.button !== 0) {
      return;
    }
    const point = pointerToPdfPoint(event, overlay);
    const handle = event.target?.dataset?.handle;
    const regionKey = event.target?.dataset?.regionKey;
    if (handle && regionKey) {
      event.preventDefault();
      selectRegion(regionKey);
      startResize(regionKey, handle, point);
      return;
    }
    if (regionKey) {
      event.preventDefault();
      selectRegion(regionKey);
      startMove(regionKey, point);
      return;
    }
    event.preventDefault();
    beginCreateRegion(point);
  });
}

function bindSlotEvents() {
  for (const button of document.querySelectorAll("[data-slot-select]")) {
    button.addEventListener("click", () => {
      state.selectedSlot = button.dataset.slotSelect;
      state.selectedRegionKey = null;
      renderSlotList();
      renderCanvas();
    });
  }

  for (const button of document.querySelectorAll("[data-region-select]")) {
    button.addEventListener("click", () => {
      state.selectedRegionKey = button.dataset.regionSelect;
      state.selectedSlot = slotKeyFromRegionKey(state.selectedRegionKey);
      state.currentPage = Number.parseInt(button.dataset.regionPage, 10);
      renderSlotList();
      renderCanvas();
    });
  }

  for (const button of document.querySelectorAll("[data-region-delete]")) {
    button.addEventListener("click", () => {
      removeRegion(button.dataset.regionDelete);
      renderSlotList();
      renderCanvas();
    });
  }

  for (const button of document.querySelectorAll("[data-region-move]")) {
    button.addEventListener("click", () => {
      moveRegion(button.dataset.regionMove, button.dataset.direction);
      renderSlotList();
      renderCanvas();
    });
  }
}

function bindGlobalPointerEvents() {
  if (window.__cropReviewPointerBound) {
    return;
  }
  window.__cropReviewPointerBound = true;
  window.addEventListener("mousemove", (event) => {
    if (!state.drag) {
      return;
    }
    const overlay = document.getElementById("page-overlay");
    if (!overlay) {
      return;
    }
    const point = pointerToPdfPoint(event, overlay);
    if (state.drag.mode === "create") {
      updateCreatedRegion(point);
      renderCanvas();
      return;
    }
    if (state.drag.mode === "move") {
      updateMovedRegion(point);
      renderCanvas();
      return;
    }
    if (state.drag.mode === "resize") {
      updateResizedRegion(point);
      renderCanvas();
    }
  });
  window.addEventListener("mouseup", () => {
    if (!state.drag) {
      return;
    }
    finalizeDrag();
  });
}

function attachKeyboardShortcuts() {
  if (window.__cropReviewKeyboardBound) {
    return;
  }
  window.__cropReviewKeyboardBound = true;
  document.addEventListener("keydown", async (event) => {
    if (bootstrap.view !== "exam") {
      return;
    }
    if (event.metaKey || event.ctrlKey || event.altKey) {
      return;
    }

    const tagName = event.target && event.target.tagName ? event.target.tagName.toLowerCase() : "";
    const editing = tagName === "textarea" || tagName === "input" || tagName === "select";
    if (editing) {
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
    if (event.key === "Delete" || event.key === "Backspace") {
      if (state.selectedRegionKey) {
        event.preventDefault();
        removeRegion(state.selectedRegionKey);
        renderSlotList();
        renderCanvas();
      }
    }
  });
}

function beginCreateRegion(point) {
  const draft = getDraft(getCurrentQuestion().number);
  const regions = getRegionsForSlot(draft, state.selectedSlot);
  regions.push({
    page: state.currentPage,
    bbox: [point.x, point.y, point.x + 0.5, point.y + 0.5],
    order: regions.length + 1,
    seed_asset_id: null,
  });
  normalizeDraftOrders(draft);
  state.selectedRegionKey = buildRegionKey(state.selectedSlot, regions.length - 1);
  state.drag = {
    mode: "create",
    questionNumber: getCurrentQuestion().number,
    slotKey: state.selectedSlot,
    regionIndex: regions.length - 1,
    page: state.currentPage,
    anchor: point,
  };
  renderSlotList();
  renderCanvas();
}

function startMove(regionKey, point) {
  const parsed = parseRegionKey(regionKey);
  const region = getRegionsForSlot(getDraft(getCurrentQuestion().number), parsed.slotKey)[parsed.index];
  state.drag = {
    mode: "move",
    questionNumber: getCurrentQuestion().number,
    slotKey: parsed.slotKey,
    regionIndex: parsed.index,
    page: region.page,
    anchor: point,
    startBBox: [...region.bbox],
  };
}

function startResize(regionKey, handle, point) {
  const parsed = parseRegionKey(regionKey);
  const region = getRegionsForSlot(getDraft(getCurrentQuestion().number), parsed.slotKey)[parsed.index];
  state.drag = {
    mode: "resize",
    questionNumber: getCurrentQuestion().number,
    slotKey: parsed.slotKey,
    regionIndex: parsed.index,
    page: region.page,
    anchor: point,
    startBBox: [...region.bbox],
    handle,
  };
}

function updateCreatedRegion(point) {
  const region = getDraggedRegion();
  const nextBBox = normalizeBBox([
    Math.min(state.drag.anchor.x, point.x),
    Math.min(state.drag.anchor.y, point.y),
    Math.max(state.drag.anchor.x, point.x),
    Math.max(state.drag.anchor.y, point.y),
  ]);
  region.bbox = clampBBoxToPage(nextBBox, state.drag.page);
}

function updateMovedRegion(point) {
  const region = getDraggedRegion();
  const start = state.drag.startBBox;
  const dx = point.x - state.drag.anchor.x;
  const dy = point.y - state.drag.anchor.y;
  region.bbox = clampBBoxToPage([
    start[0] + dx,
    start[1] + dy,
    start[2] + dx,
    start[3] + dy,
  ], state.drag.page);
}

function updateResizedRegion(point) {
  const start = state.drag.startBBox;
  const next = [...start];
  if (state.drag.handle.includes("n")) {
    next[1] = point.y;
  }
  if (state.drag.handle.includes("s")) {
    next[3] = point.y;
  }
  if (state.drag.handle.includes("w")) {
    next[0] = point.x;
  }
  if (state.drag.handle.includes("e")) {
    next[2] = point.x;
  }
  getDraggedRegion().bbox = clampBBoxToPage(normalizeBBox(next), state.drag.page);
}

function finalizeDrag() {
  const drag = state.drag;
  state.drag = null;
  if (!drag) {
    return;
  }
  const region = getRegionsForSlot(getDraft(getCurrentQuestion().number), drag.slotKey)[drag.regionIndex];
  const width = region.bbox[2] - region.bbox[0];
  const height = region.bbox[3] - region.bbox[1];
  if (width < 2 || height < 2) {
    getRegionsForSlot(getDraft(getCurrentQuestion().number), drag.slotKey).splice(drag.regionIndex, 1);
    normalizeDraftOrders(getDraft(getCurrentQuestion().number));
    state.selectedRegionKey = null;
  }
  renderSlotList();
  renderCanvas();
}

function getDraggedRegion() {
  return getRegionsForSlot(getDraft(getCurrentQuestion().number), state.drag.slotKey)[state.drag.regionIndex];
}

function moveRegion(regionKey, direction) {
  const parsed = parseRegionKey(regionKey);
  const regions = getRegionsForSlot(getDraft(getCurrentQuestion().number), parsed.slotKey);
  const targetIndex = direction === "up" ? parsed.index - 1 : parsed.index + 1;
  if (targetIndex < 0 || targetIndex >= regions.length) {
    return;
  }
  const [item] = regions.splice(parsed.index, 1);
  regions.splice(targetIndex, 0, item);
  normalizeDraftOrders(getDraft(getCurrentQuestion().number));
  state.selectedRegionKey = buildRegionKey(parsed.slotKey, targetIndex);
}

function removeRegion(regionKey) {
  const parsed = parseRegionKey(regionKey);
  const regions = getRegionsForSlot(getDraft(getCurrentQuestion().number), parsed.slotKey);
  regions.splice(parsed.index, 1);
  normalizeDraftOrders(getDraft(getCurrentQuestion().number));
  state.selectedRegionKey = null;
}

function clearSlot(draft, slotKey) {
  if (slotKey === "stem") {
    draft.stem_regions = [];
  } else {
    draft.option_regions[slotKey.split(":")[1]] = [];
  }
  normalizeDraftOrders(draft);
  state.selectedRegionKey = null;
}

function clearAllRegions(draft) {
  draft.stem_regions = [];
  for (const label of OPTION_LABELS) {
    draft.option_regions[label] = [];
  }
  normalizeDraftOrders(draft);
  state.selectedRegionKey = null;
}

async function navigateRelative(delta) {
  const visibleEntries = getVisibleQuestionEntries();
  const currentVisibleIndex = visibleEntries.findIndex((entry) => entry.index === state.currentIndex);
  const nextVisible = visibleEntries[currentVisibleIndex + delta];
  if (!nextVisible) {
    return;
  }
  await navigateToIndex(nextVisible.index);
}

async function navigateToIndex(nextIndex) {
  if (nextIndex < 0 || nextIndex >= state.detail.question_views.length || nextIndex === state.currentIndex) {
    return;
  }
  const saved = await persistDirtyDraft();
  if (!saved) {
    return;
  }
  state.currentIndex = nextIndex;
  state.currentPage = getCurrentQuestion().page;
  state.selectedRegionKey = null;
  state.selectedSlot = "stem";
  state.message = null;
  renderExam();
}

async function persistDirtyDraft() {
  const question = getCurrentQuestion();
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
    if (!options.silentSuccess) {
      state.message = "当前题没有未保存改动。";
      state.messageTone = "info";
      renderExam();
    }
    return true;
  }

  state.saving = true;
  renderExam();
  try {
    const result = await fetchJson(
      `/api/crop-review/exams/${encodeURIComponent(state.detail.meta.exam_id)}/questions/${question.number}`,
      {
        method: "PUT",
        body: JSON.stringify(draft),
      },
    );
    const savedQuestion = state.detail.question_views.find((item) => item.number === question.number);
    Object.assign(savedQuestion, {
      page: result.question.page,
      page_image_url: result.question.page_image_url,
      page_meta: result.question.page_meta,
      question_bbox: result.question.question_bbox,
      text_bbox: result.question.text_bbox,
      likely_visual: result.question.likely_visual,
      seed_regions: result.question.seed_regions,
      manual: result.question.manual,
      effective_assets: result.question.effective_assets,
    });
    state.drafts[question.number] = cloneDraft(result.question.manual);
    Object.assign(state.detail.meta, result.summary);
    state.saving = false;
    state.message = options.successMessage || "当前题的人工框选已保存并导出。";
    state.messageTone = "success";
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

function ensureCurrentQuestionVisible() {
  const visibleEntries = getVisibleQuestionEntries();
  if (!visibleEntries.length) {
    state.onlyLikelyVisual = false;
    return;
  }
  if (!visibleEntries.some((entry) => entry.index === state.currentIndex)) {
    state.currentIndex = visibleEntries[0].index;
    state.currentPage = getCurrentQuestion().page;
  }
}

function getVisibleQuestionEntries() {
  return state.detail.question_views
    .map((question, index) => ({ question, index }))
    .filter(({ question }) => {
      if (!state.onlyLikelyVisual) {
        return true;
      }
      return question.likely_visual || question.manual.status !== "pending";
    });
}

function findInitialIndex() {
  const candidate = state.detail.question_views.findIndex(
    (question) => question.likely_visual && question.manual.status === "pending"
  );
  if (candidate >= 0) {
    return candidate;
  }
  const pending = state.detail.question_views.findIndex((question) => question.manual.status === "pending");
  return pending >= 0 ? pending : 0;
}

function getCurrentQuestion() {
  return state.detail.question_views[state.currentIndex];
}

function getCurrentPageMeta() {
  return getPageMeta(state.currentPage);
}

function getPageMeta(pageNumber) {
  return state.detail.pages.find((page) => page.number === pageNumber);
}

function getDraft(questionNumber) {
  if (!state.drafts[questionNumber]) {
    const question = state.detail.question_views.find((item) => item.number === questionNumber);
    state.drafts[questionNumber] = cloneDraft(question.manual);
  }
  return state.drafts[questionNumber];
}

function cloneDraft(manual) {
  return {
    status: manual.status,
    stem_regions: (manual.stem_regions || []).map(cloneRegion),
    option_regions: Object.fromEntries(
      OPTION_LABELS.map((label) => [label, (manual.option_regions?.[label] || []).map(cloneRegion)])
    ),
  };
}

function cloneRegion(region) {
  return {
    page: region.page,
    bbox: [...region.bbox],
    order: region.order,
    seed_asset_id: region.seed_asset_id || null,
  };
}

function blankDraft() {
  return {
    status: "pending",
    stem_regions: [],
    option_regions: Object.fromEntries(OPTION_LABELS.map((label) => [label, []])),
  };
}

function normalizeDraft(draft) {
  const normalized = {
    status: draft.status,
    stem_regions: normalizeRegionList(draft.stem_regions),
    option_regions: Object.fromEntries(
      OPTION_LABELS.map((label) => [label, normalizeRegionList(draft.option_regions[label])])
    ),
  };
  return normalized;
}

function normalizeRegionList(regions) {
  return regions
    .map((region) => ({
      page: Number(region.page),
      bbox: normalizeBBox(region.bbox),
      order: Number(region.order) || 0,
      seed_asset_id: region.seed_asset_id || null,
    }))
    .sort((left, right) => left.order - right.order)
    .map((region, index) => ({ ...region, order: index + 1 }));
}

function normalizeDraftOrders(draft) {
  draft.stem_regions = normalizeRegionList(draft.stem_regions);
  for (const label of OPTION_LABELS) {
    draft.option_regions[label] = normalizeRegionList(draft.option_regions[label]);
  }
}

function isDraftDirty(question) {
  return JSON.stringify(normalizeDraft(getDraft(question.number))) !== JSON.stringify(normalizeDraft(question.manual));
}

function validateDraft(draft) {
  if (draft.status === "completed") {
    const totalRegions =
      draft.stem_regions.length + OPTION_LABELS.reduce((sum, label) => sum + draft.option_regions[label].length, 0);
    if (!totalRegions) {
      return { ok: false, message: "如果整题确认没有图，请使用“确认本题无图”，不要保存为空的 completed。" };
    }
  }
  if (draft.status === "confirmed_no_visual") {
    const hasRegions =
      draft.stem_regions.length || OPTION_LABELS.some((label) => draft.option_regions[label].length);
    if (hasRegions) {
      return { ok: false, message: "confirmed_no_visual 必须让题干和 A-E 全部槽位都为空。" };
    }
  }
  return { ok: true };
}

function getDisplayRegions(questionNumber, pageNumber) {
  const draft = getDraft(questionNumber);
  const items = [];
  draft.stem_regions.forEach((region, index) => {
    if (region.page !== pageNumber) {
      return;
    }
    items.push({
      key: buildRegionKey("stem", index),
      slotKey: "stem",
      slotColor: "stem",
      display: `题干 ${index + 1}`,
      bbox: region.bbox,
      page: region.page,
    });
  });
  OPTION_LABELS.forEach((label) => {
    draft.option_regions[label].forEach((region, index) => {
      if (region.page !== pageNumber) {
        return;
      }
      items.push({
        key: buildRegionKey(`option:${label}`, index),
        slotKey: `option:${label}`,
        slotColor: label.toLowerCase(),
        display: `${label} ${index + 1}`,
        bbox: region.bbox,
        page: region.page,
      });
    });
  });
  return items;
}

function getRegionsForSlot(draft, slotKey) {
  return slotKey === "stem" ? draft.stem_regions : draft.option_regions[slotKey.split(":")[1]];
}

function buildRegionKey(slotKey, index) {
  return `${slotKey}:${index}`;
}

function slotKeyFromRegionKey(key) {
  const parts = key.split(":");
  return parts.length === 3 ? `${parts[0]}:${parts[1]}` : parts[0];
}

function parseRegionKey(key) {
  const parts = key.split(":");
  if (parts[0] === "stem") {
    return { slotKey: "stem", index: Number(parts[1]) };
  }
  return { slotKey: `${parts[0]}:${parts[1]}`, index: Number(parts[2]) };
}

function selectRegion(regionKey) {
  state.selectedRegionKey = regionKey;
  state.selectedSlot = slotKeyFromRegionKey(regionKey);
}

function pointerToPdfPoint(event, overlay) {
  const rect = overlay.getBoundingClientRect();
  const pageMeta = getCurrentPageMeta();
  const x = ((event.clientX - rect.left) / rect.width) * pageMeta.pdf_width;
  const y = ((event.clientY - rect.top) / rect.height) * pageMeta.pdf_height;
  return {
    x: clampValue(x, 0, pageMeta.pdf_width),
    y: clampValue(y, 0, pageMeta.pdf_height),
  };
}

function clampBBoxToPage(bbox, pageNumber) {
  const pageMeta = getPageMeta(pageNumber);
  return normalizeBBox([
    clampValue(bbox[0], 0, pageMeta.pdf_width),
    clampValue(bbox[1], 0, pageMeta.pdf_height),
    clampValue(bbox[2], 0, pageMeta.pdf_width),
    clampValue(bbox[3], 0, pageMeta.pdf_height),
  ]);
}

function normalizeBBox(bbox) {
  return [
    Number(Math.min(bbox[0], bbox[2]).toFixed(2)),
    Number(Math.min(bbox[1], bbox[3]).toFixed(2)),
    Number(Math.max(bbox[0], bbox[2]).toFixed(2)),
    Number(Math.max(bbox[1], bbox[3]).toFixed(2)),
  ];
}

function clampValue(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function renderQuestionPill(question, index) {
  const active = index === state.currentIndex ? "active" : "";
  const stale = question.manual.stale ? "stale" : "";
  return `
    <button class="question-pill ${active} ${stale}" data-nav-question="${index}">
      ${question.number}
    </button>
  `;
}

function renderPageButton(page) {
  const active = state.currentPage === page.number ? "active" : "";
  return `
    <button class="page-pill ${active}" data-page-select="${page.number}">
      P${page.number}
    </button>
  `;
}

function renderStatusButton(status, currentStatus) {
  return `
    <button class="status-button ${status === currentStatus ? "active" : ""}" data-set-status="${escapeHtml(status)}">
      ${escapeHtml(labelForStatus(status))}
    </button>
  `;
}

function metricCard(label, value, detail) {
  return `
    <div class="metric-card">
      <div class="metric-label">${escapeHtml(String(label))}</div>
      <div class="metric-value">${escapeHtml(String(value))}</div>
      <div class="muted">${escapeHtml(String(detail))}</div>
    </div>
  `;
}

function summaryStatus(exam) {
  if (exam.stale_question_count) {
    return "warn";
  }
  if (exam.counts.pending === 0) {
    return "ready";
  }
  if (exam.counts.ready > 0) {
    return "progress";
  }
  return "pending";
}

function summaryLabel(exam) {
  if (exam.stale_question_count) {
    return "需复看";
  }
  if (exam.counts.pending === 0) {
    return "已完成";
  }
  if (exam.counts.ready > 0) {
    return "进行中";
  }
  return "未开始";
}

function slotDisplayLabel(slotKey) {
  return slotKey === "stem" ? "题干图" : `选项 ${slotKey.split(":")[1]}`;
}

function labelForStatus(status) {
  return state.detail?.schema?.statuses?.find((item) => item.value === status)?.label
    || state.overview?.schema?.statuses?.find((item) => item.value === status)?.label
    || status;
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

function formatBBox(bbox) {
  return bbox.map((value) => Number(value).toFixed(1)).join(", ");
}

function syncQuestionParam(questionNumber) {
  const url = new URL(window.location.href);
  url.searchParams.set("question", String(questionNumber));
  window.history.replaceState({}, "", url);
}

function renderFatal(message) {
  app.innerHTML = `
    <main class="crop-shell">
      <div class="empty-box fatal">${escapeHtml(message)}</div>
    </main>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
