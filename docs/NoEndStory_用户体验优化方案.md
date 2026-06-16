# NoEndStory 用户体验优化方案

> **编写日期**: 2026-06-15
> **范围**: P0 Bug + P1 高影响 + P2 中影响，共 16 项
> **预估总工时**: 2-3 天（单人）

---

## 〇、优化总览

| 优先级 | 数量 | 预估工时 | 说明 |
|--------|------|---------|------|
| 🔴 P0 | 1 | 5 分钟 | 代码 Bug，直接导致功能异常 |
| 🟡 P1 | 8 | 1.5-2 天 | 用户一定会注意到的体验问题 |
| 🟢 P2 | 7 | 0.5-1 天 | 部分用户会遇到的问题 |
| **合计** | **16** | **2-3 天** | |

---

## 🔴 P0 — 紧急修复

### P0-1: game.py 会话恢复缺 await

**问题**: `backend/api/routers/game.py` 第 127 行，`_process_with_session_lock()` 是 `async def`，但调用时没有 `await`。当会话过期触发自动恢复时，返回的是 coroutine 对象而非实际结果，前端收到垃圾数据。

**当前代码**:
```python
# game.py line 127
result = _process_with_session_lock(
    target_thread_id=request.thread_id,
    input_text=user_input,
    input_option_id=option_id
)
```

**修复方案**:
```python
result = await _process_with_session_lock(
    target_thread_id=request.thread_id,
    input_text=user_input,
    input_option_id=option_id
)
```

**验证**: 手动让会话过期（或删除 DB 中的 session），然后发送输入，确认返回正确的恢复响应而非 coroutine。

**预估**: 5 分钟

---

## 🟡 P1 — 高影响体验优化

### P1-1: 全面中文化

**问题**: 界面以中文为主，但多处出现英文文本，破坏沉浸感。

**涉及文件与具体修改**:

| 文件 | 位置 | 当前文本 | 修改为 |
|------|------|---------|--------|
| `FirstMeetingSelection.tsx` | 加载状态 | `Loading scenes...` | `加载场景中...` |
| `FirstMeetingSelection.tsx` | 错误状态 | `Backend is unavailable.` | `服务暂不可用，请稍后重试` |
| `FirstMeetingSelection.tsx` | 空状态 | `No scenes available.` | `暂无可选场景` |
| `FirstMeetingSelection.tsx` | 标题 | `First Meeting` | `初遇` |
| `FirstMeetingSelection.tsx` | 按钮 | `Choose` | `选择` |
| `FirstMeetingSelection.tsx` | 错误提示 | `Failed to load scenes.` | `加载场景失败` |
| `FirstMeetingSelection.tsx` | 回退场景 | `{ id: 'school', name: 'School' }` | `{ id: 'school', name: '学校' }` |
| `CharacterSetting.tsx` | 确认按钮 | `confirm` | `确认` |
| `CharacterSelection.tsx` | 选择按钮 | `CHOICE` | `选择` |
| `useGameInit.ts` | 成功消息 | `Save loaded.` | `存档已加载` |
| `SceneTransition.tsx` | 剧幕编号 | `第${actNumber}幕` | `第${chineseNum}幕` |

**SceneTransition 剧幕编号修复**:
```typescript
const CHINESE_NUMS = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十'];
// 使用: `第${CHINESE_NUMS[actNumber] || actNumber}幕`
```

**验证**: 遍历所有页面，确认无遗留英文。

**预估**: 1-2 小时

---

### P1-2: 游戏页面退出按钮

**问题**: 进入游戏后无法返回菜单，只能关闭浏览器。

**修改文件**: `frontend/src/pages/Game.tsx`

**方案**:

在游戏页面左上角添加一个半透明的返回按钮，点击时弹出确认对话框：

