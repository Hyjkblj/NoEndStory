# NoEndStory 平行工作区规划

> **编写日期**: 2026-06-15  
> **最后更新**: 2026-06-15 18:55（W1 完成）  
> **来源**: CodeReview 报告 (50+问题) + 数据库设计优化方案 + NOS Agent 架构讨论  
> **约束**: 1角色+玩家，游戏时长30分钟，单人开发  
> **原则**: 每个工作区独立可并行，互不干扰，文件级零冲突  
> **分支命名**: `w{N}-{kebab-case}` 如 `w1-p0-emergency-fixes`

---

## 〇、进度追踪

| 工作区 | 分支 | 状态 | 提交 | 合并日期 |
|--------|------|------|------|----------|
| W1: P0 紧急修复 | `w1-p0-emergency-fixes` | ✅ 已完成 | `336a6ca` | 2026-06-15 |
| W2: 数据库 Schema 升级 | `w2-db-schema` | ⬜ 待开始 | — | — |
| W3: 用户认证系统 | `w3-auth-system` | ⬜ 待开始 | — | — |
| W4: 安全防护体系 | `w4-security-defense` | ⬜ 待开始 | — | — |
| W5: API 响应标准化 | `w5-api-standardize` | ⬜ 待开始 | — | — |
| W6: Agent 架构重设计 | `w6-agent-engine` | ⬜ 待开始 | — | — |
| W7: 异步图片管线 | `w7-async-image` | ✅ 已完成 | `cad4779` | 2026-06-15 |
| W8: 会话与并发安全 | `w8-session-safety` | ✅ 已完成 | `aa41a07` | 2026-06-15 |
| W9: 代码质量重构 | `w9-code-quality` | ⬜ 待开始 | — | — |
| W10: 前端架构优化 | `w10-frontend-opt` | ⬜ 待开始 | — | — |
| W11: 可观测性体系 | `w11-observability` | ⬜ 待开始 | — | — |
| W12: 测试体系 | `w12-testing` | ⬜ 待开始 | — | — |
| W13: WebSocket 流式 | `w13-websocket` | ⬜ 待开始 | — | — |
| W14: 部署与运维 | `w14-devops` | ⬜ 待开始 | — | — |

> 进度: 3/14 ✅ | 下一步: W2 W3 W4 可并行启动（W8 已完成）

---

## 一、问题全景总汇

### 1.1 来源与规模

| 来源 | 问题数 | 严重度覆盖 |
|------|--------|-----------|
| 代码审查报告 (CodeReview) | 50+ 项 | P0×6 / P1×15 / P2×14 |
| 数据库设计优化方案 | 8 新表 + 3 旧表修正 | 结构级 |
| NOS Agent 架构讨论 | 7 Agent 设计 + 叙事节拍 | 架构级 |
| 系统安全性评估 | 6 层防护体系 | 漏洞级 |
| 用户等待时长优化 | 异步化+缓存+流式 | 体验级 |

### 1.2 核心问题归纳

```
┌────────────────────────────────────────────────────────────┐
│                      4 大主题                               │
├────────────────┬────────────────┬──────────────┬───────────┤
│  ①Agent 重设计  │  ②数据库设计   │  ③系统安全性  │④用户等待  │
│  ─────────────  │  ─────────────  │  ────────────  │────────── │
│  ·无Agent架构   │  ·连接池未配   │  ·无认证机制   │·同步阻塞  │
│  ·LLM孤立调用   │  ·无CHECK约束  │  ·错误栈泄露   │·图片生成  │
│  ·无状态管理    │  ·无UNIQUE约束 │  ·无频率限制   │  10-30秒  │
│  ·无编排层      │  ·密码f-string │  ·无成本熔断   │·无WebSocket│
│  ·15Agent→7     │  ·缺少8张表   │  ·无IP黑名单   │·无缓存层  │
│  ·LangGraph→    │  ·无迁移管理   │  ·无审计日志   │·无预生成  │
│   简单状态机    │  ·PG↔CDB不一致 │  ·游客无限制   │·无流式输出│
└────────────────┴────────────────┴──────────────┴───────────┘
```

### 1.3 拆分策略：14 个工作区

```
原则：每个工作区只触碰自己拥有的文件/目录，零重叠
───────────────────────────────────────────────────────
  未触碰任何现有文件的工作区（纯新增）：W3 W4 W6 W7 W11 W12 W13 W14
  仅触自己所属现有文件的工作区：       W1 W2 W5 W8 W9 W10
───────────────────────────────────────────────────────
```

---

## 二、14 个独立工作区明细

---

### 工作区 W1：P0 紧急修复（安全与稳定性兜底） ✅ 已完成

**分支**: `w1-p0-emergency-fixes` | **提交**: `336a6ca` | **工期**: 1 天（实际） | **变更**: 6 files, +91/-38

**目标**: 修复 6 项影响系统可用性和安全性的 P0 级问题

**实际文件清单（6 个文件）**:

| 文件 | 实际修改 |
|------|----------|
| `backend/game/story_engine.py` | P0-1: 模块级 `_get_text_gen()` 单例 `AIGenerator`，替换函数内 `AIGenerator()` 每次新建 |
| `backend/database/db_manager.py` | P0-6: f-string → `sqlalchemy.engine.URL.create()` + 连接池配置 `pool_size=20, max_overflow=40, pool_recycle=3600`（原 W2 的连接池任务提前完成） |
| `backend/database/vector_db.py` | P0-4: 三级异常处理：版本/迁移→备份重建、锁定/权限→拒绝启动、未知→人工介入 |
| `backend/api/routers/characters.py` | P0-3: 2 处移除 `traceback.format_exc()`，改为脱敏 `logger.error()` + 通用错误消息 |
| `backend/api/routers/game.py` | P0-3: 1 处移除 `traceback.format_exc()`，同上 |
| `backend/api/services/game_session.py` | P0-5: `GameSessionManager._sessions` dict 加 `threading.RLock` 保护，`create/get/delete/get_all` 全部线程安全 |

**实际实现 vs 原计划差异**:

