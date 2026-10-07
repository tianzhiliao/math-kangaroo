# 方案 C · OpenAI Style — 实施规格

> 状态：已实施（`apps/web`，见文末“实施记录”）· 设计稿：[Design 画布 › C 页](https://claude.ai/artifact/YRgumGEh7ifRoBokMNQdMp)（私有，需所有者分享）· 本地原型：`docs/design/prototypes/openai/` · 截图：`docs/design/screenshots/openai-*.png` · Token：`docs/design/tokens/plan-c.tokens.css`（取值来源 `docs/design/tokens/openai-style.tokens.json`）

本文件是把方案 C 落到 `apps/web` 的完整规格。它不改变任何业务逻辑（计分、答案校验、AI 解释、TTS、数据加载），只替换视觉层并做少量交互调整（§6）。凡是本文没写到的行为，以现有代码为准。

---

## 1. 设计理念

**“白底黑字、一根细线做骨架；把表达留给内容和少数几个时刻。”**

1. **骨架不说话。** 页面只有白底、黑字（用透明度分级）、一根 `1px rgba(0,0,0,.12)` 的线和留白。题目本身（题干 + 插图）是每屏的主角。
2. **两个字重。** UI 一律 500，正文 400，全站不出现 700/900。层级靠字号与透明度，不靠加粗。
3. **颜色只在有意义时出现。** 绿/红只表达“答对/答错”；黄/蓝/品红只出现在首页 hero 和结果页分段条里，不承载状态。
4. **为 6–7 岁孩子放大。** 题干 26px、选项 22px、所有可点区域 ≥ 44px、主按钮 48px（设计系统默认 40px，见 §9 偏离记录）。
5. **少即是多的反馈。** 颜色过渡 200ms 线性；不做 hover 上浮、不做阴影堆叠；只有对话框有一层浮层阴影。

---

## 2. 色彩 Token

完整定义见 `tokens/plan-c.tokens.css`。实现时变量统一用 `--mk-*` 前缀。

### 2.1 中性（亮色主题）

| Token | 值 | 用途 |
|---|---|---|
| `--mk-bg` | `#ffffff` | 页面底色 |
| `--mk-ink-100` | `#000000` | 标题、正文、主按钮底、当前题 |
| `--mk-ink-80` | `rgba(0,0,0,.8)` | 长段正文（首页介绍、对话框说明） |
| `--mk-ink-60` | `rgba(0,0,0,.6)` | meta 行、次要文字、图例（对比 5.7:1） |
| `--mk-ink-44` | `rgba(0,0,0,.44)` | **仅**占位符、虚线边框（3.2:1，不得用于必须阅读的文字） |
| `--mk-ink-12` | `rgba(0,0,0,.12)` | 全站唯一描边：header 底线、侧栏右线、卡片边框 |
| `--mk-ink-4` | `rgba(0,0,0,.04)` | 进度条轨道、图片占位、禁用按钮底 |
| `--mk-ink-2` | `rgba(0,0,0,.02)` | 选项卡 hover 底 |
| `--mk-raised` | `#f1f1f1` | 次按钮、图标按钮、未选中字母徽章 |
| `--mk-solid-12` | `#e0e0e0` | 考试中“已作答”题号 |
| `--mk-inverse-fg` | `#ffffff` | 墨底上的文字 |

### 2.2 答题状态

| Token | 值 | 用途 |
|---|---|---|
| `--mk-right-strong` | `#027f41` | 正确选项的边框、字母徽章底、“Right answer”标签 |
| `--mk-right-surface` | `#e6ffec` | 正确选项卡底色 |
| `--mk-right-soft` | `#def3e5` | 题号“对”、反馈胶囊、结果计数块 |
| `--mk-right-fg` | `#2c6732` | soft 底上的文字（5.8:1） |
| `--mk-right-dot` | `#9fddb1` | 图例圆点 |
| `--mk-wrong-strong` | `#f22f4d` | 错误选项卡**边框**（不用于文字） |
| `--mk-wrong-surface` | `#ffebe9` | 错误选项卡底色 |
| `--mk-wrong-soft` | `#ffe5e0` | 题号“错”、反馈胶囊、danger-soft 按钮 |
| `--mk-wrong-subtle` | `#fff4f3` | 讲解加载失败面板 |
| `--mk-wrong-fg` | `#92201d` | 红色系上的文字、错误字母徽章底（9.8:1） |
| `--mk-wrong-dot` | `#ffc9c0` | 图例圆点 |
| `--mk-warn-fg` / `--mk-warn-bar` | `#ac4f23` / `#ffaf00` | 剩余 < 5 分钟的文字与进度条 |

色弱可辨：对/错除颜色外**总有第二通道**——标签文字（Right answer / Your answer）、反馈胶囊的 ✓/✗ 线性图标、结果页计数块的文字。

### 2.3 表达色（不承载状态）

| Token | 值 | 用途 |
|---|---|---|
| `--mk-hue-blue` / `--mk-hue-yellow` / `--mk-hue-magenta` | `#29bdfd` / `#ffaf00` / `#eb56c5` | 首页 hero 背景少量算式；结果页三段分值条 |
| `--mk-series-felix` | `#e8f3fe` | 选卷卡封面：Felix · Austria |
| `--mk-series-level-p` | `#fdf6dc` | 选卷卡封面：Level P · Brazil；“变式题”面板底色 |
| `--mk-series-grade-1-2` | `#fbe8db` | 选卷卡封面：Grade 1–2 · Canada |
| `--mk-scrim` | `rgba(0,0,0,.44)` | 对话框遮罩 |
| `--mk-focus` | `#1e60e4` | 键盘焦点环（刻意不用黑色，避免与“当前题”黑描边混淆） |

暗色主题：本期**不做**。所有颜色已经是语义变量，后续可按 `openai-style.tokens.json` 的 dark 值整体切换。

---

## 3. 字体

### 3.1 字体族

- `sans`：**Inter**（400、500），通过 `next/font/google` 加载，变量 `--font-inter`，替换 `apps/web/app/layout.tsx` 里的 Geist / Geist_Mono。
- `mono`：系统等宽栈（仅首页 hero 背景算式使用），不额外加载字体。
- 全站禁止 `font-weight: 700/800/900`（现代码大量使用 `font-black` / `font-bold`，需全部替换）。

### 3.2 字阶（字号 / 行高 / 字距 / 字重 永远成组使用）

| 角色 | 桌面 | 手机（<768px） | 用在 |
|---|---|---|---|
| `display` | 64 / 64 / −0.03em / 500 | 40 / 44 / −0.03em / 500 | 首页 h1（`text-wrap: balance`） |
| `score` | 48 / 56 / −0.03em / 500 | 40 / 48 | 结果页分数（每页只出现一次） |
| `title` | 38 / 44 / −0.02em / 500 | 30 / 36 | 选卷页 h1 |
| `stem` | 26 / 34 / −0.01em / 500 | 21 / 28 | 题干（`text-wrap: pretty`） |
| `h4` | 22 / 28 / −0.01em / 500 | 同 | 卡片标题、讲解标题、对话框标题 |
| `choice` | 22 / 28 / −0.01em / 500 | 19 / 26 | 文字型选项 |
| `h5` | 18 / 24 / −0.01em / 500 | 同 | header 标题行、选卷卡系列名、变式题标题 |
| `p1` | 17 / 28 / −0.01em / 400 | 同 | 正文段落（正文**不随屏幕缩放**） |
| `explain` | 19 / 30 / −0.01em / 400 | 17 / 28 | 讲解正文 |
| `cta` | 15 / 15 / 0 / 500 | 同 | 按钮文字（系统默认 14，放大到 15） |
| `meta` | 14 / 20 / 0 / 500 | 13 / 18 | meta 行、次要标签、题号 |
| `caption` | 13 / 18 / 0 / 500 | 同 | 图例、状态标签（Right answer） |

数字一律 `font-variant-numeric: tabular-nums`（计时器、题号、分数）。

---

## 4. 间距、圆角、阴影、动效、焦点

### 4.1 间距（4px 基数）

| 场景 | 值 |
|---|---|
| Header 高度 | 64px（手机 54px），左右 24px（手机 8px） |
| 侧栏 | 宽 250–280px，内边距 24px，块间 16–20px |
| 主区内边距 | 40px 48px（手机 20px 16px） |
| 主内容最大宽 | 860px，水平居中 |
| 题干块 ↔ 选项网格 | 28px |
| 选项网格 gap | 12px（手机 8px） |
| 主区纵向块间距 | 24px |
| Footer | 上边线 + 16px 48px 内边距 |
| 题号网格 gap | 8px |

### 4.2 圆角（按值选，设计系统的命名是非单调的）

| 值 | 用在 |
|---|---|
| 6px | 输入框、结果计数块 |
| 16px | 卡片、选项卡、题干插图框、选卷卡封面 |
| 24px | 讲解面板、变式题面板、对话框、分数卡 |
| 2.5rem | 所有胶囊按钮 |
| 9999px | 题号、图标按钮、字母徽章、反馈胶囊 |

### 4.3 阴影

只有一个：`--mk-shadow-popover: 0 18px 60px rgba(0,0,0,.08)`，**仅**用于对话框。其他任何元素零阴影（删除现有 `shadow-sm/md/lg/xl/inner`）。

### 4.4 动效

| 场景 | 规格 |
|---|---|
| 颜色 / 边框 / 底色过渡 | 200ms linear，只过渡 `background-color, border-color, color, opacity` |
| 链接 / 导航 hover | 100ms |
| 对话框进入 | 遮罩 opacity 0→1，面板 opacity 0→1 + translateY(4px→0)，200ms `cubic-bezier(.2,0,0,1)` |
| 讲解面板展开 | 高度不做动画；内容 opacity 0→1 200ms |
| 计时条 | `width` 1s linear |
| 禁止 | hover 上浮（删除 `hover:-translate-y-0.5`）、`active:scale`、`transition-all`、spin 以外的循环动画 |
| `prefers-reduced-motion` | 全部时长归零，加载圈改为静态 |

### 4.5 焦点

- `:focus-visible { outline: 2px solid var(--mk-focus); outline-offset: 2px; }`，圆形控件同样 2px 偏移。
- “当前题”用黑色 2px outline（offset 2px）或黑底，与蓝色焦点环区分。
- 导航链接用颜色 + 下划线表示焦点。

---

## 5. 组件清单与规格

新建 `apps/web/components/ui/`，放通用组件；业务组件仍在 `components/exam/`、`components/question/`。

### 5.1 `Button`（新建 `components/ui/Button.tsx`）

| 变体 | 底 / 字 | 用途 |
|---|---|---|
| `primary` | `--mk-ink-100` / 白 | Next、Submit exam、Keep and exit、Choose another paper |
| `secondary` | `--mk-raised` / 黑 | Previous、End practice、Try this paper again、Hide |
| `danger-soft` | `--mk-wrong-soft` / `--mk-wrong-fg` | Clear and exit、Leave exam |
| `ghost` | 透明 / `--mk-ink-60` | Cancel |
| `outline` | 白 + 1px `--mk-ink-12` / 黑 | 备用 |

- 尺寸：`md` 高 48px、左右 24px、`cta` 字阶（默认）；`sm` 高 44px、左右 18–20px、14px。圆角 2.5rem。
- 状态：hover 时 primary 底变 `--mk-ink-80`，secondary 底变 `#e0e0e0`；disabled 底 `--mk-ink-4`、字 `--mk-ink-44`、`cursor: not-allowed`，**不再用 opacity 降低整块**。
- 渲染为 `<button>`；需要导航时用 `asChild` 或单独的 `ButtonLink`（`next/link`）。

### 5.2 `IconButton`（新建）

44×44 圆形，`--mk-raised` 底，图标 20px、1.6px 线宽、`currentColor`，**必须**带 `aria-label`。header 里的返回按钮用透明底 + `--mk-ink-60` 图标。

### 5.3 `AppHeader`（新建 `components/ui/AppHeader.tsx`）

用于考试、结果、练习三种页面：

```
[‹ 返回 IconButton] [meta 14/500 ink-60]           [右侧插槽]
                    [标题 18/500]
```

- 高 64px，底部 1px `--mk-ink-12`；`flex-wrap`，窄屏时右侧插槽换行。
- 考试：meta `Exam · Level P · Brazil`，标题 `2020 paper`，右侧 = `Timer` + `Submit exam`（primary sm）。
- 结果：meta `Exam · Submitted · 38 min`，标题 `Level P · Brazil 2020`，右侧 = `Try this paper again`（secondary sm）+ `Choose another paper`（primary sm）。
- 练习：meta `Practice · {n} right first time`，标题 `Question {i} of {total}`，右侧 = `End practice`（secondary sm）。

### 5.4 `Timer`（从 `ExamRun` 抽出，新建 `components/exam/Timer.tsx`）

- 文字 `31:24 left`（`meta` 字阶，tabular），下方 140×4px 进度条：轨道 `--mk-ink-4`，填充 `--mk-ink-100`。
- 剩余 < 5 分钟：文字 `--mk-warn-fg`，填充 `--mk-warn-bar`。
- **始终显示数字**（现在需要 hover 才显示）。
- `aria-live="polite"` 只在整分钟和最后 1 分钟时更新一次文本，避免读屏每秒播报；`role="progressbar"` 保留。

### 5.5 `QuestionSidebar` 题号（改 `components/exam/QuestionSidebar.tsx`）

- 题号 44×44 圆形（手机横排 40×40），`meta` 字阶 500，tabular。
- 桌面 4 列网格、gap 8px、居中；手机横向滚动行，当前题自动滚入视口（保留现有 `scrollIntoView` 逻辑）。

| 状态 | 样式 |
|---|---|
| `empty` | 白底 + 1px `--mk-ink-12`，字 `--mk-ink-60` |
| `answered`（考试中） | `--mk-solid-12` 底，黑字 |
| `current`（考试中、未交卷） | 黑底白字 |
| `correct` | `--mk-right-soft` 底，`--mk-right-fg` 字 |
| `wrong` | `--mk-wrong-soft` 底，`--mk-wrong-fg` 字 |
| `skipped` | 白底 + 1px **虚线** `--mk-ink-44`，字 `--mk-ink-60` |
| current + 有状态（练习/结果） | 保留状态底色，加 `outline: 2px solid #000; outline-offset: 2px` |

- 侧栏下方加**图例**（新建 `components/exam/StatusLegend.tsx`）：10px 圆点 + `caption` 文字。考试中：Now / Answered / Not yet；结果：Right / Wrong / Skipped（计数在 ScoreCard）；练习：Right / Wrong / Not tried。
- 标题行：左 `Questions`（meta ink-60），右 `5 / 24`（考试中已答数）。

### 5.6 `QuestionCard` + 选项（改 `components/question/QuestionCard.tsx`）

**题干区**
- meta 行：考试 `Question {n} · {points} points`；练习 `{Series} {year} · Question {n} · {points} points`（系列名映射见 §7.2）。`points` 取 `question.points`，缺省时由 `exam.scoring_rules` 推算。
- 右侧 `StemTtsButton`（§5.7）。
- 题干：`stem` 字阶。
- 插图：放在 1px `--mk-ink-12`、圆角 16px、内边距 12px 的框里；桌面在题干右侧（`flex-wrap`，题干 `flex: 1 1 360px`），手机在题干下方占满宽度。
- 去掉现有卡片外框（`border-2 rounded-2xl shadow-sm`）——题目直接放在页面上，靠留白分区。

**选项网格**
- 文字型：`grid-template-columns: repeat(auto-fill, minmax(250px, 1fr))`；图片型：`minmax(150px, 1fr)`；手机一律单列。
- **每个选项是真正的 `<button type="button" aria-pressed>`**（替换现在的 `div role="button"` + 手写键盘处理）。只读（变式题）时渲染为 `<div>`。
- 卡片：圆角 16px，2px 边框，最小高 64px（手机 54px），内边距 10/18/10/12px；字母徽章 44px 圆形（图片型 40px），`choice` 字阶。
- 图片型：徽章在上，图片在下（高 104px，`object-fit: contain`，加载前 `--mk-ink-4` 占位）。

| 状态 | 卡片 | 徽章 | 右侧标签 |
|---|---|---|---|
| 默认 | 白底，边 `--mk-ink-12` | `--mk-raised` 底黑字 | — |
| hover | 底 `--mk-ink-2`，边 `--mk-ink-44` | 同上 | — |
| 已选（考试中） | 白底，边黑 | 黑底白字 | — |
| 正确答案（揭晓后） | `--mk-right-surface`，边 `--mk-right-strong` | `--mk-right-strong` 底白字 | `Right answer`（right-strong） |
| 你选的错误答案 | `--mk-wrong-surface`，边 `--mk-wrong-strong` | `--mk-wrong-fg` 底白字 | `Your answer`（wrong-fg） |
| 你选的正确答案 | 同“正确答案” | 同上 | `Your answer` |
| 其他（揭晓后） | 白底，边 `--mk-ink-12`，`opacity: .5` | `--mk-raised` | — |
| 禁用（交卷后未揭晓的题） | 同“其他” | | |

### 5.7 `StemTtsButton`（同文件内）

44px 圆形 IconButton。

| 状态 | 样式 |
|---|---|
| idle | `--mk-raised` 底，喇叭图标 |
| loading | `--mk-ink-4` 底，16px 静态环（reduced-motion 下不转），`cursor: wait`，`aria-busy` |
| playing | 黑底，白色 12px 圆角方块（停止），`aria-label="Stop audio"` |
| error | `--mk-wrong-soft` 底，`--mk-wrong-fg` 图标；按钮下方 13px `--mk-wrong-fg` 文字 “Could not play the audio.”（最大宽 160px） |

### 5.8 `FeedbackPill`（新建 `components/exam/FeedbackPill.tsx`，替换练习页的 ✓/✗ 文字行）

圆角胶囊，内边距 12/20px，18px 500，`aria-live="polite"`，左侧 18px 线性图标。
- 对：`--mk-right-soft` 底 `--mk-right-fg` 字，图标 ✓，文案 `Right—the answer is {label}{, choice.text}`。（原型里的 “Right—Max weighs 8 kg” 需要理解题意，数据里没有，实施时用这个通用句式。）
- 错：`--mk-wrong-soft` 底 `--mk-wrong-fg` 字，图标 ✗，文案 `Not quite—the right answer is {label}{, choice.text}`。
- `{, choice.text}` 只在正确选项有文字时追加（图片选项省略）。

### 5.9 `PracticeExplanationPanel`（改 `components/exam/PracticeExplanationPanel.tsx`）

容器：1px `--mk-ink-12`、圆角 24px、内边距 24/28px。去掉现在的琥珀色。

| 状态 | 内容 |
|---|---|
| 收起 | 左：`Want to know why?`（h5）+ `A short explanation in simple English`（14 ink-60）；右：`Show explanation`（primary） |
| 加载中 | meta 行 `Writing the explanation…` + 两条 12px 高的 `--mk-ink-4` 骨架条（80%、62% 宽） |
| 失败 | 底色 `--mk-wrong-subtle`、无边框；文字 `--mk-wrong-fg` 16px；右侧 `Try again`（primary sm）。答案校验不一致的报错沿用现有文案 |
| 已加载 | meta `Explanation · checked against the answer key`（命中缓存时追加 ` · Saved`）；标题 `Why the answer is {correct_label}`（h4）；正文 `explain` 字阶，按句号/换行切成段落，最大宽 60ch；右上 `IconButton`（↻，`aria-label="Write the explanation again"`，触发现有 regenerate）+ `Hide`（secondary sm） |
| 重新生成中 | ↻ 按钮 `aria-busy`，图标换成静态环；正文保持旧内容 |

### 5.10 `GeneratedQuestionSection` 变式题（改 `components/question/GeneratedQuestionSection.tsx`）

- 面板：`--mk-series-level-p` 底、圆角 24px、内边距 20/24px，`aria-label="变式题"`。
- 收起：左 meta `变式题` + 标题 `Try a similar question with new numbers`（h5）；右 `Open`（primary，`aria-expanded="false"`）。
- 展开：标题行右侧变 `Close`（白底胶囊，`aria-expanded="true"`）；下方白色卡（圆角 16px、内边距 18px）内渲染只读 `QuestionCard`（`readOnly hideAudio`，选项 5 列紧凑卡，徽章 32px）。
- **考试进行中不显示变式题**；交卷后的回看、练习模式显示（§6）。

### 5.11 `ConfirmDialog`（新建 `components/ui/ConfirmDialog.tsx`）+ `PracticeExitDialog` 改造

- 遮罩 `--mk-scrim`；面板白底、1px `--mk-ink-12`、圆角 24px、内边距 28px、最大宽 480px、`--mk-shadow-popover`。
- 标题 h4，说明 `p1`（ink-80），按钮**纵向堆叠、全宽**（48px）：主操作在上。
- 行为：`role="dialog" aria-modal="true" aria-labelledby`；打开时焦点落在**安全操作**（Keep working / Stay / Keep and exit）；Esc 和点遮罩 = 取消；焦点锁在对话框内；关闭后焦点回到触发按钮。
- 实例：

| 场景 | 标题 | 说明 | 按钮（上→下） |
|---|---|---|---|
| 交卷 | Submit your exam? | You answered {a} of {n}. After you submit, answers can’t be changed. | Submit exam（primary）· Keep working（secondary） |
| 离开考试 | Leave this exam? | Answers you have not submitted will be lost. | Stay（primary）· Leave exam（danger-soft） |
| 结束练习 | Save your practice progress? | You are on question {i}. Keep your progress to continue next time, or clear it to start fresh from question 1. | Keep and exit（primary）· Clear and exit（danger-soft）· Cancel（ghost） |

### 5.12 `ScoreCard`（新建 `components/exam/ScoreCard.tsx`，结果页）

- 黑底白字卡，圆角 24px，内边距 22px：`Score`（14 白 60%）→ `79`（score 字阶）+ `of 120`（17 白 60%）。
- 三段分值条：每段一行 `Questions 1–8 · 3 points each` / `15 / 24`（13/500），下方 6px 条（轨道白 20%，填充依次 hue-blue / hue-yellow / hue-magenta）。数据来自 `scoring_rules`，见 §8 的 `computeTierBreakdown`。
- 卡下方三个计数块（圆角 6px）：right（right-soft / right-fg）、wrong（wrong-soft / wrong-fg）、skipped（raised / 黑）。

### 5.13 `PaperCard` + `FilterPills`（选卷页，新建 `components/exam/PaperCard.tsx`）

- 卡片整体是 `<Link>`：封面块（高 104px、圆角 16px、底色按系列 §2.3、左下角年份 30px/500），下方 meta `15 questions · 60 min`（14 ink-60）与系列名 `Felix · Austria`（h5）。
- 网格 `repeat(auto-fill, minmax(260px, 1fr))`，gap 24px 16px。
- 筛选胶囊：44px 高；选中 = 黑底白字，未选 = `--mk-raised`。选项 All / Felix · Austria / Level P · Brazil / Grade 1–2 · Canada。筛选状态写进 URL `?series=felix`。

### 5.14 `PageState`（新建 `components/ui/PageState.tsx`）

统一替换各页面散落的 loading / empty / error 块：居中、`--mk-raised` 底（全页时无底）、28px 静态/旋转环 + 15px/500 ink-60 文案。

| 场景 | 标题 | 说明 | 操作 |
|---|---|---|---|
| 加载 | — | Loading papers… / Loading question bank… / Opening practice… | — |
| 无试卷 | No papers yet | They appear here once added. | Back to home（链接） |
| 加载考试失败 | Could not load this exam | Check the connection and try again. | Try again（primary，refetch）+ Back to home |
| 题号越界 | There is no question {n} | Practice has questions 1 to {total}. | Go to question 1 |

### 5.15 `HeroMarks`（首页背景，新建 `components/home/HeroMarks.tsx`）

- 约 20 个绝对定位的短算式（`60 − 52 = 8`、`3 + 5`、`△ □ ○`、`8 kg`…），系统等宽字体 16/22/28px，±4° 旋转；85% 为 `--mk-ink-12`，其余为三种 hue（opacity .85）。
- `aria-hidden="true"`、`pointer-events: none`，位置写死（不随机，SSR 一致）。
- **安全区**：顶部 72px（header）和中间 560px 宽的文字/按钮列内不放任何算式（原型里有几处与导航重叠，实施时必须修正）。手机端只保留 8 个，且都在两侧 15% 内。
- 可选动效：整体 2px 呼吸位移，6s 不等分关键帧；reduced-motion 关闭。

---

## 6. 页面布局与交互改动

截图对应 `docs/design/screenshots/openai-{n}-*.png`。

### 6.1 首页 `/`（`app/page.tsx`，改为 client component）

布局：透明 header（`Math Kangaroo` 左，`Exam` `Practice` 右，14/500）叠在 hero 上 → hero（居中：meta `Felix · Level P · Grade 1–2 · 2014–2025`，`display` 标题 “Get ready for Math Kangaroo”，`p1` 介绍，两个按钮）→ 两张卡片（最大宽 1120px，`auto-fit minmax(320px,1fr)`，gap 24px）。

交互改动：
- 主按钮根据练习进度变化：有 `lastVisitedQuestion` → `Continue practice at question {n}`（→ `/practice/q/{n}`）；没有 → `Start practice`（→ `/practice`）。次按钮 `Choose an exam paper` → `/exam`。
- 练习卡显示 `Practice · {答过的题数} of {total} done` 和 4px 进度条（`total` 来自 `/api/practice-bank`，加载中隐藏这一行）。
- 考试卡 meta 由 manifest 计算：`Exam · {exam 数} papers`；时长区间见 §7.3。

### 6.2 选卷页 `/exam`（`app/exam/page.tsx`）

布局：header → `title` “Choose a paper” + `p1` 说明 → 筛选胶囊 → `PaperCard` 网格（最大宽 1216px）。

交互改动：
- 用 **系列 + 年份** 取代 “2023‑1 / 2023‑2” 的标签（删除 `yearLabelByExamId`）。
- 新增筛选（§5.13）。排序保持：年份降序，同年按系列 Felix → Grade 1–2 → Level P（与现在的 `exam_id` 字典序一致即可）。

### 6.3 考试进行中 `/exam/[examId]`（`components/exam/ExamRun.tsx`）

布局：`AppHeader`（返回 = 离开考试；右侧 Timer + Submit exam）→ 左侧栏（Questions 标题行 + 题号 + 图例）| 主区（`QuestionCard`）→ footer（`Previous` secondary · `{i} of {n}` meta · `Next` primary）。

交互改动：
- **Submit 移到 header，Exit 改成 header 的返回按钮**；footer 只剩上一题/下一题，避免孩子误触。
- `window.confirm` → `ConfirmDialog`（交卷、离开两种）。交卷说明里带上已答数量。
- Timer 始终显示数字；剩余 < 5 分钟变警示色（§5.4）。
- 考试进行中**隐藏变式题**。
- 最后一题时 `Next` 变为 `Review & submit`（primary），点击打开交卷对话框。
- 侧栏右上显示已答数 `5 / 24`。

### 6.4 交卷后 / 结果（`ExamRun` 的 `submitted` 状态）

布局：`AppHeader`（结果版）→ 左侧栏（`ScoreCard` + 计数块 + 题号）| 主区（回看当前题：题干下方加结果胶囊 `You chose B—the right answer is C. −1 point`；选项按 §5.6 揭晓；之后显示变式题）→ footer（Previous · `Next mistake: question {k}` 链接 · Next）。

交互改动：
- 交卷后默认跳到**第 1 道错题**（没有错题则停在第 1 题）。
- `Next mistake` 跳到当前题之后的下一道错题，没有则隐藏。
- `Try this paper again` 重置答案与计时，留在本页；`Choose another paper` → `/exam`。
- header meta 显示用时（`durationSec − secondsLeft`，取整分钟）。
- 跳过的题胶囊文案：`You skipped this one—the right answer is C. 0 points`。

### 6.5 练习 `/practice/q/[n]`（`components/exam/PracticeBankLoader.tsx`）与 `/practice/[examId]`（`PracticeRun.tsx`）

两者统一为同一套布局（建议抽出 `components/exam/PracticeLayout.tsx`，两边只负责数据）：

`AppHeader`（返回 → `/`；meta 显示“答对数”；标题 `Question {i} of {total}`；右侧 `End practice`）→ 左侧栏（`Go to question` 输入框 + 题号滚动区 + 图例）| 主区（`QuestionCard` → `FeedbackPill` → `PracticeExplanationPanel` → 变式题）→ footer（Previous · `{i} of {total}` · Next question）。

交互改动：
- **Go to question**：`<label>` + 数字输入（44px 高、圆角 6px、占位 `1 to {total}`），回车跳转；越界时输入框下方显示 13px `--mk-wrong-fg` 提示 `Enter a number from 1 to {total}`，不跳转。
- “答对数”= 已答题中 `answer === correct_label` 的数量（练习答案每题只能选一次，即“第一次就答对”）。
- 反馈改为 `FeedbackPill`；讲解面板默认收起（保持现状）。
- 题号区高度：桌面 `calc(100dvh − 64px − 200px)` 可滚动，当前题保持在可视范围（现有逻辑）。
- `End practice` 打开结束练习对话框（§5.11）。
- `PracticeRun`（单卷练习）的 `Next` 仍需先作答（保留现有规则）；题库练习保持随时可前进。

### 6.6 变式题

见 §5.10。出现位置：练习页解释面板之后；考试结果回看时题目之后。考试进行中不出现。

### 6.7 手机（< 768px）

参见 `openai-7-mobile.png`：
- header 54px：返回图标 · 标题 `Question {i} of {total}`（16/500）· `End`（secondary 40px）。
- 侧栏变为横向题号条（40px 圆形，gap 8px，下边线），当前题自动滚入。
- 选项单列；题干 21px；插图全宽 116px 高。
- 底部固定栏：反馈胶囊 + `Previous`（1fr）/ `Next question`（2fr），留出安全区 `padding-bottom: max(20px, env(safe-area-inset-bottom))`；主区底部预留 150px。
- 考试页手机端：header 第二行放 Timer 与 Submit。

---

## 7. 数据与文案映射

### 7.1 不需要改后端的
所有页面数据都来自现有接口：`/api/exams`、`/api/exams/[id]`、`/api/practice-bank`、`/api/generated/...`、`/api/ai/*`。

### 7.2 系列名映射（新建 `apps/web/lib/series.ts`）

| `manifest.level` | 显示名 | 封面色 | 筛选 key |
|---|---|---|---|
| `felix` | Felix · Austria | `--mk-series-felix` | `felix` |
| `level-p` | Level P · Brazil | `--mk-series-level-p` | `level-p` |
| `grade-1-2` | Grade 1–2 · Canada | `--mk-series-grade-1-2` | `grade-1-2` |

未知 level 回退为 `family` 原文 + `--mk-raised` 封面。

### 7.3 时长
`ManifestExamEntry` 没有 `duration_minutes`，而选卷卡需要显示时长。二选一：
- **推荐**：在 `src/kangaroo_pdf/release_pipeline.py` 生成 manifest 时带上 `duration_minutes`，前端 `null` 时按 45 分钟显示（与 `ExamRun` 默认一致）。
- 过渡：卡片 meta 只显示题数，不显示时长。

### 7.4 文案原则
- 不用感叹号；CTA = 动词 + 宾语（“Choose an exam paper”，不写 “Learn more”）。
- 定义用破折号：`Not quite—the right answer is B`。
- 对孩子用 you，不用 “您/we”。保留“变式题”中文标签（与现状一致）。

---

## 8. 需要改动的文件

| 文件 | 改动 |
|---|---|
| `apps/web/app/layout.tsx` | Geist → `Inter`（`next/font/google`，weights 400/500，`variable: "--font-inter"`）；删除 Geist_Mono |
| `apps/web/app/globals.css` | 用 `docs/design/tokens/plan-c.tokens.css` 的 `:root` 替换现有变量；`body` 背景 `--mk-bg`、字体 `--mk-font-sans`；全局 `:focus-visible`；`prefers-reduced-motion`；`.tap-target` 保留但最小 44px |
| `apps/web/tailwind.config.ts` | `theme.extend`：`colors.mk.*` 映射到 CSS 变量；`fontFamily.sans`；`fontSize` 加入 §3.2 的成组字阶（`display`、`score`、`title`、`stem`、`h4`、`choice`、`h5`、`p1`、`explain`、`cta`、`meta`、`caption`，各带 lineHeight/letterSpacing/fontWeight）；`borderRadius`（`md`=6px、`card`=16px、`panel`=24px、`button`=2.5rem）；`boxShadow.popover` |
| `apps/web/app/page.tsx` | 首页重做（§6.1），改为 client component，使用 `usePracticeAnswersStore` 与 practice-bank 查询 |
| `apps/web/components/home/HeroMarks.tsx` | 新建（§5.15） |
| `apps/web/app/exam/page.tsx` | 选卷页重做（§6.2），删除 `yearLabelByExamId` |
| `apps/web/components/exam/PaperCard.tsx` | 新建（§5.13） |
| `apps/web/lib/series.ts` | 新建（§7.2） |
| `apps/web/app/practice/page.tsx` | 加载/空状态改用 `PageState` |
| `apps/web/components/exam/ExamRun.tsx` | 布局改为 AppHeader + 侧栏 + footer；交卷/离开对话框；结果态（ScoreCard、Next mistake、Try again、用时）；隐藏考试中变式题 |
| `apps/web/components/exam/Timer.tsx` | 新建（§5.4），从 ExamRun 抽出 |
| `apps/web/components/exam/ScoreCard.tsx` | 新建（§5.12） |
| `apps/web/lib/scoring.ts` | 新增 `computeTierBreakdown(exam, answers)` → `[{from, to, points, earned, max}]`；`computeExamScore` 不变 |
| `apps/web/components/exam/QuestionSidebar.tsx` | 题号样式与状态（§5.5），标题行计数，图例插槽 |
| `apps/web/components/exam/StatusLegend.tsx` | 新建 |
| `apps/web/components/exam/PracticeBankLoader.tsx` | 使用 `PracticeLayout`；Go to question；答对数；PageState |
| `apps/web/components/exam/PracticeRun.tsx` | 使用 `PracticeLayout` |
| `apps/web/components/exam/PracticeLayout.tsx` | 新建（§6.5，两种练习共用） |
| `apps/web/components/exam/FeedbackPill.tsx` | 新建（§5.8） |
| `apps/web/components/exam/PracticeExplanationPanel.tsx` | 重新设计各状态（§5.9），逻辑不变 |
| `apps/web/components/exam/PracticeExitDialog.tsx` | 改为基于 `ConfirmDialog`（§5.11） |
| `apps/web/components/exam/SessionLoader.tsx` | Loading / Fail 改用 `PageState`，Fail 增加 Try again |
| `apps/web/components/question/QuestionCard.tsx` | 题干区、插图框、选项 `<button>` 化与状态表（§5.6）、TTS 按钮状态（§5.7）；新增 `metaLabel` / `points` props |
| `apps/web/components/question/AssetFigure.tsx` | 加载前 `--mk-ink-4` 占位底；尺寸规则按 §5.6 |
| `apps/web/components/question/AssetGrid.tsx` | 间距 8/12px |
| `apps/web/components/question/GeneratedQuestionSection.tsx` | 面板样式与 Open/Close（§5.10）；新增 `hidden` 控制（考试中不渲染） |
| `apps/web/components/ui/Button.tsx`、`IconButton.tsx`、`AppHeader.tsx`、`ConfirmDialog.tsx`、`PageState.tsx` | 新建（§5.1–5.3、5.11、5.14） |
| `src/kangaroo_pdf/release_pipeline.py` + `release-data/manifest.json` | （可选，§7.3）manifest 加 `duration_minutes` |
| `README.md` / `docs/screenshots/*.png` | 实施完成后更新截图 |

不需要改：`app/api/**`、`lib/fastapi*.ts`、`lib/api-errors.ts`、`lib/practice-answers-store.ts`（只读使用）、`apps/api/**`。

---

## 9. 对设计系统的有意偏离

| 项目 | 设计系统 | 本方案 | 原因 |
|---|---|---|---|
| 按钮高度 | 40px（`button-height` 2.5rem） | 48px（sm 44px） | 6–7 岁孩子的触控目标 |
| 按钮字号 | 14px | 15px | 同上 |
| 题干 / 选项字号 | 无此角色 | 26px / 22px（500） | 题目是主角，需要大于 `text-h4` |
| 焦点环颜色 | 未指定 | `#1e60e4` | 与“当前题”黑色描边区分 |
| 首页 hero 安全区 | — | 顶部 72px + 中列 560px 不放算式 | 原型中算式与导航重叠 |

---

## 10. 验收标准

### 10.1 视觉一致性
- [ ] `apps/web` 中搜索 `font-black`、`font-bold`、`font-extrabold`、`font-weight: 700` 结果为 0。
- [ ] 不再引用 Geist；页面计算字体为 Inter。
- [ ] `box-shadow` / `shadow-*` 只出现在 `ConfirmDialog`。
- [ ] 不再出现 `hover:-translate-y`、`active:scale`、`transition-all`。
- [ ] 颜色只通过 `--mk-*` 变量或 Tailwind 映射使用，组件内没有裸十六进制色值（token 文件除外）。
- [ ] 1280×900 下，首页、选卷、考试、结果、练习、结束练习对话框与 `docs/design/screenshots/openai-{1..6}-*.png` 布局一致（间距、字号、颜色、圆角）；390×844 下练习页与 `openai-7-mobile.png` 一致。

### 10.2 可用性与无障碍
- [ ] 所有可点控件 ≥ 44×44px；主按钮 48px 高。
- [ ] 必须阅读的文字对比度 ≥ 4.5:1（axe 或 Lighthouse 无 color-contrast 报错）；`--mk-ink-44` 未用于正文。
- [ ] 选项是 `<button aria-pressed>`，Tab 可依次到达，Enter / Space 可选择；只读变式题选项不可聚焦。
- [ ] 键盘焦点环（蓝色 2px）在所有交互元素上可见，与“当前题”样式可区分。
- [ ] 三个对话框：焦点落在安全操作、Esc 取消、焦点锁定、关闭后焦点回到触发元素；不再调用 `window.confirm`。
- [ ] 计时器读屏不按秒播报。
- [ ] 对/错除颜色外都有文字或图标。
- [ ] `prefers-reduced-motion: reduce` 下没有位移和旋转动画。

### 10.3 行为
- [ ] 计分结果与改版前完全一致（`computeExamScore` 未改）。新增的 `computeTierBreakdown` 满足：题数 + 各段得分之和 − 答错数 = 截断前总分；最后总分仍按 `Math.max(0, …)` 截断。
- [ ] 考试中不显示变式题；交卷后与练习中显示且可展开/收起。
- [ ] 交卷后默认定位到第一道错题；`Next mistake` 正确跳转，无错题时隐藏。
- [ ] Timer 剩余 < 5 分钟变警示色；时间到自动交卷（现有行为）。
- [ ] Go to question：合法题号跳转并更新 `lastVisitedQuestion`；非法输入提示且不跳转。
- [ ] 首页主按钮在有/无练习进度时文案与链接正确。
- [ ] 选卷筛选可用，刷新后由 URL 恢复。
- [ ] TTS、解释、重新生成、缓存提示的现有逻辑全部保留。

### 10.4 响应式与工程
- [ ] 390 / 768 / 1280 / 1440 宽度下无横向滚动；< 768px 侧栏变横向题号条，底部操作栏固定。
- [ ] `cd apps/web && npm run lint`（`tsc --noEmit`）与 `npm run build` 通过。
- [ ] `python -m pytest` 通过（如改了 `release_pipeline.py`）。
- [ ] README 截图更新为新版界面。

---

## 实施记录

- §7.3 时长：采用“过渡”方案——选卷卡和首页考试卡只显示题数/试卷数，不显示时长；manifest 未改。
- §5.15 手机端 hero 算式：手机正文列占满屏宽，两侧 15% 仍会压到文字，因此改为只放在导航与 meta 之间、按钮与卡片之间两条空白带里。
- 结果页“答对”的题也显示结果胶囊：`You chose C—that’s right. +3 points`（规格只写了答错与跳过两种）。
- 解释失败面板除 `Try again` 外保留 `Hide`，方便收起。
- 新增共用组件 `components/exam/SessionLayout.tsx`（header + 侧栏 + 860px 主列 + 底栏），考试、结果、练习三种页面共用。

## 附：参考产物

- 原型源码：`docs/design/prototypes/openai/*.dc.html`（本地预览方法见 `docs/design/README.md`）
- 截图：`docs/design/screenshots/openai-1-home.png` … `openai-8-components.png`
- 组件与状态总表：`openai-8-components.png`
- 设计系统原始 token：`docs/design/tokens/openai-style.tokens.json`