```tsx
// 添加状态
const [showExitConfirm, setShowExitConfirm] = useState(false);

// 在游戏页面左上角渲染
<div style={{ position: 'fixed', top: 16, left: 16, zIndex: 1001 }}>
  <Button
    type="text"
    icon={<ArrowLeftOutlined />}
    onClick={() => setShowExitConfirm(true)}
    style={{ color: 'rgba(255,255,255,0.6)', fontSize: 18 }}
  />
</div>

<Modal
  title="确认退出"
  open={showExitConfirm}
  onOk={() => {
    saveGameProgress();  // 保存当前进度
    navigate('/firststep');
  }}
  onCancel={() => setShowExitConfirm(false)}
  okText="保存并退出"
  cancelText="继续游戏"
>
  <p>退出将自动保存当前进度，下次可以继续。</p>
</Modal>
```

**键盘支持**: 同时监听 Escape 键触发退出确认：
```tsx
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') setShowExitConfirm(true);
  };
  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, []);
```

**预估**: 1 小时

---

### P1-3: 游戏结束画面

**问题**: 游戏结束时只有一个 toast 提示，无结算信息、无后续操作。

**修改文件**: `frontend/src/pages/Game.tsx`

**方案**:

当 `is_game_finished` 为 true 时，渲染一个全屏结束覆盖层：

```tsx
const GameEndOverlay = ({ ending, onRestart, onBack }) => (
  <div className="game-end-overlay">
    <div className="end-card">
      <h1>故事落幕</h1>
      <div className="ending-type">
        {ending.type === 'good_ending' && '✨ 美好结局'}
        {ending.type === 'bad_ending' && '💔 遗憾结局'}
        {ending.type === 'neutral_ending' && '🌅 平淡结局'}
        {ending.type === 'open_ending' && '🔮 开放结局'}
      </div>
      <p className="ending-desc">{ending.description}</p>
      <div className="final-states">
        <span>好感度: {ending.favorability}</span>
        <span>信任度: {ending.trust}</span>
        <span>敌意值: {ending.hostility}</span>
      </div>
      <div className="end-actions">
        <Button type="primary" onClick={onRestart}>再来一局</Button>
        <Button onClick={onBack}>返回菜单</Button>
      </div>
    </div>
  </div>
);
```

**数据来源**: 调用 `GET /api/v1/game/check-ending?thread_id=xxx` 获取结局信息。

**预估**: 2 小时（含样式）

---

### P1-4: 对话打字机效果

**问题**: 对话文字瞬间全部出现，叙事游戏应有的沉浸感缺失。

**修改文件**: `frontend/src/components/Game/GameDialogue.tsx`

**方案**:

用 `useState` + `useEffect` 实现逐字显示：

```tsx
const [displayedText, setDisplayedText] = useState('');
const [isTyping, setIsTyping] = useState(false);

useEffect(() => {
  if (!currentDialogue) {
    setDisplayedText('');
    return;
  }

  setIsTyping(true);
  setDisplayedText('');
  let i = 0;
  const interval = setInterval(() => {
    i++;
    setDisplayedText(currentDialogue.slice(0, i));
    if (i >= currentDialogue.length) {
      clearInterval(interval);
      setIsTyping(false);
    }
  }, 30); // 每 30ms 显示一个字符

  return () => clearInterval(interval);
}, [currentDialogue]);

// 点击跳过打字效果
const handleSkipTyping = () => {
  setDisplayedText(currentDialogue);
  setIsTyping(false);
};
```

**渲染**:
```tsx
<div className="dialogue-text" onClick={isTyping ? handleSkipTyping : undefined}>
  {displayedText}
  {isTyping && <span className="cursor">|</span>}
</div>
```

**流式集成**: 当 WebSocket 流式模式启用时，直接用 chunk 替代打字机效果（chunk 到达即显示）。

**预估**: 1-2 小时（含动画样式）

---

### P1-5: TTS 静音控制

**问题**: 音频自动播放，用户无法关闭或调节音量。

**修改文件**: `frontend/src/hooks/useGameTts.ts` + `frontend/src/pages/Game.tsx`

**方案**:

**Step 1**: 在 `useGameTts` 中添加静音状态：
```tsx
const [ttsEnabled, setTtsEnabled] = useState(() => {
  return localStorage.getItem('tts_enabled') !== 'false'; // 默认开启
});
const [ttsVolume, setTtsVolume] = useState(() => {
  return parseFloat(localStorage.getItem('tts_volume') || '0.8');
});

// 持久化
useEffect(() => {
  localStorage.setItem('tts_enabled', String(ttsEnabled));
}, [ttsEnabled]);

useEffect(() => {
  localStorage.setItem('tts_volume', String(ttsVolume));
}, [ttsVolume]);
```

**Step 2**: 在 `useEffect` 中检查静音：
```tsx
if (!ttsEnabled) return; // 静音时不播放
audio.volume = ttsVolume;
```

**Step 3**: 在 Game.tsx 右上角添加音频控制按钮：
```tsx
<div style={{ position: 'fixed', top: 16, right: 16, zIndex: 1001 }}>
  <Button
    type="text"
    icon={ttsEnabled ? <SoundOutlined /> : <AudioMutedOutlined />}
    onClick={() => setTtsEnabled(!ttsEnabled)}
    style={{ color: 'rgba(255,255,255,0.6)' }}
  />
</div>
```

**预估**: 1 小时

---

### P1-6: 对话历史可滚动

**问题**: 只显示当前台词，无法回看之前的对话。

**修改文件**: `frontend/src/components/Game/GameDialogue.tsx` + `frontend/src/pages/Game.tsx`

**方案**:

将 `messages` 数组渲染为可滚动的对话历史：

```tsx
<div className="dialogue-history" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
  {messages.map((msg, idx) => (
    <div key={idx} className={`message ${msg.role}`}>
      {msg.role === 'story_background' && (
        <div className="story-bg">{msg.content}</div>
      )}
      {msg.role === 'character' && (
        <div className="char-msg">
          <span className="speaker">{characterName}</span>
          <span className="text">{msg.content}</span>
        </div>
      )}
      {msg.role === 'user' && (
        <div className="user-msg">{msg.content}</div>
      )}
    </div>
  ))}
  <div ref={messagesEndRef} /> {/* 滚动锚点 */}
</div>
```

**样式**: 区分角色对话（左侧气泡）和玩家选择（右侧气泡），故事背景居中显示。

**预估**: 2 小时

---

### P1-7: 图片生成失败用户提示

**问题**: 角色创建成功但无头像，用户不知道发生了什么。

**修改文件**: `backend/api/routers/characters.py`

**方案**:

当图片生成失败时，在响应中明确告知：

```python
if image_urls:
    character_info['image_urls'] = image_urls
    character_info['image_warning'] = None
else:
    character_info['image_urls'] = []
    character_info['image_warning'] = '角色立绘生成失败，您可以稍后在角色设置中重新生成'
```

**前端处理**: `CharacterSetting.tsx` 收到响应后，如果 `image_warning` 存在，显示提示：
```tsx
if (data.image_warning) {
  message.warning(data.image_warning);
}
```

**预估**: 30 分钟

---

### P1-8: 设置页面功能实现

**问题**: 点击"设置"显示"功能开发中"，是死胡同。

**修改文件**: `frontend/src/pages/FirstStep.tsx`

**方案**:

实现基础设置面板，包含：

| 设置项 | 控件 | 存储 |
|--------|------|------|
| TTS 开关 | Switch | `localStorage.tts_enabled` |
| TTS 音量 | Slider (0-100) | `localStorage.tts_volume` |
| 文字速度 | Select (快/中/慢) | `localStorage.text_speed` |
| 清除存档 | Button + 确认弹窗 | 清除 localStorage |
| 版本号 | 文本显示 | 读取 `package.json` 版本 |