| 问题 | 原计划 | 实际实现 | 原因 |
|------|--------|----------|------|
| P0-1 LLM 单例 | 引入 `get_llm_service()` 工厂 | 模块级 `_get_text_gen()` 单例 `AIGenerator` | 最小改动，保持兼容 `ResponseWrapper` 等现有逻辑 |
| P0-5 并发隔离 | StoryEngine 无状态化（`SessionContext`） | `GameSessionManager` 加 `RLock` | 代码审查发现：每个 `GameSession` 已创建独立 `StoryEngine` 实例，真正并发风险在 `_sessions` dict 无保护 |
| P0-6 连接池 | 仅 URL 安全构建 | 同时追加连接池参数 | 一次性完成 `db_manager.py` 修改，避免与 W2 重复触碰同一文件 |

**与其它工作区的边界更新**:
- W2 `db_manager.py` 的连接池任务已由 W1 完成，W2 无需再触碰 `db_manager.py`
- W8 原计划重构 `story_engine.py` 无状态化 → 现无需改动（已通过 `GameSession` 隔离）
- W8 重点转为：会话 PostgreSQL 持久化 + Feature Flag + app.py 503 修复

**经验教训**:
- 分支命名: `w{N}-{kebab-case}`
- 流程: `git checkout -b wN-xxx → 修改 → git add + commit → git checkout main → git merge`
- 如果 git 未配置 `user.email`/`user.name`，需先 `git config user.email/user.name`（仅 repo 级别）

---

### 工作区 W2：数据库 Schema 升级（约束 + 迁移）

**优先级**: 🔴 高 | **工期**: 2-3 天（减去连接池已由 W1 完成） | **风险**: 中（涉及数据迁移）

**目标**: 修复现有 3 表的缺陷，引入 Alembic 迁移管理

**文件清单**:

| 文件 | 修改内容 |
|------|----------|
| `backend/models/character.py` | `characters` 表：加 `creator_user_id UUID`、`deleted_at TIMESTAMP`、3 条新索引 |
| `backend/models/character.py` | `character_states` 表：12 条 CHECK 约束 + `UNIQUE(character_id)` |
| `backend/models/character.py` | `character_attributes` 表：`UNIQUE(character_id, attribute_type)` + 组合索引 |
| `backend/database/db_manager.py` | Saga 补偿模式：`add_event_safe()` → PG 先写，CDB 后写，失败标记 `pending_sync`（注：连接池已由 W1 完成） |
| `backend/alembic/` (新建) | Alembic 初始化 + 第一版迁移脚本 |
| `backend/alembic.ini` (新建) | Alembic 配置文件 |
| `backend/requirements.txt` | 追加 `alembic==1.13.0` |

**交付物**:
- [ ] `characters` 表：`creator_user_id`、`deleted_at`、索引
- [ ] `character_states` 表：12 条 `CHECK(0-100)` 约束 + UNIQUE 约束
- [ ] `character_attributes` 表：UNIQUE + 索引
- [ ] `db_manager.py` 双写补偿方法（Saga 模式）
- [ ] `alembic upgrade head` 可执行
- [ ] 回滚命令 `alembic downgrade -1` 可用

**与其它工作区的边界**:
- W2 不触碰 `story_engine.py` / `ai_generator.py` / 任何路由
- W2 新表 `scene_images`/`cost_logs`/`audit_logs` 交由 W4/W7/W11 创建各自的 migration
- W2 不涉及认证相关表（W3 负责）
- W2 的 `db_manager.py` 修改仅追加 Saga 方法，连接池配置已由 W1 完成

---

### 工作区 W3：用户认证系统（游客 + 注册 + JWT）

**优先级**: 🔴 高 | **工期**: 3-5 天 | **风险**: 中

**目标**: 从零构建完整用户认证体系，实现游客→注册升级流

**文件清单（全部新建，0 个现有文件修改）**:

| 文件 | 内容 |
|------|------|
| `backend/api/routers/auth.py` | 6 个认证端点：`/guest` `/register` `/login` `/refresh` `/me` `/logout` |
| `backend/api/services/auth_service.py` | 认证业务逻辑：游客创建、注册、登录、密码哈希、token 签发/吊销 |
| `backend/api/middleware/auth.py` | JWT 验证中间件：`Depends(get_current_user)` |
| `backend/api/schemas/auth.py` | Pydantic 请求/响应模型：`GuestRequest` `RegisterRequest` `LoginRequest` `TokenResponse` `UserResponse` |
| `backend/migrations/versions/002_users.py` | `users` 表 + `user_tokens` 表 migration |
| `backend/migrations/versions/003_game_plays.py` | `game_plays` 表 migration |
| `frontend/src/pages/Login.tsx` | 登录页面 |
| `frontend/src/pages/Register.tsx` | 注册页面 |
| `frontend/src/components/AuthGuard.tsx` | 路由守卫组件 |
| `frontend/src/services/auth.ts` | 认证 API 调用封装 |
| `frontend/src/stores/authStore.ts` | 前端认证状态管理 |

**交付物**:
- [ ] `POST /api/v1/auth/guest` — 游客创建 + JWT 签发
- [ ] `POST /api/v1/auth/register` — 邮箱注册（可升级游客）
- [ ] `POST /api/v1/auth/login` — 密码登录（bcrypt 验证）
- [ ] `POST /api/v1/auth/refresh` — refresh_token 轮换
- [ ] `GET /api/v1/auth/me` — 当前用户信息
- [ ] `POST /api/v1/auth/logout` — 吊销 token
- [ ] `users` 表：UUID 主键、user_type、用户名、邮箱、密码哈希、免费次数控制
- [ ] `user_tokens` 表：SHA256 哈希存储、吊销机制、刷新轮换、每用户上限 5 个
- [ ] `game_plays` 表：关联用户、thread_id、角色ID、免费标记、自动计算时长
- [ ] 前端登录/注册页面 + 路由守卫
- [ ] 游客→注册升级流：保留已有游戏记录

