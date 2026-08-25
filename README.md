# 企业AI智能办公助手（E-AI Office Assistant）

> 架构师：梁政（定框架、定规则、定验收） ｜ 代码：AI按规则实现 ｜ 目标岗位：AI应用/数字化/大模型应用

一个可部署上线的企业级 AI 应用平台，三个模块：
- **模块A · 企业知识库问答（RAG）**：上传文档 → 提问 → 带引用来源的答案
- **模块B · 智能会议纪要**：粘贴文字稿 → 自动生成摘要/关键决定/待办
- **模块C · 客户数据智能管理**：导入Excel → AI提取/清洗 → 搜索 + 看板

## 开发原则（重要）

- **按模块开发，禁止一把梭**：每个模块有独立验收标准，验收通过才进下一步（见 `docs/01_开发计划.md`）
- **架构师定规则，AI执行**：AI必须遵守 `AGENTS.md` 与 `地基卡.md` 的约束
- **每个模块必须可运行、可演示、可部署**：不交付"半成品代码"

## 文档索引

| 文档 | 用途 |
|------|------|
| `地基卡.md` | 技术栈/目录/数据模型/API 锁定（AI不得擅改） |
| `AGENTS.md` | AI开发规则（每次开工必须读） |
| `docs/01_开发计划.md` | 模块化开发计划与验收清单 |
| `docs/02_技术架构.md` | 架构设计说明 |
| `docs/03_环境配置.md` | 前置环境安装与运行 |
| `docs/04_问题排查.md` | 常见问题与解决 |

## 快速启动（开发期）

```bash
# 后端（详见 docs/03）
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # 填入 DEEPSEEK_API_KEY
uvicorn app.main:app --reload --port 8000

# 前端（阶段0之后创建）
cd frontend
npm install
npm run dev
```

## 验收总纲

- [ ] 三个模块全部能在网页上操作
- [ ] 至少部署上线成可点开的网址（面试能演示）
- [ ] 1分钟演示录屏 + README + GitHub仓库
- [ ] 面试话术：架构师视角讲清"业务→架构→规则→验收"
