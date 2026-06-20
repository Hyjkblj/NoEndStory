/** 游戏相关类型定义 */

export interface GameMessage {
  id?: string;
  role: 'story_background' | 'character' | 'player' | 'assistant' | 'user' | 'system';
  content: string;
  timestamp?: string;
}

export interface PlayerOption {
  id: number;
  text: string;
  type?: string;
  state_changes?: Record<string, number>;
}

export interface VoiceConfig {
  voiceId?: string;
  speed?: number;
  volume?: number;
  pitch?: number;
  voice_type?: string;
  preset_voice_id?: string | null;
  voice_name?: string;
  voice_description?: string;
  voice_id?: string;
}

export interface GameSave {
  threadId: string;
  characterId?: string;
  lastScene?: string;
  savedAt?: string;
  messages?: GameMessage[];
  lastMessage?: string;
  timestamp?: number;
}

export interface MainGameSave {
  id?: string;
  threadId?: string;
  characterId?: string;
  characterName?: string;
  lastScene?: string;
  lastPlayed?: string | number;
  lastMessage?: string;
  timestamp?: number;
  totalPlays?: number;
}

export interface SelectedScene {
  id?: string;
  name?: string;
  sceneId?: string;
  sceneName?: string;
  isSelected?: boolean;
  imageExtensions?: string[];
}

export interface CharacterData {
  id?: string;
  characterId?: string;
  selectedCharacterId?: string;
  name?: string;
  imageUrl?: string;
  avatarUrl?: string;
  image_urls?: string[];
  originalImageUrl?: string;
  selectedImageUrl?: string;
  selectedImageIndex?: number;
  transparentImageUrl?: string;
  voiceConfig?: VoiceConfig;
  personality?: Record<string, unknown>;
  selectedScene?: SelectedScene;
  gender?: 'male' | 'female';
  age?: number;
  height?: number;
  weight?: number;
  identity?: string;
  appearance?: unknown;
  personalityKeywords?: unknown;
  style?: unknown;
  isAvailable?: boolean;
}

export interface InitialGameData {
  threadId?: string;
  characterId?: string;
  sceneId?: string;
  characterName?: string;
  characterImageUrl?: string;
  scene?: string;
  scene_image_url?: string;
  composite_image_url?: string;
  story_background?: string;
  character_dialogue?: string;
  player_options?: PlayerOption[];
  voiceConfig?: VoiceConfig;
}

export type StoredMainSave = MainGameSave;

export interface SaveSummary {
  characterName: string;
  lastScene: string;
  lastPlayed: string;
  excerpt?: string;
  threadId?: string;
  characterId?: string;
}

export interface EndingRelationshipMetric {
  key: string;
  label: string;
  value: number | null;
  tone?: 'warm' | 'soft' | 'tense' | 'quiet';
}

export interface EndingMemory {
  title: string;
  description: string;
  choice?: string;
}

export interface EndingRecord {
  id: string;
  threadId: string;
  characterId?: string;
  characterName: string;
  title: string;
  type: string;
  typeLabel: string;
  description: string;
  finalDialogue: string;
  sceneId?: string;
  sceneName?: string;
  createdAt: number;
  relationship: EndingRelationshipMetric[];
  keyMemories: EndingMemory[];
  visual: {
    compositeImageUrl?: string | null;
    sceneImageUrl?: string | null;
    characterImageUrl?: string | null;
  };
}