```tsx
const SettingsModal = ({ open, onClose }) => (
  <Modal title="设置" open={open} onCancel={onClose} footer={null}>
    <div className="settings-panel">
      <div className="setting-item">
        <span>语音播放</span>
        <Switch defaultChecked={ttsEnabled} onChange={setTtsEnabled} />
      </div>
      <div className="setting-item">
        <span>语音音量</span>
        <Slider defaultValue={ttsVolume * 100} onChange={v => setTtsVolume(v / 100)} />
      </div>
      <div className="setting-item">
        <span>文字速度</span>
        <Select defaultValue="medium">
          <Select.Option value="fast">快 (20ms/字)</Select.Option>
          <Select.Option value="medium">中 (30ms/字)</Select.Option>
          <Select.Option value="slow">慢 (50ms/字)</Select.Option>
        </Select>
      </div>
      <Divider />
      <div className="setting-item">
        <span>清除存档</span>
        <Button danger onClick={handleClearSave}>清除所有存档</Button>
      </div>
      <div className="version">v1.0.0</div>
    </div>
  </Modal>
);
```

**预估**: 2 小时

---

## 🟢 P2 — 中影响体验优化

### P2-1: 键盘快捷键

**问题**: 不能用数字键选选项、不能用 Enter 确认。

**修改文件**: `frontend/src/pages/Game.tsx`

**方案**:

```tsx
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (loading) return;

    // 数字键 1-3 选择选项
    const num = parseInt(e.key);
    if (num >= 1 && num <= 3 && currentOptions.length >= num) {
      handleOptionSelect(num - 1);
      return;
    }

    // Enter 确认（如果有选项且只有一个）
    if (e.key === 'Enter' && currentOptions.length === 1) {
      handleOptionSelect(0);
      return;
    }

    // Escape 触发退出确认
    if (e.key === 'Escape') {
      setShowExitConfirm(true);
    }
  };

  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, [loading, currentOptions, handleOptionSelect]);
```

**UI 提示**: 在选项按钮上显示快捷键提示：
```tsx
<Button>{idx + 1}. {option.text}</Button>
```

**预估**: 30 分钟

---

### P2-2: Loading 进度感

**问题**: 只显示"思考中..."，10-30 秒等待无任何反馈。

**修改文件**: `frontend/src/pages/Game.tsx`

**方案**:

将静态文字替换为渐进式提示：

```tsx
const LOADING_TIPS = [
  '正在构思剧情...',
  '角色正在思考...',
  '整理对话中...',
  '即将呈现...',
];

const [tipIndex, setTipIndex] = useState(0);

useEffect(() => {
  if (!loading) { setTipIndex(0); return; }
  const timer = setInterval(() => {
    setTipIndex(prev => (prev + 1) % LOADING_TIPS.length);
  }, 3000);
  return () => clearInterval(timer);
}, [loading]);
```

同时添加一个简单的动画 spinner 或进度条（CSS 动画，非真实进度）。

**预估**: 30 分钟

---

### P2-3: 剧幕编号中文化

**问题**: "第一幕" vs "第2幕"，中阿数字混杂。

**修改文件**: `frontend/src/components/Game/SceneTransition.tsx`

**方案**:

```typescript
const CHINESE_NUMS = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十'];

function toChineseActNumber(n: number): string {
  if (n <= 10) return CHINESE_NUMS[n] || String(n);
  return String(n); // 超过 10 用阿拉伯数字
}

// 使用: `第${toChineseActNumber(actNumber)}幕`
```

**预估**: 10 分钟

---

### P2-4: TTS 配置持久化

**问题**: 服务重启后角色语音配置丢失。

**修改文件**: `backend/api/services/tts_service.py`

**方案**:

将 `voice_configs` 从内存 dict 改为读写 PostgreSQL：

