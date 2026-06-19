import { useCallback, useEffect, useState } from 'react';
import { Typography, Spin } from 'antd';
import { getStaticAssetUrl } from '@/services/api';

const { Text } = Typography;

export interface GameSceneBackgroundProps {
  compositeImageUrl: string | null;
  sceneImageUrl: string | null;
  characterImageUrl: string | null;
  expected?: boolean;
  missingLayerTimeoutMs?: number;
  imageLoadTimeoutMs?: number;
  onVisualReady?: () => void;
  onVisualError?: (message: string) => void;
}

export default function GameSceneBackground({
  compositeImageUrl,
  sceneImageUrl,
  characterImageUrl,
  expected = false,
  missingLayerTimeoutMs = 12000,
  imageLoadTimeoutMs = 20000,
  onVisualReady,
  onVisualError,
}: GameSceneBackgroundProps) {
  const [loadedCompositeUrl, setLoadedCompositeUrl] = useState<string | null>(null);
  const [loadedSceneUrl, setLoadedSceneUrl] = useState<string | null>(null);
  const [loadedCharacterUrl, setLoadedCharacterUrl] = useState<string | null>(null);
  const [renderErrorKey, setRenderErrorKey] = useState<string | null>(null);

  const visualKey = compositeImageUrl
    ? `composite:${compositeImageUrl}`
    : `layered:${sceneImageUrl ?? ''}|${characterImageUrl ?? ''}`;
  const hasRenderError = renderErrorKey === visualKey;
  const isCompositeMode = Boolean(compositeImageUrl);
  const isLayeredMode = !isCompositeMode && Boolean(sceneImageUrl || characterImageUrl);
  const hasRequiredLayers = Boolean(sceneImageUrl && characterImageUrl);
  const compositeLoaded = Boolean(compositeImageUrl && loadedCompositeUrl === compositeImageUrl);
  const sceneLoaded = Boolean(sceneImageUrl && loadedSceneUrl === sceneImageUrl);
  const characterLoaded = Boolean(characterImageUrl && loadedCharacterUrl === characterImageUrl);
  const compositeReady = isCompositeMode && compositeLoaded;
  const layeredReady = isLayeredMode && hasRequiredLayers && sceneLoaded && characterLoaded;
  const visualReady = !hasRenderError && (compositeReady || layeredReady);

  const reportVisualError = useCallback(
    (message: string) => {
      setRenderErrorKey(visualKey);
      onVisualError?.(message);
    },
    [onVisualError, visualKey]
  );

  useEffect(() => {
    if (!visualReady) return;
    onVisualReady?.();
  }, [onVisualReady, visualReady]);

  useEffect(() => {
    if (!expected || compositeImageUrl || hasRequiredLayers || hasRenderError) return;

    const timer = window.setTimeout(() => {
      if (!sceneImageUrl && !characterImageUrl) {
        reportVisualError('缺少场景与角色图层，已停止当前画面渲染。');
        return;
      }

      if (!sceneImageUrl) {
        reportVisualError('缺少场景图层，已停止当前画面渲染。');
        return;
      }

      if (!characterImageUrl) {
        reportVisualError('缺少角色图层，已停止当前画面渲染。');
      }
    }, missingLayerTimeoutMs);

    return () => window.clearTimeout(timer);
  }, [
    characterImageUrl,
    compositeImageUrl,
    expected,
    hasRenderError,
    hasRequiredLayers,
    missingLayerTimeoutMs,
    reportVisualError,
    sceneImageUrl,
  ]);

  useEffect(() => {
    if (!expected || visualReady || hasRenderError) return;
    if (!compositeImageUrl && !hasRequiredLayers) return;

    const timer = window.setTimeout(() => {
      if (compositeImageUrl) {
        reportVisualError('合成画面加载超时，已停止当前画面渲染。');
        return;
      }

      if (!sceneLoaded) {
        reportVisualError('场景图层加载超时，已停止当前画面渲染。');
        return;
      }

      if (!characterLoaded) {
        reportVisualError('角色图层加载超时，已停止当前画面渲染。');
      }
    }, imageLoadTimeoutMs);

    return () => window.clearTimeout(timer);
  }, [
    characterLoaded,
    compositeImageUrl,
    expected,
    hasRenderError,
    hasRequiredLayers,
    imageLoadTimeoutMs,
    reportVisualError,
    sceneLoaded,
    visualReady,
  ]);

  if (hasRenderError) return null;

  if (isCompositeMode && compositeImageUrl) {
    const imageUrl = getStaticAssetUrl(compositeImageUrl);

    return (
      <>
        {!compositeLoaded && (
          <div className="game-visual-preparing">
            <Spin size="large" />
            <Text>画面准备中...</Text>
          </div>
        )}
        <img
          src={imageUrl}
          alt="游戏场景"
          className="composite-scene-image"
          style={{ opacity: compositeLoaded ? 1 : 0, transition: 'opacity 0.5s ease' }}
          onLoad={() => setLoadedCompositeUrl(compositeImageUrl)}
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.style.display = 'none';
            reportVisualError('合成画面加载失败，已停止当前画面渲染。');
          }}
        />
      </>
    );
  }

  if (isLayeredMode && hasRequiredLayers && sceneImageUrl && characterImageUrl) {
    const sceneUrl = getStaticAssetUrl(sceneImageUrl);
    const characterUrl = getStaticAssetUrl(characterImageUrl);

    return (
      <>
        {!layeredReady && (
          <div className="game-visual-preparing">
            <Spin size="large" />
            <Text>画面准备中...</Text>
          </div>
        )}
        <img
          src={sceneUrl}
          alt="场景背景"
          className="scene-background-image"
          style={{ opacity: layeredReady ? 1 : 0, transition: 'opacity 0.5s ease' }}
          onLoad={() => setLoadedSceneUrl(sceneImageUrl)}
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.style.display = 'none';
            reportVisualError('场景图层加载失败，已停止当前画面渲染。');
          }}
        />
        <img
          src={characterUrl}
          alt="角色"
          className="character-overlay-image"
          style={{ opacity: layeredReady ? 1 : 0, transition: 'opacity 0.5s ease' }}
          onLoad={() => setLoadedCharacterUrl(characterImageUrl)}
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.style.display = 'none';
            reportVisualError('角色图层加载失败，已停止当前画面渲染。');
          }}
        />
      </>
    );
  }

  if (expected) {
    return (
      <div className="game-visual-preparing">
        <Spin size="large" />
        <Text>图层准备中...</Text>
      </div>
    );
  }

  return (
    <div className="game-visual-empty" aria-hidden="true" />
  );
}
