import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, App as AntdApp } from 'antd';
import { LeftOutlined, RightOutlined } from '@ant-design/icons';
import backgroundImage from '@/assets/images/firstbackgound.jpg';
import LoadingScreen from '@/components/loading';
import { checkServerHealth, initGame, initializeStory, getScenes, getStaticAssetUrl } from '@/services/api';
import { ROUTES } from '@/config/routes';
import * as gameStorage from '@/storage/gameStorage';
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
    name: data.name || 'Unnamed Scene',
    description: data.description || '',
    imageUrl,
  };
};

function FirstMeetingSelection() {
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('Loading scenes...');
  const [currentSceneIndex, setCurrentSceneIndex] = useState(0);
  const [sceneOptions, setSceneOptions] = useState<SceneOption[]>([]);

  const wheelTimeoutRef = useRef<number | null>(null);
  const isWheelingRef = useRef(false);

  useEffect(() => {
    const loadScenes = async () => {
      setLoading(true);
      setLoadingMessage('Loading scenes...');

      try {
        const isHealthy = await checkServerHealth();
        if (!isHealthy) {
          message.error('Backend is unavailable.');
          setSceneOptions([]);
          return;
        }

        const response = (await getScenes()) as SceneApiResponse | null | undefined;
        const scenesData = Array.isArray(response?.scenes) ? response.scenes : [];

        if (scenesData.length === 0) {
          message.warning('No scenes available.');
          setSceneOptions([]);
          return;
        }

        const scenes = scenesData.map((scene, index) => normalizeScene(scene, index));
        setSceneOptions(scenes);
      } catch (error: unknown) {
        const err = error as { response?: { data?: { message?: string } }; message?: string };
        message.error(err.response?.data?.message || err.message || 'Failed to load scenes.');
        setSceneOptions([
          {
            id: 'school',
            name: 'School',
            description: 'A lively campus scene.',
          },
        ]);
      } finally {
        setLoading(false);
      }
    };

    void loadScenes();
  }, [message]);

  const currentScene = sceneOptions.length > 0 ? sceneOptions[currentSceneIndex] : null;

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
      message.error('No scene selected.');
      return;
    }

    try {
      const isHealthy = await checkServerHealth();
      if (!isHealthy) {
        message.error('Backend is unavailable.');
        return;
      }

      const characterData = gameStorage.getCharacterData();
      if (!characterData?.characterId) {
        message.error('Character is missing, please create one first.');
        navigate(ROUTES.CHARACTER_SETTING);
        return;
      }

      const characterId = characterData.characterId;
      gameStorage.setCharacterData({ ...characterData, selectedScene });

      setLoading(true);
      setLoadingMessage('Initializing game...');

      const initResponse = await initGame({
        game_mode: 'solo',
        character_id: characterId,
      });

      const threadId = initResponse?.thread_id as string | undefined;
      if (!threadId) throw new Error('Missing thread_id from initGame response.');

      setLoadingMessage('Preparing first scene...');

      const characterImageUrl =
        characterData.selectedImageUrl || characterData.originalImageUrl || characterData.imageUrl;

      const storyResponse = (await initializeStory(
        threadId,
        characterId,
        selectedScene.id,
        characterImageUrl
      )) as StoryInitResponse;

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
      navigate(ROUTES.GAME);
    } catch (error: unknown) {
      const err = error as { message?: string; response?: { data?: { message?: string } } };
      let errorMessage = 'Failed to select scene, please try again.';
      if (err.message?.includes('timeout')) {
        errorMessage = 'Initialization timed out, please try again shortly.';
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
            <p>No scenes available.</p>
            <Button onClick={() => navigate(ROUTES.CHARACTER_SETTING)}>Back To Character Setup</Button>
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
          <span className="title-text">First Meeting</span>
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
            Choose
          </Button>
        </div>
      </div>
    </div>
  );
}

export default FirstMeetingSelection;

