import axios from 'axios';

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加token等认证信息
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    // 统一错误处理
    if (error.response) {
      switch (error.response.status) {
        case 401:
          // 未授权，清除token并跳转到登录页
          localStorage.removeItem('token');
          window.location.href = '/login';
          break;
        case 403:
          console.error('没有权限访问');
          break;
        case 404:
          console.error('请求的资源不存在');
          break;
        case 500:
          console.error('服务器错误');
          break;
        default:
          console.error('请求失败:', error.response.data?.message || error.message);
      }
    } else {
      console.error('网络错误:', error.message);
    }
    return Promise.reject(error);
  }
);

// 检查后端服务健康状态
export const checkServerHealth = async (): Promise<boolean> => {
  try {
    const response = await axios.get('/health', {
      timeout: 5000,
    });
    return response.status === 200;
  } catch (error) {
    console.error('后端服务不可用:', error);
    return false;
  }
};

// 创建角色请求接口
export interface CreateCharacterRequest {
  name: string;
  appearance: Record<string, any>;
  personality: Record<string, any>;
  background: Record<string, any>;
  gender?: string;
  age?: number;
  identity?: string;
  initial_scene?: string;
  initial_scene_prompt?: string;
}

// 创建角色（包含AI图片生成，需要较长超时时间）
export const createCharacter = async (data: CreateCharacterRequest) => {
  try {
    // 创建角色接口包含AI图片生成（组图3张），每张约 60–120 秒，总时长可能超过 5 分钟
    const response = await api.post('/v1/characters/create', data, {
      timeout: 180000,  // 420 秒（7 分钟），覆盖 3 张图 × 120s + 缓冲
    });
    return response;
  } catch (error: any) {
    console.error('创建角色失败:', error);
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      throw new Error('创建角色超时，图片生成可能需要更长时间。请查看后端终端是否已开始生图，并检查网络与生图服务后重试。');
    }
    throw error;
  }
};

// 获取角色信息
export const getCharacter = async (characterId: string) => {
  try {
    const response = await api.get(`/v1/characters/${characterId}`);
    return response;
  } catch (error: any) {
    console.error('获取角色信息失败:', error);
    throw error;
  }
};

// 获取角色图片列表
export const getCharacterImages = async (characterId: string) => {
  try {
    console.log('[API] 获取角色图片:', characterId);
    // 设置较长的超时时间（60秒），因为可能涉及图片处理
    const response = await api.get(`/v1/characters/${characterId}/images`, {
      timeout: 60000,  // 60秒超时
    });
    console.log('[API] 角色图片响应:', response);
    return response;
  } catch (error: any) {
    console.error('获取角色图片失败:', error);
    // 如果是超时错误，提供更友好的错误提示
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      console.warn('获取角色图片超时，但不影响游戏进行');
      // 不抛出错误，让调用方决定如何处理
    }
    throw error;
  }
};

// 去除角色图片背景（使用rembg高质量模型）
export interface RemoveBackgroundRequest {
  image_url?: string;  // 可选，如果不提供则使用角色最新图片
}

export interface RemoveBackgroundResponse {
  original_url: string;
  transparent_url: string;
  local_path: string;
}

export const removeCharacterBackground = async (characterId: string, imageUrl?: string, imageUrls?: string[], selectedIndex?: number) => {
  try {
    // 去除背景可能需要较长时间，设置更长超时（60秒）
    const response = await api.post<RemoveBackgroundResponse>(
      `/v1/characters/${characterId}/remove-background`,
      { 
        image_url: imageUrl,
        image_urls: imageUrls,
        selected_index: selectedIndex
      },
      { timeout: 60000 }  // 60秒超时
    );
    return response;
  } catch (error: any) {
    console.error('去除背景失败:', error);
    // 如果是超时错误，提供更友好的错误提示
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      throw new Error('去除背景超时，处理可能需要更长时间，请稍后重试');
    }
    throw error;
  }
};

