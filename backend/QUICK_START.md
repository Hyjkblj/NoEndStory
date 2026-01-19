# 快速启动指南

## ✅ 依赖已安装完成

所有核心依赖已正确安装：
- NumPy: 1.26.4
- ChromaDB: 0.4.22
- rembg: 2.0.41
- 其他依赖：已安装

## 🚀 启动后端

### 方法1: 使用启动脚本（推荐，自动修复 numpy 版本）

```powershell
cd d:\Develop\Project\NoEndStory\backend
.\venv\Scripts\Activate.ps1
.\start_backend.ps1
```

启动脚本会自动：
- 检查 numpy 版本
- 如果发现 numpy 2.x，自动降级到 1.26.4
- 验证所有依赖
- 启动后端服务

### 方法2: 直接启动

```powershell
cd d:\Develop\Project\NoEndStory\backend
.\venv\Scripts\Activate.ps1
python .\run_api.py
```

### 方法3: 如果遇到 numpy 版本问题

如果在新终端中遇到 `np.float_` 错误，先运行修复脚本：

```powershell
cd d:\Develop\Project\NoEndStory\backend
.\venv\Scripts\Activate.ps1
.\fix_numpy.ps1
python .\run_api.py
```

## 📋 启动成功标志

如果启动成功，应该看到：

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## 🔧 常见问题

### Q1: 启动时提示 `np.float_` 错误

**解决方案**：
```powershell
pip uninstall numpy -y
pip install "numpy==1.26.4" --force-reinstall --no-deps
```

### Q2: rembg 无法导入

**解决方案**：
```powershell
pip install "rembg==2.0.41"
```

### Q3: ChromaDB 无法导入

**解决方案**：
确保 numpy 版本为 1.26.4：
```powershell
pip install "numpy==1.26.4" --force-reinstall
```

## 📝 验证安装

运行验证脚本：
```powershell
python verify_dependencies.py
```

## 🎯 功能验证

启动后端后，可以测试以下功能：

1. **健康检查**：`GET http://localhost:8000/health`
2. **创建角色**：`POST http://localhost:8000/api/v1/characters/create`
3. **去除背景**：`POST http://localhost:8000/api/v1/characters/{character_id}/remove-background`
4. **初始化故事**：`POST http://localhost:8000/api/v1/characters/initialize-story`

## ✨ 已启用的功能

- ✅ AI图片生成（火山引擎Seedream）
- ✅ rembg背景去除（isnet-general-use模型）
- ✅ 静态文件服务（角色图片、场景图片、合成图片）
- ✅ 游戏会话管理
- ✅ 向量数据库（ChromaDB）

---

**现在可以正常使用后端服务了！** 🎉
