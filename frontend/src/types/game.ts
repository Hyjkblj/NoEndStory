/** 对话消息（游戏内） */
export interface GameMessage {
  role: 'user' | 'assistant';
  content: string;
}

/** 玩家选项 */
export interface PlayerOption {
  id: number;
  text: string;
  type: string;
  state_changes?: Record<string, number>;
}

/** 存档：按 thread 保存的完整消息列表与元信息 */
export interface GameSave {
  threadId: string;
  characterId?: string;
  messages: GameMessage[];
  lastMessage?: string;
  timestamp: number;
}

/** 主存档入口（继续游戏用） */
export interface MainGameSave {
  threadId: string;
  characterId?: string;
  lastMessage?: string;
  timestamp: number;
}

/** 选中的场景（大场景） */
export interface SelectedScene {
  id: string;
  name?: string;
  description?: string;
  imageUrl?: string;
}

/** sessionStorage 中的角色数据（创建/选择角色后写入） */
export interface CharacterData {
  characterId: string;
  name?: string;
  height?: number;
  weight?: number;
  age?: number;
  gender?: 'male' | 'female';
  appearance?: string[];
  personality?: string[];
  style?: string | null;
  imageUrl?: string;
  image_urls?: string[];
  transparentImageUrl?: string;
  originalImageUrl?: string;
  selectedImageUrl?: string;
  selectedImageIndex?: number;
  selectedCharacterId?: string;
  selectedScene?: SelectedScene;
  voiceConfig?: unknown;
  timestamp?: number;
}

/** 初遇页写入的初始游戏数据（供 Game 页消费） */
export interface InitialGameData {
  scene?: string;
  character_dialogue?: string;
  player_options?: PlayerOption[];
  composite_image_url?: string;
  scene_image_url?: string;
}
