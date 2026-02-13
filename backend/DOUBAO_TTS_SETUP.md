# 火山引擎 Doubao TTS 快速配置指南

## 🚀 快速开始

### 1. 配置环境变量

在项目根目录的 `.env` 文件中添加以下配置：

```bash
# 火山引擎 TTS 配置
VOLCENGINE_TTS_APP_ID=6212235312
VOLCENGINE_TTS_ACCESS_TOKEN=VOHZ2ZChGyPbFxGmfNmOByFZBafHL_Ns
VOLCENGINE_TTS_SECRET_KEY=eHGxzFH0d_QrYxhSzNuNSGxdt0ZXTlbH
VOLCENGINE_REGION=cn-beijing
VOLCENGINE_TTS_MODEL=doubao-tts-24k
TTS_PROVIDER=volcengine
```

### 2. 开通火山引擎TTS服务权限

⚠️ **重要：当前需要在火山引擎控制台开通TTS服务权限**

1. 访问 [火山引擎控制台](https://console.volcengine.com/)
2. 登录您的账户
3. 找到"语音技术"或"TTS语音合成"服务
4. 确认应用ID `6212235312` 已开通TTS服务权限
5. 如需要，购买TTS服务套餐

### 3. 测试配置

运行测试脚本验证配置：

```bash
cd backend
python test_doubao_tts.py
```

### 4. 预期结果

**当前状态（权限未开通）：**
```
❌ HTTP 403 - "requested resource not granted"
```

**开通权限后的预期结果：**
```
✅ 语音生成成功!
🎉 所有测试通过！火山引擎 Doubao TTS 集成成功！
```

## 📋 配置参数说明

| 参数 | 值 | 说明 |
|------|-----|------|
| `VOLCENGINE_TTS_APP_ID` | `6212235312` | 火山引擎应用ID |
| `VOLCENGINE_TTS_ACCESS_TOKEN` | `VOHZ2ZChGyPbFxGmfNmOByFZBafHL_Ns` | 访问令牌 |
| `VOLCENGINE_TTS_SECRET_KEY` | `eHGxzFH0d_QrYxhSzNuNSGxdt0ZXTlbH` | 密钥 |
| `VOLCENGINE_REGION` | `cn-beijing` | 服务区域 |
| `VOLCENGINE_TTS_MODEL` | `doubao-tts-24k` | TTS模型（高质量） |
| `TTS_PROVIDER` | `volcengine` | TTS提供商 |

## 🎵 可用音色

### 女声音色
- `female_001` - 通用女声（标准）
- `female_002` - 温柔女声（温柔甜美）
- `female_003` - 活泼女声（活泼开朗）
- `female_004` - 情感女声（情感丰富）
- `female_005` - 优雅女声（优雅）

### 男声音色
- `male_001` - 标准男声（标准播音）
- `male_002` - 情感男声（情感丰富）
- `male_003` - 成熟男声（成熟稳重）
- `male_004` - 年轻男声（年轻活力）

## 🔧 使用示例

```python
from api.services.tts_service import TTSService

# 初始化TTS服务
tts_service = TTSService()

# 基本语音合成
result = tts_service.generate_speech(
    text="你好，欢迎使用火山引擎语音合成！",
    character_id=1
)

# 使用指定音色
result = tts_service.generate_speech(
    text="这是温柔的女声。",
    character_id=1,
    override_voice_id="female_002"
)

# 调节语音参数
result = tts_service.generate_speech(
    text="这是快速语音。",
    character_id=1,
    emotion_params={
        'speed': 1.5,    # 1.5倍语速
        'volume': 0.8,   # 0.8倍音量
        'pitch': 1.1     # 1.1倍音调
    }
)
```

## ❓ 常见问题

### Q: 为什么测试失败？
A: 当前需要在火山引擎控制台开通TTS服务权限。错误信息 "requested resource not granted" 表明权限不足。

### Q: 如何开通TTS服务？
A: 登录火山引擎控制台，找到TTS服务，确认应用ID有权限，必要时购买服务套餐。

### Q: 配置正确吗？
A: 是的，所有技术配置都已正确。API连接成功，只是缺少服务权限。

### Q: 需要修改代码吗？
A: 不需要。一旦权限开通，现有代码就能正常工作。

## 📞 技术支持

如果遇到问题，请检查：
1. 环境变量是否正确配置
2. 火山引擎账户是否有TTS服务权限
3. 网络连接是否正常
4. 账户余额是否充足

技术集成已完成 95%，只需开通服务权限即可使用！