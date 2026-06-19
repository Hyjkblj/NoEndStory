/** 游戏相关常量定义 */

// ========== 加载提示 ==========

export const LOADING_TIPS = [
  '正在构思剧情...',
  '角色正在思考...',
  '整理对话中...',
  '即将呈现...',
];

// ========== 结局类型标签（对齐后端 classify_ending） ==========

export const ENDING_TYPE_LABELS: Record<string, string> = {
  happy_ending: '甜蜜结局',      // favorability >= 70, hostility <= 20
  bad_ending: '遗憾结局',        // hostility >= 50 or favorability <= 20
  neutral_ending: '暧昧未满',    // favorability >= 40, trust >= 50
  open_ending: '未完待续',       // 默认
};

// ========== 关系指标标签 ==========

export const RELATIONSHIP_LABELS: Array<{ key: string; label: string; tone: 'warm' | 'soft' | 'tense' | 'neutral' }> = [
  { key: 'favorability', label: '好感', tone: 'warm' },
  { key: 'trust', label: '信任', tone: 'soft' },
  { key: 'dependence', label: '依赖', tone: 'warm' },
  { key: 'emotion', label: '心绪', tone: 'soft' },
  { key: 'stress', label: '压力', tone: 'tense' },
];

// ========== 音色类型标签 ==========

export const VOICE_TYPE_LABELS = [
  { key: 'female' as const, title: '多情感女声' },
  { key: 'male' as const, title: '多情感男声' },
];

// ========== 结局描述模板（对齐后端 classify_ending） ==========

export const ENDING_DESCRIPTIONS: Record<string, string> = {
  happy_ending: '你们把一段关系慢慢推近，许多未说出口的话终于有了回应。',
  bad_ending: '有些靠近停在了半路，但那些选择依然成为这段故事真实的痕迹。',
  neutral_ending: '心跳和不安交错在一起，这段关系停在了仍需确认的地方。',
  open_ending: '这段故事暂时收束，但你们之间仍留下了可以被重新打开的余温。',
};

// ========== 错误消息 ==========

export const ERROR_MESSAGES = {
  GAME_SESSION_EXPIRED: '游戏会话已过期',
  GAME_SESSION_RECOVERING: '游戏会话已过期。正在尝试恢复...',
  GAME_SESSION_RECOVERED: '游戏会话已恢复，请重新选择选项',
  GAME_SESSION_RECOVER_FAILED: '游戏会话已过期且无法恢复，请返回重新开始游戏',
  GAME_SESSION_NOT_FOUND: '游戏会话已过期，请返回重新开始游戏',
  PROCESS_OPTION_FAILED: '处理选项失败，请稍后重试',
  PROCESS_OPTION_TIMEOUT: '处理选项超时，AI生成可能需要更长时间。请稍后重试，或检查网络连接。',
  VOICE_LIST_NOT_FOUND: '未获取到多情感音色列表，请检查后端服务',
  VOICE_SERVICE_UNAVAILABLE: 'TTS 服务暂不可用，但您仍可选择音色（游戏中使用时需确保 TTS 服务已启用）',
  VOICE_LIST_LOAD_FAILED: '获取音色列表失败，请检查后端服务',
  VOICE_PREVIEW_FAILED: '试听音频播放失败',
  VOICE_PREVIEW_UNAVAILABLE: '试听功能暂不可用（TTS 服务未启用），但您仍可选择此音色',
  CHARACTER_IMAGE_LOAD_FAILED: '获取角色图片失败',
  CHARACTER_ID_INVALID: '角色ID无效，跳过图片加载',
} as const;

// ========== 成功消息 ==========

export const SUCCESS_MESSAGES = {
  GAME_SESSION_RECOVERED: '游戏会话已恢复',
} as const;

// ========== 默认值 ==========

export const DEFAULT_VALUES = {
  CHARACTER_NAME: '角色',
  ENDING_TITLE: '故事落幕',
  LOADING_MESSAGE: '正在加载角色...',
} as const;

// ========== 打字机效果速度 ==========

export const TYPING_SPEED = {
  NORMAL: 30,
  FAST: 15,
  SLOW: 50,
} as const;
