/**
 * 游戏页相关工具：角色图片、场景图片 URL 等
 */
import * as gameStorage from '@/storage/gameStorage';
import { getSceneNameById } from '@/config/scenes';
import type { StoredMainSave, SaveSummary } from '@/types/game';

/** 从存储中按优先级解析角色图片 URL（透明图 > 原图，排除已删除的 portrait_img） */
export function getCharacterImageFromStorage(): string | undefined {
  const characterData = gameStorage.getCharacterData();
  if (!characterData) return undefined;
  if (characterData.transparentImageUrl) return characterData.transparentImageUrl;
  const imageUrl = characterData.imageUrl;
  const isDeleted = (url: string) => /portrait_img[123]/.test(url);
  if (imageUrl && isDeleted(imageUrl) && characterData.originalImageUrl && !isDeleted(characterData.originalImageUrl)) {
    return characterData.originalImageUrl;
  }
  if (imageUrl && isDeleted(imageUrl)) return undefined;
  return characterData.originalImageUrl || imageUrl;
}

/** 当后端未返回 scene_image_url 时，生成可尝试的场景图 URL 列表（smallscenes 优先，再 scenes） */
export function getFallbackSceneImageUrls(sceneId: string): string[] {
  const sceneName = getSceneNameById(sceneId);
  const encoded = encodeURIComponent(sceneName);
  return [
    `/static/images/smallscenes/UNKNOWN_SCENE_${sceneId}_${encoded}_scene_v1.jpg`,
    `/static/images/smallscenes/UNKNOWN_SCENE_${sceneId}_${encoded}_scene_v1.jpeg`,
    `/static/images/smallscenes/UNKNOWN_SCENE_${sceneId}_${encoded}_scene_v1.png`,
    `/static/images/scenes/${sceneId}_${encoded}.jpeg`,
    `/static/images/scenes/${sceneId}_${encoded}.jpg`,
    `/static/images/scenes/${sceneId}_${encoded}.png`,
  ];
}

/** 格式化最后游玩时间 */
export function formatLastPlayed(value?: string | number): string {
  if (!value) return '上次故事';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '上次故事';
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

/** 从存档数据中提取摘要信息 */
export function getSaveSummary(save: StoredMainSave | null): SaveSummary | null {
  if (!save) return null;
  return {
    threadId: save.threadId || save.id || '',
    characterId: save.characterId,
    characterName: save.characterName || '未命名角色',
    lastMessage: save.lastMessage || '',
    timeAgo: formatLastPlayed(save.lastPlayed || save.timestamp),
  };
}
