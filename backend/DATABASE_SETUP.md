# 数据库服务搭建指南 - Chroma 本地部署

## ✅ 数据库架构

项目使用两种数据库：

1. **PostgreSQL**：存储结构化数据（用户、线程、对话历史等）
2. **Chroma（本地部署）**：存储向量数据（剧情记忆，用于 RAG）

---

## 一、环境准备

### 1.1 安装 PostgreSQL

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql

# Windows
# 下载安装包：https://www.postgresql.org/download/windows/
```

### 1.2 创建数据库

```bash
# 连接到 PostgreSQL
sudo -u postgres psql

# 创建数据库
CREATE DATABASE noendstory;

# 创建用户（可选）
CREATE USER noendstory_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE noendstory TO noendstory_user;

# 退出
\q
```

### 1.3 安装 Python 依赖

```bash
# 确保虚拟环境已激活
pip install -r requirements.txt
```

---

## 二、配置环境变量

### 2.1 复制环境变量文件

```bash
cd backend
copy env.example .env
```

### 2.2 编辑 .env 文件

至少需要配置：

```env
# PostgreSQL 数据库连接
DATABASE_URL=postgresql://user:password@localhost/noendstory

# OpenAI API Key
OPENAI_API_KEY=sk-your-key-here

# Chroma 数据库路径（可选，默认 ./chroma_db）
CHROMA_DB_PATH=./chroma_db
```

---

## 三、初始化数据库

### 3.1 初始化 PostgreSQL

```bash
# 从项目根目录运行
python scripts/init_db.py
```

这会创建所有 PostgreSQL 表：
- users
- threads
- story_states
- conversations
- image_cache

### 3.2 初始化 Chroma（本地部署）

```bash
# 从项目根目录运行
python scripts/init_chroma.py
```

这会：
- 创建 `./chroma_db` 目录（如果不存在）
- 创建 `story_memories` Collection
- 配置为使用余弦相似度

---

## 四、验证安装

### 4.1 验证 PostgreSQL

```bash
# 连接到数据库
psql -d noendstory

# 查看表
\dt

# 应该看到：
# - users
# - threads
# - story_states
# - conversations
# - image_cache

# 退出
\q
```

### 4.2 验证 Chroma

```python
# 在 Python 中验证
from app.services.memory_service import MemoryService

memory_service = MemoryService()
info = memory_service.get_collection_info()
print(f"Collection: {info['name']}")
print(f"记录数: {info['count']}")
```

---

## 五、使用示例

### 5.1 PostgreSQL 使用

```python
from app.database.session import get_db
from app.models.database import User, Thread
from sqlalchemy.orm import Session

# 在 FastAPI 路由中使用
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users
```

### 5.2 Chroma 使用（本地部署）

```python
from app.services.memory_service import MemoryService

# 初始化服务（自动使用本地部署）
memory_service = MemoryService()

# 存储记忆
memory_id = memory_service.store_memory(
    thread_id="thread_123",
    content="Alice 在海边遇到了 Bob，他们成为了朋友。",
    scene="beach",
    importance=0.8
)

# 检索相关上下文
context = memory_service.get_relevant_context(
    thread_id="thread_123",
    query="Alice 和 Bob 的关系如何？",
    top_k=5
)

print(context)
```

---

## 六、数据库目录结构

```
项目根目录/
├── backend/
│   ├── chroma_db/          # Chroma 数据库目录（自动创建）
│   │   ├── chroma.sqlite3
│   │   └── ...
│   └── ...
└── ...
```

---

## 七、注意事项

### 7.1 Chroma 本地部署特性

- ✅ **数据持久化**：数据存储在本地目录，重启后不丢失
- ✅ **无需额外服务**：不需要启动 Chroma 服务器
- ✅ **适合 MVP**：开箱即用，零配置
- ⚠️ **并发限制**：不支持多进程并发写入（读取可以并发）
- ⚠️ **单机部署**：只能单机部署，不支持分布式

### 7.2 数据备份

**PostgreSQL 备份**：
```bash
pg_dump -d noendstory > backup.sql
```

**Chroma 备份**：
```bash
# 直接复制整个目录
cp -r ./chroma_db ./chroma_db_backup
```

---

## 八、常见问题

### Q1: Chroma 数据库在哪里？

A: 默认在 `./chroma_db` 目录（相对于 backend 目录），可在 `.env` 中配置 `CHROMA_DB_PATH`。

### Q2: 如何迁移 Chroma 数据？

A: 直接复制整个 `chroma_db` 目录即可：
```bash
cp -r ./chroma_db /backup/location/
```

### Q3: 并发写入问题？

A: 本地部署不支持并发写入。如果以后需要多进程写入，可以迁移到服务器模式（HttpClient）。

---

*数据库服务搭建完成！现在可以使用 PostgreSQL 存储结构化数据，使用 Chroma 存储向量数据了。*
