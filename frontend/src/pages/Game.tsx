import { useEffect, useState, useCallback } from 'react';
import { Typography, Spin, Button, Modal, App as AntdApp } from 'antd';
import {
  ArrowLeftOutlined,
  SoundOutlined,
  AudioMutedOutlined,
  SaveOutlined,
  ReloadOutlined,
  HomeOutlined,
  UserAddOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { processGameInput, initGame, getStaticAssetUrl, isGuestEndingLimitError } from '@/services/api';
import SceneTransition from '@/components/SceneTransition';
import { useRouteTransition, useRouteTransitionReady } from '@/hooks/useRouteTransition';
import { GameSceneBackground, GameDialogue } from '@/components/Game';
import { getSceneNameById } from '@/config/scenes';
import * as gameStorage from '@/storage/gameStorage';
import { logger } from '@/utils/logger';
import { useGameState, useGameInit, useGameTts, useTtsControls } from '@/hooks';
import type { EndingMemory, EndingRecord, EndingRelationshipMetric, PlayerOption } from '@/types/game';
import { ROUTES } from '@/config/routes';
import './Game.css';

const { Text } = Typography;

const LOADING_TIPS = [
  '正在构思剧情...',
  '角色正在思考...',
  '整理对话中...',
  '即将呈现...',
];

type GameResponseData = {
  thread_id?: string;
  scene?: string;
  composite_image_url?: string;
  scene_image_url?: string;
  story_background?: string;
  character_dialogue?: string;
  final_dialogue?: string;
  player_options?: PlayerOption[];
  is_game_finished?: boolean;
  event_title?: string;
  ending_title?: string;
  ending_type?: string;
  ending_description?: string;
  current_states?: Record<string, number> | null;
  state_changes?: Record<string, number>;
  tts_emotion?: Record<string, unknown> | null;
  guest_ending_limited?: boolean;
};

const ENDING_TYPE_LABELS: Record<string, string> = {
  good_ending: '甜蜜结局',
  sweet_ending: '甜蜜结局',
  neutral_ending: '暧昧未满',
  open_ending: '未完待续',
  bad_ending: '遗憾结局',
  distant_ending: '疏离结局',
  fragile_ending: '摇晃结局',
};

const RELATIONSHIP_LABELS: Array<{ key: string; label: string; tone: EndingRelationshipMetric['tone'] }> = [
  { key: 'favorability', label: '好感', tone: 'warm' },
  { key: 'trust', label: '信任', tone: 'soft' },
  { key: 'dependence', label: '依赖', tone: 'warm' },
  { key: 'emotion', label: '心绪', tone: 'soft' },
  { key: 'stress', label: '压力', tone: 'tense' },
];

const getNumericState = (states: Record<string, number> | null | undefined, key: string): number | null => {
  const value = states?.[key];
  return typeof value === 'number' && Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : null;
};

const formatMetricValue = (value: number | null | undefined) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null;
  return Math.round(Math.max(0, Math.min(100, value)));
};

const inferEndingType = (states: Record<string, number> | null | undefined): string => {
  const favorability = getNumericState(states, 'favorability') ?? 50;
  const trust = getNumericState(states, 'trust') ?? 50;
  const hostility = getNumericState(states, 'hostility') ?? 0;
  const stress = getNumericState(states, 'stress') ?? 0;
  const anxiety = getNumericState(states, 'anxiety') ?? 0;

  if (favorability >= 70 && trust >= 60) return 'sweet_ending';
  if (hostility >= 60 || favorability <= 30) return 'distant_ending';
  if (stress >= 75 || anxiety >= 70) return 'fragile_ending';
  return 'open_ending';
};

const buildRelationshipMetrics = (states: Record<string, number> | null | undefined): EndingRelationshipMetric[] => (
  RELATIONSHIP_LABELS.map(({ key, label, tone }) => ({
    key,
    label,
    tone,
    value: getNumericState(states, key),
  }))
);