// 初始化故事（触发初遇场景）
// 注意：此接口需要较长时间（AI生图、图片合成等），使用更长的超时时间
export const initializeStory = async (threadId: string, characterId: string, sceneId?: string, characterImageUrl?: string) => {
  try {
    // 参数验证
    if (!threadId || !characterId) {
      throw new Error(`缺少必要参数: threadId=${threadId}, characterId=${characterId}`);
    }
    
    // 确保characterId是字符串
    const characterIdStr = String(characterId);
    
    console.log('[API] 初始化故事请求参数:', {
      thread_id: threadId,
      character_id: characterIdStr,
      scene_id: sceneId || 'school',
      character_image_url: characterImageUrl || undefined
    });
    
    // 优化：由于图片生成已改为异步，可以降低超时时间
    const response = await api.post('/v1/characters/initialize-story', {
      thread_id: threadId,
      character_id: characterIdStr,  // 确保是字符串
      scene_id: sceneId || 'school',  // 默认使用school场景
      character_image_url: characterImageUrl || undefined,  // 用户选择的角色图片URL（透明背景）
    }, {
      timeout: 60000,  // 优化：从120秒降到60秒（图片异步生成，对话立即返回）
    });
    return response;
  } catch (error: any) {
    console.error('初始化故事失败:', error);
    if (error.response?.status === 422) {
      console.error('422验证错误详情:', error.response.data);
      const errorDetail = error.response?.data?.detail || error.response?.data?.message || '请检查请求参数';
      throw new Error(`参数验证失败: ${JSON.stringify(errorDetail)}`);
    }
    if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
      throw new Error('初始化故事超时，图片生成可能需要更长时间，请稍后重试');
    }
    throw error;
  }
};

// 获取场景列表
export const getScenes = async () => {
  try {
    console.log('[API] 请求场景列表: GET /api/v1/characters/scenes');
    const response = await api.get('/v1/characters/scenes');
    console.log('[API] 场景列表响应（拦截器处理后）:', response);
    console.log('[API] response.data:', response?.data);
    console.log('[API] response.data?.scenes:', response?.data?.scenes);
    return response;
  } catch (error: any) {
    console.error('获取场景列表失败:', error);
    console.error('错误详情:', {
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message
    });
    throw error;
  }
};

// 游戏相关接口

// 初始化游戏请求接口
export interface GameInitRequest {
  user_id?: string;
  game_mode: string;
  character_id: string;
}

// 游戏输入请求接口
export interface GameInputRequest {
  thread_id: string;
  user_input: string;
  user_id?: string;
  character_id?: string;  // 用于会话恢复
}

// 初始化游戏（可能需要较长时间，设置更长超时）
export const initGame = async (data: GameInitRequest) => {
  try {
    console.log('[API] 初始化游戏请求:', data);
    // 初始化游戏可能涉及AI生成，需要更长的超时时间
    const response = await api.post('/v1/game/init', data, {
      timeout: 60000,  // 60秒超时
    });
    console.log('[API] 初始化游戏响应（拦截器处理后）:', response);
    console.log('[API] response.data:', response?.data);
    return response;
  } catch (error: any) {
    console.error('初始化游戏失败:', error);
    // 如果是超时错误，提供更友好的错误提示
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      throw new Error('初始化游戏超时，请检查后端服务是否正常运行');
    }
    throw error;
  }
};

// 处理玩家输入
// 注意：此接口可能涉及AI生成和图片合成，需要较长的超时时间
export const processGameInput = async (data: GameInputRequest) => {
  try {
    console.log('[API] 处理玩家输入请求:', data);
    // 优化：由于图片生成已改为异步，可以降低超时时间
    const response = await api.post('/v1/game/input', data, {
      timeout: 90000,  // 优化：从120秒降到90秒（图片异步生成，对话立即返回）
    });
    console.log('[API] 处理玩家输入响应（拦截器处理后）:', response);
    return response;
  } catch (error: any) {
    console.error('处理玩家输入失败:', error);
    // 如果是超时错误，提供更友好的错误提示
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      throw new Error('处理玩家输入超时，AI生成可能需要更长时间。请稍后重试，或检查网络连接。');
    }
    // 如果是会话不存在的错误，尝试自动恢复
    if (error.response?.status === 400 && error.response?.data?.message?.includes('not found')) {
      console.warn('会话不存在，可能需要重新初始化');
    }
    throw error;
  }
};

