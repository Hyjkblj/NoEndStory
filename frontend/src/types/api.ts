/**
 * 与后端 API 响应格式一致：{ code, message, data }
 * 拦截器已返回 response.data，故请求成功时得到的就是该结构
 */
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data?: T;
}

/**
 * 从后端统一响应体中取出 data，若 code !== 200 则抛出
 */
export function unwrapResponse<T>(body: ApiResponse<T> | null | undefined): T {
  if (body == null) {
    throw new Error('请求无响应');
  }
  if (body.code !== 200) {
    throw new Error(body.message || '请求失败');
  }
  return body.data as T;
}

// ---------- 后端接口返回的 data 类型 ----------

export interface CreateCharacterData {
  character_id?: number;
  name?: string;
  image_url?: string;
  image_urls?: string[];
  [key: string]: unknown;
}

export interface GameInitData {
  thread_id: string;
  user_id?: string;
  game_mode?: string;
}

export interface GameInputData {
  thread_id?: string;
  scene?: string;
  character_dialogue?: string;
  player_options?: { id: number; text: string; type: string; state_changes?: Record<string, number> }[];
  composite_image_url?: string;
  scene_image_url?: string;
  is_game_finished?: boolean;
  story_background?: string;
}

export interface ScenesData {
  scenes: Array<{ id: string; name?: string; description?: string; [key: string]: unknown }>;
}

export interface CharacterImagesData {
  images: string[];
}

export interface RemoveBackgroundData {
  original_url: string;
  transparent_url: string;
  local_path: string;
}
