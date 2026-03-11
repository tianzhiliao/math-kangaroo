# Tasks

- [ ] Task 1: 实现下半区题型识别与布局决策引擎
  - [ ] SubTask 1.1: 在 `QuestionCard` 中识别题干图形数量（0/1/多）
  - [ ] SubTask 1.2: 识别答案图形类型（纯图5项/长条图5项/其他）
  - [ ] SubTask 1.3: 按识别结果动态挂载布局 class（左图右选项/全宽方卡/长条优先）

- [ ] Task 2: 固化左侧图片区域固定窗口规则
  - [ ] SubTask 2.1: 禁止左侧图形区域滚动并固定窗口尺寸
  - [ ] SubTask 2.2: 单图场景实现约60%占比 + 15-20px留白
  - [ ] SubTask 2.3: 多图场景实现10px间距 + 总占用约80%

- [ ] Task 3: 实现右侧答案区题型化排版
  - [ ] SubTask 3.1: 5个纯图答案实现 2×3/1×5 弹性网格
  - [ ] SubTask 3.2: 保证纯图项最小尺寸 `80×80px`，比例 `1:1/4:3`
  - [ ] SubTask 3.3: 无左图 + 5图答案切换方形卡片布局（18%-20%宽度、圆角8px、1dp阴影）
  - [ ] SubTask 3.4: 5个长条图场景压缩左侧至40%，右侧条目高度≥60px

- [ ] Task 4: 通用约束与容错态完善
  - [ ] SubTask 4.1: 统一卡片高度边界（min 320px / max 70vh）
  - [ ] SubTask 4.2: 统一图片 `object-fit: contain` 并禁形变
  - [ ] SubTask 4.3: 增加骨架屏加载态
  - [ ] SubTask 4.4: 增加加载失败占位图与重试按钮

- [ ] Task 5: 响应式与兼容性验证
  - [ ] SubTask 5.1: `<=768px` 切换上下堆叠并确保无横向滚动
  - [ ] SubTask 5.2: 验证图形题、纯文字题、长内容题组合场景
  - [ ] SubTask 5.3: 执行 `npm run build` 验证
  - [ ] SubTask 5.4: 记录 Chrome/Safari/Edge/微信浏览器的兼容性检查结果

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 1 and Task 2
- Task 4 depends on Task 1 and Task 3
- Task 5 depends on all previous tasks
