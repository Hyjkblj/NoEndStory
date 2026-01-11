"""
记忆服务（RAG）- 使用 Chroma 本地部署
"""
import chromadb
from openai import OpenAI
from typing import List, Dict, Optional
import os
import uuid
from app.core.config import settings


class MemoryService:
    """
    记忆服务 - 使用 Chroma 本地部署（PersistentClient）存储和检索剧情记忆
    
    特性：
    - 本地持久化存储
    - 使用 OpenAI Embeddings API 生成向量
    - 支持按 thread_id 和 scene 过滤
    - 支持批量操作
    """
    
    def __init__(self, chroma_db_path: Optional[str] = None):
        """
        初始化 Chroma 数据库服务（本地部署）
        
        Args:
            chroma_db_path: Chroma 数据库存储路径，默认使用配置中的路径
        """
        db_path = chroma_db_path or settings.chroma_db_path
        
        # 创建目录（如果不存在）
        os.makedirs(db_path, exist_ok=True)
        
        # 创建 Chroma 客户端（本地持久化模式）
        self.client = chromadb.PersistentClient(path=db_path)
        
        # 创建或获取 Collection
        self.collection = self.client.get_or_create_collection(
            name="story_memories",
            metadata={
                "hnsw:space": "cosine",  # 使用余弦相似度（推荐用于文本向量）
                "description": "剧情记忆向量存储"
            }
        )
        
        # OpenAI 客户端（用于生成向量）
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        self.embedding_model = settings.openai_embedding_model
    
    def store_memory(
        self,
        thread_id: str,
        content: str,
        scene: Optional[str] = None,
        importance: float = 0.5,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        存储剧情记忆向量
        
        Args:
            thread_id: 线程 ID（玩家会话 ID）
            content: 记忆内容（原始文本）
            scene: 场景名称（可选）
            importance: 重要性评分 0-1（可选）
            metadata: 额外元数据（可选）
        
        Returns:
            memory_id: 存储的记忆 ID
        """
        # 使用 OpenAI Embeddings API 生成向量
        embedding_response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=content
        )
        embedding = embedding_response.data[0].embedding
        
        # 构建元数据
        memory_metadata = {
            "thread_id": thread_id,
            "importance": str(importance)
        }
        
        if scene:
            memory_metadata["scene"] = scene
        
        if metadata:
            memory_metadata.update(metadata)
        
        # 生成唯一 ID
        memory_id = f"{thread_id}_{uuid.uuid4().hex[:8]}"
        
        # 存储到 Chroma
        self.collection.add(
            embeddings=[embedding],  # 向量列表（单个向量也要放在列表中）
            documents=[content],  # 原始文本
            metadatas=[memory_metadata],  # 元数据
            ids=[memory_id]  # 唯一 ID
        )
        
        return memory_id
    
    def get_relevant_context(
        self,
        thread_id: str,
        query: str,
        top_k: int = 5,
        scene: Optional[str] = None
    ) -> str:
        """
        检索相关上下文（RAG）
        
        Args:
            thread_id: 线程 ID
            query: 查询文本
            top_k: 返回前 k 个最相关的结果
            scene: 场景过滤（可选）
        
        Returns:
            相关上下文的文本（用换行符连接）
        """
        # 生成查询向量
        query_embedding_response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=query
        )
        query_embedding = query_embedding_response.data[0].embedding
        
        # 构建查询过滤器（元数据过滤）
        where_filter = {"thread_id": thread_id}
        if scene:
            where_filter["scene"] = scene
        
        # 查询相似向量
        results = self.collection.query(
            query_embeddings=[query_embedding],  # 查询向量（列表形式）
            n_results=top_k,  # 返回数量
            where=where_filter,  # 元数据过滤
            include=["documents", "metadatas", "distances"]  # 返回的字段
        )
        
        # 构建上下文（从 documents 中提取）
        if results["documents"] and len(results["documents"][0]) > 0:
            contexts = results["documents"][0]
            return "\n".join(contexts)
        else:
            return ""
    
    def delete_memory(self, memory_id: str):
        """删除指定记忆"""
        self.collection.delete(ids=[memory_id])
    
    def delete_thread_memories(self, thread_id: str):
        """删除指定线程的所有记忆"""
        # 获取所有该线程的记忆
        results = self.collection.get(
            where={"thread_id": thread_id}
        )
        
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
    
    def get_collection_info(self) -> Dict:
        """获取 Collection 信息"""
        return {
            "name": self.collection.name,
            "count": self.collection.count(),
            "metadata": self.collection.metadata
        }
    
    def batch_store_memories(
        self,
        memories: List[Dict]
    ):
        """
        批量存储记忆
        
        Args:
            memories: 记忆列表，每个元素包含：
                - thread_id: 线程 ID
                - content: 内容
                - scene: 场景（可选）
                - importance: 重要性（可选）
                - metadata: 元数据（可选）
        """
        embeddings = []
        documents = []
        metadatas = []
        ids = []
        
        for memory in memories:
            # 生成向量
            embedding_response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=memory["content"]
            )
            embedding = embedding_response.data[0].embedding
            
            # 构建元数据
            memory_metadata = {
                "thread_id": memory["thread_id"],
                "importance": str(memory.get("importance", 0.5))
            }
            
            if memory.get("scene"):
                memory_metadata["scene"] = memory["scene"]
            
            if memory.get("metadata"):
                memory_metadata.update(memory["metadata"])
            
            embeddings.append(embedding)
            documents.append(memory["content"])
            metadatas.append(memory_metadata)
            ids.append(memory.get("id") or f"{memory['thread_id']}_{uuid.uuid4().hex[:8]}")
        
        # 批量添加
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
