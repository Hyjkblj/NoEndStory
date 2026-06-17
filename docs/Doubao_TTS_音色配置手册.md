# 豆包 TTS（Doubao / 火山引擎）音色配置手册

> **模型版本**：Seed-TTS 1.0 / Seed-TTS 2.0 / Seed-ICL 2.0（声音复刻）
> **数据来源**：火山引擎官方文档、JianYingAPI、LinkAI、Gitee volcano-engine-tts-sound-list
> **更新日期**：2026-06-17

---

## 一、豆包 TTS 模型概览

| 模型 | Resource ID | 音色 ID 格式 | 情绪控制方式 |
|------|------------|-------------|-------------|
| **Seed-TTS 2.0** | `seed-tts-2.0` | `BVxxx_streaming`、`*_uranus_bigtts`、`saturn_*` | `context_texts` 自然语言描述（V3 API） |
| **Seed-TTS 1.0** | `seed-tts-1.0` | `zh_*_mars_bigtts`、`zh_*_moon_bigtts`、`zh_*_saturn_bigtts` | `emotion` 参数枚举值（V1 API） |
| **Seed-ICL 2.0** | `seed-icl-2.0` | `S_xxxxxxxxx`（克隆音色） | `context_texts` 自然语言描述（V3 API） |

---

## 二、API 端点与认证

### 2.1 V1 HTTP API（当前项目使用）

```
POST https://openspeech.bytedance.com/api/v1/tts
```

**认证 Headers**：
```
Content-Type: application/json
Authorization: Bearer; {ACCESS_TOKEN}
```

**情绪控制**：通过 `emotion` 参数（仅限 1.0 模型的多情感音色）

### 2.2 V3 HTTP API（单向流式，推荐用于情绪控制）

```
POST https://openspeech.bytedance.com/api/v3/tts/unidirectional
```

**认证 Headers**：
```
Content-Type: application/json
X-Api-App-Id: {APP_ID}
X-Api-Access-Key: {ACCESS_KEY}
X-Api-Resource-Id: seed-tts-2.0  (或 seed-tts-1.0 / seed-icl-2.0)
```

**情绪控制**：通过 `additions` 字段中的 `context_texts`（自然语言描述）

---

## 三、情绪触发机制详解

### 3.1 方式一：V1 API `emotion` 参数（Seed-TTS 1.0 多情感音色）

**适用音色**：带 `_emo_` 标识的多情感音色（10个）

**请求示例**：
```json
{
    "app": {
        "appid": "{APP_ID}",
        "token": "{ACCESS_TOKEN}",
        "cluster": "volcano_tts"
    },
    "user": { "uid": "user_001" },
    "audio": {
        "voice_type": "zh_female_tianxinxiaomei_emo_v2_mars_bigtts",
        "encoding": "wav",
        "emotion": "happy"
    },
    "request": {
        "reqid": "tts_12345",
        "text": "今天真是太开心了！",
        "text_type": "plain",
        "operation": "query"
    }
}
```

**`emotion` 参数可选值**：

| 值 | 中文含义 | 值 | 中文含义 |
|----|---------|-----|---------|
| `happy` | 开心 | `sad` | 悲伤 |
| `angry` | 生气 | `surprised` | 惊讶 |
| `fear` | 恐惧 | `hate` | 厌恶 |
| `excited` | 激动 | `coldness` | 冷漠 |
| `neutral` | 中性 | `depressed` | 沮丧 |

### 3.2 方式二：V3 API `context_texts` 自然语言（Seed-TTS 2.0）

**适用音色**：所有 2.0 音色 + 克隆音色

**请求示例**：
```json
{
    "user": { "uid": "your-app-name" },
    "req_params": {
        "text": "你好呀，今天过得怎么样？",
        "speaker": "BV001_streaming",
        "audio_params": {
            "format": "mp3",
            "sample_rate": 24000
        },
        "additions": "{\"context_texts\":[\"用甜蜜撒娇的声音，像在跟男朋友撒娇，语调上扬很开心\"],\"model_type\":4}"
    }
}
```

> ⚠️ **关键注意**：`additions` 必须是**序列化后的 JSON 字符串**，不是 JSON 对象！传对象不会报错但情绪会静默失效。

**好的提示 vs 不好的提示**：

