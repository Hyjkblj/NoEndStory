# Chroma 数据库快速开始

## ✅ 当前配置

- **部署方式**：本地部署（PersistentClient）
- **存储位置**：`./chroma_db`（可在 `.env` 中配置）
- **距离度量**：余弦相似度（cosine）
- **Collection 名称**：`story_memories`

---

## 一、初始化（5 分钟）

### 1. 配置环境变量

```bash
# 复制环境变量模板
copy env.example .env

# 编辑 .env，至少配置：
# - OPENAI_API_KEY
# - CHROMA_DB_PATH（可选，默认 ./chroma_db）
```

### 2. 初始化 Chroma

```bash
# 从项目根目录运行
python scripts/init_chroma.py
```

**输出示例**：
```
✅ Chroma 数据库初始化成功！
   部署方式: 本地部署（PersistentClient）
   路径: D:\Develop\Project\No End Story\backend\chroma_db
   Collection: story_memories
   当前记录数: 0
   配置: 余弦相似度（cosine）
```

---

## 二、使用示例

### 2.1 基本使用

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

print(f"存储记忆 ID: {memory_id}")

# 检索相关上下文
context = memory_service.get_relevant_context(
    thread_id="thread_123",
    query="Alice 和 Bob 的关系如何？",
    top_k=5
)

print(f"相关上下文:\n{context}")
```

### 2.2 批量操作

```python
# 批量存储记忆
memories = [
    {
        "thread_id": "thread_123",
        "content": "Alice 在海边遇到了 Bob...",
        "scene": "beach",
        "importance": 0.8
    },
    {
        "thread_id": "thread_123",
        "content": "Bob 告诉 Alice 一个秘密...",
        "scene": "beach",
        "importance": 0.7
    }
]

memory_service.batch_store_memories(memories)
```

---

## 三、验证

```python
# 验证 Chroma 服务
from app.services.memory_service import MemoryService

memory_service = MemoryService()
info = memory_service.get_collection_info()

print(f"✅ Collection: {info['name']}")
print(f"✅ 记录数: {info['count']}")
print(f"✅ 配置: {info['metadata']}")
```

---

*Chroma 本地部署配置完成！可以开始使用向量数据库了。*
