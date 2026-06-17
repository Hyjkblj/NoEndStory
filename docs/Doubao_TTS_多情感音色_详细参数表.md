# 豆包 TTS 多情感音色详细配置手册

> 9 个多情感音色的完整 Voice ID、参数说明及 API 调用示例
> TTS 提供商：火山引擎（VolcEngine Doubao TTS）
> 模型版本：Seed-TTS 1.0（多情感系列）
> API 端点：`POST https://openspeech.bytedance.com/api/v1/tts`

---

## 一、9 个多情感音色 Voice ID 对照表

| # | UI 名称 | API Voice ID | 性别 | 多情感数 | 风格 |
|---|--------|-------------|------|---------|------|
| 1 | 冷酷哥哥 | `zh_male_aojiaobazong_emo_v2_mars_bigtts` | 男 | +8 | 高冷傲娇 |
| 2 | 京腔侃爷 | `zh_male_jingqiangkanye_emo_mars_bigtts` | 男 | +5 | 北京腔、风趣 |
| 3 | 优柔公子 | `zh_male_yourougongzi_emo_v2_mars_bigtts` | 男 | +7 | 温润儒雅 |
| 4 | 儒雅男友 | `zh_male_junlangnanyou_emo_v2_mars_bigtts` | 男 | +7 | 阳光俊朗 |
| 5 | 阳光青年 | `zh_male_ruyayichen_emo_v2_mars_bigtts` | 男 | +7 | 阳光直率 |
| 6 | 高冷御姐 | `zh_female_gaolengyujie_emo_v2_mars_bigtts` | 女 | +9 | 高冷成熟 |
| 7 | 柔美女友 | `zh_female_linjuayi_emo_v2_mars_bigtts` | 女 | +9 | 温柔亲切 |
| 8 | 爽快思思 | `zh_female_tianxinxiaomei_emo_v2_mars_bigtts` | 女 | +7 | 阳光爽快 |
| 9 | 魅力女友 | `zh_female_sajiaonvyou_moon_bigtts` | 女 | +3 | 轻熟妩媚 |

> ⚠️ 音色 #9（魅力女友）的 `_emo_` 变体 ID 待确认，上表给出的是基础 moon 系列 ID，可能有独立的 `_emo_v2_mars_bigtts` 版本。

---

## 二、API 请求完整参数

### 2.1 请求格式

```
POST https://openspeech.bytedance.com/api/v1/tts
Content-Type: application/json
Authorization: Bearer; {ACCESS_TOKEN}
```

### 2.2 完整参数

```json
{
    "app": {
        "appid": "{APP_ID}",
        "token": "{ACCESS_TOKEN}",
        "cluster": "volcano_tts"
    },
    "user": {
        "uid": "user_001"
    },
    "audio": {
        "voice_type": "zh_male_aojiaobazong_emo_v2_mars_bigtts",
        "emotion": "happy",
        "encoding": "wav",
        "speed_ratio": 1.0,
        "volume_ratio": 1.0,
        "pitch_ratio": 1.0
    },
    "request": {
        "reqid": "tts_{timestamp}_{hash}",
        "text": "你好呀，今天天气真不错！",
        "text_type": "plain",
        "operation": "query"
    }
}
```

### 2.3 参数说明

| 参数路径 | 类型 | 必填 | 说明 |
|---------|------|------|------|
| `app.appid` | string | ✅ | 火山引擎应用 APP ID |
| `app.token` | string | ✅ | 火山引擎 Access Token |
| `app.cluster` | string | ✅ | 固定值 `volcano_tts` |
| `user.uid` | string | ✅ | 用户标识，任意字符串 |
| `audio.voice_type` | string | ✅ | 音色 Voice ID（见第一章） |
| `audio.emotion` | string | 选填 | 情绪值（见第三章） |
| `audio.encoding` | string | ✅ | 输出格式：`wav` / `mp3` / `ogg` / `pcm` |
| `audio.speed_ratio` | float | 选填 | 语速 0.5~2.0，默认 1.0 |
| `audio.volume_ratio` | float | 选填 | 音量 0.1~2.0，默认 1.0 |
| `audio.pitch_ratio` | float | 选填 | 音调 0.5~2.0，默认 1.0 |
| `request.reqid` | string | ✅ | 请求 ID，建议用时间戳+哈希保证唯一 |
| `request.text` | string | ✅ | 待合成文本（最大 5000 字符） |
| `request.text_type` | string | ✅ | 文本类型：`plain`（纯文本） |
| `request.operation` | string | ✅ | 固定值 `query` |

---

## 三、情绪参数（`emotion`）完整可选值

> 仅多情感 `_emo_` 音色支持此参数，其他音色传入无效。