```python
# 新增 migration: 008_voice_configs.py
# CREATE TABLE voice_configs (
#   character_id INTEGER PRIMARY KEY,
#   voice_id VARCHAR(100),
#   speed FLOAT DEFAULT 1.0,
#   volume FLOAT DEFAULT 1.0,
#   pitch FLOAT DEFAULT 1.0,
#   updated_at TIMESTAMP DEFAULT NOW()
# );

def get_voice_config(self, character_id: int) -> Optional[Dict]:
    # 优先从 DB 读取，降级到内存
    with self.db_manager.get_session() as session:
        row = session.query(VoiceConfigModel).filter_by(character_id=character_id).first()
        if row:
            return {'voice_id': row.voice_id, 'speed': row.speed, ...}
    return self._memory_configs.get(character_id)

def save_voice_config(self, character_id: int, config: Dict):
    with self.db_manager.get_session() as session:
        existing = session.query(VoiceConfigModel).filter_by(character_id=character_id).first()
        if existing:
            existing.voice_id = config.get('voice_id')
            # ... update fields
        else:
            session.add(VoiceConfigModel(character_id=character_id, **config))
    self._memory_configs[character_id] = config  # 同步缓存
```

**预估**: 1 小时（含 migration）

---

### P2-5: 清理 console.log

**问题**: 生产环境浏览器控制台可见调试日志。

**涉及文件**:
- `frontend/src/pages/CharacterSelection.tsx` (6+ 处)
- `frontend/src/pages/FirstMeetingSelection.tsx` (3+ 处)
- `frontend/src/pages/Game.tsx` (2+ 处)

**方案**:

全部替换为条件式日志或删除：

```typescript
// 方案 A: 删除（推荐，生产环境不需要）
// 直接删除所有 console.log 语句

// 方案 B: 条件式（保留调试能力）
const DEBUG = import.meta.env.DEV;
if (DEBUG) console.log('[角色选择]...', data);
```

**验证**: 全局搜索 `console.log`，确认前端代码中无遗留。

**预估**: 20 分钟

---

### P2-6: 错误消息脱敏

**问题**: `str(e)` 可能泄露文件路径、DB 连接信息。

**修改文件**: `backend/api/routers/characters.py`, `backend/api/routers/game.py`

**方案**:

统一使用安全的错误消息：

```python
# Before
raise HTTPException(status_code=500, detail=f"创建角色失败: {str(e)}")

# After
logger.error(f"创建角色失败: {e}", exc_info=True)  # 日志保留完整错误
raise HTTPException(status_code=500, detail="创建角色失败，请稍后重试")  # 用户只看到通用消息
```

逐文件检查所有 `str(e)` 拼接，替换为通用提示。

**预估**: 30 分钟

---

### P2-7: 删除 useWebSocket 死代码

**问题**: `useWebSocket.ts` 从未被导入使用，增加打包体积。

**方案**:

```bash
# 确认无引用
grep -r "useWebSocket" frontend/src/ --include="*.ts" --include="*.tsx"
# 如果只在自身文件中出现，直接删除
rm frontend/src/hooks/useWebSocket.ts
```

**注意**: 如果后续计划启用 WebSocket 模式，可以保留但加 `@deprecated` 注释。

**预估**: 5 分钟

---

## 附录：实施顺序建议

```
Day 1（上午）:
  P0-1  await 修复                              5 min
  P1-1  全面中文化                               1-2 h
  P2-3  剧幕编号中文化                           10 min
  P2-5  清理 console.log                         20 min
  P2-6  错误消息脱敏                              30 min

Day 1（下午）:
  P1-2  退出按钮 + Escape 键                     1 h
  P1-5  TTS 静音控制                              1 h
  P2-1  键盘快捷键                                30 min

Day 2（上午）:
  P1-4  打字机效果                                1-2 h
  P2-2  Loading 进度感                            30 min
  P1-7  图片生成失败提示                           30 min

Day 2（下午）:
  P1-3  游戏结束画面                              2 h
  P1-6  对话历史可滚动                            2 h

Day 3（上午）:
  P1-8  设置页面                                  2 h
  P2-4  TTS 配置持久化                            1 h
  P2-7  删除死代码                                5 min
```

---

> **文档版本**: v1.0
> **最后更新**: 2026-06-15
