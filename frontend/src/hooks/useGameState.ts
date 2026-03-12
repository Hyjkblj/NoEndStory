import { useState, useRef, useCallback } from 'react';
import type { GameMessage, PlayerOption } from '@/types/game';

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

export function useGameState(): GameStateBag {
  const [messages, setMessages] = useState<GameMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [characterId, setCharacterId] = useState<string | null>(null);
  const [currentOptions, setCurrentOptions] = useState<PlayerOption[]>([]);
  const [currentScene, setCurrentScene] = useState<string | null>(null);
  const [actNumber, setActNumber] = useState(1);
  const [showTransition, setShowTransition] = useState(false);
  const [transitionSceneName, setTransitionSceneName] = useState('');
  const [compositeImageUrl, setCompositeImageUrl] = useState<string | null>(null);
  const [sceneImageUrl, setSceneImageUrl] = useState<string | null>(null);
  const [characterImageUrl, setCharacterImageUrl] = useState<string | null>(null);
  const [shouldUseComposite, setShouldUseComposite] = useState(false);
  const [currentDialogue, setCurrentDialogue] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const previousSceneRef = useRef<string | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  return {
    messages,
    setMessages,
    loading,
    setLoading,
    threadId,
    setThreadId,
    characterId,
    setCharacterId,
    currentOptions,
    setCurrentOptions,
    currentScene,
    setCurrentScene,
    actNumber,
    setActNumber,
    showTransition,
    setShowTransition,
    transitionSceneName,
    setTransitionSceneName,
    compositeImageUrl,
    setCompositeImageUrl,
    sceneImageUrl,
    setSceneImageUrl,
    characterImageUrl,
    setCharacterImageUrl,
    shouldUseComposite,
    setShouldUseComposite,
    currentDialogue,
    setCurrentDialogue,
    messagesEndRef,
    previousSceneRef,
    scrollToBottom,
  };
}
