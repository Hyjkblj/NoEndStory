/**
 * 游戏页相关工具：角色图片、场景图片 URL 等
 */
import * as gameStorage from '@/storage/gameStorage';
import { getSceneNameById } from '@/config/scenes';

const ORIGINAL_CHARACTER_IMAGE_PATTERN = /portrait_img\d+/i;

export function isGeneratedOriginalCharacterImage(url?: string | null): boolean {
  return Boolean(url && ORIGINAL_CHARACTER_IMAGE_PATTERN.test(url));
}

export function isLikelyTransparentCharacterLayer(url?: string | null): url is string {
  const value = typeof url === 'string' ? url.trim() : '';
  return Boolean(value && !isGeneratedOriginalCharacterImage(value));
}

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
export function getCharacterLayerImageFromStorage(): string | undefined {
  const characterData = gameStorage.getCharacterData();
  if (!characterData) return undefined;

  const candidates = [
    characterData.transparentImageUrl,
    characterData.imageUrl,
  ];

  return candidates.find(isLikelyTransparentCharacterLayer);
}

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
