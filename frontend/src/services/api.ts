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

// 创建角色
export const createCharacter = async (data: CreateCharacterRequest) => {
  try {
    const response = await api.post('/v1/characters/create', data);
    return response;
  } catch (error: any) {
    console.error('创建角色失败:', error);
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
    const response = await api.get(`/v1/characters/${characterId}/images`);
    return response;
  } catch (error: any) {
    console.error('获取角色图片失败:', error);
    throw error;
  }
};

// 初始化故事（触发初遇场景）
export const initializeStory = async (threadId: string, characterId: string) => {
  try {
    const response = await api.post('/v1/characters/initialize-story', {
      thread_id: threadId,
      character_id: characterId,
    });
    return response;
  } catch (error: any) {
    console.error('初始化故事失败:', error);
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

// 初始化游戏
export const initGame = async (data: GameInitRequest) => {
  try {
    const response = await api.post('/v1/game/init', data);
    return response;
  } catch (error: any) {
    console.error('初始化游戏失败:', error);
    throw error;
  }
};

// 处理玩家输入
export const processGameInput = async (data: GameInputRequest) => {
  try {
    const response = await api.post('/v1/game/input', data);
    return response;
  } catch (error: any) {
    console.error('处理玩家输入失败:', error);
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

export default api;
