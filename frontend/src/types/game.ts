/** 游戏相关类型定义 */

export interface GameMessage {
  id: string;
  role: 'character' | 'player' | 'system';
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
  voiceId: string;
  speed: number;
  volume: number;
  pitch: number;
}

export interface GameSave {
  threadId: string;
  characterId: string;
  lastScene: string;
  savedAt: string;
}

export interface MainGameSave {
  id: string;
  characterId: string;
  characterName: string;
  lastScene: string;
  lastPlayed: string;
  totalPlays: number;
}

export interface SelectedScene {
  sceneId: string;
  sceneName: string;
  isSelected: boolean;
}

export interface CharacterData {
  id?: string;
  name?: string;
  imageUrl?: string;
  avatarUrl?: string;
  voiceConfig?: VoiceConfig;
  personality?: Record<string, unknown>;
  isAvailable?: boolean;
}

export interface InitialGameData {
  threadId: string;
  characterId: string;
  sceneId: string;
  characterName: string;
  characterImageUrl: string;
  voiceConfig?: VoiceConfig;
}

// ========== 存档相关类型 ==========

export interface StoredMainSave {
  threadId?: string;
  characterId?: string;
  characterName?: string;
  lastMessage?: string;
  timestamp?: number;
}

export interface SaveSummary {
  threadId: string;
  characterId?: string;
  characterName: string;
  lastMessage: string;
  timeAgo: string;
}

// ========== 角色选择相关类型 ==========

export interface CharacterOption {
  id: string;
  name: string;
  imageUrl?: string;
  imageUrls?: string[];
  gender?: string;
}

// ========== 场景选择相关类型 ==========

export interface SceneOption {
  id: string;
  name: string;
  description?: string;
  imageUrl?: string;
}

// ========== 结局相关类型 ==========

export type EndingTone = 'warm' | 'soft' | 'tense' | 'neutral';

export interface EndingRelationshipMetric {
  key: string;
  label: string;
  tone: EndingTone;
  value: number | null;
}

export interface EndingMemory {
  title: string;
  description: string;
  choice?: string;
}

export interface EndingRecord {
  endingType: string;
  endingTypeLabel: string;
  endingTitle: string;
  endingDescription: string;
  sceneName: string;
  finalDialogue: string;
  lastChoice?: string;
  relationshipMetrics: EndingRelationshipMetric[];
  memories: EndingMemory[];
  savedAt: number;
}
