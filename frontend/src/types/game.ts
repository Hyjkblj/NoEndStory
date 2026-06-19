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
