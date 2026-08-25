# 企业 AI 智能办公助手（E-AI Office Assistant）

> 把传统企业散落的制度文档、会议记录、客户数据，变成「可检索、可提取、可问答」的 AI 知识资产。

一个可部署、可演示的企业级 AI 应用平台，内置三大模块：

| 模块 | 一句话能力 | 核心价值 |
|------|-----------|---------|
| **A · 企业知识库问答（RAG）** | 上传文档 → 提问 → 带引用来源的答案 | 制度/流程"秒答"，答不出的确定性拒答，不编造 |
| **B · 会议信息智能提取** | 会议纪要/音频 → 提取客户·项目·公司实体卡片 → 人工确认入库 | 从"小时级人肉整理"到"分钟级 AI + 人确认"的自生长闭环 |
| **C · 客户数据智能管理** | 实体库 + 跟进/静默告警/看板/项目时间轴 + **实体问答** | "张三什么情况？" → AI 一句话汇总公司/项目/进度/需求 |

> 架构师：梁政（定框架、定规则、定验收）｜ 代码：AI 按规则实现、人工校验 ｜ 定位：AI 应用 / 数字化 / 大模型应用方向

---

## 演示截图

<!-- 在这里放演示截图：把图片放到 docs/screenshots/ 下并替换下面的路径 -->

| 知识库问答 | 信息提取 | 客户数据 |
|-----------|---------|---------|
| `docs/screenshots/kb.png` | `docs/screenshots/extract.png` | `docs/screenshots/customer.png` |

> ⚠️ 截图待补充：运行项目后自行截图放入 `docs/screenshots/`，替换上表路径即可显示。

---

## 技术栈

| 层 | 选型 | 说明 |
|----|------|------|
| 前端 | React 18 + Vite + Ant Design 5 + Axios | macOS 玻璃拟态三栏界面，零额外 UI 库 |
| 后端 | Python 3.11 + FastAPI + Uvicorn | 类型友好、自带 OpenAPI 文档 |
| ORM / 数据库 | SQLAlchemy 2 + SQLite | 零运维；接口抽象，可切 MySQL |
| 向量检索 | numpy 余弦 + SQLite BLOB（自实现） | chromadb 在 Windows 跨进程索引崩溃的踩坑替代，毫秒级、可迁 Milvus |
| 向量模型 | sentence-transformers `bge-small-zh-v1.5` | 中文效果好、本地推理免费 |
| 大模型 | DeepSeek API（deepseek-chat） | OpenAI 兼容接口，统一走 AI 适配层，可无缝切换 |
| 文档解析 | pypdf / python-docx / openpyxl | 知识库与 Excel 导入 |
| ASR（预留） | MiMo ASR | 音频转写（代码就绪，key 待配置） |

## 功能亮点

1. **可信 RAG**：检索相似度 < 0.45 确定性拒答（不靠 LLM 自觉）+ 回答带可点击来源 + 金标评估集自动回归（命中率 90%）
2. **AI 提取人工确认闭环**（AI 提取、人决策）：清洗 → 三路提取实体卡片 → 人工可编辑确认 → 入库，增量不覆盖、来源可追溯
3. **实体问答**：客户/项目/公司卡片向量化 + 关联展开，一句话问出客户全貌
4. **资料库隔离**：文件夹式按库检索，多业务线互不污染
5. **AI 适配层**：`app/ai/llm.py` 统一封装（超时/重试/温度），换模型只改一处；提示词集中管理
6. **会话续聊**：最近 6 条历史拼入提示词，上下文连贯

## 快速启动（本地开发）

> 前置：Windows + Python 3.11 + Node.js 18+；准备一个 DeepSeek API Key（[platform.deepseek.com](https://platform.deepseek.com)）

```bash
# 1. 后端
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # 填入 DEEPSEEK_API_KEY
python scripts/seed_demo_data.py   # 可选：一键初始化纯虚构演示知识库（10 篇文档）
uvicorn app.main:app --reload --port 8000

# 2. 前端（另开一个终端）
cd frontend
npm install
npm run dev
```

启动后浏览器打开 **http://127.0.0.1:5173**：

- **知识库**：直接提问"财务报销需要什么材料？"，可先上传 `backend/sample_data/*.md` 里的制度文档
- **信息提取**：上传 `backend/sample_data/演示素材/演示会议_XX科技项目排期讨论.md` → AI 提取实体 → 人工确认入库
- **客户数据**：导入 `backend/sample_data/演示素材/演示客户数据.xlsx`，然后问"张三什么情况？"

> 演示数据全部为**纯虚构**（"XX 科技有限公司"），不含任何真实企业/人名/项目信息，可安全用于公网演示。

## 目录结构

```
EAI-Office-Assistant/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口
│   │   ├── ai/                # 大模型适配层（llm/prompts/asr/cards）
│   │   ├── rag/               # 切片/向量化/检索
│   │   └── routers/           # kb / chat / meeting / customer
│   ├── scripts/               # seed_demo_data / eval_kb / scan_sensitive / smoke_test
│   ├── sample_data/           # 纯虚构演示数据（10 篇制度文档 + 演示素材）
│   └── tests/
├── frontend/                  # React + Vite + AntD
├── docs/                      # 开发计划/技术架构/面试问答等 19 篇文档
└── 地基卡.md / AGENTS.md       # 技术栈与开发规则锁定
```

## 文档索引

| 文档 | 用途 |
|------|------|
| `地基卡.md` | 技术栈 / 目录 / 数据模型 / API 锁定 |
| `AGENTS.md` | AI 开发规则（模块化、测试三遍、安全红线） |
| `docs/01_开发计划.md` | 模块化开发计划与验收清单 |
| `docs/02_技术架构.md` | 架构设计说明（面试必答） |
| `docs/03_环境配置.md` | 前置环境安装与运行 |
| `docs/04_问题排查.md` | 常见问题与解决 |
| `docs/15_项目技术框架设计解说.md` | 项目完整技术讲解 |
| `docs/16_项目面试问答表.md` | 面试高频问答背诵版 |
| `docs/18_部署方案与行动手册.md` | 部署（Docker + 云服务器）与数据安全手册 |

## 安全红线

- `.env`、`*.db`、`uploads/`、`sample_data_company/`、`sample_data_demo/` 均被 `.gitignore` 锁定，禁止入库
- 推送 / 部署前请运行 `python backend/scripts/scan_sensitive.py` 扫描敏感词，命中数必须为 0
- 公网部署前执行 `python backend/scripts/seed_demo_data.py` 重置为纯虚构演示数据

## License

MIT（代码仅供学习与演示，请勿用于商业用途）。