**与其它工作区的边界**:
- W3 创建 `users`/`user_tokens`/`game_plays` 表，不与他人冲突
- W3 的 `Depends(get_current_user)` 中间件 W4/W5 可直接依赖
- W3 不修改任何现有路由，新路由注册在 `app.py` 的唯一一行追加

---

### 工作区 W4：安全防护体系（频率限制 + IP黑名单 + 成本熔断）

**优先级**: 🟡 中高 | **工期**: 2-3 天 | **风险**: 低

**目标**: 构建 6 层防滥用体系，从 IP 限制到成本熔断

**文件清单（全部新建）**:

| 文件 | 内容 |
|------|------|
| `backend/api/middleware/rate_limit.py` | 请求频率限制中间件：基于内存的滑动窗口，支持端点差异化配置 |
| `backend/api/middleware/cost_guard.py` | 成本监控中间件：记录每次 API 成本，触发熔断时返回 429 |
| `backend/api/routers/admin_security.py` | 管理端点：查看/手动封禁 IP、每日成本统计、池统计 |
| `backend/api/services/security_service.py` | 封禁逻辑：自动检测条件（1h内5+游客→封1h，24h内10+→封24h）|
| `backend/migrations/versions/004_banned_ips.py` | `banned_ips` 表 migration |
| `backend/migrations/versions/005_cost_logs.py` | `cost_logs` 表 migration |
| `backend/migrations/versions/006_audit_logs.py` | `audit_logs` 表 migration |

**交付物**:
- [ ] 6 层防护全部生效：
  - Layer 1: IP 级别免费次数限制（24h/3次）
  - Layer 2: Token 消耗监控 + 自动熔断（$2/h, $5/d）
  - Layer 3: 请求频率限制（按端点差异化）
  - Layer 4: IP + 设备指纹联合限制
  - Layer 5: Cloudflare Turnstile 人机验证（预留接口）
  - Layer 6: 邮箱验证（预留接口）
- [ ] `banned_ips` 表：支持过期封禁和永久封禁
- [ ] `cost_logs` 表：每次调用记录 cost_usd
- [ ] `audit_logs` 表：旧值/新值 JSON 对比
- [ ] 管理员 API：手动封禁、成本查看、黑名单管理
- [ ] 环境变量：`COST_LIMIT_PER_IP_DAILY`、`GUEST_FREE_PLAYS` 等

**与其它工作区的边界**:
- W4 的 `.env` 新增变量与 W3 不重叠（各自命名前缀）
- W4 中间件在 `app.py` 中以单行注册，与 W3 的 auth 中间件并行
- W4 的迁移文件与 W2/W3 独立（独立 migration 文件）

---

### 工作区 W5：API 响应标准化（Pydantic 模型 + 统一格式）

**优先级**: 🟡 中高 | **工期**: 2-3 天 | **风险**: 低

**目标**: 消除前后端契约不一致，所有端点使用 Pydantic 响应模型，统一错误码

**文件清单**:

| 文件 | 修改内容 |
|------|----------|
| `backend/api/schemas.py` | 新增 `GameInitResponse` `GameInputResponse` `CharacterCreateResponse` `ErrorResponse` 等全部响应模型 |
| `backend/api/response.py` | 确保与 `error_handler.py` 输出格式一致（统一为 `{code, message, data}`） |
| `backend/api/middleware/error_handler.py` | 异常响应改为 `{code: int, message: str, data: null}` 格式 |
| `backend/api/routers/game.py` | 所有 `response_model=dict` → `response_model=GameXxxResponse` |
| `backend/api/routers/characters.py` | 所有 `response_model=dict` → `response_model=CharacterXxxResponse` |
| `frontend/src/types/api.ts` | 移除 `unwrapResponse` 双格式兼容，统一解析 `{code, message, data}` |
| `frontend/src/types/index.ts` | 删除重复的 `ApiResponse<T>` |
| `frontend/scripts/generate-types.ts` (新建) | 从后端 OpenAPI schema 自动生成 TypeScript 类型脚本 |

**交付物**:
- [ ] 14 个路由端点全部绑定具体 Pydantic 模型
- [ ] 错误响应格式统一：`{code: 4xx/5xx, message: "...", data: null}`
- [ ] 成功响应格式统一：`{code: 200, message: "ok", data: {...}}`
- [ ] 前端 `unwrapResponse()` 只处理一种格式
- [ ] `types/index.ts` 中 `ApiResponse` 死代码已移除
- [ ] OpenAPI → TypeScript 生成脚本可运行

**与其它工作区的边界**:
- W5 修改现有路由文件，与 W3/W4 不冲突（W3 是新增路由，W4 是中间件）
- W5 的 schema 修改不影响 W6（Agent 引擎新建独立模块）
- 前端类型清理与 W10（前端优化）互补，W5 只做类型层面

---

### 工作区 W6：Agent 架构重设计（NOS 简化版，7 Agent + 状态机）

**优先级**: 🟡 中 | **工期**: 4-6 周 | **风险**: 中

**目标**: 构建 NOS 简化版 Agent 引擎，与现有 `StoryEngine` 并行运行

**约束**: 1角色+玩家，30分钟游戏，7个Agent，评分替代MCTS，简单状态机替代LangGraph

```
                ┌──────────────────────────────┐
                │      Director Agent           │
                │  (NarrativePlanner + Event    │
                │   Selector + FutureEvaluator)  │
                └──────────┬───────────────────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │  Emotion   │  │   World    │  │  Memory    │
    │   Agent    │  │ Simulator  │  │  (简版)    │
    │   12维情绪  │  │ 时间/天气  │  │ 当前上下文  │
    └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
          └───────────────┼───────────────┘
                          ▼
                   ┌─────────────┐
                   │ Consistency │
                   │    Agent    │
                   └──────┬──────┘
                          ▼
                   ┌─────────────┐
                   │  Dialogue   │
                   │   Agent     │
                   └──────┬──────┘
                  ┌───────┼───────┐
                  ▼       ▼       ▼
               Image    TTS     Text
              Director Director Output
```

**文件清单（全部新建，100% 新增代码）**:

