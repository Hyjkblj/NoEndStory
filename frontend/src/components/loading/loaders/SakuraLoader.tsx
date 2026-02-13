import { Typography } from 'antd';
import type { LoadingAnimationProps } from '../LoadingScreen.types';
import './SakuraLoader.css';

const { Text } = Typography;

/**
 * 樱花加载动画组件
 */
function SakuraLoader({ message = '正在连接服务器...', className = '' }: LoadingAnimationProps) {
  return (
    <div className={`loading-screen ${className}`}>
      {/* 背景遮罩 */}
      <div className="loading-backdrop" />
      
      {/* 加载内容 */}
      <div className="loading-content">
        {/* 旋转的樱花加载动画 */}
        <div className="sakura-loader">
          <div className="sakura-petal-loader sakura-1">
            <svg width="40" height="40" viewBox="0 0 20 20">
              <path
                d="M10 2C10 2 12 6 16 6C12 6 10 10 10 10C10 10 8 6 4 6C8 6 10 2 10 2Z"
                fill="#ffb3d9"
                opacity="0.9"
              />
            </svg>
          </div>
          <div className="sakura-petal-loader sakura-2">
            <svg width="40" height="40" viewBox="0 0 20 20">
              <path
                d="M10 2C10 2 12 6 16 6C12 6 10 10 10 10C10 10 8 6 4 6C8 6 10 2 10 2Z"
                fill="#ffc0cb"
                opacity="0.8"
              />
            </svg>
          </div>
          <div className="sakura-petal-loader sakura-3">
            <svg width="40" height="40" viewBox="0 0 20 20">
              <path
                d="M10 2C10 2 12 6 16 6C12 6 10 10 10 10C10 10 8 6 4 6C8 6 10 2 10 2Z"
                fill="#ff99cc"
                opacity="0.85"
              />
            </svg>
          </div>
        </div>

        {/* 加载文本 */}
        <Text className="loading-text">{message}</Text>
        
        {/* 加载点动画 */}
        <div className="loading-dots">
          <span className="dot dot-1">.</span>
          <span className="dot dot-2">.</span>
          <span className="dot dot-3">.</span>
        </div>
      </div>
    </div>
  );
}

export default SakuraLoader;
