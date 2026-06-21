import axios from 'axios';
import type { PlayerOption } from '@/types/game';

const GUEST_ENDING_LIMIT_CODE = 'GUEST_ENDING_LIMIT';

export class GuestEndingLimitError extends Error {
  code = GUEST_ENDING_LIMIT_CODE;
  hint?: string;

  constructor(message = '这次游客体验已经完成，24小时后可再次开启。注册账号可解锁更多旅程。', hint?: string) {
    super(message);
    this.name = 'GuestEndingLimitError';
    this.hint = hint;
  }
}

export const isGuestEndingLimitError = (error: unknown): error is GuestEndingLimitError =>
  error instanceof GuestEndingLimitError ||
  (error instanceof Error && error.name === 'GuestEndingLimitError');

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

type ApiErrorData = {
  code?: string | number;
  error_code?: string;
  message?: string;
  detail?: unknown;
  hint?: string;
  [key: string]: unknown;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const unwrapResponseData = <T>(response: unknown): T => {
  if (isRecord(response) && 'data' in response) {
    return (response as { data: T }).data;
  }
  return response as T;
};

const getErrorStatus = (error: unknown): number | undefined =>
  axios.isAxiosError(error) ? error.response?.status : undefined;

const getErrorData = (error: unknown): ApiErrorData | undefined => {
  if (!axios.isAxiosError(error)) return undefined;
  const data = error.response?.data;
  return isRecord(data) ? (data as ApiErrorData) : undefined;
};

const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) return getErrorData(error)?.message ?? error.message;
  if (error instanceof Error) return error.message;
  return String(error);
};

const getHeaderValue = (headers: unknown, key: string): string | undefined => {
  const lowerKey = key.toLowerCase();
  if (isRecord(headers)) {
    const getter = headers.get;
    if (typeof getter === 'function') {
      const value = getter.call(headers, key) ?? getter.call(headers, lowerKey);
      return typeof value === 'string' ? value : undefined;
    }

    const value = headers[key] ?? headers[lowerKey];
    return typeof value === 'string' ? value : undefined;
  }
  return undefined;
};

const getGuestEndingLimitError = (data: unknown, headers?: unknown): GuestEndingLimitError | null => {
  const headerCode = getHeaderValue(headers, 'X-Error-Code');
  const headerLimit = getHeaderValue(headers, 'X-Guest-Ending-Limit');

  if (isRecord(data)) {
    const detail = isRecord(data.detail) ? data.detail : undefined;
    const code = detail?.code ?? data.error_code ?? data.code ?? headerCode;
    const isLimit =
      code === GUEST_ENDING_LIMIT_CODE ||
      headerLimit === '1';

    if (!isLimit) return null;

    const message =
      typeof detail?.message === 'string' && detail.message.trim()
        ? detail.message
        : typeof data.message === 'string' && data.message.trim()
          ? data.message
          : undefined;
    const hint =
      typeof detail?.hint === 'string'
        ? detail.hint
        : typeof data.hint === 'string'
          ? data.hint
          : undefined;
    return new GuestEndingLimitError(message, hint);
  }

  if (headerCode === GUEST_ENDING_LIMIT_CODE || headerLimit === '1') {
    return new GuestEndingLimitError();
  }

  return null;
};

const isTimeoutError = (error: unknown): boolean => {
  if (axios.isAxiosError(error)) {
    return error.code === 'ECONNABORTED' || Boolean(error.message?.includes('timeout'));
  }
  if (error instanceof Error) return error.message.includes('timeout');
  return false;
};

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status;
      const guestLimitError = status === 403
        ? getGuestEndingLimitError(error.response?.data, error.response?.headers)
        : null;
      if (guestLimitError) {
        return Promise.reject(guestLimitError);
      }

      if (status === 401) {
        console.warn('Unauthorized request.');
      } else if (status === 403) {
        console.error('Forbidden request.');
      } else if (status === 404) {
        console.error('Resource not found.');
      } else if (status === 500) {
        console.error('Server error.');
      } else {
        console.error('Request failed:', getErrorMessage(error));
      }
    } else {
      console.error('Network error:', getErrorMessage(error));
    }
    return Promise.reject(error);
  }
);

export const getStaticAssetUrl = (url?: string | null): string => {
  if (!url) return '';
  const value = String(url).trim();
  if (!value) return '';
  if (/^(https?:|data:|blob:|file:)/i.test(value)) return value;
  if (value.startsWith('//')) {
    const protocol = typeof window !== 'undefined' ? window.location.protocol : 'http:';
    return `${protocol}${value}`;
  }
  if (value.startsWith('/')) return value;
  return `/${value.replace(/^\/+/, '')}`;
};