| 文件 | 内容 |
|------|------|
| `backend/game/agents/__init__.py` | Agent 模块入口 |
| `backend/game/agents/base.py` | `BaseAgent` 抽象基类：`think(state) → action`、`observe(observation)` |
| `backend/game/agents/state.py` | `AgentState` dataclass：角色状态、世界状态、叙事阶段、对话历史 |
| `backend/game/agents/orchestrator.py` | `AgentOrchestrator`：简单的顺序状态机，数据流串联所有 Agent |
| `backend/game/agents/director_agent.py` | **Director Agent**：内含 NarrativePlanner（起承转合4节拍）+ EventSelector（加权采样）+ FutureEvaluator（3候选评分） |
| `backend/game/agents/emotion_agent.py` | **Emotion Agent**：12维情绪计算 + PAD三维映射 + 情绪衰减模型 |
| `backend/game/agents/world_simulator.py` | **World Simulator**：游戏内时间推进（虚拟时钟）、天气变化、场景切换管理 |
| `backend/game/agents/event_agent.py` | **Event Agent**：事件池管理 + 加权采样 + 随机因子注入 |
| `backend/game/agents/consistency_agent.py` | **Consistency Agent**：输出前校验角色不死而复生、时间线不跳跃、情绪不突变、伏笔回収 |
| `backend/game/agents/dialogue_agent.py` | **Dialogue Agent**：调用现有 LLM 框架生成台词，适配 Agent 输出格式 |
| `backend/game/agents/memory.py` | **MemoryManager（简版）**：Working Memory（当前对话上下文）+ Episodic Memory（近期事件）× ChromaDB 存取 |
| `backend/game/agents/narrative_beats.py` | **30分钟叙事节拍表**：起(0-5min) → 承(5-13min) → 转(13-23min) → 合(23-30min) → 结局 |
| `backend/tests/agents/` (新建) | Agent 单元测试：每个 Agent 独立可测 |

**30 分钟叙事节拍表**:

```
0:00  ┌─ 起 (Opening) ──────────────┐
      │ 角色登场，建立关系基调          │  ~5min
      │ 3-5轮对话                     │
5:00  ├─ 承 (Rising) ────────────────┤
      │ 关系深化，出现小矛盾/误会        │  ~8min
      │ 5-8轮对话，1-2个事件            │
13:00 ├─ 转 (Climax) ───────────────┤
      │ 核心冲突爆发                   │  ~10min
      │ 关键选择，情绪剧烈波动           │
      │ 5-8轮对话，2-3个事件            │
23:00 ├─ 合 (Resolution) ────────────┤
      │ 冲突化解/升级，导向结局          │  ~7min
      │ 3-5轮对话                     │
30:00 └─ Ending ────────────────────┘
```

**Director Agent 内部结构**:

```python
class DirectorAgent(BaseAgent):
    """导演Agent：内含3个子模块"""
    
    class NarrativePlanner:
        def plan_beat(self, elapsed_minutes: float) -> Beat:
            """根据已过时间返回当前叙事节拍"""
    
    class EventSelector:
        def select_event(self, beat: Beat, world_state, emotion_state) -> Event:
            """加权采样选择下一个事件，含随机因子"""
    
    class FutureEvaluator:
        def evaluate_candidates(self, events: list[Event], state) -> Event:
            """3候选评分（非MCTS），按符合节拍+情感影响+一致性评分"""
```

**交付物**:
- [ ] `BaseAgent` 接口：`think()` / `observe()` / Brain-Memory-Tools 三层
- [ ] `AgentOrchestrator`：顺序状态机，输入→Director→Emotion/World/Memory→Consistency→Dialogue→输出
- [ ] 7 个 Agent 全部实现并通过单元测试
- [ ] 30分钟叙事节拍自动切换
- [ ] 3候选 FutureEvaluator（每轮 LLM 调用 3-5 次，非 10-20 次）
- [ ] 与现有 `ImageService`/`TTSService` 的适配接口
- [ ] 可与现有 `StoryEngine` 通过 Feature Flag 切换

**与其它工作区的边界**:
- W6 **完全新建**，不修改任何 `story_engine.py` / `ai_generator.py` / `game_service.py`
- W6 通过 `game_service.py` 的 Feature Flag 切换新旧引擎（W8 负责切换逻辑）
- W6 复用的现有模块（LLM 框架、ChromaDB、DB Manager）通过依赖注入，不改动它们
- W6 的 `MemoryManager` 封装 ChromaDB 调用，与 W2 的双写补偿兼容

---

### 工作区 W7：异步图片处理管线（预生成池 + 后台渲染） ✅ 已完成

**分支**: `w7-async-image` | **提交**: `cad4779` | **工期**: 1 天 | **变更**: 5 files, +1389 lines

**优先级**: 🟡 中 | **工期**: 1-2 周 | **风险**: 低

**目标**: 消除场景切换时的 10-30 秒同步等待

**文件清单（全部新建）**:

| 文件 | 内容 |
|------|------|
| `backend/api/services/image/image_pool_service.py` | **场景图片池服务**：加权随机抽取、池大小管理（5-10张）、低分淘汰 |
| `backend/api/services/image/background_generator.py` | **后台预生成器**：池低于 MIN_POOL_SIZE 时自动触发异步生成 |
| `backend/api/services/image/image_cache.py` | **LRU 内存缓存**：最近 50 张图片在内存，减少磁盘 IO |
| `backend/migrations/versions/007_scene_images.py` | `scene_images` 表 migration |
| `backend/api/routers/admin_scenes.py` | 管理端点：预热场景、池统计、手动触发生成 |

**场景图片池策略**:

```
每个场景维护 5-10 张变体图片
  ├─ MIN_POOL_SIZE = 5   （少于5张时自动触发补充生成）
  └─ MAX_POOL_SIZE = 10  （超过10张时清理低分图片）

随机抽取逻辑：
  SELECT * FROM scene_images
  WHERE scene_id = ? AND status = 'active' AND quality_score >= 3.0
  ORDER BY RANDOM() * quality_score DESC
  LIMIT 1

成本估算（72个小场景）：
  预热 TOP 20 高频场景：20 × 5 × $0.10 = $10（一次性）
  其余懒加载：$0.10/次（首次等3-5s，后续复用）
```

