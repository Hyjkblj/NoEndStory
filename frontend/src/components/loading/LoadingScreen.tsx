import type { LoadingAnimationProps } from './types';
import { getLoadingAnimation, VIDEO_LOADING_CONFIG, DEFAULT_LOADING_TYPE } from './loadingConfig';

/**
 * 统一的加载屏幕组件
 * 
 * 这个组件会根据配置自动使用对应的加载动画
 * 要更换加载动画，只需修改 loadingConfig.ts 中的配置
 */
function LoadingScreen(props: LoadingAnimationProps) {
  const LoadingAnimation = getLoadingAnimation();
  
  // 如果使用视频加载动画，自动注入视频配置
  if (DEFAULT_LOADING_TYPE === 'video' && !props.videoSrc) {
    return (
      <LoadingAnimation
        {...props}
        videoSrc={VIDEO_LOADING_CONFIG.videoSrc}
        muted={VIDEO_LOADING_CONFIG.muted}
        loop={VIDEO_LOADING_CONFIG.loop}
        autoPlay={VIDEO_LOADING_CONFIG.autoPlay}
      />
    );
  }
  
  return <LoadingAnimation {...props} />;
}

export default LoadingScreen;
