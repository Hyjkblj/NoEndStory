import { useEffect, useCallback, useRef } from 'react';
import { App as AntdApp } from 'antd';
import { useNavigate } from 'react-router-dom';
import { GuestEndingLimitError, initGame, initializeStory, getCharacterImages } from '@/services/api';
import * as gameStorage from '@/storage/gameStorage';
import { getSceneNameById } from '@/config/scenes';
import { ROUTES } from '@/config/routes';
import { getCharacterLayerImageFromStorage, isLikelyTransparentCharacterLayer } from '@/utils/game';
import { logger } from '@/utils/logger';
import type { GameMessage, PlayerOption } from '@/types/game';
import type { GameStateBag } from './useGameState';

export interface UseGameInitResult {
  loadGameSave: (threadId: string) => void;
  saveGameProgress: (threadId: string, messages: GameMessage[], characterId?: string) => void;
  setCharacterImage: (characterId: string | null) => void;
}

interface StoryData {
  scene?: string;
  scene_image_url?: string;
  composite_image_url?: string;
  story_background?: string;
  character_dialogue?: string;
  player_options?: PlayerOption[];
}

export function useGameInit(state: GameStateBag): UseGameInitResult {
  const { message } = AntdApp.useApp();
  const navigate = useNavigate();
  const {
    setMessages,
    setThreadId,
    setCharacterId,
    setCurrentScene,
    setTransitionSceneName,
    setActNumber,
    setShowTransition,
    setCurrentDialogue,
    setCurrentOptions,
    setCompositeImageUrl,
    setShouldUseComposite,
    setSceneImageUrl,
    setCharacterImageUrl,
    previousSceneRef,
  } = state;

  const loadCharacterImageFromAPI = useCallback(
    (characterId: string | null) => {
      if (!characterId || characterId === 'undefined' || characterId === 'null' || String(characterId).trim() === '') return;
      getCharacterImages(String(characterId))
        .then((data) => {
          const layerImage = data?.images?.find(isLikelyTransparentCharacterLayer);
          if (layerImage) setCharacterImageUrl(layerImage);
          else logger.warn('[game] no transparent character layer found for layered rendering');
        })
        .catch((error: unknown) => {
          const err = error as { message?: string };
          logger.warn('[game] failed to fetch character images:', err.message || error);
        });
    },
    [setCharacterImageUrl]
  );

  const setCharacterImage = useCallback(
    (characterId: string | null) => {
      const imageUrl = getCharacterLayerImageFromStorage();
      if (imageUrl) {
        setCharacterImageUrl(imageUrl);
        return;
      }
      loadCharacterImageFromAPI(characterId);
    },
    [setCharacterImageUrl, loadCharacterImageFromAPI]
  );

  const loadGameSave = useCallback(
    (threadId: string) => {
      try {
        const save = gameStorage.getGameSave(threadId);
        if (save?.messages?.length) {
          setMessages(save.messages);
          message.success('存档已加载');
        }
      } catch (error: unknown) {
        logger.error('failed to load save:', error);
        message.error('加载存档失败');
      }
    },
    [setMessages, message]
  );

  const saveGameProgress = useCallback(
    (threadId: string, messages: GameMessage[], characterId?: string) => {
      try {
        const lastMessage = messages.length > 0 ? messages[messages.length - 1].content : undefined;
        gameStorage.setGameSave({ threadId, characterId, messages, lastMessage, timestamp: Date.now() });
        gameStorage.setMainGameSave({ threadId, characterId, lastMessage, timestamp: Date.now() });
        gameStorage.cleanupGuestOldGameData({ keepThreadId: threadId, keepLatestEnding: true });
      } catch (error: unknown) {
        logger.error('failed to save progress:', error);
      }
    },
    []
  );

  const applySceneTransition = useCallback(
    (sceneId: string, sceneName?: string) => {
      setCurrentScene(sceneId);
      previousSceneRef.current = sceneId;
      setTransitionSceneName(sceneName || getSceneNameById(sceneId));
      setActNumber(1);
      setShowTransition(true);
    },
    [previousSceneRef, setActNumber, setCurrentScene, setShowTransition, setTransitionSceneName]
  );

  const applyStoryData = useCallback(
    (storyData: StoryData, characterId: string) => {
      if (storyData.scene) {
        applySceneTransition(storyData.scene);
      }

      if (storyData.composite_image_url) {
        setCompositeImageUrl(storyData.composite_image_url);
        setShouldUseComposite(true);
        setSceneImageUrl(null);
        setCharacterImageUrl(null);
      } else if (storyData.scene_image_url) {
        setShouldUseComposite(false);
        setSceneImageUrl(storyData.scene_image_url);
        setCharacterImage(characterId);
      } else if (storyData.scene) {
        setShouldUseComposite(false);
        setSceneImageUrl(null);
        logger.warn('[游戏初始化] 后端未返回场景图片，停止使用前端猜测路径', {
          scene: storyData.scene,
        });
        setCharacterImage(characterId);
      }

      if (storyData.character_dialogue) setCurrentDialogue(storyData.character_dialogue);
      if (Array.isArray(storyData.player_options)) setCurrentOptions(storyData.player_options);
    },
    [
      applySceneTransition,
      setCharacterImage,
      setCharacterImageUrl,
      setCompositeImageUrl,
      setCurrentDialogue,
      setCurrentOptions,
      setSceneImageUrl,
      setShouldUseComposite,
    ]
  );

  const initializeGame = useCallback(async () => {
    const restoreThreadId = gameStorage.getRestoreThreadId();
    const characterData = gameStorage.getCharacterData();

    if (restoreThreadId) {
      loadGameSave(restoreThreadId);
      setThreadId(restoreThreadId);
      gameStorage.removeRestoreIds();
      return;
    }

    const gameThreadId = gameStorage.getGameThreadId();
    const gameCharacterId = gameStorage.getGameCharacterId();

    if (gameThreadId && gameCharacterId) {
      setThreadId(gameThreadId);
      setCharacterId(gameCharacterId);
      gameStorage.setCurrentCharacterId(gameCharacterId);

      const initialGameData = gameStorage.getInitialGameData();
      if (initialGameData) {
        try {
          if (initialGameData.scene) {
            applySceneTransition(initialGameData.scene);
          } else if (characterData?.selectedScene?.id) {
            applySceneTransition(characterData.selectedScene.id, characterData.selectedScene.name);
          }

          if (initialGameData.composite_image_url || initialGameData.scene_image_url || initialGameData.scene) {
            applyStoryData(initialGameData, gameCharacterId);
          }

          const initialMessages: GameMessage[] = [];
          if (initialGameData.character_dialogue) {
            initialMessages.push({ role: 'assistant', content: initialGameData.character_dialogue });
          }
          if (initialMessages.length > 0) setMessages(initialMessages);

          setCharacterImage(gameCharacterId);
          gameStorage.clearInitialGameData();
        } catch (error: unknown) {
          logger.error('failed to parse initial game data', error);
        }
      } else if (characterData?.selectedScene?.id) {
        try {
          applySceneTransition(characterData.selectedScene.id, characterData.selectedScene.name);

          const imageUrl = getCharacterLayerImageFromStorage();
          const storyData = (await initializeStory(
            gameThreadId,
            gameCharacterId,
            characterData.selectedScene.id,
            imageUrl
          )) as StoryData;

          applyStoryData(storyData, gameCharacterId);
        } catch (error: unknown) {
          logger.error('failed to fetch initial story data', error);
        }
      }

      gameStorage.removeGameThreadId();
      return;
    }

    if (characterData?.characterId) {
      const charId = characterData.characterId;
      setCharacterId(charId);
      gameStorage.setCurrentCharacterId(charId);

      try {
        const initRes = await initGame({ game_mode: 'solo', character_id: charId });
        const newThreadId = initRes?.thread_id as string | undefined;
        if (!newThreadId) {
          message.error('Missing thread id, cannot initialize game.');
          return;
        }

        setThreadId(newThreadId);
        const imageUrl = getCharacterLayerImageFromStorage();
        const storyData = (await initializeStory(newThreadId, charId, undefined, imageUrl)) as StoryData;

        applyStoryData(storyData, charId);

        const initialMessages: GameMessage[] = [];
        if (storyData.story_background) {
          initialMessages.push({ role: 'assistant', content: storyData.story_background });
        }
        if (storyData.character_dialogue) {
          initialMessages.push({ role: 'assistant', content: storyData.character_dialogue });
        }
        setMessages(initialMessages);
      } catch (error: unknown) {
        if (error instanceof GuestEndingLimitError) {
          logger.warn('[game] guest ending limit blocked game initialization');
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

        logger.error('failed to initialize game', error);
        message.error('Failed to initialize game.');
      }
    }
  }, [
    applySceneTransition,
    applyStoryData,
    loadGameSave,
    message,
    navigate,
    setCharacterId,
    setCharacterImage,
    setMessages,
    setThreadId,
  ]);

  const initializedRef = useRef(false);
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    void initializeGame();
  }, [initializeGame]);

  return { loadGameSave, saveGameProgress, setCharacterImage };
}

