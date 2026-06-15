/**
 * 所有数据类型的集中导出入口。
 * 类型定义请各自在对应模块维护：api.ts / game.ts
 */

export type { ApiResponse, unwrapResponse } from './api';
export type {
  GameMessage,
  PlayerOption,
  GameSave,
  MainGameSave,
  SelectedScene,
  CharacterData,
  InitialGameData,
} from './game';

// 向后兼容：重新导出 game.ts 中的类型
export type {
  CreateCharacterData,
  GameInitData,
  GameInputData,
  ScenesData,
  CharacterImagesData,
  RemoveBackgroundData,
} from './api';