const getEndingDescription = (endingType: string, responseData: GameResponseData): string => {
  if (responseData.ending_description) return responseData.ending_description;
  if (responseData.story_background) return responseData.story_background;

  if (endingType === 'sweet_ending' || endingType === 'good_ending') {
    return '你们把一段关系慢慢推近，许多未说出口的话终于有了回应。';
  }
  if (endingType === 'distant_ending' || endingType === 'bad_ending') {
    return '有些靠近停在了半路，但那些选择依然成为这段故事真实的痕迹。';
  }
  if (endingType === 'fragile_ending') {
    return '心跳和不安交错在一起，这段关系停在了仍需确认的地方。';
  }
  return '这段故事暂时收束，但你们之间仍留下了可以被重新打开的余温。';
};

const buildEndingMemories = (
  responseData: GameResponseData,
  params: {
    sceneName: string;
    finalDialogue: string;
    lastChoice?: string;
    endingTypeLabel: string;
  }
): EndingMemory[] => {
  const memories: EndingMemory[] = [
    {
      title: '初遇被安放在这里',
      description: `这段故事最终停在「${params.sceneName}」的光线里。`,
    },
  ];

  if (params.lastChoice) {
    memories.push({
      title: '最后的选择',
      description: '你把这一刻推向了最终结局。',
      choice: params.lastChoice,
    });
  }

  if (params.finalDialogue) {
    memories.push({
      title: '最后一句对白',
      description: params.finalDialogue,
    });
  }

  memories.push({
    title: '关系被封存为',
    description: params.endingTypeLabel,
  });

  if (responseData.story_background && responseData.story_background !== params.finalDialogue) {
    memories.push({
      title: '结局旁白',
      description: responseData.story_background,
    });
  }

  return memories.slice(0, 5);
};