// 检查结局
export const checkEnding = async (threadId: string) => {
  try {
    const response = await api.get(`/v1/game/check-ending/${threadId}`);
    return response;
  } catch (error: any) {
    console.error('检查结局失败:', error);
    throw error;
  }
};

// 触发结局
export const triggerEnding = async (threadId: string) => {
  try {
    const response = await api.post('/v1/game/trigger-ending', {
      thread_id: threadId,
    });
    return response;
  } catch (error: any) {
    console.error('触发结局失败:', error);
    throw error;
  }
};

// ========== TTS 音色相关 ==========

/** 预设音色项（与后端 preset_voices 一致） */
export interface PresetVoiceItem {
  id: string;
  name: string;
  description?: string;
  voice_id?: string | null;
  gender?: string;
  style?: string;
  preview_text?: string;
}

/** 获取预设音色列表；gender 可选：male | female | neutral，不传则返回所有 */
export const getPresetVoices = async (gender?: string) => {
  try {
    const response = await api.get(
      '/v1/tts/presets',
      gender ? { params: { gender } } : undefined
    ) as { data?: { gender?: string; voices?: PresetVoiceItem[] | Record<string, PresetVoiceItem[]> } };
    const data = response?.data;
    const voices = data?.voices;
    if (Array.isArray(voices)) return voices;
    if (voices && typeof voices === 'object' && !Array.isArray(voices)) {
      const r = voices as Record<string, PresetVoiceItem[]>;
      return [...(r.female || []), ...(r.male || []), ...(r.neutral || [])];
    }
    return [];
  } catch (error: any) {
    console.error('获取预设音色列表失败:', error);
    throw error;
  }
};

/** 使用角色音色合成语音（用于对话自动播放） */
export const generateSpeech = async (
  text: string,
  characterId: number | string,
  options?: { use_cache?: boolean; emotion_params?: Record<string, unknown> }
) => {
  try {
    const characterIdNum = typeof characterId === 'string' ? parseInt(characterId, 10) : characterId;
    if (Number.isNaN(characterIdNum)) throw new Error('无效的 character_id');
    const response = await api.post('/v1/tts/generate', {
      text: text.slice(0, 600),
      character_id: characterIdNum,
      use_cache: options?.use_cache ?? true,
      emotion_params: options?.emotion_params,
    }) as { data?: { audio_url: string; duration?: number; cached?: boolean } };
    const data = response?.data;
    return data ? { audio_url: data.audio_url, duration: data.duration, cached: data.cached } : null;
  } catch (error: any) {
    console.warn('TTS 合成失败:', error?.message || error);
    return null;
  }
};

/** 试听预设音色：返回试听音频 URL（45s 超时，避免后端鉴权失败时长时间等待） */
export const getVoicePreviewAudio = async (
  presetVoiceId: string,
  text?: string
): Promise<{ audio_url: string; duration?: number } | null> => {
  try {
    const response = await api.post(
      '/v1/tts/preview',
      {
        preset_voice_id: presetVoiceId,
        text: text || undefined,
      },
      { timeout: 45000 }
    ) as { data?: { audio_url: string; duration?: number } };
    const data = response?.data;
    return data ? { audio_url: data.audio_url, duration: data.duration } : null;
  } catch (error: any) {
    const msg = error?.message || String(error);
    const isTimeout = msg.includes('timeout') || error?.code === 'ECONNABORTED';
    console.warn('试听请求失败:', msg);
    if (isTimeout) {
      console.warn('试听超时：请检查网络或阿里云百炼（DashScope）语音服务账号状态与计费。');
    }
    return null;
  }
};

/** 设置角色音色配置 */
export const setVoiceConfig = async (params: {
  character_id: number;
  voice_type: string;
  preset_voice_id?: string | null;
  voice_design_description?: string | null;
  voice_params?: Record<string, unknown>;
}) => {
  try {
    const response = await api.post('/v1/tts/voice/config', params);
    return response;
  } catch (error: any) {
    console.error('设置音色配置失败:', error);
    throw error;
  }
};

export default api;
