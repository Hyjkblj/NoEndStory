import { useEffect, useCallback, useRef } from 'react';
import { App as AntdApp } from 'antd';
import { initGame, initializeStory, getCharacterImages } from '@/services/api';
import * as gameStorage from '@/storage/gameStorage';
import { getSceneNameById } from '@/config/scenes';
import { getCharacterImageFromStorage, getFallbackSceneImageUrls } from '@/utils/game';
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
          if (data?.images?.length) setCharacterImageUrl(data.images[0]);
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
      const imageUrl = getCharacterImageFromStorage();
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
          message.success('Save loaded.');
        }
      } catch (error: unknown) {
        logger.error('failed to load save:', error);
        message.error('Failed to load save.');
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
        setSceneImageUrl(getFallbackSceneImageUrls(storyData.scene)[0]);
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

          const imageUrl = getCharacterImageFromStorage();
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
        const imageUrl = getCharacterImageFromStorage();
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
        logger.error('failed to initialize game', error);
        message.error('Failed to initialize game.');
      }
    }
  }, [
    applySceneTransition,
    applyStoryData,
    loadGameSave,
    message,
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

