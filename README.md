# 未完待续 No End Story

**未完待续**是一款 AI 恋爱互动叙事游戏。玩家从角色设定、音色选择、初遇场景开始，进入由大语言模型实时生成的剧情流程；系统会根据玩家选择持续生成对白、选项、角色状态变化、场景画面、语音播报与最终结局。

当前 Web 版本支持子路径部署，线上入口规划为：

[http://hyjkblj.online/galgame/](http://hyjkblj.online/galgame/)

## 项目亮点

- **AI 无限剧情流**：剧情、对白、选项和结局由 LLM 动态生成，不依赖固定脚本路线。
- **恋爱游戏完整链路**：覆盖首页、角色设定、音色选择、初遇场景、主游戏、结局展示与结局收藏册。
- **分层画面渲染**：游戏主界面使用“场景图层 + 角色图层 + 对话 UI”的组合渲染方式，降低完整复合图反复生成的成本。
- **角色生成与抠图**：支持根据玩家设定生成角色立绘，并完成背景移除，用于后续分层渲染。
- **多情感语音体验**：角色可选择多情感男声 / 女声，剧情对白可生成 TTS 音频。
- **沉浸式过场动画**：角色生图等待、页面过渡和游戏加载都配有独立动画，减少玩家等待感。
- **游客体验与成本控制**：游客可直接游玩；完成一次完整结局后，通过 IP 做 24 小时额度限制，避免重复生成造成成本浪费。
- **Docker 生产部署**：支持前端 Nginx、后端 FastAPI、PostgreSQL、Redis 一体化部署，图片和音频产物保存在运行时 volume 中。
- **域名子路径适配**：前端路由、静态资源、API 请求均支持 `/galgame` 前缀，便于多个项目共用同一域名。

## 架构设计

```text
玩家浏览器 / Electron
        │
        ▼
React 前端应用
        │
        ├── 页面流程：Home / FirstStep / CharacterSetting / CharacterSelection / FirstMeeting / Game / EndingArchive
        ├── 游戏表现：分层画面、对白框、选项、音量设置、背景音乐、加载动画
        └── API Client：统一处理 /api、/static、游客额度错误和子路径前缀
        │
        ▼
Nginx 入口层
        │
        ├── 托管前端静态资源
        ├── 转发 /galgame/api 到后端
        └── 转发 /galgame/static 到后端静态资源服务
        │
        ▼
FastAPI 后端服务
        │
        ├── GameService：游戏初始化、玩家输入、事件推进、结局判断
        ├── ScriptEngine V2：剧情编排、场景流转、状态变化
        ├── CharacterService：角色创建、角色数据、角色图片生成
        ├── ImageService：场景图、角色图、抠图、复合资源管理
        ├── TTSService：音色配置、试听、对白语音合成
        └── Middleware：限流、成本保护、游客额度、请求日志
        │
        ├──────────────┬──────────────┬──────────────┐
        ▼              ▼              ▼              ▼
   PostgreSQL        Redis        Vector DB      AI Providers
  角色/会话/结局   缓存/短期状态   长期记忆检索   LLM / TTS / 图片生成
```

## 前端技术栈

| 能力 | 技术 |
| --- | --- |
| UI 框架 | React 19 + TypeScript |
| 构建工具 | Vite |
| 路由 | React Router |
| 组件库 | Ant Design |
| 桌面端 | Electron + electron-builder |
| 请求层 | Axios |
| 资源路径 | `VITE_APP_BASE_PATH` 支持 `/galgame` 子路径 |
| 体验能力 | 背景音乐、按钮音效、TTS 播放、路由过场、角色生图等待动画 |

## 后端技术栈

| 能力 | 技术 |
| --- | --- |
| Web 框架 | FastAPI + Uvicorn |
| 语言 | Python 3.11 |
| ORM | SQLAlchemy |
| 数据库 | PostgreSQL + pgvector |
| 缓存 | Redis |
| 向量记忆 | ChromaDB / 本地向量库 |
| 文本生成 | 火山引擎 Ark / DashScope / OpenAI 兼容接口 |
| 图片生成 | 火山引擎 Seedream / VectorEngine 兼容接口 |
| 语音合成 | 火山引擎 TTS / DashScope / edge-tts |
| 部署 | Docker Compose + Nginx |

## 核心模块

```text
NoEndStory/
├── frontend/
│   ├── src/pages/              # 首页、角色设定、音色选择、游戏主界面、结局收藏册
│   ├── src/components/         # 通用布局、游戏画面、加载动画、背景音乐
│   ├── src/hooks/              # 游戏初始化、TTS、路由过场、按钮音效
│   ├── src/services/api.ts     # API 封装与游客额度错误处理
│   └── src/config/basePath.ts  # /galgame 子路径适配
├── backend/
│   ├── api/                    # FastAPI 路由、服务、中间件、Schema
│   ├── game/script_engine_v2/  # 当前主剧情编排引擎
│   ├── models/                 # 数据库模型
│   ├── database/               # PostgreSQL 与向量库访问
│   ├── audio/                  # TTS 语音相关能力
│   └── images/                 # 本地开发生成资源目录
├── deploy/
│   ├── docker-compose.player.yml
│   ├── player.env.example
│   └── postgres-init/
└── scripts/
    └── deploy-server.sh
```

## 部署概览

项目支持 Docker Compose 部署，生产环境包含：

- `frontend`：Nginx + 前端静态资源，对外提供 Web 入口。
- `backend`：FastAPI 游戏服务，仅在容器网络内部暴露。
- `postgres`：保存角色、游戏会话、结局、游客额度等结构化数据。
- `redis`：用于缓存和短期状态。

生成的角色图、场景图、复合图、TTS 音频和向量数据不进入镜像，而是保存到 Docker volume，避免镜像过大。

## 访问入口

| 环境 | 入口 |
| --- | --- |
| 本地前端开发 | `http://localhost:3000/` |
| 本地后端开发 | `http://localhost:8001/` |
| Docker 后端容器内部 | `http://backend:8000/` |
| 生产 Web 入口 | `http://hyjkblj.online/galgame/` |

## License

本项目许可证以仓库内许可证文件为准。