export const checkServerHealth = async (): Promise<boolean> => {
  try {
    const response = await axios.get('/health', { timeout: 5000 });
    return response.status === 200;
  } catch (error: unknown) {
    console.error('Backend health check failed:', error);
    return false;
  }
};

export interface CreateCharacterRequest {
  name: string;
  appearance: Record<string, unknown>;
  personality: Record<string, unknown>;
  background: Record<string, unknown>;
  gender?: string;
  age?: number;
  identity?: string;
  initial_scene?: string;
  initial_scene_prompt?: string;
}

export interface CreateCharacterResponse {
  character_id?: string | number;
  name?: string;
  image_url?: string;
  image_urls?: string[];
  [key: string]: unknown;
}

export const createCharacter = async (data: CreateCharacterRequest): Promise<CreateCharacterResponse> => {
  try {
    const response = await api.post('/v1/characters/create', data, { timeout: 180000 });
    return unwrapResponseData<CreateCharacterResponse>(response);
  } catch (error: unknown) {
    if (isTimeoutError(error)) {
      throw new Error('Character creation timed out. Please retry in a moment.');
    }
    throw error;
  }
};

export const getCharacter = async (characterId: string): Promise<Record<string, unknown>> => {
  const response = await api.get(`/v1/characters/${characterId}`);
  return unwrapResponseData<Record<string, unknown>>(response);
};

export const getCharacterImages = async (characterId: string): Promise<{ images?: string[] }> => {
  try {
    const response = await api.get(`/v1/characters/${characterId}/images`, { timeout: 60000 });
    return unwrapResponseData<{ images?: string[] }>(response);
  } catch (error: unknown) {
    if (isTimeoutError(error)) console.warn('Character image fetch timed out.');
    throw error;
  }
};

export interface RemoveBackgroundRequest {
  image_url?: string;
}

export interface RemoveBackgroundResponse {
  transparent_url: string;
  local_path: string;
  selected_image_url?: string;
  deleted_count?: number;
}

export const removeCharacterBackground = async (
  characterId: string,
  imageUrl?: string,
  imageUrls?: string[],
  selectedIndex?: number
): Promise<RemoveBackgroundResponse> => {
  try {
    const response = await api.post(
      `/v1/characters/${characterId}/remove-background`,
      {
        image_url: imageUrl,
        image_urls: imageUrls,
        selected_index: selectedIndex,
      },
      { timeout: 60000 }
    );
    return unwrapResponseData<RemoveBackgroundResponse>(response);
  } catch (error: unknown) {
    if (isTimeoutError(error)) throw new Error('Background removal timed out. Please retry.');
    throw error;
  }
};

export interface InitializeStoryResponse {
  thread_id?: string;
  scene?: string;
  scene_image_url?: string;
  composite_image_url?: string;
  story_background?: string;
  character_dialogue?: string;
  player_options?: PlayerOption[];
  is_game_finished?: boolean;
  [key: string]: unknown;
}

export const initializeStory = async (
  threadId: string,
  characterId: string,
  sceneId?: string,
  characterImageUrl?: string
): Promise<InitializeStoryResponse> => {
  try {
    if (!threadId || !characterId) {
      throw new Error(`Missing required params: threadId=${threadId}, characterId=${characterId}`);
    }

    const response = await api.post(
      '/v1/characters/initialize-story',
      {
        thread_id: threadId,
        character_id: String(characterId),
        scene_id: sceneId || 'school',
        character_image_url: characterImageUrl || undefined,
      },
      { timeout: 180000 }
    );
    return unwrapResponseData<InitializeStoryResponse>(response);
  } catch (error: unknown) {
    if (getErrorStatus(error) === 422) {
      const errorData = getErrorData(error);
      const detail = errorData?.detail || errorData?.message || 'Invalid request parameters.';
      throw new Error(`Request validation failed: ${JSON.stringify(detail)}`);
    }
    if (isTimeoutError(error)) {
      throw new Error('Story initialization timed out. Please retry.');
    }
    throw error;
  }
};

export interface GetScenesResponse {
  scenes?: unknown[];
  [key: string]: unknown;
}

export const getScenes = async (): Promise<GetScenesResponse> => {
  try {
    const response = await api.get('/v1/characters/scenes');
    return unwrapResponseData<GetScenesResponse>(response);
  } catch (error: unknown) {
    console.error('Failed to fetch scenes:', {
      status: getErrorStatus(error),
      data: getErrorData(error),
      message: getErrorMessage(error),
    });
    throw error;
  }
};

export interface GameInitRequest {
  user_id?: string;
  game_mode: string;
  character_id: string;
}

export interface GameInputRequest {
  thread_id: string;
  user_input: string;
  user_id?: string;
  character_id?: string;
}

export interface GameInitResponse {
  thread_id?: string;
  [key: string]: unknown;
}