| ❌ 不好的提示（笼统，效果弱） | ✅ 好的提示（有场景、有细节，效果强） |
|---------------------------|----------------------------------|
| `"开心"` | `"用甜蜜撒娇的声音，像在跟男朋友撒娇，语调上扬很开心"` |
| `"用温柔的语气说"` | `"用ASMR悄悄话的声音，非常小声非常轻柔，像在耳边低语"` |
| `"悲伤"` | `"用哭泣的声音，边哭边说，很伤心，声音颤抖带着哽咽"` |
| `"生气"` | `"用愤怒的语气，提高音量，声音带着压抑的怒火"` |

### 3.3 方式三：逐句情感控制（高级）

对于一段包含多种情绪的文本，使用 `[情绪]` 标记拆分为逐句调用：

**输入文本**：
```
[开心]你好呀！今天天气真好。[温柔]辛苦了一天，快休息吧。[害羞]你别这么说嘛。
```

**处理流程**：
1. 按 `[情绪]文本` 格式解析
2. 每个片段单独调用 API，传入对应的 `context_texts`
3. 合并返回的音频片段
4. 展示时去掉标记

### 3.4 当前项目的情绪支持路径

当前项目 `voice_model_service.py` 使用 V1 HTTP API：

```python
# voice_model_service.py 第262-284行
request_data = {
    "app": { "appid": self.app_id, "token": self.access_token, "cluster": "volcano_tts" },
    "audio": {
        "voice_type": voice_id or "BV001_streaming",
        "encoding": "wav",
        "speed_ratio": kwargs.get('speed_ratio', 1.0),
        "volume_ratio": kwargs.get('volume_ratio', 1.0),
        "pitch_ratio": kwargs.get('pitch_ratio', 1.0)
        # ⚠️ 当前缺少 emotion 字段！
    },
    "request": { "reqid": "...", "text": cleaned_text, "text_type": "plain", "operation": "query" }
}
```

**问题**：`audio` 对象中**缺少 `emotion` 字段**，即使传入 `emotion_params`，V1 API 也只能调整 speed/volume/pitch，无法传递情绪值。

**修复方式**：在 `_synthesize_with_volcengine()` 中，将 `kwargs` 中的 `emotion` 值写入 `audio.emotion` 字段（仅对 `_emo_` 音色生效）。

---

## 四、支持情绪的音色列表

> 以下仅列出**明确支持情绪控制**的音色。分为两类：V3 API `context_texts` 自然语言控制（2.0 音色）和 V1 API `emotion` 参数控制（1.0 `_emo_` 音色）。

### 4.1 Seed-TTS 2.0 音色（76个，`BVxxx_streaming`）— 支持 `context_texts`

> 所有 2.0 音色均支持通过 V3 API 的 `context_texts` 自然语言描述进行情绪控制。
> 情绪触发方式：`"additions": "{\"context_texts\":[\"用撒娇甜蜜的语气，语调上扬很开心\"]}"`

#### 通用场景（12个）
| 编号 | 音色名 | Voice ID | 性别 |
|------|--------|----------|------|
| 1 | 通用女声 | `BV001_streaming` | 女 |
| 2 | 通用女声二 | `BV001_V2_streaming` | 女 |
| 3 | 通用男声 | `BV002_streaming` | 男 |
| 4 | 灿灿 | `BV700_streaming` | 女 |
| 5 | 灿灿二 | `BV700_V2_streaming` | 女 |
| 6 | 梓梓 | `BV406_streaming` | 女 |
| 7 | 梓梓二 | `BV406_V2_streaming` | 女 |
| 8 | 燃燃 | `BV407_streaming` | 女 |
| 9 | 燃燃二 | `BV407_V2_streaming` | 女 |
| 10 | 炀炀 | `BV705_streaming` | 女 |
| 11 | 擎苍 | `BV701_streaming` | 男 |
| 12 | 擎苍二 | `BV701_V2_streaming` | 男 |

#### 有声阅读（10个）
| 编号 | 音色名 | Voice ID | 性别 |
|------|--------|----------|------|
| 13 | 阳光青年 | `BV123_streaming` | 男 |
| 14 | 反卷青年 | `BV120_streaming` | 男 |
| 15 | 通用赘婿 | `BV119_streaming` | 男 |
| 16 | 古风少御 | `BV115_streaming` | 女 |
| 17 | 霸气青叔 | `BV107_streaming` | 男 |
| 18 | 质朴青年 | `BV100_streaming` | 男 |
| 19 | 温柔淑女 | `BV104_streaming` | 女 |
| 20 | 开朗青年 | `BV004_streaming` | 男 |
| 21 | 甜宠少御 | `BV113_streaming` | 女 |
| 22 | 儒雅青年 | `BV102_streaming` | 男 |

