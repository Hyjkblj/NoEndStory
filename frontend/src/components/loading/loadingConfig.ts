/**
 * 加载动画配置
 * 
 * 要更换加载动画，只需修改这里的配置即可
 * 
 * 可用的加载动画类型：
 * - 'sakura': 樱花加载动画
 * - 'simple': 简单加载动画（备用）
 * - 'video': 视频加载动画（推荐，更丰富的视觉体验）
 * 
 * 添加新的加载动画：
 * 1. 在 loading/ 目录下创建新的组件文件
 * 2. 实现 LoadingAnimationProps 接口
 * 3. 在此文件中导入并添加到 LOADING_ANIMATIONS
 * 4. 修改 DEFAULT_LOADING_TYPE 为新的类型
 */

import type { LoadingAnimationComponent } from './types';
import SakuraLoading from './SakuraLoading';
import SimpleLoading from './SimpleLoading';
import VideoLoading from './VideoLoading';

/**
 * 视频加载配置
 * 如果使用视频加载动画，在这里配置视频路径
 */
export const VIDEO_LOADING_CONFIG = {
  /** 视频文件路径（相对于 public 目录或使用绝对 URL） */
  videoSrc: '/videos/loading.mp4', // 默认路径，可以修改
  /** 是否静音播放（推荐 true，避免自动播放被浏览器阻止） */
  muted: true,
  /** 是否循环播放 */
  loop: true,
  /** 是否自动播放 */
  autoPlay: true,
};

/**
 * 可用的加载动画映射
 */
export const LOADING_ANIMATIONS: Record<string, LoadingAnimationComponent> = {
  sakura: SakuraLoading,
  simple: SimpleLoading,
  video: VideoLoading,
};

/**
 * 默认加载动画类型
 * 修改这里即可切换加载动画
 * 
 * 推荐使用 'video' 以获得更好的视觉体验
 */
export const DEFAULT_LOADING_TYPE: keyof typeof LOADING_ANIMATIONS = 'video';

/**
 * 获取加载动画组件
 */
export const getLoadingAnimation = (type?: string): LoadingAnimationComponent => {
  const animationType = type || DEFAULT_LOADING_TYPE;
  return LOADING_ANIMATIONS[animationType] || LOADING_ANIMATIONS[DEFAULT_LOADING_TYPE];
};