export const initGame = async (data: GameInitRequest): Promise<GameInitResponse> => {
  try {
    const response = await api.post('/v1/game/init', data, { timeout: 60000 });
    return unwrapResponseData<GameInitResponse>(response);
  } catch (error: unknown) {
    if (isTimeoutError(error)) throw new Error('Game initialization timed out.');
    throw error;
  }
};

export interface ProcessGameInputResponse {
  thread_id?: string;
  scene?: string;
  scene_image_url?: string;
  composite_image_url?: string;
  character_dialogue?: string;
  player_options?: PlayerOption[];
  story_background?: string;
  event_title?: string;
  current_states?: Record<string, number>;
  state_changes?: Record<string, number>;
  tts_emotion?: Record<string, unknown>;
  is_event_finished?: boolean;
  is_game_finished?: boolean;
  ending_title?: string;
  ending_type?: string;
  ending_description?: string;
  guest_ending_limited?: boolean;
  [key: string]: unknown;
}

export const processGameInput = async (data: GameInputRequest): Promise<ProcessGameInputResponse> => {
  try {
    const response = await api.post('/v1/game/input', data, { timeout: 180000 });
    return unwrapResponseData<ProcessGameInputResponse>(response);
  } catch (error: unknown) {
    if (isTimeoutError(error)) throw new Error('Game input processing timed out.');
    const errorData = getErrorData(error);
    if (getErrorStatus(error) === 400 && typeof errorData?.message === 'string' && errorData.message.includes('not found')) {
      console.warn('Game session not found, may require re-init.');
    }
    throw error;
  }
};

export const checkEnding = async (threadId: string): Promise<Record<string, unknown>> => {
  const response = await api.get(`/v1/game/check-ending/${threadId}`);
  return unwrapResponseData<Record<string, unknown>>(response);
};

export const triggerEnding = async (threadId: string): Promise<Record<string, unknown>> => {
  const response = await api.post('/v1/game/trigger-ending', { thread_id: threadId });
  return unwrapResponseData<Record<string, unknown>>(response);
};

export interface PresetVoiceItem {
  id: string;
  name: string;
  description?: string;
  voice_id?: string | null;
  gender?: string;
  style?: string;
  preview_text?: string;
  supports_emotion?: boolean;
  emotions?: string[];
}

export const getPresetVoices = async (gender?: string): Promise<PresetVoiceItem[]> => {
  try {
    const response = await api.get('/v1/tts/presets', gender ? { params: { gender } } : undefined);
    const payload = unwrapResponseData<{ voices?: PresetVoiceItem[] | Record<string, PresetVoiceItem[]> }>(response);
    const voices = payload?.voices;
    if (Array.isArray(voices)) return voices;
    if (voices && typeof voices === 'object') {
      const grouped = voices as Record<string, PresetVoiceItem[]>;
      return [
        ...(grouped.female || []),
        ...(grouped.male || []),
        ...(grouped.emo_female || []),
        ...(grouped.emo_male || []),
        ...(grouped.neutral || []),
      ];
    }
    return [];
  } catch (error: unknown) {
    console.error('Failed to fetch preset voices:', error);
    throw error;
  }
};

export const generateSpeech = async (
  text: string,
  characterId: number | string,
  options?: { use_cache?: boolean; emotion_params?: Record<string, unknown> }
): Promise<{ audio_url: string; duration?: number; cached?: boolean } | null> => {
  try {
    const characterIdNum = typeof characterId === 'string' ? parseInt(characterId, 10) : characterId;
    if (Number.isNaN(characterIdNum)) throw new Error('Invalid character_id');

    const response = await api.post('/v1/tts/generate', {
      text: text.slice(0, 600),
      character_id: characterIdNum,
      use_cache: options?.use_cache ?? true,
      emotion_params: options?.emotion_params,
    });
    return unwrapResponseData<{ audio_url: string; duration?: number; cached?: boolean }>(response);
  } catch (error: unknown) {
    console.warn('TTS generation failed:', getErrorMessage(error));
    return null;
  }
};

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
    );
    return unwrapResponseData<{ audio_url: string; duration?: number }>(response);
  } catch (error: unknown) {
    const msg = getErrorMessage(error);
    console.warn('Voice preview failed:', msg);
    if (isTimeoutError(error)) console.warn('Voice preview timed out.');
    return null;
  }
};

export const setVoiceConfig = async (params: {
  character_id: number;
  voice_type: string;
  preset_voice_id?: string | null;
  voice_design_description?: string | null;
  voice_params?: Record<string, unknown>;
}): Promise<Record<string, unknown>> => {
  const response = await api.post('/v1/tts/voice/config', params);
  return unwrapResponseData<Record<string, unknown>>(response);
};

export default api;