| 值 | 中文 | 说明 |
|----|------|------|
| `happy` | 开心 | 语调上扬，轻快愉悦 |
| `sad` | 悲伤 | 语调下沉，沉重缓慢 |
| `angry` | 生气 | 语速加快，音量提高 |
| `surprised` | 惊讶 | 语调起伏大 |
| `fear` | 恐惧 | 声音颤抖 |
| `hate` | 厌恶 | 语气冷淡带反感 |
| `excited` | 激动 | 语速快，音量高 |
| `coldness` | 冷漠 | 平淡无感情 |
| `neutral` | 中性 | 自然状态（默认） |
| `depressed` | 沮丧 | 低沉缓慢 |

---

## 四、每个音色的详细配置卡片

### 1. 冷酷哥哥

| 属性 | 值 |
|------|-----|
| **Voice ID** | `zh_male_aojiaobazong_emo_v2_mars_bigtts` |
| **性别** | 男 |
| **模型** | Seed-TTS 1.0 |
| **多情感** | 10 种（happy/sad/angry/surprised/fear/hate/excited/coldness/neutral/depressed） |
| **语速范围** | 0.5 ~ 2.0 |
| **音量范围** | 0.1 ~ 2.0 |
| **音调范围** | 0.5 ~ 2.0 |
| **编码格式** | wav / mp3 / ogg / pcm |
| **风格** | 声线磁性干净的高冷青年，性格傲娇，待人疏离 |
| **推荐情绪** | happy/coldness/angry/neutral |

**试听文本建议**：
- 开心：「哼，今天心情还不错，算你走运。」
- 冷漠：「随便你怎么想，我无所谓。」

---

### 2. 京腔侃爷

| 属性 | 值 |
|------|-----|
| **Voice ID** | `zh_male_jingqiangkanye_emo_mars_bigtts` |
| **性别** | 男 |
| **模型** | Seed-TTS 1.0 |
| **多情感** | 10 种 |
| **语速范围** | 0.5 ~ 2.0 |
| **音量范围** | 0.1 ~ 2.0 |
| **音调范围** | 0.5 ~ 2.0 |
| **编码格式** | wav / mp3 / ogg / pcm |
| **风格** | 声音低沉带有京腔，风趣痞痞青年 |
| **推荐情绪** | happy/excited/neutral/surprised |

---

### 3. 优柔公子

| 属性 | 值 |
|------|-----|
| **Voice ID** | `zh_male_yourougongzi_emo_v2_mars_bigtts` |
| **性别** | 男 |
| **模型** | Seed-TTS 1.0 |
| **多情感** | 10 种 |
| **语速范围** | 0.5 ~ 2.0 |
| **音量范围** | 0.1 ~ 2.0 |
| **音调范围** | 0.5 ~ 2.0 |
| **编码格式** | wav / mp3 / ogg / pcm |
| **风格** | 声音低沉温柔的温润公子，儒雅有书卷气 |
| **推荐情绪** | sad/gentle/neutral/calm |

---

### 4. 儒雅男友

| 属性 | 值 |
|------|-----|
| **Voice ID** | `zh_male_junlangnanyou_emo_v2_mars_bigtts` |
| **性别** | 男 |
| **模型** | Seed-TTS 1.0 |
| **多情感** | 10 种 |
| **语速范围** | 0.5 ~ 2.0 |
| **音量范围** | 0.1 ~ 2.0 |
| **音调范围** | 0.5 ~ 2.0 |
| **编码格式** | wav / mp3 / ogg / pcm |
| **风格** | 明亮少年感的俊朗公子，阳光直爽，充满活力 |
| **推荐情绪** | happy/excited/surprised/neutral |

---

### 5. 阳光青年

| 属性 | 值 |
|------|-----|
| **Voice ID** | `zh_male_ruyayichen_emo_v2_mars_bigtts` |
| **性别** | 男 |
| **模型** | Seed-TTS 1.0 |
| **多情感** | 10 种 |
| **语速范围** | 0.5 ~ 2.0 |
| **音量范围** | 0.1 ~ 2.0 |
| **音调范围** | 0.5 ~ 2.0 |
| **编码格式** | wav / mp3 / ogg / pcm |
| **风格** | 充满少年感的阳光大学生，直率活泼，有点爱说教 |
| **推荐情绪** | happy/excited/neutral/surprised |

---

### 6. 高冷御姐

| 属性 | 值 |
|------|-----|
| **Voice ID** | `zh_female_gaolengyujie_emo_v2_mars_bigtts` |
| **性别** | 女 |
| **模型** | Seed-TTS 1.0 |
| **多情感** | 10 种 |
| **语速范围** | 0.5 ~ 2.0 |
| **音量范围** | 0.1 ~ 2.0 |
| **音调范围** | 0.5 ~ 2.0 |
| **编码格式** | wav / mp3 / ogg / pcm |
| **风格** | 高冷成熟音御姐，气质妩媚，行事利落有气场 |
| **推荐情绪** | coldness/angry/neutral/surprised |

---

### 7. 柔美女友

