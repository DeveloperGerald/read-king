# ReadKing 页面设计（Desktop-first）

## 全局样式（Global Styles）
- 设计目标：内容优先、状态清晰、操作可预期（上传/索引/生成皆可追踪）。
- 栅格与间距：12 列网格；内容最大宽度 1200px；区块间距 24px；卡片内边距 16px。
- 颜色 Token（示例）：
  - --bg: #0B1220（深色背景）
  - --surface: #111A2E（卡片底）
  - --text: #E6EAF2（主文字）
  - --muted: #9AA4B2（次级文字）
  - --primary: #5B8CFF（主按钮）
  - --danger: #FF5B5B（错误）
  - --success: #3DDC97（成功）
- 字体：标题 20/24/28；正文 14/16；等宽用于日志与代码块。
- 交互：按钮 hover 提升亮度 6%；禁用态降低不透明度并禁止点击；全局 toast 用于成功/失败提示。

---

## 1) 工作台（首页）
### Layout
- 顶部导航 + 主内容双列：左侧“书籍列表”，右侧“报告列表”；上方固定“上传卡片”。
- CSS：主区使用 CSS Grid（2 列，gap 24）；≤1024px 变为单列堆叠。

### Meta Information
- Title: ReadKing 工作台
- Description: 上传书籍、查看索引与报告状态
- OG: og:title=ReadKing，og:type=website

### Page Structure
1. 顶部导航（Navbar）
2. 生成需求卡（Requirement Card）
3. 上传区（Upload Card，仅在需求填写后解锁）
3. 书籍列表（Books Panel）
4. 报告列表（Reports Panel）

### Sections & Components
- Navbar：左侧产品名；右侧“刷新状态”按钮。
- Requirement Card：
  - 两个输入：生成需求（可选）、读后感（可选）。
  - 主按钮“进入上传”，点击后解锁上传区并将需求缓存（localStorage）。
- Upload Card：
  - 文件选择（支持拖拽）；显示文件名/大小；上传进度条。
  - 完成后在 toast 提示，并自动在“书籍列表”出现。
- Books Panel（表格或卡片列表）：列包含标题、上传时间、索引状态（badge）。点击进入 `/books/:bookId`。
- Reports Panel：列包含关联书籍、状态（badge）、更新时间。点击进入 `/reports/:reportId`。

---

## 2) 书籍处理页（/books/:bookId）
### Layout
- 三段纵向结构：书籍概览 → 索引构建 → 预览与生成。
- 预览区使用 Tabs：Context / Prompt / Outline。

### Meta Information
- Title: 书籍处理 - {bookTitle}
- Description: 构建索引并预览生成输入

### Page Structure
1. 面包屑（工作台 / 书籍）
2. 书籍概览卡
3. 索引构建卡
4. 预览与生成区（Tabs + 主按钮）

### Sections & Components
- 书籍概览卡：文件名、MIME、大小、索引状态、最近更新时间。
- 索引构建卡：
  - 主按钮“构建索引”；显示步骤条：解析→切分→向量化→入库。
  - 失败时展示错误摘要与“重试”按钮。
- 预览 Tabs（只读）：
  - Context：展示将用于检索增强的片段（可折叠、带来源 chunk index）。
  - Prompt：展示最终 prompt 文本（等宽、可复制）。
  - Outline：展示大纲（层级列表）。
- 生成按钮：
  - “生成报告”置于预览区右上；点击后创建 report 并跳转报告页。

---

## 3) 报告页（/reports/:reportId）
### Layout
- 左右分栏：左侧大纲（可滚动固定），右侧 Markdown 渲染内容。
- CSS：Grid 280px + 1fr；≤1024px 改为上下堆叠。

### Meta Information
- Title: 报告 - {reportId}
- Description: 查看生成状态与 Markdown 正文

### Page Structure
1. 顶部栏（返回 + 状态）
2. 左侧 Outline Panel
3. 右侧 Markdown Panel
4. 工具栏（复制/下载）

### Sections & Components
- 顶部栏：返回工作台；状态 badge；processing 时显示细进度（如“写作中…”）。
- Outline Panel：从 outline_md 解析为树；点击节点滚动定位右侧对应标题。
- Markdown Panel：
  - 渲染 report_md；支持代码块样式与标题锚点。
  - 空态：未完成时展示 skeleton；失败时显示 error_message。
- 工具栏：
  - “复制 Markdown”“下载 .md”两个动作；下载文件名建议为 `{bookTitle}-report.md`。
