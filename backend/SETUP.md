# No End Story - 环境设置指南

## 一、创建虚拟环境

### Windows

```bash
# 进入 backend 目录
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate
```

### macOS/Linux

```bash
# 进入 backend 目录
cd backend

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

---

## 二、安装依赖

激活虚拟环境后：

```bash
# 安装所有依赖
pip install -r requirements.txt

# 或者升级 pip 后安装
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 三、配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
# 至少需要配置：
# - DATABASE_URL
# - OPENAI_API_KEY
```

---

## 四、初始化数据库

```bash
# 从项目根目录运行

# 初始化 PostgreSQL
python scripts/init_db.py

# 初始化 Chroma
python scripts/init_chroma.py
```

---

## 五、验证安装

```bash
# 在激活的虚拟环境中测试
python -c "import chromadb; print('✅ ChromaDB 安装成功')"
python -c "from openai import OpenAI; print('✅ OpenAI 安装成功')"
python -c "from sqlalchemy import create_engine; print('✅ SQLAlchemy 安装成功')"
```

---

## 六、退出虚拟环境

```bash
# Windows
deactivate

# macOS/Linux
deactivate
```

---

*更多信息请参考项目文档*
