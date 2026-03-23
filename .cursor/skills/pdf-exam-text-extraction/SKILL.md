---
name: pdf-exam-text-extraction
description: 用于考试 PDF 题干/选项纯文本提取。适用于需要排除图形内文字、进行多轮迭代修正并输出可人工审核 JSON/HTML 的场景。
---

# PDF 纯文字提取（考试卷）

## 适用场景

- 需要从考试 PDF 中提取每题题干与 A-E 选项文本。
- 要求严格排除图形中的数字/字母/符号。
- 需要“提取 -> 质检 -> 人审 -> 迭代”闭环，而不是一次性脚本跑完。
- 目标产物包含：
  - 可并入业务数据的 JSON 文本字段。
  - 便于人工核对的静态 HTML 审核页。

## 不可违反的红线

1. 只保留 `stem_text` 与 `choices[].text` 的纯文本信息。
2. 图形/图片内任何字符都不提取（即便图中有字母数字也不纳入文本）。
3. 页眉页脚和版权噪声不得混入题干或选项。
4. 选项标签必须保持 A-E 对齐，不能错位或串位。
5. 未通过质量闸门前，不写入业务主数据。

## 关键入口（本仓库）

- 提取脚本：`scripts/extract_text_only_exam.py`
- 抽取核心：`src/kangaroo_pdf/text_only.py`
- 审核页渲染：`scripts/render_text_only_review.py`
- 前端业务数据样式参考：`release-data/exams/*/exam.json`

## 标准执行流程（6 阶段）

### 1) 预检

- 明确输入 PDF 路径。
- 明确输出路径：
  - `.generated/text-only/<exam-id>.text-only.json`
  - `.generated/text-only/<exam-id>.review.html`
- 确认目标结构为 `questions[].id/number/stem_text/choices[label,text]`。

### 2) 提取

- 先跑主提取，得到文本 JSON：

```bash
python scripts/extract_text_only_exam.py \
  --pdf original_pdf_data/<input>.pdf \
  --output-json .generated/text-only/<exam-id>.text-only.json
```

- 如果流程要求硬闸门，启用 QA gate：

```bash
python scripts/extract_text_only_exam.py \
  --pdf original_pdf_data/<input>.pdf \
  --output-json .generated/text-only/<exam-id>.text-only.json \
  --qa-gate \
  --max-high-risk 0 \
  --max-option-alignment-conflict 0 \
  --max-illegal-char-ratio 0.0
```

### 3) 清洗与结构对齐检查

- 关注 `quality_summary` 与每题 `quality`：
  - `image_text_leak_suspected`
  - `footer_noise_detected`
  - `option_alignment_conflict`
  - `illegal_char_count`
  - `risk_flags`
- 检查选项是否 A-E 完整且语义不乱序。
- 检查图形题的选项是否正确留空（而不是混入噪声字符）。

### 4) 生成审核页并人工核对

```bash
python scripts/render_text_only_review.py \
  --json .generated/text-only/<exam-id>.text-only.json \
  --output-html .generated/text-only/<exam-id>.review.html
```

- 人审重点：
  - 图形题是否没有图内字符泄漏。
  - 页脚版权语是否完全消失。
  - 题干语义是否通顺，选项是否完整准确。

### 5) 失败分流（按问题类型修复）

- **图形文字泄漏**：优先检查视觉遮罩与贴边 token 过滤（word 级过滤 + 回退路径一致性）。
- **页眉页脚污染**：加强 header/footer band + 噪声关键词 + 尾部截断。
- **选项错位**：加强多通道对账（几何分段 vs 文本分段），冲突打标后回退。
- **异常字符**：做字符规范化（NFKC、控制字符剔除、OCR 混淆修复）并可追踪 edits。

### 6) 迭代闭环与通过标准

- 采用轮次化迭代：每轮必须“重跑提取 + 重做审核页 + 复核质量指标”。
- 通过条件（建议）：
  - `blocking_errors == []`
  - `high_risk_question_count == 0`
  - `image_text_leak_suspected_count == 0`
  - `footer_noise_detected_count == 0`
  - `option_alignment_conflict_count == 0`

## 可复用性结论

结论：**该经验可以复用**，但分成两层：

- 可直接复用：
  - 迭代闭环方法（提取/QA/人审/回写规则）
  - 质量闸门思想（blocking + risk flags）
  - 审核页驱动问题定位方式
- 需要按试卷适配：
  - 文件命名与分类规则
  - 题目总数与分页窗口规则
  - 选项标签格式（是否固定 A-E）
  - 页眉页脚噪声模式（不同主办方版权文本）
  - 答案表版式（若要同步做 answer 提取）

## 新试卷复用检查清单

1. 小样本先跑 1 套，再扩展全量，不要直接全量改数据。
2. 人审至少覆盖：
   - 所有高风险题
   - 所有图形题
   - 随机抽样非风险题
3. 未通过前，只在 `.generated` 产物迭代，不覆盖业务 JSON。
4. 通过后再把 `stem_text`/`choices[].text` 合并进 `release-data/exams/<exam-id>/exam.json`。

## 交付建议

- 每轮保留质量摘要：高风险题数、冲突题数、非法字符率、人工复核结论。
- 在 PR 或变更说明中显式记录“本轮修了什么、剩余风险是什么”。