#### 智能助手（6个）
| 编号 | 音色名 | Voice ID | 性别 |
|------|--------|----------|------|
| 23 | 甜美小源 | `BV405_streaming` | 女 |
| 24 | 亲切女声 | `BV007_streaming` | 女 |
| 25 | 知性女声 | `BV009_streaming` | 女 |
| 26 | 诚诚 | `BV419_streaming` | 女 |
| 27 | 童童 | `BV415_streaming` | 女 |
| 28 | 亲切男声 | `BV008_streaming` | 男 |

#### 视频配音（17个）
| 编号 | 音色名 | Voice ID | 性别 |
|------|--------|----------|------|
| 29 | 译制片男声 | `BV408_streaming` | 男 |
| 30 | 懒小羊 | `BV426_streaming` | 男 |
| 31 | 清新文艺女声 | `BV428_streaming` | 女 |
| 32 | 鸡汤女声 | `BV403_streaming` | 女 |
| 33 | 智慧老者 | `BV158_streaming` | 男 |
| 34 | 慈爱姥姥 | `BV157_streaming` | 女 |
| 35 | 说唱小哥 | `BR001_streaming` | 男 |
| 36 | 活力解说男 | `BV410_streaming` | 男 |
| 37 | 小帅 | `BV411_streaming` | 男 |
| 38 | ⭐ 小帅多情感 | `BV437_streaming` | 男 |
| 39 | 小美 | `BV412_streaming` | 女 |
| 40 | 纨绔青年 | `BV159_streaming` | 男 |
| 41 | 直播一姐 | `BV418_streaming` | 男 |
| 42 | 沉稳解说男 | `BV142_streaming` | 男 |
| 43 | 潇洒青年 | `BV143_streaming` | 男 |
| 44 | 阳光男声 | `BV056_streaming` | 男 |
| 45 | 活泼女声 | `BV005_streaming` | 女 |
| 46 | 小萝莉 | `BV064_streaming` | 女 |

#### 特色/广告/新闻/教育（12个）
| 编号 | 音色名 | Voice ID | 性别 | 分类 |
|------|--------|----------|------|------|
| 47 | 奶气萌娃 | `BV051_streaming` | 男 | 特色 |
| 48 | 动漫海绵 | `BV063_streaming` | 男 | 特色 |
| 49 | 动漫海星 | `BV417_streaming` | 男 | 特色 |
| 50 | 动漫小新 | `BV050_streaming` | 男 | 特色 |
| 51 | 天才童声 | `BV061_streaming` | 男 | 特色 |
| 52 | 促销男声 | `BV401_streaming` | 男 | 广告 |
| 53 | 促销女声 | `BV402_streaming` | 女 | 广告 |
| 54 | 磁性男声 | `BV006_streaming` | 男 | 广告 |
| 55 | 新闻女声 | `BV011_streaming` | 女 | 新闻 |
| 56 | 新闻男声 | `BV012_streaming` | 男 | 新闻 |
| 57 | 知性姐姐 | `BV034_streaming` | 女 | 教育 |
| 58 | 温柔小哥 | `BV033_streaming` | 男 | 教育 |

#### 方言音色（17个）
| 编号 | 音色名 | Voice ID | 方言 | 性别 |
|------|--------|----------|------|------|
| 59 | 东北老铁 | `BV021_streaming` | 东北话 | 男 |
| 60 | 东北丫头 | `BV020_streaming` | 东北话 | 女 |
| 61 | 方言灿灿 | `BV704_streaming` | 方言 | 女 |
| 62 | 佟掌柜 | `BV210_streaming` | 陕西 | 女 |
| 63 | 沪上阿姨 | `BV217_streaming` | 上海 | 女 |
| 64 | 广西老表 | `BV213_streaming` | 广西 | 男 |
| 65 | 甜美台妹 | `BV025_streaming` | 台湾 | 女 |
| 66 | 台普男声 | `BV227_streaming` | 台湾 | 男 |
| 67 | 港剧男神 | `BV026_streaming` | 粤语 | 男 |
| 68 | 广东话 | `BV424_streaming` | 粤语 | 女 |
| 69 | 天津话 | `BV212_streaming` | 天津 | 男 |
| 70 | 郑州话 | `BV214_streaming` | 郑州 | 男 |
| 71 | 重庆话 | `BV019_streaming` | 重庆 | 男 |
| 72 | 四川话 | `BV221_streaming` | 四川 | 女 |
| 73 | 重庆话女 | `BV423_streaming` | 重庆 | 女 |
| 74 | 湖南话 | `BV226_streaming` | 湖南 | 女 |
| 75 | 长沙话 | `BV216_streaming` | 长沙 | 女 |