**交付物**:
- [x] `scene_images` 表 + migration（含质量分数、状态、元数据字段）
- [x] `ImagePoolService`：加权随机抽取 + 池管理（MIN/MAX_POOL_SIZE 配置）
- [x] `BackgroundGenerator`：异步预生成（ThreadPoolExecutor，2线程并发）
- [x] `ImageCache`：LRU 50 张内存缓存（支持 TTL 过期清理）
- [x] 管理员预热 API：`POST /admin/scenes/pre-generate`
- [x] 池统计 API：`GET /admin/scenes/pool-stats`
- [x] 额外 API：`GET /admin/scenes/random-image`、缓存管理、生成状态查询
- [ ] 场景切换时极速返回（命中缓存 < 50ms，池命中 < 200ms）← 需要实际运行验证

**与其它工作区的边界**:
- W7 的 `scene_images` 迁移不与 W2/W4 冲突（独立 migration 文件）
- W7 封装现有 ImageService，不修改其内部实现
- W7 的缓存层透明，不影响 Agent 调用方式

---

### 工作区 W8：会话持久化 + Agent 引擎开关

**优先级**: 🔴 高 | **工期**: 1 周（简化后） | **风险**: 中

**目标**: 解决 P1-11（服务重启会话丢失）和 P1-13（配置失败静默启动），引入 Agent 引擎 Feature Flag

**⚠️ 范围调整（W1 后）**: 原计划包含 StoryEngine 无状态化，但代码审查确认每个 `GameSession` 已创建独立 `StoryEngine` 实例，实例变量不存在跨会话共享。`GameSessionManager._sessions` 并发安全问题已由 W1 修复。W8 重点调整为会话持久化和 Feature Flag。

**文件清单**:

| 文件 | 修改内容 |
|------|----------|
| `backend/api/services/game_session.py` | `GameSessionManager._sessions` 改为 PostgreSQL 持久化存储（`game_sessions` 表） |
| `backend/api/services/game_service.py` | 引入 Feature Flag：`USE_NOS_AGENT_ENGINE=false`，切换 W6 Agent 引擎 vs 旧 StoryEngine |
| `backend/api/app.py` (L31-40) | 关键服务启动失败 → 返回 503 而非静默启动 |
| `backend/api/app.py` (L85-173) | 静态文件挂载 6 次重复合并为循环（W9b 合并入 W8） |

**交付物**:
- [ ] `GameSessionManager` PostgreSQL 持久化（`game_sessions` 表）
- [ ] 会话状态 JSON 序列化/反序列化
- [ ] Feature Flag：`USE_NOS_AGENT_ENGINE=false`（默认用旧引擎）
- [ ] W6 Agent 引擎通过 Feature Flag 切换接入
- [ ] 关键服务失败时 503 响应
- [ ] 静态文件挂载 DRY（W9b 合并）

**与其它工作区的边界**:
- W8 不再重构 `story_engine.py`（会话隔离已通过 GameSession 实现）
- W8 的 `game_service.py` Feature Flag 切换逻辑不影响 W5（API 格式不变）
- W8 的 `game_sessions` 表是独立 migration，不与他人冲突

**实际实现** (2026-06-15):

| 文件 | 实际修改 |
|------|----------|
| `backend/models/character.py` | 新增 `GameSession` 模型：`thread_id`（UUID唯一索引）、`user_id`、`character_id`、`game_mode`、`is_initialized`、`current_scene`、`session_data`（JSON）、`expires_at`（过期时间） |
| `backend/api/services/game_session.py` | 重写 `GameSessionManager`：内存缓存 + PostgreSQL 持久化双层存储，支持从数据库自动加载未过期会话，`to_dict()`/`from_dict()` 序列化，`cleanup_expired_sessions()` 清理过期会话 |
| `backend/api/services/game_service.py` | 新增 `USE_NOS_AGENT_ENGINE` Feature Flag（环境变量控制，默认 `false`） |
| `backend/api/app.py` | 1. 关键服务（数据库）启动失败标记 `_startup_failed`，中间件拦截返回 503；2. 静态文件挂载 6 处 try-except 合并为 `STATIC_MOUNTS` 配置列表 + 循环挂载 |

**实际实现 vs 原计划差异**:

| 问题 | 原计划 | 实际实现 | 原因 |
|------|--------|----------|------|
| 会话持久化 | 简单数据库存储 | 内存缓存 + DB 双层，启动时自动加载 | 避免每次读取都查库，提升性能 |
| 会话过期 | 未提及 | 新增 `expires_at` 字段 + 自动清理 | 防止数据库无限膨胀 |
| 静态文件DRY | 简单循环 | `STATIC_MOUNTS` 配置列表 + 统一处理 | 更清晰的配置管理，支持跳过未配置项 |

---

### 工作区 W9a：AI 生成器重构（函数拆分 + 服务合并）

**优先级**: 🟡 中 | **工期**: 1 周 | **风险**: 中

**⚠️ W9 已拆分**: 原 W9 与 W8 共享 `story_engine.py` + `app.py`，为消除文件冲突，拆为两部分：
- **W9a**（本工作区）：仅修改 `ai_generator.py`，与 W8 零冲突
- **W9b**：`story_engine.py` + `app.py` 清理 → 并入 W8

**目标**: 解决 P1-1（AIGenerator/TextModelService 功能重复）和 P1-3（函数过长）

**文件清单（仅 2 个文件）**:

| 文件 | 修改内容 |
|------|----------|
| `backend/game/ai_generator.py` | 与 `backend/models/text_model_service.py` 功能合并为统一 `TextGenerationService` |
| `backend/game/ai_generator.py` (L131-390) | `generate_character_dialogue` ~260 行拆分为 `_build_prompt()` `_call_llm()` `_parse_response()` `_ensure_quality()` |
| `backend/game/ai_generator.py` (L744-776) | `_tokenize_text` token set 计算结果缓存 |
| `backend/game/ai_generator.py` (L83) | `DatabaseManager()` 改为依赖注入 |
| `backend/game/ai_generator.py` (L660-693) | `_ensure_dialogue_unique` 重写为语义去重（基于 embedding 相似度） |
| `backend/utils/logger.py` | 统一日志级别和格式 |

