import { useEffect, useState, useCallback } from 'react';
import { Typography, Spin, Button, Modal, App as AntdApp } from 'antd';
import { ArrowLeftOutlined, SoundOutlined, AudioMutedOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { processGameInput, initGame } from '@/services/api';
import SceneTransition from '@/components/SceneTransition';
import { GameSceneBackground, GameDialogue } from '@/components/Game';
import { SCENE_CONFIGS, getSceneImageUrl, buildSceneImageUrl, getSceneNameById } from '@/config/scenes';
import * as gameStorage from '@/storage/gameStorage';
import { getFallbackSceneImageUrls } from '@/utils/game';
import { logger } from '@/utils/logger';
import { useGameState, useGameInit, useGameTts, useTtsControls } from '@/hooks';
import type { PlayerOption } from '@/types/game';
import { ROUTES } from '@/config/routes';
import './Game.css';

const { Text } = Typography;

const LOADING_TIPS = [
  '正在构思剧情...',
  '角色正在思考...',
  '整理对话中...',
  '即将呈现...',
];

function Game() {
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const state = useGameState();
  const { saveGameProgress, setCharacterImage } = useGameInit(state);
  const { ttsEnabled, setTtsEnabled, ttsVolume, stopTts } = useTtsControls();
  useGameTts(state.currentDialogue, state.characterId, { enabled: ttsEnabled, volume: ttsVolume });
  const { messages, threadId, characterId, scrollToBottom } = state;

  // 退出确认
  const [showExitConfirm, setShowExitConfirm] = useState(false);
  // Loading 进度提示
  const [tipIndex, setTipIndex] = useState(0);

  useEffect(() => {
    const characterData = gameStorage.getCharacterData();
    if (characterData?.voiceConfig) logger.debug('[游戏] 角色音色配置:', characterData.voiceConfig);
  }, []);

  useEffect(() => {
    scrollToBottom();
    if (threadId && messages.length > 0) {
      saveGameProgress(threadId, messages, characterId ?? undefined);
    }
  }, [messages, threadId, characterId, scrollToBottom, saveGameProgress]);

  // Loading 提示轮播
  useEffect(() => {
    if (!state.loading) { setTipIndex(0); return; }
    const timer = setInterval(() => {
      setTipIndex((prev) => (prev + 1) % LOADING_TIPS.length);
    }, 3000);
    return () => clearInterval(timer);
  }, [state.loading]);

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Escape: 退出确认
      if (e.key === 'Escape') {
        setShowExitConfirm(true);
        return;
      }
      // 数字键 1-3: 选择选项
      if (state.loading) return;
      const num = parseInt(e.key);
      if (num >= 1 && num <= 3 && state.currentOptions.length >= num) {
        handleOptionSelect(num - 1);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [state.loading, state.currentOptions]);

  const handleSceneChange = (newScene: string | null) => {
    if (!newScene) return;
    if (state.previousSceneRef.current !== newScene && state.previousSceneRef.current !== null) {
      state.setActNumber((n) => n + 1);
      state.setTransitionSceneName(getSceneNameById(newScene));
      state.setShowTransition(true);
    }
    state.previousSceneRef.current = newScene;
    state.setCurrentScene(newScene);
  };

  const handleGameResponse = (responseData: {
    scene?: string;
    composite_image_url?: string;
    scene_image_url?: string;
    character_dialogue?: string;
    player_options?: PlayerOption[];
    is_game_finished?: boolean;
  }) => {
    if (responseData.scene && responseData.scene !== state.currentScene) {
      handleSceneChange(responseData.scene);
    }
    if (responseData.composite_image_url) {
      state.setCompositeImageUrl(responseData.composite_image_url);
      state.setShouldUseComposite(true);
      state.setSceneImageUrl(null);
      state.setCharacterImageUrl(null);
    } else if (responseData.scene_image_url) {
      state.setShouldUseComposite(false);
      state.setSceneImageUrl(responseData.scene_image_url);
    } else if (responseData.scene) {
      const sceneConfig = SCENE_CONFIGS.find((s) => s.id === responseData.scene);
      if (sceneConfig) {
        const sceneUrl = getSceneImageUrl(sceneConfig);
        if (sceneUrl) state.setSceneImageUrl(sceneUrl);
        else {
          const ext = sceneConfig.imageExtensions?.[0] ?? '.jpeg';
          state.setSceneImageUrl(buildSceneImageUrl(sceneConfig.id, sceneConfig.name, ext));
        }
      } else {
        state.setSceneImageUrl(getFallbackSceneImageUrls(responseData.scene)[0]);
      }
      if (!state.characterImageUrl) {
        setCharacterImage(state.characterId || gameStorage.getCurrentCharacterId());
      }
    }
    if (responseData.character_dialogue) {
      state.setCurrentDialogue(responseData.character_dialogue);
      state.setMessages((prev) => [...prev, { role: 'assistant', content: responseData.character_dialogue! }]);
    }
    if (Array.isArray(responseData.player_options)) state.setCurrentOptions(responseData.player_options);
    else state.setCurrentOptions([]);
    if (responseData.is_game_finished) message.info('游戏结束');
  };

  const handleOptionSelect = useCallback(async (optionId: number) => {
    if (state.loading || !state.threadId) return;
    const selectedOption = state.currentOptions[optionId];
    if (!selectedOption) return;

    state.setMessages((prev) => [...prev, { role: 'user', content: selectedOption.text }]);
    state.setCurrentOptions([]);
    state.setCurrentDialogue('');
    state.setLoading(true);

    try {
      const response = await processGameInput({
        thread_id: state.threadId,
        user_input: `option:${optionId + 1}`,
        character_id: state.characterId || gameStorage.getCurrentCharacterId() || undefined,
      });
      const responseThreadId = response?.thread_id;
      if (responseThreadId && responseThreadId !== state.threadId) {
        state.setThreadId(responseThreadId);
        message.info('游戏会话已恢复');
      }
      handleGameResponse(response);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } }; message?: string };
      logger.error('处理选项失败', err);
      let errorMessage = '处理选项失败，请稍后重试';
      const errorMsg = err.response?.data?.message || err.message || '';

      if (errorMsg.includes('会话已过期') || errorMsg.includes('not found') || errorMsg.includes('无法恢复')) {
        errorMessage = '游戏会话已过期。正在尝试恢复...';
        message.warning(errorMessage);
        const charId = state.characterId || gameStorage.getCurrentCharacterId();
        if (charId) {
          try {
            const initResponse = await initGame({ game_mode: 'solo', character_id: charId });
            const newThreadId = initResponse?.thread_id;
            if (newThreadId) {
              state.setThreadId(newThreadId);
              gameStorage.setGameIds(newThreadId, charId);
              message.success('游戏会话已恢复，请重新选择选项');
              return;
            }
          } catch (recoverError) {
            logger.error('[游戏恢复] 恢复失败', recoverError);
            errorMessage = '游戏会话已过期且无法恢复，请返回重新开始游戏';
          }
        } else errorMessage = '游戏会话已过期，请返回重新开始游戏';
        message.error(errorMessage);
      } else if (err.message?.includes('超时')) {
        message.error('处理选项超时，AI生成可能需要更长时间。请稍后重试，或检查网络连接。');
      } else if (err.response?.data?.message) {
        message.error(err.response.data.message);
      } else {
        message.error(errorMessage);
      }
      state.setMessages((prev) => prev.filter((_, idx) => idx !== prev.length - 1 || prev[prev.length - 1]?.role !== 'user'));
    } finally {
      state.setLoading(false);
    }
  }, [state.loading, state.threadId, state.currentOptions, state.characterId]);

  const handleExit = () => {
    stopTts();
    saveGameProgress(state.threadId!, messages, state.characterId ?? undefined);
    setShowExitConfirm(false);
    navigate(ROUTES.FIRST_STEP);
  };

  // 获取角色名称
  const characterName = gameStorage.getCharacterData()?.name || '角色';

  return (
    <div className="game-scene-container">
      {/* 左上角：退出按钮 */}
      <div className="game-top-left-controls">
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => setShowExitConfirm(true)}
          className="game-control-btn"
        />
      </div>

      {/* 右上角：音频控制 */}
      <div className="game-top-right-controls">
        <Button
          type="text"
          icon={ttsEnabled ? <SoundOutlined /> : <AudioMutedOutlined />}
          onClick={() => setTtsEnabled(!ttsEnabled)}
          className="game-control-btn"
        />
      </div>

      {/* 退出确认弹窗 */}
      <Modal
        title="确认退出"
        open={showExitConfirm}
        onOk={handleExit}
        onCancel={() => setShowExitConfirm(false)}
        okText="保存并退出"
        cancelText="继续游戏"
      >
        <p>退出将自动保存当前进度，下次可以继续。</p>
      </Modal>

      {/* 场景转场动画 */}
      {state.showTransition && (
        <SceneTransition
          sceneName={state.transitionSceneName}
          actNumber={state.actNumber}
          onComplete={() => state.setShowTransition(false)}
        />
      )}

      {/* Loading 覆盖层 */}
      {state.loading && (
        <div className="game-loading-overlay">
          <div className="game-loading-content">
            <Spin size="large" />
            <div style={{ marginTop: '16px' }}>
              <Text>{LOADING_TIPS[tipIndex]}</Text>
            </div>
          </div>
        </div>
      )}

      {/* 场景背景 */}
      <div className="game-scene-background">
        <GameSceneBackground
          shouldUseComposite={state.shouldUseComposite}
          compositeImageUrl={state.compositeImageUrl}
          sceneImageUrl={state.sceneImageUrl}
          characterImageUrl={state.characterImageUrl}
        />
      </div>

      {/* 对话区域（含历史 + 打字机效果） */}
      <GameDialogue
        currentDialogue={state.currentDialogue}
        currentOptions={state.currentOptions}
        loading={state.loading}
        onOptionSelect={handleOptionSelect}
        messages={messages}
        characterName={characterName}
        typeSpeed={30}
      />
    </div>
  );
}

export default Game;
