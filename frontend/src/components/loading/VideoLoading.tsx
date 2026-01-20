import { Typography } from 'antd';
import type { LoadingAnimationProps } from './types';
import './VideoLoading.css';

const { Text } = Typography;

/**
 * 视频加载动画组件
 * 
 * 使用说明：
 * 1. 将视频文件放在 public/videos/ 目录（推荐）或 src/assets/videos/ 目录
 * 2. 在 loadingConfig.ts 中配置视频路径
 * 3. 视频会自动播放、循环，直到加载完成
 */
function VideoLoading({ 
  message = '正在加载...',
  videoSrc,
  muted = true,
  loop = true,
  autoPlay = true,
}: LoadingAnimationProps) {
  // 从配置或 props 获取视频路径
  const videoPath = videoSrc || '/videos/loading.mp4';

  return (
    <div className="video-loading-screen">
      {/* 背景遮罩（可选，用于增强文字可读性） */}
      <div className="video-loading-backdrop" />
      
      {/* 视频容器 */}
      <div className="video-loading-container">
        <video
          className="video-loading-player"
          src={videoPath}
          autoPlay={autoPlay}
          muted={muted}
          loop={loop}
          playsInline
          onError={(e) => {
            console.error('视频加载失败:', e);
          }}
        >
          您的浏览器不支持视频播放
        </video>
      </div>

      {/* 加载文本（可选，显示在视频上方） */}
      {message && (
        <div className="video-loading-content">
          <Text className="video-loading-text">{message}</Text>
        </div>
      )}
    </div>
  );
}

export default VideoLoading;