**交付物**:
- [ ] `TextGenerationService` 统一入口（替换 AIGenerator + TextModelService 双入口）
- [ ] `generate_character_dialogue` 拆分为 4 个子函数
- [ ] `_tokenize_text` token set 缓存
- [ ] 语义去重替换规则去重
- [ ] W6 Agent 引擎通过统一 `TextGenerationService` 调用 LLM

**W9b 合并到 W8 的内容**:
- ~~`story_engine.py` print()→logger~~ → 并入 W8
- ~~`story_engine.py` 正则预编译~~ → 并入 W8
- ~~`story_engine.py` ImageService 循环依赖~~ → 并入 W8
- ~~`app.py` DRY 静态文件挂载~~ → 并入 W8
- ~~`game_service.py` 重复 import~~ → 并入 W8

---

### 工作区 W10：前端架构优化（状态拆分 + 类型清理 + UX 提升）

**优先级**: 🟡 中 | **工期**: 1-2 周 | **风险**: 低

**目标**: 前端性能优化和用户体验提升

**文件清单**:

| 文件 | 修改内容 |
|------|----------|
| `frontend/src/hooks/useGameState.ts` | 拆分为 `useDialogueState` / `useSceneState` / `useGameProgress` / `useEmotionState` |
| `frontend/src/router/index.tsx` | `createXxxRouter` 改为 `useMemo` 缓存，避免每次渲染重建 |
| `frontend/src/types/index.ts` | 删除 `User`/`Thread`/`Message`/`StoryState` 死代码 |
| `frontend/src/types/game.ts` | `voiceConfig: unknown` → 具体类型 `VoiceConfig` |
| `frontend/src/services/api.ts` (L354) | `slice(0,600)` 硬编码 → 环境变量 `MAX_TTS_TEXT_LENGTH` |
| `frontend/src/pages/Game.tsx` | 加载状态优化 + 错误边界 + 降级 UI |
| `frontend/src/components/Game/GameDialogue.tsx` | 流式输出动画效果 + 打字机效果 |

**交付物**:
- [ ] `useGameState` 拆分为 4 个独立 Hook（每个 < 8 个返回值）
- [ ] 路由器对象缓存（useMemo）
- [ ] 0 个死代码类型定义
- [ ] `voiceConfig` 类型安全
- [ ] TTS 截断长度可配置
- [ ] 错误边界组件 + 友好降级页面
- [ ] 对话流式输出动画

**与其它工作区的边界**:
- W10 仅触碰前端文件，不涉及任何后端
- W10 的类型清理与 W5 的 API 标准化互补

---

### 工作区 W11：可观测性体系（日志 + Token 监控 + 管理面板）

**优先级**: 🟡 中 | **工期**: 1 周 | **风险**: 低

**目标**: 建立 Token 消耗监控、统一日志、管理统计面板

**文件清单（全部新建）**:

| 文件 | 内容 |
|------|------|
| `backend/monitoring/__init__.py` | 监控模块入口 |
| `backend/monitoring/token_tracker.py` | Token 消耗追踪器：记录每次 LLM 调用的 input/output tokens + 成本 |
| `backend/monitoring/usage_stats.py` | 使用统计：按用户/IP/端点/时间维度的聚合查询 |
| `backend/monitoring/health.py` | 健康检查增强：DB 连接、CDB 状态、LLM 提供商可达性 |
| `backend/api/routers/admin_stats.py` | 统计 API：每日成本、Token 用量、活跃用户数、游戏完成率 |
| `frontend/src/pages/AdminDashboard.tsx` | 管理面板页面（若需要） |
| `backend/middleware/request_logger.py` | 请求日志中间件：记录所有 API 调用的耗时、状态码、用户 |

**交付物**:
- [ ] 每次 LLM 调用自动记录 token 数和成本
- [ ] `GET /admin/stats/daily` — 每日成本趋势
- [ ] `GET /admin/stats/usage` — Token 用量排行
- [ ] `GET /health` — 增强健康检查（DB+CDB+LLM）
- [ ] 结构化日志（JSON 格式，可选）
- [ ] 请求日志中间件（可按环境开关）

**与其它工作区的边界**:
- W11 全部新建文件，零冲突
- W11 的 `token_tracker` 封装在 LLM 调用的外围，不修改 LLM 框架内部

---

### 工作区 W12：测试体系（单元测试 + 集成测试 + 压力测试）

**优先级**: 🟢 低（但建议尽早开始） | **工期**: 持续 | **风险**: 低

**目标**: 建立测试文化和测试基础设施

**文件清单（全部新建）**:

| 文件 | 内容 |
|------|------|
| `backend/tests/__init__.py` | 测试配置 + fixtures（mock DB, mock LLM） |
| `backend/tests/conftest.py` | Pytest fixtures：测试数据库、测试客户端、mock LLM 响应 |
| `backend/tests/test_llm_providers.py` | LLM 适配器单元测试 |
| `backend/tests/test_emotion_agent.py` | Emotion Agent 单元测试（12维计算逻辑） |
| `backend/tests/test_director_agent.py` | Director Agent 单元测试（叙事节拍切换） |
| `backend/tests/test_consistency_agent.py` | Consistency Agent 单元测试（矛盾检测规则） |
| `backend/tests/test_api_auth.py` | 认证 API 集成测试 |
| `backend/tests/test_api_game.py` | 游戏 API 集成测试 |
| `backend/tests/test_agent_orchestrator.py` | Agent 编排流程集成测试 |
| `backend/tests/load_test.py` | Locust 压力测试脚本 |
| `scripts/run_tests.ps1` | 一键运行测试脚本 |