| 属性 | 值 |
|------|-----|
| **Voice ID** | `zh_female_linjuayi_emo_v2_mars_bigtts` |
| **性别** | 女 |
| **模型** | Seed-TTS 1.0 |
| **多情感** | 10 种 |
| **语速范围** | 0.5 ~ 2.0 |
| **音量范围** | 0.1 ~ 2.0 |
| **音调范围** | 0.5 ~ 2.0 |
| **编码格式** | wav / mp3 / ogg / pcm |
| **风格** | 声音甜美的知心姐姐，温柔亲切，善于倾听 |
| **推荐情绪** | happy/sad/gentle/neutral |

---

### 8. 爽快思思

| 属性 | 值 |
|------|-----|
| **Voice ID** | `zh_female_tianxinxiaomei_emo_v2_mars_bigtts` |
| **性别** | 女 |
| **模型** | Seed-TTS 1.0 |
| **多情感** | 10 种 |
| **语速范围** | 0.5 ~ 2.0 |
| **音量范围** | 0.1 ~ 2.0 |
| **音调范围** | 0.5 ~ 2.0 |
| **编码格式** | wav / mp3 / ogg / pcm |
| **风格** | 声音温暖的直爽小妹，阳光热情，为人爽快 |
| **推荐情绪** | happy/excited/surprised/neutral |

---

### 9. 魅力女友

| 属性 | 值 |
|------|-----|
| **Voice ID** | `zh_female_sajiaonvyou_moon_bigtts`（待确认是否有 `_emo_v2_mars_bigtts` 版本） |
| **性别** | 女 |
| **模型** | Seed-TTS 1.0（moon 系列） |
| **多情感** | +3（情绪支持有限，需确认） |
| **语速范围** | 0.5 ~ 2.0 |
| **音量范围** | 0.1 ~ 2.0 |
| **音调范围** | 0.5 ~ 2.0 |
| **编码格式** | wav / mp3 / ogg / pcm |
| **风格** | 嗲软轻飘的轻熟美人，妩媚有耐心，温柔勾人 |
| **推荐情绪** | happy/sad/neutral |

---

## 五、Python 调用示例

```python
import requests
import json
import time
import hashlib

APP_ID = "your_app_id"
ACCESS_TOKEN = "your_access_token"
VOICE_ID = "zh_male_aojiaobazong_emo_v2_mars_bigtts"  # 冷酷哥哥
TEXT = "哼，今天心情还不错，算你走运。"

reqid = f"tts_{int(time.time())}_{hash(TEXT) % 10000}"

payload = {
    "app": {
        "appid": APP_ID,
        "token": ACCESS_TOKEN,
        "cluster": "volcano_tts"
    },
    "user": {"uid": "user_001"},
    "audio": {
        "voice_type": VOICE_ID,
        "emotion": "happy",
        "encoding": "wav",
        "speed_ratio": 1.0,
        "volume_ratio": 1.0,
        "pitch_ratio": 1.0
    },
    "request": {
        "reqid": reqid,
        "text": TEXT,
        "text_type": "plain",
        "operation": "query"
    }
}

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer; {ACCESS_TOKEN}"
}

resp = requests.post(
    "https://openspeech.bytedance.com/api/v1/tts",
    headers=headers,
    json=payload,
    timeout=30
)

data = resp.json()
if data.get("code") == 3000:
    import base64
    audio_bytes = base64.b64decode(data["data"])
    with open("output.wav", "wb") as f:
        f.write(audio_bytes)
    print("✅ 语音合成成功 → output.wav")
else:
    print(f"❌ 错误: code={data.get('code')}, msg={data.get('message')}")
```

---

## 六、curl 调用示例

```bash
curl -X POST "https://openspeech.bytedance.com/api/v1/tts" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer; {ACCESS_TOKEN}" \
  -d '{
    "app": {
      "appid": "{APP_ID}",
      "token": "{ACCESS_TOKEN}",
      "cluster": "volcano_tts"
    },
    "user": {"uid": "user_001"},
    "audio": {
      "voice_type": "zh_female_gaolengyujie_emo_v2_mars_bigtts",
      "emotion": "happy",
      "encoding": "wav",
      "speed_ratio": 1.0,
      "volume_ratio": 1.0,
      "pitch_ratio": 1.0
    },
    "request": {
      "reqid": "tts_20260617_0001",
      "text": "今天天气真不错呢！",
      "text_type": "plain",
      "operation": "query"
    }
  }'
```

---

## 七、参数速查表

| 参数 | 类型 | 范围/可选值 | 默认值 |
|------|------|------------|--------|
| `voice_type` | string | 见第一章 Voice ID 列表 | — |
| `emotion` | string | `happy` `sad` `angry` `surprised` `fear` `hate` `excited` `coldness` `neutral` `depressed` | 无（不用时省略） |
| `encoding` | string | `wav` `mp3` `ogg` `pcm` | `wav` |
| `speed_ratio` | float | 0.5 ~ 2.0 | 1.0 |
| `volume_ratio` | float | 0.1 ~ 2.0 | 1.0 |
| `pitch_ratio` | float | 0.5 ~ 2.0 | 1.0 |
| `text` | string | 1 ~ 5000 字符 | — |
| `text_type` | string | `plain` | — |
| `operation` | string | `query` | — |
