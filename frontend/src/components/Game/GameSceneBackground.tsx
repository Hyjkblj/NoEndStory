import { useState } from 'react';
import { Typography, Spin } from 'antd';
import { getStaticAssetUrl } from '@/services/api';

const { Text } = Typography;

export interface GameSceneBackgroundProps {
  shouldUseComposite: boolean;
  compositeImageUrl: string | null;
  sceneImageUrl: string | null;
  characterImageUrl: string | null;
  onCompositeError?: () => void;
  onSceneError?: () => void;
  onCharacterError?: () => void;
}

export default function GameSceneBackground({
  shouldUseComposite,
  compositeImageUrl,
  sceneImageUrl,
  characterImageUrl,
  onCompositeError,
  onSceneError,
  onCharacterError,
}: GameSceneBackgroundProps) {
  const [compositeLoaded, setCompositeLoaded] = useState(false);
  const [sceneLoaded, setSceneLoaded] = useState(false);
  const [characterLoaded, setCharacterLoaded] = useState(false);

  // 合成图片模式
  if (shouldUseComposite) {
    if (!compositeImageUrl) {
      return (
        <div className="scene-placeholder-fallback" style={{ display: 'flex' }}>
          <Spin size="large" />
          <Text style={{ color: '#fff', fontSize: '18px', marginTop: 16 }}>场景合成中...</Text>
        </div>
      );
    }

    return (
      <>
        {!compositeLoaded && (
          <div className="scene-placeholder-fallback" style={{ display: 'flex' }}>
            <Spin size="large" />
            <Text style={{ color: '#fff', fontSize: '18px', marginTop: 16 }}>加载场景中...</Text>
          </div>
        )}
        <img
          src={getStaticAssetUrl(compositeImageUrl)}
          alt="游戏场景"
          className="composite-scene-image"
          style={{ opacity: compositeLoaded ? 1 : 0, transition: 'opacity 0.5s ease' }}
          onLoad={() => setCompositeLoaded(true)}
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.style.display = 'none';
            onCompositeError?.();
          }}
        />
      </>
    );
  }

  // 分层模式（场景 + 角色）
  return (
    <>
      {/* 场景背景 */}
      {sceneImageUrl ? (
        <>
          {!sceneLoaded && (
            <div className="scene-placeholder-fallback" style={{ display: 'flex' }}>
              <Spin size="large" />
              <Text style={{ color: '#fff', fontSize: '18px', marginTop: 16 }}>加载场景中...</Text>
            </div>
          )}
          <img
            src={getStaticAssetUrl(sceneImageUrl)}
            alt="场景背景"
            className="scene-background-image"
            style={{ opacity: sceneLoaded ? 1 : 0, transition: 'opacity 0.5s ease' }}
            onLoad={() => setSceneLoaded(true)}
            onError={(e) => {
              const target = e.target as HTMLImageElement;
              target.style.display = 'none';
              const placeholder = target.parentElement?.querySelector('.scene-placeholder-fallback') as HTMLElement;
              if (placeholder) placeholder.style.display = 'flex';
              onSceneError?.();
            }}
          />
        </>
      ) : (
        <div className="scene-placeholder-fallback" style={{ display: 'flex' }}>
          <Spin size="large" />
          <Text style={{ color: '#fff', fontSize: '18px', marginTop: 16 }}>加载场景中...</Text>
        </div>
      )}

      {/* 角色叠加 */}
      {characterImageUrl && (
        <>
          {!characterLoaded && (
            <div style={{
              position: 'absolute', top: '50%', left: '50%',
              transform: 'translate(-50%, -50%)', zIndex: 3
            }}>
              <Spin />
            </div>
          )}
          <img
            src={getStaticAssetUrl(characterImageUrl)}
            alt="角色"
            className="character-overlay-image"
            style={{ opacity: characterLoaded ? 1 : 0, transition: 'opacity 0.5s ease' }}
            onLoad={() => setCharacterLoaded(true)}
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
              onCharacterError?.();
            }}
          />
        </>
      )}
    </>
  );
}