function Game() {
  const navigate = useNavigate();
  const { message, modal } = AntdApp.useApp();
  const state = useGameState();
  const { saveGameProgress, setCharacterImage } = useGameInit(state);
  const { activeTransitionId, failRouteTransition } = useRouteTransition();
  const { ttsEnabled, setTtsEnabled, ttsVolume, stopTts } = useTtsControls();
  const { messages, threadId, characterId, scrollToBottom } = state;
  const { setCurrentOptions, setLoading, setShowTransition } = state;

  // 退出确认
  const [showExitConfirm, setShowExitConfirm] = useState(false);
  // Loading 进度提示
  const [tipIndex, setTipIndex] = useState(0);
  // 游戏结束状态
  const [gameFinished, setGameFinished] = useState(false);
  const [endingTitle, setEndingTitle] = useState('故事落幕');
  const [endingRecord, setEndingRecord] = useState<EndingRecord | null>(null);
  const [endingSaved, setEndingSaved] = useState(false);
  const [isGuestEndingLimited, setIsGuestEndingLimited] = useState(false);
  // 场景/角色分层画面渲染异常时停止当前交互
  const [visualError, setVisualError] = useState<string | null>(null);
  const [visualReady, setVisualReady] = useState(false);
  // TTS 情感参数（从后端响应中获取）
  const [ttsEmotionParams, setTtsEmotionParams] = useState<Record<string, unknown> | null>(null);
  // 获取角色名称
  const characterName = gameStorage.getCharacterData()?.name || '角色';

  // TTS 播放（带情感参数）
  useGameTts(state.currentDialogue, state.characterId, {
    enabled: ttsEnabled,
    volume: ttsVolume,
    emotion_params: ttsEmotionParams,
  });

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
      // 游戏结束或加载中时禁用选项快捷键
      if (state.loading || gameFinished) return;
      // 数字键 1-3: 选择选项
      const num = parseInt(e.key);
      if (num >= 1 && num <= 3 && state.currentOptions.length >= num) {
        handleOptionSelect(num - 1);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [state.loading, state.currentOptions, gameFinished]);

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

  const ensureCharacterLayer = () => {
    if (state.characterImageUrl) return;
    setCharacterImage(state.characterId || gameStorage.getCurrentCharacterId());
  };

  const visualKey = `${state.compositeImageUrl ?? ''}|${state.sceneImageUrl ?? ''}|${state.characterImageUrl ?? ''}`;
  const expectedVisual = Boolean(state.compositeImageUrl || state.sceneImageUrl || state.characterImageUrl);
  const hasStoryContent = Boolean(
    state.currentDialogue || state.currentOptions.length > 0 || messages.length > 0
  );
  const gameRouteReady = Boolean(
    gameFinished ||
    (!visualError && !state.loading && state.threadId && expectedVisual && visualReady)
  );

  useEffect(() => {
    setVisualReady(false);
  }, [visualKey]);

  useRouteTransitionReady(gameRouteReady, { delayMs: 180 });

  const handleVisualReady = useCallback(() => {
    setVisualReady(true);
    setVisualError(null);
  }, []);

  const handleVisualError = useCallback(
    (errorMessage: string) => {
      logger.error('[游戏画面] 分层渲染停止:', errorMessage);
      setVisualError(errorMessage);
      failRouteTransition(errorMessage, activeTransitionId ?? undefined);
      setLoading(false);
      setCurrentOptions([]);
      setShowTransition(false);
      stopTts();
    },
    [activeTransitionId, failRouteTransition, setCurrentOptions, setLoading, setShowTransition, stopTts]
  );

  useEffect(() => {
    if (visualError || gameFinished) return;
    if (state.loading || !state.threadId || !hasStoryContent || expectedVisual) return;

    const timer = window.setTimeout(() => {
      const errorMessage = '缺少可渲染的场景与角色画面，已停止进入游戏。';
      logger.error('[游戏画面] 缺少可渲染画面:', {
        threadId: state.threadId,
        currentScene: state.currentScene,
      });
      setVisualError(errorMessage);
      failRouteTransition(errorMessage, activeTransitionId ?? undefined);
      setCurrentOptions([]);
      setShowTransition(false);
      stopTts();
    }, 12000);

    return () => window.clearTimeout(timer);
  }, [
    activeTransitionId,
    expectedVisual,
    failRouteTransition,
    gameFinished,
    hasStoryContent,
    setCurrentOptions,
    setShowTransition,
    state.currentScene,
    state.loading,
    state.threadId,
    stopTts,
    visualError,
  ]);

  const createEndingRecord = (responseData: GameResponseData, lastChoice?: string): EndingRecord => {
    const sceneId = responseData.scene || state.currentScene || undefined;
    const sceneName = sceneId ? getSceneNameById(sceneId) : '最后的场景';
    const endingType = responseData.ending_type || inferEndingType(responseData.current_states);
    const endingTypeLabel = ENDING_TYPE_LABELS[endingType] || '特别结局';
    const finalDialogue = responseData.final_dialogue || responseData.character_dialogue || state.currentDialogue || '';
    const title = responseData.ending_title || responseData.event_title || endingTypeLabel;
    const threadIdValue = responseData.thread_id || state.threadId || `local-${Date.now()}`;

    return {
      id: `ending-${threadIdValue}-${Date.now()}`,
      threadId: threadIdValue,
      characterId: state.characterId || gameStorage.getCurrentCharacterId() || undefined,
      characterName,
      title,
      type: endingType,
      typeLabel: endingTypeLabel,
      description: getEndingDescription(endingType, responseData),
      finalDialogue,
      sceneId,
      sceneName,
      createdAt: Date.now(),
      relationship: buildRelationshipMetrics(responseData.current_states),
      keyMemories: buildEndingMemories(responseData, {
        sceneName,
        finalDialogue,
        lastChoice,
        endingTypeLabel,
      }),
      visual: {
        compositeImageUrl: responseData.composite_image_url || state.compositeImageUrl,
        sceneImageUrl: responseData.scene_image_url || state.sceneImageUrl,
        characterImageUrl: state.characterImageUrl,
      },
    };
  };

  const handleGameResponse = (responseData: GameResponseData, lastChoice?: string) => {
    setVisualError(null);
    if (!responseData.is_game_finished) setIsGuestEndingLimited(false);

    // 更新 TTS 情感参数
    if (responseData.tts_emotion) {
      setTtsEmotionParams(responseData.tts_emotion);
    }

    if (responseData.scene && responseData.scene !== state.currentScene) {
      handleSceneChange(responseData.scene);
    }
    if (responseData.composite_image_url) {
      state.setCompositeImageUrl(responseData.composite_image_url);
      state.setShouldUseComposite(true);
      state.setSceneImageUrl(null);
      state.setCharacterImageUrl(null);
    } else if (responseData.scene_image_url) {
      state.setCompositeImageUrl(null);
      state.setShouldUseComposite(false);
      state.setSceneImageUrl(responseData.scene_image_url);
      ensureCharacterLayer();
    } else if (responseData.scene) {
      state.setCompositeImageUrl(null);
      state.setShouldUseComposite(false);
      state.setSceneImageUrl(null);
      logger.warn('[游戏画面] 后端未返回场景图片，停止使用前端猜测路径', {
        scene: responseData.scene,
      });
      ensureCharacterLayer();
    }
    if (responseData.character_dialogue) {
      state.setCurrentDialogue(responseData.character_dialogue);
      state.setMessages((prev) => [...prev, { role: 'assistant', content: responseData.character_dialogue! }]);
    }
    if (Array.isArray(responseData.player_options)) state.setCurrentOptions(responseData.player_options);
    else state.setCurrentOptions([]);
    // 结局处理：标记结束状态，清空选项
    if (responseData.is_game_finished) {
      const record = createEndingRecord(responseData, lastChoice);
      setGameFinished(true);
      setEndingRecord(record);
      setEndingSaved(false);
      state.setCurrentOptions([]);
      const title = record.title || '故事落幕';
      setEndingTitle(title);
      setIsGuestEndingLimited(responseData.guest_ending_limited !== false);
    }
  };

  const handleOptionSelect = useCallback(async (optionId: number) => {
    if (state.loading || !state.threadId || gameFinished || visualError) return;
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
      handleGameResponse(response, selectedOption.text);
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
            if (isGuestEndingLimitError(recoverError)) {
              message.warning(recoverError.message || '这次游客体验已经完成，24小时后可再次开启。');
              navigate(ROUTES.FIRST_STEP, { replace: true });
              return;
            }
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
  }, [state.loading, state.threadId, state.currentOptions, state.characterId, gameFinished, visualError]);

  const handleExit = () => {
    stopTts();
    saveGameProgress(state.threadId!, messages, state.characterId ?? undefined);
    setShowExitConfirm(false);
    navigate(ROUTES.FIRST_STEP);
  };

  const handleSaveEnding = () => {
    if (!endingRecord) return;
    gameStorage.saveEndingRecord(endingRecord);
    gameStorage.cleanupGuestOldGameData({ keepThreadId: null, keepLatestEnding: true });
    setEndingSaved(true);
    message.success('这段回忆已经保存');
  };

  const handleRestartAfterEnding = () => {
    if (isGuestEndingLimited) {
      showRegisterHint();
      return;
    }

    stopTts();
    gameStorage.cleanupGuestOldGameData({
      keepThreadId: null,
      keepLatestEnding: false,
      clearCharacterData: true,
      clearSession: true,
    });
    navigate(ROUTES.CHARACTER_SETTING);
  };

  const showRegisterHint = () => {
    modal.info({
      title: '注册后可以继续新的旅程',
      content: (
        <div className="game-guest-limit-content">
          <p>游客模式今天已经完成一段故事。注册账号后，可以继续开启更多相遇，并保留更多结局回忆。</p>
        </div>
      ),
      okText: '我知道了',
      className: 'game-guest-limit-modal',
      icon: <UserAddOutlined className="game-guest-limit-icon" />,
    });
  };

  const handleBackHomeAfterEnding = () => {
    if (endingRecord && !endingSaved) gameStorage.saveEndingRecord(endingRecord);
    stopTts();
    gameStorage.cleanupGuestOldGameData({
      keepThreadId: null,
      keepLatestEnding: true,
      clearSession: true,
    });
    navigate(ROUTES.HOME);
  };

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
          compositeImageUrl={state.compositeImageUrl}
          sceneImageUrl={state.sceneImageUrl}
          characterImageUrl={state.characterImageUrl}
          expected={Boolean(state.compositeImageUrl || state.sceneImageUrl || state.characterImageUrl)}
          onVisualReady={handleVisualReady}
          onVisualError={handleVisualError}
        />
        {visualError && (
          <div className="game-visual-error" role="alert">
            <div className="game-visual-error-card">
              <span>画面渲染已停止</span>
              <p>{visualError}</p>
            </div>
          </div>
        )}
      </div>

      {/* 对话区域（含历史 + 打字机效果） */}
      <GameDialogue
        currentDialogue={state.currentDialogue}
        currentOptions={state.currentOptions}
        loading={state.loading || Boolean(visualError)}
        onOptionSelect={handleOptionSelect}
        characterName={characterName}
        typeSpeed={30}
      />

      {/* 结局覆盖层 */}
      {gameFinished && (
        <section className="game-ending-overlay" aria-live="polite">
          <div className="game-ending-backdrop" />
          <div className="game-ending-shell">
            <div className="game-ending-visual" aria-hidden="true">
              {endingRecord?.visual.compositeImageUrl ? (
                <img
                  src={getStaticAssetUrl(endingRecord.visual.compositeImageUrl)}
                  alt=""
                  className="ending-visual-scene"
                />
              ) : endingRecord?.visual.sceneImageUrl ? (
                <img
                  src={getStaticAssetUrl(endingRecord.visual.sceneImageUrl)}
                  alt=""
                  className="ending-visual-scene"
                />
              ) : (
                <div className="ending-visual-empty" />
              )}
              {endingRecord?.visual.characterImageUrl && !endingRecord.visual.compositeImageUrl && (
                <img
                  src={getStaticAssetUrl(endingRecord.visual.characterImageUrl)}
                  alt=""
                  className="ending-visual-character"
                />
              )}
              <div className="ending-visual-shade" />
            </div>

            <div className="game-ending-content">
              <div className="ending-heading">
                <span className="ending-kicker">No End Story</span>
                <span className="ending-type-badge">{endingRecord?.typeLabel || '特别结局'}</span>
                <h1 className="ending-title">{endingTitle}</h1>
                <p className="ending-description">
                  {endingRecord?.description || '这一段故事抵达了它的终点。'}
                </p>
              </div>

              {endingRecord?.finalDialogue && (
                <blockquote className="ending-final-dialogue">
                  <span>{endingRecord.characterName}</span>
                  <p>{endingRecord.finalDialogue}</p>
                </blockquote>
              )}

              <div className="ending-panel-grid">
                <section className="ending-panel ending-relationship-panel" aria-label="最终关系状态">
                  <div className="ending-panel-header">
                    <span>Final Relation</span>
                    <strong>最终关系</strong>
                  </div>
                  <div className="ending-metrics">
                    {(endingRecord?.relationship || []).map((metric) => {
                      const metricValue = formatMetricValue(metric.value);

                      return (
                        <div key={metric.key} className={`ending-metric ending-metric-${metric.tone || 'quiet'}`}>
                          <div className="ending-metric-row">
                            <span>{metric.label}</span>
                            <strong>{metricValue == null ? '--' : metricValue}</strong>
                          </div>
                          <div className="ending-metric-track">
                            <span style={{ width: `${metricValue ?? 0}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </section>

                <section className="ending-panel ending-memory-panel" aria-label="回忆时间线">
                  <div className="ending-panel-header">
                    <span>Memory Archive</span>
                    <strong>回忆封存</strong>
                  </div>
                  <ol className="ending-memory-list">
                    {(endingRecord?.keyMemories || []).map((memory) => (
                      <li key={`${memory.title}-${memory.description}`}>
                        <span className="ending-memory-dot" />
                        <div>
                          <strong>{memory.title}</strong>
                          <p>{memory.description}</p>
                          {memory.choice && <em>{memory.choice}</em>}
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>
              </div>

              <div className="ending-actions">
                <Button
                  size="large"
                  icon={<SaveOutlined />}
                  onClick={handleSaveEnding}
                  disabled={endingSaved || !endingRecord}
                  className="ending-save-button"
                >
                  {endingSaved ? '已保存' : '保存回忆'}
                </Button>
                {isGuestEndingLimited ? (
                  <Button
                    type="primary"
                    size="large"
                    icon={<UserAddOutlined />}
                    onClick={showRegisterHint}
                    className="ending-primary-button"
                  >
                    注册解锁更多旅程
                  </Button>
                ) : (
                  <Button
                    type="primary"
                    size="large"
                    icon={<ReloadOutlined />}
                    onClick={handleRestartAfterEnding}
                    className="ending-primary-button"
                  >
                    再来一局
                  </Button>
                )}
                <Button
                  size="large"
                  icon={<HomeOutlined />}
                  onClick={handleBackHomeAfterEnding}
                  className="ending-home-button"
                >
                  回到首页
                </Button>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

export default Game;
