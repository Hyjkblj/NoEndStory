import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, App as AntdApp } from 'antd';
import { LeftOutlined, RightOutlined } from '@ant-design/icons';
import backgroundImage from '@/assets/images/firstbackgound.jpg';
import LoadingScreen from '@/components/loading';
import { useRouteTransition, useRouteTransitionReady } from '@/hooks/useRouteTransition';
import {
  checkServerHealth,
  initGame,
  initializeStory,
  getScenes,
  getStaticAssetUrl,
  isGuestEndingLimitError,
} from '@/services/api';
import { ROUTES } from '@/config/routes';
import * as gameStorage from '@/storage/gameStorage';
import { preloadImages } from '@/utils/preload';
import type { PlayerOption } from '@/types/game';
import './FirstMeetingSelection.css';

interface SceneOption {
  id: string;
  name: string;
  description: string;
  imageUrl?: string;
}

interface SceneApiItem {
  id?: string;
  name?: string;
  description?: string;
  imageUrl?: string;
}

interface SceneApiResponse {
  scenes?: unknown[];
}

interface StoryInitResponse {
  character_dialogue?: string;
  player_options?: PlayerOption[];
  composite_image_url?: string;
  scene_image_url?: string;
  scene?: string;
}

const normalizeScene = (scene: unknown, index: number): SceneOption => {
  const data = (scene && typeof scene === 'object' ? scene : {}) as SceneApiItem;
  const rawImage = data.imageUrl;
  const imageUrl =
    typeof rawImage === 'string' && rawImage !== '' && rawImage !== 'null'
      ? rawImage
      : undefined;

  return {
    id: data.id || `scene-${index}`,
    name: data.name || '未命名场景',
    description: data.description || '',
    imageUrl,
  };
};

