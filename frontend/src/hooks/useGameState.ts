import { useState, useRef, useCallback, useMemo } from 'react';
import type { GameMessage, PlayerOption } from '@/types/game';

// ======== W10: 拆分为 4 个独立 Hook ========

/** 对话消息状态 */
export function useDialogueState() {
  const [messages, setMessages] = useState<GameMessage[]>([]);
  const [currentDialogue, setCurrentDialogue] = useState('');
  const [currentOptions, setCurrentOptions] = useState<PlayerOption[]>([]);

  return { messages, setMessages, currentDialogue, setCurrentDialogue, currentOptions, setCurrentOptions };
}

/** 会话元数据状态 */
export function useSessionMeta() {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [characterId, setCharacterId] = useState<string | null>(null);

  return { threadId, setThreadId, characterId, setCharacterId };
}

/** 场景与视觉状态 */
export function useSceneState() {
  const [currentScene, setCurrentScene] = useState<string | null>(null);
  const [sceneImageUrl, setSceneImageUrl] = useState<string | null>(null);
  const [compositeImageUrl, setCompositeImageUrl] = useState<string | null>(null);
  const [characterImageUrl, setCharacterImageUrl] = useState<string | null>(null);
  const [shouldUseComposite, setShouldUseComposite] = useState(false);
  const [showTransition, setShowTransition] = useState(false);
  const [transitionSceneName, setTransitionSceneName] = useState('');
  const previousSceneRef = useRef<string | null>(null);

  return {
    currentScene, setCurrentScene,
    sceneImageUrl, setSceneImageUrl,
    compositeImageUrl, setCompositeImageUrl,
    characterImageUrl, setCharacterImageUrl,
    shouldUseComposite, setShouldUseComposite,
    showTransition, setShowTransition,
    transitionSceneName, setTransitionSceneName,
    previousSceneRef,
  };
}

/** 游戏进度与 UI 状态 */
export function useGameProgress() {
  const [loading, setLoading] = useState(false);
  const [actNumber, setActNumber] = useState(1);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  return { loading, setLoading, actNumber, setActNumber, messagesEndRef, scrollToBottom };
}

export interface GameStateBag {
  messages: GameMessage[];
  setMessages: React.Dispatch<React.SetStateAction<GameMessage[]>>;
  loading: boolean;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  threadId: string | null;
  setThreadId: React.Dispatch<React.SetStateAction<string | null>>;
  characterId: string | null;
  setCharacterId: React.Dispatch<React.SetStateAction<string | null>>;
  currentOptions: PlayerOption[];
  setCurrentOptions: React.Dispatch<React.SetStateAction<PlayerOption[]>>;
  currentScene: string | null;
  setCurrentScene: React.Dispatch<React.SetStateAction<string | null>>;
  actNumber: number;
  setActNumber: React.Dispatch<React.SetStateAction<number>>;
  showTransition: boolean;
  setShowTransition: React.Dispatch<React.SetStateAction<boolean>>;
  transitionSceneName: string;
  setTransitionSceneName: React.Dispatch<React.SetStateAction<string>>;
  compositeImageUrl: string | null;
  setCompositeImageUrl: React.Dispatch<React.SetStateAction<string | null>>;
  sceneImageUrl: string | null;
  setSceneImageUrl: React.Dispatch<React.SetStateAction<string | null>>;
  characterImageUrl: string | null;
  setCharacterImageUrl: React.Dispatch<React.SetStateAction<string | null>>;
  shouldUseComposite: boolean;
  setShouldUseComposite: React.Dispatch<React.SetStateAction<boolean>>;
  currentDialogue: string;
  setCurrentDialogue: React.Dispatch<React.SetStateAction<string>>;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  previousSceneRef: React.MutableRefObject<string | null>;
  scrollToBottom: () => void;
}

/** 向后兼容的聚合 Hook（旧代码可继续使用） */
export function useGameState(): GameStateBag {
  const dialogue = useDialogueState();
  const session = useSessionMeta();
  const scene = useSceneState();
  const progress = useGameProgress();

  /* eslint-disable react-hooks/exhaustive-deps */
  const gameState = useMemo(() => ({
    ...dialogue,
    ...session,
    ...scene,
    ...progress,
  }), [dialogue.messages, dialogue.currentDialogue, dialogue.currentOptions,
       session.threadId, session.characterId,
       scene.currentScene, scene.sceneImageUrl, scene.compositeImageUrl,
       scene.characterImageUrl, scene.shouldUseComposite, scene.showTransition,
       scene.transitionSceneName,
       progress.loading, progress.actNumber]);
  /* eslint-enable react-hooks/exhaustive-deps */

  return gameState;
}
