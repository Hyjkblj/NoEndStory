"""配置文件"""
import os
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'noendstory'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

# 向量数据库配置
# 统一使用“项目根目录/vector_db”作为默认库位置（历史数据也在这里），避免从不同工作目录启动时读到不同库。
_backend_dir = os.path.dirname(os.path.abspath(__file__))  # .../backend
_project_root_dir = os.path.dirname(_backend_dir)  # 项目根目录
_default_vector_db_path = os.path.join(_project_root_dir, 'vector_db')
VECTOR_DB_PATH = os.getenv('VECTOR_DB_PATH', _default_vector_db_path)

# Embedding模型配置（用于向量数据库的长时记忆）
# 可选值：
# - 'default': ChromaDB默认模型（all-MiniLM-L6-v2，英文为主）
# - 'text2vec-chinese': 中文优化模型（推荐用于中文游戏）
# - 'm3e-base': 中文embedding模型
# - 'bge-small-zh-v1.5': 百度开源中文embedding模型
# - 'paraphrase-multilingual': 多语言模型（支持中英文）
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text2vec-chinese')

# AI模型配置（可选，当前代码未使用）
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# 国内AI模型配置（替代方案）
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', '')  # 通义千问（阿里云）
# 通义千问模型选择：qwen-turbo（快速，成本低）、qwen-plus（平衡）、qwen-max（最强，成本高）、qwen-flash（极速，成本最低）
DASHSCOPE_MODEL = os.getenv('DASHSCOPE_MODEL', 'qwen-flash')  # 默认使用qwen-flash（极速模型）
ZHIPU_API_KEY = os.getenv('ZHIPU_API_KEY', '')  # 智谱AI
BAIDU_API_KEY = os.getenv('BAIDU_API_KEY', '')  # 百度文心一言
BAIDU_SECRET_KEY = os.getenv('BAIDU_SECRET_KEY', '')

# 火山引擎配置
# 注意：从.env读取时去除首尾空格，避免配置格式错误
VOLCENGINE_ARK_API_KEY = os.getenv('VOLCENGINE_ARK_API_KEY', '').strip()  # Bearer Token (ARK API Key)
VOLCENGINE_REGION = os.getenv('VOLCENGINE_REGION', 'cn-beijing')  # 区域，默认：cn-beijing

# 文本生成配置（火山引擎）
VOLCENGINE_TEXT_MODEL = os.getenv('VOLCENGINE_TEXT_MODEL', 'deepseek-v3-2-251201')  # 文本生成模型：deepseek-v3-2-251201
VOLCENGINE_TEXT_API_URL = os.getenv('VOLCENGINE_TEXT_API_URL', '')  # 文本生成API端点（可选，默认根据region自动构建）

# 图片生成配置（火山引擎 Seedream）
VOLCENGINE_IMAGE_MODEL = os.getenv('VOLCENGINE_IMAGE_MODEL', 'doubao-seedream-4-0-250828')  # 图片生成模型：doubao-seedream-4-0-250828（默认）或 doubao-seedream-4-5-251128
VOLCENGINE_IMAGE_SIZE = os.getenv('VOLCENGINE_IMAGE_SIZE', '2K')  # 图片尺寸：2K, 4K, 1024x1024等

# 本地模型配置（Ollama）
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen:7b')  # 或 chatglm3:6b

# 游戏配置
GAME_CONFIG = {
    'max_events': 3,  # 中间事件数量
    'total_events': 5,  # 总事件数（开头1 + 中间3 + 结尾1）
}

# 图片保存配置
IMAGE_SAVE_DIR = os.getenv('IMAGE_SAVE_DIR', './images/characters')  # 角色图片保存目录
SCENE_IMAGE_SAVE_DIR = os.getenv('SCENE_IMAGE_SAVE_DIR', './images/scenes')  # 场景图片保存目录（大场景）
SMALL_SCENE_IMAGE_SAVE_DIR = os.getenv('SMALL_SCENE_IMAGE_SAVE_DIR', './images/smallscenes')  # 小场景图片保存目录
COMPOSITE_IMAGE_SAVE_DIR = os.getenv('COMPOSITE_IMAGE_SAVE_DIR', './images/composite')  # 合成图片保存目录（场景+人物）
IMAGE_SAVE_ENABLED = os.getenv('IMAGE_SAVE_ENABLED', 'true').lower() == 'true'  # 是否启用本地保存

