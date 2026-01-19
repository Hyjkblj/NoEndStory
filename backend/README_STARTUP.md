# 后端启动说明

## ✅ 当前状态

所有依赖已正确安装并验证通过：
- ✅ NumPy: 1.26.4
- ✅ ChromaDB: 0.4.22  
- ✅ rembg: 2.0.41
- ✅ 后端应用可以成功导入

## 🚀 启动后端（三种方法）

### 方法1: 使用启动脚本（最推荐）

启动脚本会自动检查并修复 numpy 版本问题：

```powershell
cd d:\Develop\Project\NoEndStory\backend
.\venv\Scripts\Activate.ps1
.\start_backend.ps1
```

### 方法2: 直接启动

如果确定 numpy 版本正确：

```powershell
cd d:\Develop\Project\NoEndStory\backend
.\venv\Scripts\Activate.ps1
python .\run_api.py
```

### 方法3: 手动修复后启动

如果遇到 `np.float_` 错误：

```powershell
cd d:\Develop\Project\NoEndStory\backend
.\venv\Scripts\Activate.ps1

# 修复 numpy 版本
pip uninstall numpy -y
pip install "numpy==1.26.4" --force-reinstall --no-deps

# 启动
python .\run_api.py
```

## 📋 启动成功标志

看到以下信息表示启动成功：

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## 🔍 验证服务

启动后可以访问：
- 健康检查：http://localhost:8000/health
- API 文档：http://localhost:8000/docs

## 📝 已启用的功能

从导入日志可以看到以下服务已初始化：

1. **AI图片生成服务**
   - 服务：火山引擎Seedream (VolcEngine)
   - 模型：doubao-seedream-4-5-251128
   - 状态：✅ 已启用

2. **rembg背景去除服务**
   - 模型：isnet-general-use
   - 状态：✅ 已初始化

3. **静态文件服务**
   - 角色图片：`/static/images/characters`
   - 场景图片：`/static/images/scenes`
   - 合成图片：`/static/images/composite`
   - 状态：✅ 已配置

## 🎯 测试功能

启动后端后，可以测试以下 API：

1. **创建角色**（包含AI图片生成）
   ```
   POST /api/v1/characters/create
   ```

2. **去除背景**（使用rembg）
   ```
   POST /api/v1/characters/{character_id}/remove-background
   ```

3. **初始化故事**（初遇场景）
   ```
   POST /api/v1/characters/initialize-story
   ```

## ⚠️ 注意事项

- **numpy 版本**：必须保持为 1.26.4，如果被升级到 2.x，ChromaDB 将无法工作
- **每次新终端**：如果在新终端中启动，建议使用 `start_backend.ps1` 脚本，它会自动检查并修复
- **依赖冲突**：如果安装新包时 numpy 被升级，运行 `fix_numpy.ps1` 修复

## 📚 相关文档

- `INSTALL_GUIDE.md` - 完整安装指南
- `QUICK_START.md` - 快速启动指南
- `INSTALL_SUCCESS.md` - 安装成功确认

---

**准备就绪，可以启动后端服务了！** 🚀
