# 题目卡片内部布局重设计实施方案

## 1. 目标与约束
- 目标：在不改变题目卡片整体尺寸的前提下，重构内部布局为「上文下图右选项」结构，提升阅读效率与点击体验。
- 约束：
  - 卡片外层宽高策略保持不变（沿用现有页面/容器尺寸约束）。
  - 题干文字固定在上部，避免遮挡图形与选项。
  - 下部左侧图形区面积最大化。
  - 下部右侧选项区保持整齐、可点击、可读。
  - 保持现有数据结构（`stem_text` / `stem_graphics` / `options`）与交互逻辑（选中态）不变。

## 2. 现状问题简析（基于当前 `QuestionCard.tsx`）
- 当前题干与题干图形处于同一纵向区域，图形区可用高度受文本和 margin 影响较大。
- 选项位于图形区下方，整体形成「题干+图形+选项」的纵向堆叠，导致图形难以放大。
- 对于图形题，用户视线往返距离较长（图形在上，选项在下），交互效率一般。

## 3. 新布局结构（保持卡片总尺寸不变）

### 3.1 结构分区
- **上部（固定文字区）**：仅放题干文字。
- **下部（双栏工作区）**：
  - 左栏：题干图形区（优先最大化面积）。
  - 右栏：答案选项区（规则网格或垂直列表）。

### 3.2 空间分配比例（桌面优先）
- 卡片内部高度按 100% 处理（不改外层尺寸）。
- 上部题干区：建议占内部高度 `24%~30%`（默认 `28%`）。
- 下部工作区：占 `70%~76%`（默认 `72%`）。
- 下部横向比例：
  - 图形区：`62%~68%`（默认 `64%`）。
  - 选项区：`32%~38%`（默认 `36%`）。

> 该分配将图形区提升为视觉中心，同时保证选项区点击热区与文案可读性。

## 4. 实施步骤（代码改造步骤）

### 步骤 1：重构 `QuestionCard` DOM 层次
- 文件：`src/components/exam/QuestionCard.tsx`
- 将现有结构拆分为：
  1. `question-card__header`（题干文字）
  2. `question-card__body`
     - `question-card__figure`（题干图形）
     - `question-card__options`（选项列表）

### 步骤 2：设置卡片内部网格与高度约束
- 顶层卡片保持原外观（圆角、阴影、边框）不变。
- 内层改为两行网格（header + body）并使用百分比/`minmax` 控制。
- 防止内容撑破卡片：关键容器增加 `min-h-0`、`overflow-hidden/auto`。

### 步骤 3：放大图形区渲染能力
- 图形容器设置居中 + 自动滚动（当图过大时不压缩选项区可点击性）。
- 注入 SVG 外层包裹统一约束：
  - `max-width: 100%`
  - `max-height` 按区域高度限制
  - `object-fit: contain` 的等价效果（对 SVG 使用 `width/height` 约束）

### 步骤 4：选项区布局优化
- 桌面：优先单列大按钮（保证点击面积），必要时可双列（短选项场景）。
- 选项按钮高度下限：`>= 56px`，保持触达友好。
- 选项间距：`12~16px`，保持视觉节奏。
- 保留当前选中态、hover、active 动效。

### 步骤 5：响应式规则落地
- 大屏（>=1280）：按 64/36 双栏，图形优先最大化。
- 中屏（768~1279）：按 58/42 双栏，避免选项拥挤。
- 小屏（<768）：改为上下结构（文字 -> 图形 -> 选项），但下部中图形仍优先高度分配。

### 步骤 6：验证与回归
- 验证点：
  - 题干长文本不遮挡图形/选项。
  - 图形题显示面积显著增大。
  - 选项可点击区域、间距、对齐稳定。
  - 不同题型（纯文字、纯图、图文混合）显示正常。
  - 移动端无横向溢出。

## 5. CSS 样式方案（可直接落地）

> 说明：以下为可直接放入组件样式层（Tailwind 类 + 补充 CSS）的实现草案。  
> 若项目坚持纯 Tailwind，可将选择器样式转为 `@layer components`。

```css
/* QuestionCard 内部布局核心 */
.question-card {
  height: 100%;
  display: grid;
  grid-template-rows: minmax(88px, 28%) minmax(0, 72%);
  gap: 12px;
}

.question-card__header {
  overflow: auto;
  padding-right: 4px;
}

.question-card__stem {
  font-size: clamp(18px, 1.25vw, 24px);
  line-height: 1.45;
  font-weight: 700;
  color: #1e293b;
  white-space: pre-wrap;
  word-break: break-word;
}

.question-card__body {
  min-height: 0;
  display: grid;
  grid-template-columns: 64% 36%;
  gap: 14px;
}

.question-card__figure {
  min-width: 0;
  min-height: 0;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px;
  overflow: auto;
}

.question-card__figure-inner {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
}

.question-card__figure-inner > * {
  max-width: 100%;
  max-height: 100%;
}

.question-card__options {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-auto-rows: minmax(56px, auto);
  gap: 12px;
  overflow: auto;
  padding-right: 2px;
}

.question-option {
  min-height: 56px;
}
```

## 6. Tailwind 结构建议（组件内类名映射）

```tsx
<div className="question-card">
  <section className="question-card__header">
    <h2 className="question-card__stem">{question.stem_text}</h2>
  </section>

  <section className="question-card__body">
    <div className="question-card__figure">
      <div className="question-card__figure-inner">{/* stem_graphics */}</div>
    </div>

    <div className="question-card__options">
      {/* option buttons */}
    </div>
  </section>
</div>
```

## 7. 响应式适配规则

### 7.1 Desktop（>=1280px）
- `grid-template-columns: 64% 36%`
- 图形区优先显示完整图，选项区单列大按钮。

### 7.2 Tablet（768px~1279px）
- `grid-template-columns: 58% 42%`
- 顶部文字区最大高度建议不超过 34%，防止压缩图形区。
- 选项字号可降至 `16~18px`。

### 7.3 Mobile（<768px）
- 改为纵向三段：
  - 题干（约 22%）
  - 图形（约 43%）
  - 选项（约 35%）
- 图形区保持优先高度；选项按钮高度不低于 `52px`。
- 防止过长文本挤压：题干区启用纵向滚动。

可用媒体查询示例：

```css
@media (max-width: 1279px) {
  .question-card__body {
    grid-template-columns: 58% 42%;
  }
}

@media (max-width: 767px) {
  .question-card {
    grid-template-rows: minmax(72px, 22%) minmax(0, 78%);
  }

  .question-card__body {
    grid-template-columns: 1fr;
    grid-template-rows: 43% 57%;
  }
}
```

## 8. 验收标准（本次改造完成判定）
- 卡片外层尺寸策略保持不变（无整体尺寸放大/缩小）。
- 题干固定上部，内容可读且不遮挡图形、选项。
- 图形区在桌面端视觉面积显著大于改造前。
- 选项区排列整齐、点击区域达标（>=52~56px）。
- 断点切换（桌面/平板/手机）布局稳定，无重叠、溢出、遮挡。