---

### 4.2 Seed-TTS 1.0 多情感音色（10个，`_emo_` 系列）— 支持 `emotion` 参数

> 通过 V1 API 的 `audio.emotion` 参数控制情绪，支持 10 种预定义情绪值。
> 情绪触发方式：在请求 `audio` 对象中添加 `"emotion": "happy"`
> 可选值：`happy`（开心）、`sad`（悲伤）、`angry`（生气）、`surprised`（惊讶）、`fear`（恐惧）、`hate`（厌恶）、`excited`（激动）、`coldness`（冷漠）、`neutral`（中性）、`depressed`（沮丧）

| 编号 | 音色名 | Voice ID | 性别 | 特点 |
|------|--------|----------|------|------|
| E1 | 甜心小美（多情感） | `zh_female_tianxinxiaomei_emo_v2_mars_bigtts` | 女 | 甜美少女音，情感丰富 |
| E2 | 高冷御姐（多情感） | `zh_female_gaolengyujie_emo_v2_mars_bigtts` | 女 | 高冷御姐，适合强势角色 |
| E3 | 傲娇霸总（多情感） | `zh_male_aojiaobazong_emo_v2_mars_bigtts` | 男 | 霸道总裁，适合强势男主 |
| E4 | 俊朗男友（多情感） | `zh_male_junlangnanyou_emo_v2_mars_bigtts` | 男 | 阳光俊朗，适合年轻男主 |
| E5 | 儒雅男友（多情感） | `zh_male_ruyayichen_emo_v2_mars_bigtts` | 男 | 儒雅温和，适合温柔男主 |
| E6 | 邻居阿姨（多情感） | `zh_female_linjuayi_emo_v2_mars_bigtts` | 女 | 亲切阿姨，适合长辈角色 |
| E7 | 优柔公子（多情感） | `zh_male_yourougongzi_emo_v2_mars_bigtts` | 男 | 忧郁温柔，适合文艺男主 |
| E8 | 京腔侃爷（多情感） | `zh_male_jingqiangkanye_emo_mars_bigtts` | 男 | 北京腔，幽默风趣 |
| E9 | 广州德哥（多情感） | `zh_male_guangzhoudege_emo_mars_bigtts` | 男 | 粤语，广州话 |
| E10 | 双节棍小哥（多情感） | `zh_male_zhoujielun_emo_v2_mars_bigtts` | 男 | 周杰伦风格 |

---

## 五、情绪控制完整方案对比

| 方案 | API 版本 | 音色范围 | 控制方式 | 精细度 | 使用复杂度 |
|------|---------|---------|----------|--------|-----------|
| **emotion 参数** | V1 | 仅 `_emo_` 音色（10个） | `"emotion": "happy"` | 低（10种预定义） | 低 |
| **context_texts** | V3 | 全部 2.0 音色 + 克隆音色 | `"context_texts":["用撒娇的语气..."]` | 高（自然语言任意描述） | 中 |
| **逐句情感控制** | V3 | 全部 2.0 音色 + 克隆音色 | `[开心]文本[悲伤]文本` 分句调用 | 极高（每句可变） | 高 |

---

## 六、当前项目 `preset_voices.py` 对照

当前 `backend/data/preset_voices.py` 仅收录了 24 个音色（12女+9男+1中性+2混音），其中仅 3 个标注了 `emotions` 列表：

| 当前预设 ID | 对应音色 | 标注情绪 |
|-----------|---------|---------|
| `female_004` | `BV004_streaming`（情感女声） | happy/sad/angry/surprised/neutral |
| `female_009` | `zh_female_aijia_emotion_bigtts`（艾佳情感版） | gentle/excited/melancholy/cheerful/neutral |
| `male_002` | `BV007_streaming`（情感男声） | confident/gentle/serious/cheerful/neutral |

**问题**：当前音色列表不完整（缺少 150+ 音色），情绪控制未接入（`emotion` 字段缺失），V3 `context_texts` 未使用。

---

## 七、建议的优化方向

1. **扩充 `preset_voices.py`**：按游戏角色需求精选 20-30 个音色（优先选用 `_emo_` 多情感音色 + 2.0 通用音色）
2. **V1 API 接入 `emotion` 参数**：为 `_emo_` 音色在请求中添加 `audio.emotion` 字段
3. **V3 API 接入 `context_texts`**：为所有 2.0 音色启用自然语言情绪控制
4. **前端展示情绪标签**：每张音色卡片标注支持的情绪类型
5. **前端情绪选择器**：在音色选择流程中增加情绪选择步骤
