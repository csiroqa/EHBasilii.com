# EHBasilii Orchestration

个人博客，基于 [Hugo](https://gohugo.io/) 静态站点生成器与 [FixIt](https://github.com/hugo-fixit/FixIt) 主题构建。

## 技术栈

| 层级 | 技术 |
|---|---|
| 站点引擎 | Hugo (Go templates, SCSS pipeline) |
| 主题 | FixIt（深度定制） |
| 字体 | 全栈自托管 WOFF2，含 Gentium Book Plus（正文）、Iosevka Fixed Slab（等宽）、Source Serif 4（CJK 降级）、Source Han Serif/Sans SC（CJK 正文与标题）|
| 字型优化 | Python 字体子集工具（[subsets.py](scripts/subsets.py)）：逐页 CJK 字符提取 → MD5 哈希去重 → fontTools 子集化，每页仅加载页面独有的字形 |
| 样式 | SCSS 覆写主题默认变量，CSS `light-dark()` 实现双色板 |
| 图表 | Mermaid (ESM, CDN 加载)，`look: handDrawn` 手绘风格，多层 SVG（亮色/暗色/中性）+ Panzoom 缩放平移 + 主题切换同步 |
| 连字 | Hyphenopoly.js，对英文、法文、拉丁文、古希腊文启用 |
| 排版 | 旧风格数字 (`oldstyle-nums`)、常见连字 (`common-ligatures`)、悬挂标点（CJK）、`text-wrap: pretty`、`widows/orphans` 控制 |
| 语法高亮 | 自定义书卷调色板（赭石关键字、竹青字符串、霁蓝数字、花青标识符、藤黄类型） |
| 国际化 | 6 种语言：中文、English、français、Latīnum、Ἑλλάς、日本語 |
| 部署 | GitHub → Cloudflare Pages（Rocket Loader 注入，生产环境自动压缩）|
| 构建 | `public/` 和 `resources/` 由 `.gitignore` 忽略，托管端构建 |

## 设计理念：书香（Bookish）

本站的视觉设计根植于**中国传统书卷美学**与**西方经典版面设计**，不依附主流设计系统（Material、Bootstrap 等），目标是模拟在纸上阅读的体验。

### 色彩 — 四时之色

- **明色幅**：以宣纸（`#faf7f0`）为底、松烟墨（`#2d2822`）为字、花青靛蓝（`#4f6782`）为链接点缀。铜绿、竹青、霁蓝、藤黄、朱砂构成语义色板。
- **暗色幅**：以砚石（`#1e1d1a`）为底、烛纸暖黄（`#e3ddd3`）为字、泥金（`#c4ae80`）为链接。整个色板在暗色下整体向暖色偏移，模仿烛光下阅读的质感。

### 字体系统

正文使用 Gentium Book Plus，一款专为长篇阅读设计的文艺复兴风格衬线字体。代码使用 Iosevka Fixed Slab，窄体等宽且带有 slab serif。CJK 内容回退至 Source Han Serif/Sans。英文与 CJK 正文基线与灰度经过反复调试以取得视觉协调。

### 朱丝栏（代码块）

代码块左侧有一条 **3px 竖线**（朱丝栏的现代演绎），源于中国传统手抄本的栏线装饰。语法高亮色板也取自国画颜料命名。

### 表格 — 学术风格

表头底部以主题色画线，斑马纹极淡（仅 1.6%–2.5% 透明度），表身 `::first-child` 使用次级文字色，减少阅读干扰。

### Mermaid — 褪去科技感

Mermaid 图表使用 `handDrawn`（roughjs）渲染引擎，配色与全站一致：节点为纸色底、主色描边；边标签使用斜体和书眉风格字号；连线和箭头使用瓦灰色，不抢视线。

### 排版细节

- 正文 `20px`，CJK 略缩至 `18.7px`（基于中宫密度校准）
- 行高固定 `1.8`，字间距 `0.03em`
- 自动断词（hyphenation）仅对非 CJK 语言启用
- `publisher` / `author` 端的 Schema.org 结构化数据