function FirstMeetingSelection() {
  const navigate = useNavigate();
  const { transitionTo } = useRouteTransition();
  const { message } = AntdApp.useApp();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('加载场景中...');
  const [currentSceneIndex, setCurrentSceneIndex] = useState(0);
  const [sceneOptions, setSceneOptions] = useState<SceneOption[]>([]);

  const wheelTimeoutRef = useRef<number | null>(null);
  const isWheelingRef = useRef(false);

  useEffect(() => {
    const loadScenes = async () => {
      setLoading(true);
      setLoadingMessage('加载场景中...');

      try {
        const isHealthy = await checkServerHealth();
        if (!isHealthy) {
          message.error('服务暂不可用，请稍后重试');
          setSceneOptions([]);
          return;
        }

        const response = (await getScenes()) as SceneApiResponse | null | undefined;
        const scenesData = Array.isArray(response?.scenes) ? response.scenes : [];

        if (scenesData.length === 0) {
          message.warning('暂无可选场景');
          setSceneOptions([]);
          return;
        }

        const scenes = scenesData.map((scene, index) => normalizeScene(scene, index));
        setSceneOptions(scenes);
      } catch (error: unknown) {
        const err = error as { response?: { data?: { message?: string } }; message?: string };
        message.error(err.response?.data?.message || err.message || '加载场景失败');
        setSceneOptions([
          {
            id: 'school',
            name: '学校',
            description: '充满活力的校园场景',
          },
        ]);
      } finally {
        setLoading(false);
      }
    };

    void loadScenes();
  }, [message]);

  const currentScene = sceneOptions.length > 0 ? sceneOptions[currentSceneIndex] : null;

  useRouteTransitionReady(!loading && sceneOptions.length > 0, { delayMs: 120 });

  const handlePreviousScene = () => {
    setCurrentSceneIndex((prev) => (prev === 0 ? sceneOptions.length - 1 : prev - 1));
  };

  const handleNextScene = () => {
    setCurrentSceneIndex((prev) => (prev === sceneOptions.length - 1 ? 0 : prev + 1));
  };

  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    e.preventDefault();

    if (isWheelingRef.current) return;
    isWheelingRef.current = true;

    if (e.deltaY > 50) {
      handleNextScene();
    } else if (e.deltaY < -50) {
      handlePreviousScene();
    }

    if (wheelTimeoutRef.current) window.clearTimeout(wheelTimeoutRef.current);
    wheelTimeoutRef.current = window.setTimeout(() => {
      isWheelingRef.current = false;
    }, 300);
  };

  useEffect(() => {
    return () => {
      if (wheelTimeoutRef.current) window.clearTimeout(wheelTimeoutRef.current);
    };
  }, []);

  const handleSelectScene = async () => {
    const selectedScene = sceneOptions[currentSceneIndex];
    if (!selectedScene) {
      message.error('请选择一个场景');
      return;
    }

    let redirectToCharacterSetting = false;

    setLoading(true);
    setLoadingMessage('正在初始化游戏...');

    try {
      const didNavigate = await transitionTo({
        to: ROUTES.GAME,
        variant: 'story',
        disableReadyFallback: true,
        work: async ({ animateTo, setProgress }) => {
          setProgress(14);
          const isHealthy = await checkServerHealth();
          if (!isHealthy) {
            message.error('服务暂不可用，请稍后重试');
            return false;
          }

          await animateTo(28, 420);

          const characterData = gameStorage.getCharacterData();
          if (!characterData?.characterId) {
            message.error('请先创建角色');
            redirectToCharacterSetting = true;
            return false;
          }

          const characterId = characterData.characterId;
          gameStorage.setCharacterData({ ...characterData, selectedScene });

          const initResponse = await initGame({
            game_mode: 'solo',
            character_id: characterId,
          });

          const threadId = initResponse?.thread_id as string | undefined;
          if (!threadId) throw new Error('初始化失败：未获取到会话ID');

          await animateTo(52, 560);

          const characterImageUrl =
            characterData.selectedImageUrl || characterData.originalImageUrl || characterData.imageUrl;

          const storyResponse = (await initializeStory(
            threadId,
            characterId,
            selectedScene.id,
            characterImageUrl
          )) as StoryInitResponse;

          await animateTo(78, 620);

          gameStorage.cleanupGuestOldGameData({
            keepThreadId: threadId,
            keepLatestEnding: false,
          });
          gameStorage.setInitialGameData({
            character_dialogue: storyResponse.character_dialogue,
            player_options: Array.isArray(storyResponse.player_options)
              ? storyResponse.player_options
              : [],
            composite_image_url: storyResponse.composite_image_url,
            scene_image_url: storyResponse.scene_image_url,
            scene: storyResponse.scene,
          });
          gameStorage.setGameIds(threadId, characterId);

          await preloadImages([
            storyResponse.composite_image_url,
            storyResponse.scene_image_url,
            characterImageUrl,
          ], 10000);
          await animateTo(90, 420);
        },
      });

      if (!didNavigate) {
        setLoading(false);
        if (redirectToCharacterSetting) navigate(ROUTES.CHARACTER_SETTING);
      }
    } catch (error: unknown) {
      if (isGuestEndingLimitError(error)) {
        gameStorage.cleanupGuestOldGameData({
          keepThreadId: null,
          keepLatestEnding: true,
          clearCharacterData: true,
          clearSession: true,
        });
        message.warning(error.message || '这次游客体验已经完成，24小时后可再次开启。');
        navigate(ROUTES.FIRST_STEP, { replace: true });
        return;
      }

      const err = error as { message?: string; response?: { data?: { message?: string } } };
      let errorMessage = '选择场景失败，请重试';
      if (err.message?.includes('timeout')) {
        errorMessage = '初始化超时，请稍后重试';
      } else if (err.response?.data?.message) {
        errorMessage = err.response.data.message;
      }
      message.error(errorMessage);
      setLoading(false);
    }
  };

  if (loading && sceneOptions.length === 0) {
    return <LoadingScreen message={loadingMessage} />;
  }

  if (sceneOptions.length === 0) {
    return (
      <div className="first-meeting-selection-container">
        <div className="first-meeting-content">
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <p>暂无可选场景</p>
            <Button onClick={() => navigate(ROUTES.CHARACTER_SETTING)}>返回角色创建</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="first-meeting-selection-container">
      <div
        className="first-meeting-background"
        style={{
          backgroundImage: `url(${backgroundImage})`,
        }}
      />

      <div className="first-meeting-content">
        <div className="meeting-title-banner">
          <span className="title-text">初遇</span>
        </div>

        <div className="scene-display-area" onWheel={handleWheel}>
          <button
            className="scene-nav-arrow scene-nav-left"
            onClick={handlePreviousScene}
            aria-label="Previous scene"
          >
            <LeftOutlined />
          </button>

          <div className="scene-content">
            {currentScene?.imageUrl ? (
              <img
                key={`scene-img-${currentScene.id}-${currentSceneIndex}`}
                src={getStaticAssetUrl(currentScene.imageUrl)}
                alt={currentScene.name}
                className="scene-image"
                style={{ display: 'none' }}
                onLoad={(e) => {
                  const img = e.target as HTMLImageElement;
                  img.style.display = 'block';
                  const placeholder = img.parentElement?.querySelector('.scene-placeholder') as HTMLElement;
                  if (placeholder) placeholder.style.display = 'none';
                }}
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  const placeholder = target.parentElement?.querySelector('.scene-placeholder') as HTMLElement;
                  if (placeholder) placeholder.style.display = 'flex';
                }}
              />
            ) : null}
            <div
              className="scene-placeholder"
              style={{
                display: currentScene?.imageUrl ? 'none' : 'flex',
              }}
            >
              <span className="placeholder-text">{currentScene?.name || 'Unknown'}</span>
              {currentScene?.description && (
                <span className="placeholder-description">{currentScene.description}</span>
              )}
            </div>
          </div>

          <button
            className="scene-nav-arrow scene-nav-right"
            onClick={handleNextScene}
            aria-label="Next scene"
          >
            <RightOutlined />
          </button>
        </div>

        <div className="scene-choice-button-container">
          <Button className="scene-choice-button" onClick={handleSelectScene} disabled={loading}>
            选择
          </Button>
        </div>
      </div>
    </div>
  );
}

export default FirstMeetingSelection;

