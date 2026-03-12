import type { LoadingAnimationComponent } from './types';
import SakuraLoading from './SakuraLoading';
import SimpleLoading from './SimpleLoading';
import VideoLoading from './VideoLoading';

export const VIDEO_LOADING_CONFIG = {
  videoSrc: '/videos/loading.mp4',
  muted: true,
  loop: true,
  autoPlay: true,
};

export const LOADING_ANIMATIONS: Record<string, LoadingAnimationComponent> = {
  sakura: SakuraLoading,
  simple: SimpleLoading,
  video: VideoLoading,
};

export const DEFAULT_LOADING_TYPE: keyof typeof LOADING_ANIMATIONS = 'sakura';

export const getLoadingAnimation = (type?: string): LoadingAnimationComponent => {
  const animationType = type || DEFAULT_LOADING_TYPE;
  return LOADING_ANIMATIONS[animationType] || LOADING_ANIMATIONS[DEFAULT_LOADING_TYPE];
};