**交付物**:
- [ ] `pytest` 可运行，覆盖率 > 60%
- [ ] 每个 Agent 独立可测（mock LLM 响应）
- [ ] 认证流程集成测试通过
- [ ] 游戏核心流程集成测试通过
- [ ] Locust 压力测试脚本（50 并发/60s）

**与其它工作区的边界**:
- W12 完全独立，依赖其他工作区产出的接口定义

---

### 工作区 W13：WebSocket 流式通信（实时对话输出）

**优先级**: 🟢 低 | **工期**: 1 周 | **风险**: 低

**目标**: 从 HTTP 请求-响应升级为 WebSocket 实时流式输出

**文件清单（全部新建）**:

| 文件 | 内容 |
|------|------|
| `backend/api/routers/ws_game.py` | WebSocket 端点：建立连接 → 接收输入 → 流式返回 Agent 输出 |
| `backend/api/services/ws_game_service.py` | WebSocket 游戏服务：管理连接生命周期、流式推送 |
| `frontend/src/hooks/useWebSocket.ts` | WebSocket 连接管理 Hook |
| `frontend/src/services/wsClient.ts` | WebSocket 客户端封装 |

**交付物**:
- [ ] `ws://host:8000/api/v1/ws/game/{thread_id}` 端点
- [ ] LLM 输出逐 token 流式推送
- [ ] 前端自动重连 + 心跳保活
- [ ] 与 HTTP 模式通过 Feature Flag 切换

**与其它工作区的边界**:
- W13 全部新建，与 W6 Agent 引擎通过统一接口对接

---

### 工作区 W14：部署与运维（Docker + CI/CD + 环境管理）

**优先级**: 🟢 低 | **工期**: 1 周 | **风险**: 低

**目标**: 完善部署流程和环境管理

**文件清单**:

| 文件 | 修改内容 |
|------|----------|
| `deploy/docker-compose.yml` | 增加 services：Redis（预留）、pgAdmin |
| `backend/Dockerfile` | 多阶段构建优化（builder + runner）、健康检查 |
| `.github/workflows/ci.yml` (新建) | CI：lint + test + build |
| `.github/workflows/deploy.yml` (新建) | CD：部署到阿里云 |
| `scripts/deploy.ps1` (新建) | 一键部署脚本 |
| `.env.example` | 追加 W3/W4 新增的所有环境变量 |
| `backend/requirements.txt` | 统一追加所有新增依赖 |

**交付物**:
- [ ] `docker-compose up` 一键启动全部服务
- [ ] Docker 镜像体积优化 < 500MB
- [ ] CI 流水线：代码检查 + 测试 + 构建
- [ ] 一键部署脚本

**与其它工作区的边界**:
- W14 处理的是配置和脚本，不触碰业务代码

---

## 三、文件级冲突矩阵（W1 完成后更新）

```
              W1  W2  W3  W4  W5  W6  W7  W8  W9  W10 W11 W12 W13 W14
story_engine  ●               ○       ●   ●                        
ai_generator                              ●                        
db_manager    ●   ○                                                  ← W2 仅追加 Saga 方法，不再配置连接池
vector_db     ●                                                     
models/char       ●           ✅ W8 完成，新增 GameSession 模型
api/routers/*  ●               ●                                    
api/app.py                                 ●   ●   ✅ W8 完成（503 + DRY）
api/response                        ●                              
api/schemas                         ●                              
api/error_handler                   ●                              
api/game_session ●                 ●   ✅ W8 完成（PostgreSQL 持久化）
api/game_service                    ✅ W8 完成（Feature Flag）  
frontend/src          ○       ●   ●           ●                    
deploy/*                                                       ●   
```

```
● = 本工作区修改该文件
○ = 本工作区仅追加方法/轻量修改该文件（非重构）
✅ = 本工作区已完成

零重叠确认（W8 完成后）：
- W1 W8 已合并 main，不再与其他工作区并行
- W2 与 W9 无交集
- W2 的 db_manager.py 仅追加 Saga 方法，W1 已配置连接池
- W3 W4 W6 W7 W11 W12 W13 全部新建文件 → 零冲突
- W9b（story_engine + app.py 清理）已并入 W8 完成
```

---

## 四、依赖关系图（W1 完成后）

```
✅ W1 (P0修复) ─ 已完成，基线确立 ──────────────────────┐
  │                                                        │
  ├──► W2 (数据库升级) ──────────────────────────────────┤
  │     │                                                  │
  │     └──► W3 (认证系统) ──┐                            │
  │                          ├──► W5 (API标准化) ──┐      │
  ├──► W4 (安全防护) ────────┘                      │      │
  │                                                 ▼      │
  ├──► ✅ W8 (会话持久化) ───► W6 (Agent引擎) ──► W13(WS)   │
  │                              │                          │
  ├──► W7 (异步图片) ───────────┼──► 集成测试 ────────────┤
  │                              │                          │
  ├──► W9a (ai_generator重构) ──┤                          │
  │                              │                          │
  ├──► W11 (可观测性) ──────────┤                          │
  │                              │                          │
  ├──► W10 (前端优化) ──────────┘                          │
  │                                                        │
  ├──► W12 (测试体系) ────────────────────────────────────┤
  │                                                        │
  └──► W14 (部署运维) ────────────────────────────────────┘
```

**说明**:
- W1 W8 已完成 ✅，当前 main 分支即为安全基线
- **W2 W3 W4 W7 W9a W10 W11 W12 W14 可立即并行启动**
- W8 已完成：会话持久化（PostgreSQL）、Feature Flag、503 响应、静态文件 DRY
- W6 可开始：W8（Feature Flag）已完成，W9a（TextGenerationService）可并行
- W9b（story_engine/app.py 清理）已并入 W8 完成

---

## 五、推荐执行路线

### 第一梯队（第 1 周）：基础 + 阻塞项

```
Day 1-2  ✅ W1: P0 紧急修复（已完成）

Day 3-7  并行启动（W1 已合并，可立即开始）:
            ████████ W2: 数据库 Schema 升级
            ████████ W3: 用户认证系统
            ████████ W4: 安全防护体系
            ████████ W7: 异步图片处理管线
```

