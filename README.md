# No End Story — AI 无限剧情流游戏

一款基于大语言模型的**无限剧情流文字冒险游戏**。AI 实时生成剧情、对话、选项和场景图像，每次游玩都是独一无二的故事。

## 核心特性

- 🎭 **动态剧情生成** — 大模型实时推进剧情，非脚本化
- 🎨 **AI 场景图像** — 自动生成场景图、角色立绘、合成画面
- 🗣️ **语音合成（TTS）** — 角色台词实时语音播报，支持情绪语调
- 🧠 **记忆系统** — 向量数据库 + RAG，AI 能回忆之前的对话
- 🔚 **多结局系统** — 好结局 / 坏结局 / 中立结局 / 开放结局
- 📖 **结局收藏册** — 浏览已达成的结局，可展开查看剧情详情
- 🚪 **游客免注册体验** — 无需登录即可试玩（每日限制 1 次结局）
- 🖥️ **桌面应用** — 支持 Electron 打包为 Windows 桌面端

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 + TypeScript + Ant Design 6 + Vite |
| 桌面端 | Electron |
| 后端 | Python 3.10+ + FastAPI + Uvicorn |
| 数据库 | PostgreSQL + SQLAlchemy ORM |
| 缓存 | Redis |
| 向量数据库 | ChromaDB |
| AI 模型 | 火山引擎（豆包）/ DashScope / OpenAI 兼容接口 |
| TTS | 火山引擎语音合成 / DashScope |
| 图片生成 | 火山引擎 SeedDream / VectorEngine |

## 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis

### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库、Redis、AI API Key 等配置

# 初始化数据库
python create_database.py

# 运行数据库迁移
python migrations/versions/008_guest_ending_log.py

# 启动
python run_api.py
```

后端默认运行在 `http://localhost:8000`，API 文档：`http://localhost:8000/docs`

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 构建
npm run build

# 桌面端开发
npm run electron:dev

# 打包桌面端
npm run electron:build
```

前端默认运行在 `http://localhost:5173`

## 项目结构

```
NoEndStory/
├── backend/
│   ├── api/
│   │   ├── routers/          # API 路由（game, auth, health, voice）
│   │   ├── services/         # 业务逻辑层（GameService, TTS, Image）
│   │   ├── middleware/       # 中间件（限流、CORS、审计日志）
│   │   ├── schemas/          # Pydantic 请求/响应模型
│   │   ├── utils/            # 工具函数（IP 获取等）
│   │   └── dependencies.py   # FastAPI 依赖注入
│   ├── game/
│   │   ├── script_engine_v2/ # 剧情引擎 V2（ScriptEngine + Orchestrator）
│   │   ├── agents/           # Agent 引擎（旧版）
│   │   └── story_engine.py   # 故事引擎（事件、对话、结局）
│   ├── models/               # SQLAlchemy 数据库模型
│   ├── migrations/           # 数据库迁移脚本
│   ├── database/             # 数据库管理器
│   ├── llm/                  # 大模型调用层（多厂商适配）
│   ├── audio/                # TTS 语音合成
│   ├── images/               # 图片资源（角色、场景、合成）
│   └── data/                 # 静态数据（角色、场景定义）
├── frontend/
│   ├── src/
│   │   ├── pages/            # 页面组件
│   │   │   ├── Home.tsx          # 首页（角色选择 + 侧边栏）
│   │   │   ├── FirstStep.tsx     # 角色设定（新/继续游戏决策）
│   │   │   ├── Game.tsx          # 游戏主界面
│   │   │   ├── EndingArchive.tsx # 结局收藏册
│   │   │   └── CharacterSetting.tsx
│   │   ├── hooks/            # 自定义 Hooks（WebSocket, GameInit, Audio）
│   │   ├── services/         # API 调用层
│   │   ├── store/            # 状态管理（GameContext）
│   │   ├── components/       # 通用组件
│   │   └── utils/            # 工具函数（gameStorage, API 客户端）
│   └── electron/             # Electron 桌面端入口
└── docs/                     # 设计文档
```

## API 概览

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/game/init` | POST | 初始化游戏会话 |
| `/api/v1/game/input` | POST | 处理玩家输入（文本/选项） |
| `/api/v1/game/check-ending/{thread_id}` | GET | 检查结局条件 |
| `/api/v1/game/trigger-ending` | POST | 触发结局 |
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/voice/characters/{id}/voices` | GET | 角色音色列表 |
| `/api/v1/voice/preview` | POST | 音色试听 |

## 游客结局限制

游客（无 Authorization header）每天限触发 **1 次结局**。以 IP 为粒度，次日自动重置。

- 触发结局后再次开新局 → 返回 `403 GUEST_ENDING_LIMIT`
- 前端识别此错误码后弹窗提示注册
- 可通过 `GUEST_ENDING_IP_WHITELIST` 环境变量配置 IP 白名单（默认放行 `127.0.0.1, ::1`）

```bash
# .env
GUEST_ENDING_IP_WHITELIST=127.0.0.1,::1
```

## 环境变量

关键配置项（详见 `backend/.env.example`）：

```bash
# 数据库
DB_HOST=localhost
DB_PORT=5432
DB_NAME=noendstory

# Redis
REDIS_HOST=localhost
REDIS_PORT=6380

# AI 模型
VOLCENGINE_ARK_API_KEY=         # 火山引擎 API Key
LLM_TEXT_MODEL=deepseek-v4-pro-260425

# TTS
TTS_PROVIDER=volcengine          # volcengine / dashscope / edge-tts

# 图片生成
VECTORENGINE_API_KEY=            # VectorEngine API Key（可选）

# 游客限制
GUEST_ENDING_IP_WHITELIST=127.0.0.1,::1
```

## 许可证

[MIT License](LICENSE)
