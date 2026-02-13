# 火山引擎 Doubao TTS 快速开始指南

## 🚀 当前状态

✅ **代码集成完成** - 所有技术实现已就绪  
❌ **等待权限开通** - 需要在火山引擎控制台开通TTS服务权限

## 🔧 权限检查

### 第一步：运行权限检查
```bash
cd backend
python check_tts_permissions.py
```

### 第二步：如果权限不足
1. 登录火山引擎控制台：https://console.volcengine.com/
2. 导航到：**语音技术** → **语音合成**
3. 确认服务状态：
   - 服务已开通 ✅
   - 有可用配额 ✅
   - 无地域限制 ✅

## 🎯 权限开通后的测试

### 基础功能测试
```bash
# 完整测试套件
python test_doubao_tts.py

# 快速测试
python -c "
from api.services.tts_service import TTSService
tts = TTSService()
result = tts.generate_speech('你好，火山引擎！', 1)
print('测试结果:', result)
"
```

### WebSocket流式测试
```bash
python test_websocket_tts.py
```

## 📋 配置说明

### 当前配置（已设置）
```python
# 火山引擎 TTS 配置
VOLCENGINE_TTS_APP_ID = "6212235312"
VOLCENGINE_TTS_ACCESS_TOKEN = "VOHZ2ZCh...L_Ns"  # 已配置
VOLCENGINE_TTS_SECRET_KEY = "eHGxzFH0...TlbH"   # 已配置
VOLCENGINE_TTS_RESOURCE_ID = "volc.tts.default"
TTS_PROVIDER = "volcengine"
```

### 模式切换
```python
# HTTP模式（默认）
VOLCENGINE_TTS_USE_WEBSOCKET = False

# WebSocket流式模式
VOLCENGINE_TTS_USE_WEBSOCKET = True
```

## 🎵 可用音色

系统已配置14种火山引擎音色：

| 音色ID | 名称 | 描述 |
|--------|------|------|
| female_001 | 通用女声 | 标准女声，适合通用场景 |
| male_001 | 标准男声 | 标准男声，适合播音、解说 |
| female_002 | 甜美女声 | 甜美可爱，适合年轻角色 |
| male_002 | 磁性男声 | 低沉磁性，适合成熟角色 |
| ... | ... | ... |

## 🔄 备用方案

### 如果权限问题持续
```python
# 方案1：切换到阿里云百炼
TTS_PROVIDER = "dashscope"

# 方案2：使用本地TTS
TTS_PROVIDER = "edge-tts"
```

## 📞 技术支持

### 权限问题
- 火山引擎技术支持
- 控制台在线客服
- 提供错误信息：`[resource_id=volc.tts.default] requested resource not granted`

### 技术问题
- 查看详细文档：`DOUBAO_TTS_FINAL_SUMMARY.md`
- 运行调试工具：`python debug_volcengine_tts.py`

## ✅ 成功标志

权限开通成功后，你将看到：
```
🎉 权限检查通过！可以使用火山引擎TTS服务
✅ 语音生成成功!
   音频URL: /static/audio/cache/xxx.wav
   音频路径: /path/to/audio.wav
   是否缓存: False
   音频时长: 2.34秒
```

---

**总结**：技术集成已完成，只需开通火山引擎TTS服务权限即可使用。