### 第二梯队（第 2-3 周）：功能 + 优化

```
Week 2-3 (W2 W3 W4 W7 完成后):
            ████████ W5: API 响应标准化
            ████████ ✅ W8: 会话持久化 + Feature Flag（已完成）
            ████████ W9a: ai_generator.py 重构 + TextGenerationService 统一
            ████████ W10: 前端架构优化
            ████████ W11: 可观测性体系
```

### 第三梯队（第 4-6 周）：核心架构升级

```
Week 4-6:
            ████████████████████ W6: Agent 架构重设计（最大工作区）
                                  （✅ W8 Feature Flag 已完成，等待 W9a TextGenerationService）

            ████████ W13: WebSocket 流式通信
            ████████ W14: 部署与运维
```

### 贯穿全程

```
全程:       ████████████████████████████ W12: 测试体系（持续构建）
```

---

## 六、单人执行建议

### 6.1 简化线路（2-3 个月）

如果严格按"1角色+30分钟"约束，且需尽快上线：

```
优先队列（必须完成）:
  ✅ W1: P0 修复（1-2天）
  ✅ W3: 认证系统（3-5天）
  ✅ W4: 安全防护（2-3天）
  ✅ W7: 异步图片（1-2周）
  ✅ W8: 会话管理（1-2周）

核心升级（体验飞跃）:
  ✅ W2: 数据库升级（2-3天）
  ✅ W5: API 标准化（2-3天）
  ✅ W6: Agent 架构（4-6周）← 核心价值

可选（时间充裕时）:
  ⬜ W9: 代码质量（1-2周）
  ⬜ W10: 前端优化（1-2周）
  ⬜ W11: 可观测性（1周）
  ⬜ W13: WebSocket（1周）
  ⬜ W14: DevOps（1周）
  ⬜ W12: 测试（持续）
```

### 6.2 API 成本预估

```
改造前（当前系统）:
  单局游戏 LLM 调用: 45-70 次
  月均 API 成本: ¥500-2,000

改造后（NOS 简化版）:
  单局游戏 LLM 调用: 15-25 次（每轮 3-5 次 × 5-8 轮）
  月均 API 成本: ¥1,000-3,000

对比（完整 NOS 15 Agent + MCTS）:
  单局游戏 LLM 调用: 100-200 次
  月均 API 成本: ¥5,000-15,000
```

### 6.3 技术复杂度对照表

| 工作区 | 复杂度 | 单人可行 | 关键风险 | 状态 |
|--------|--------|---------|---------|------|
| W1: P0 修复 | ⭐ | ✅ | 改动小，影响大，需谨慎 | ✅ 完成 |
| W2: 数据库升级 | ⭐⭐ | ✅ | migration 兼容性 | ⬜ |
| W3: 认证系统 | ⭐⭐⭐ | ✅ | JWT 安全实现 | ⬜ |
| W4: 安全防护 | ⭐⭐ | ✅ | 熔断阈值调优 | ⬜ |
| W5: API 标准化 | ⭐⭐ | ✅ | 前后端同步 | ⬜ |
| **W6: Agent 架构** | **⭐⭐⭐⭐** | ✅ 可行 | 设计与实现工作量 | ⬜ |
| W7: 异步图片 | ⭐⭐ | ✅ | 异步任务管理 | ⬜ |
| W8: 会话持久化 | ⭐⭐ | ✅ | Feature Flag 切换逻辑 | ⬜ |
| W9a: AI 生成器重构 | ⭐⭐ | ✅ | 重构风险 | ⬜ |
| W10: 前端优化 | ⭐⭐ | ✅ | 状态拆分影响面 | ⬜ |
| W11: 可观测性 | ⭐ | ✅ | 简单 | ⬜ |
| W12: 测试 | ⭐⭐ | ✅ | 持续投入 | ⬜ |
| W13: WebSocket | ⭐⭐ | ✅ | 连接管理 | ⬜ |
| W14: 部署 | ⭐ | ✅ | 环境变量同步 | ⬜ |

---

## 七、附录：所有工作区环境变量汇总

```bash
# ===== W3: 认证 =====
JWT_SECRET=<random-32-chars>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# ===== W4: 安全防护 =====
GUEST_FREE_PLAYS=1
GUEST_MAX_CREATIONS_PER_IP_PER_HOUR=5
GUEST_MAX_FREE_PLAYS_PER_IP_PER_DAY=3
COST_LIMIT_PER_IP_DAILY=5.0
COST_LIMIT_PER_IP_HOURLY=2.0
TURNSTILE_SITE_KEY=
TURNSTILE_SECRET_KEY=

# ===== W6: Agent 引擎 =====
USE_NOS_AGENT_ENGINE=false
AGENT_FUTURE_CANDIDATE_COUNT=3
AGENT_MAX_DIALOGUE_ROUNDS=25

# ===== W7: 异步图片 =====
SCENE_IMAGE_MIN_POOL_SIZE=5
SCENE_IMAGE_MAX_POOL_SIZE=10
IMAGE_CACHE_SIZE=50

# ===== W10: 前端 =====
MAX_TTS_TEXT_LENGTH=600

# ===== W13: WebSocket =====
WS_HEARTBEAT_INTERVAL=30
WS_MAX_MESSAGE_SIZE=65536
```

---

> **文档版本**: v1.1  
> **最后更新**: 2026-06-15 18:55（W1 完成）  
> **核心原则**: 14 个工作区文件级零重叠  
> **变更摘要（v1.0 → v1.1）**:  
> - W1 已完成（6 files, +91/-38），分支 `w1-p0-emergency-fixes` → 合并 main  
> - 连接池配置由 W1 提前完成，W2 移除该任务  
> - P0-5 实际修复为 `GameSessionManager` 加锁（非 StoryEngine 重构）  
> - W9 拆分为 W9a（ai_generator.py 独占）+ W9b（并入 W8）  
> - W8 范围缩小为会话持久化 + Feature Flag  
> - 新增进度追踪表（§0）和分支命名规范
