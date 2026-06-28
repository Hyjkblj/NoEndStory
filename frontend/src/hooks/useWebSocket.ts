import { useCallback, useEffect, useRef, useState } from 'react';
import { withAppBasePath } from '@/config/basePath';

const WS_BASE = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;

interface WsMessage {
  type: string;
  content?: string;
  options?: Array<{ id: number; text: string }>;
  current_states?: Record<string, number>;
  scene?: string;
  elapsed_minutes?: number;
  message?: string;
  summary?: string;
  emotion_tags?: string;
}

export function useWebSocket(threadId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const connectRef = useRef<() => void>(() => {});
  const reconnectTimerRef = useRef<ReturnType<typeof window.setTimeout> | null>(null);
  const shouldReconnectRef = useRef(true);
  const reconnectAttempt = useRef(0);
  const [connected, setConnected] = useState(false);
  const [dialogueChunks, setDialogueChunks] = useState<string[]>([]);
  const [options, setOptions] = useState<Array<{ id: number; text: string }>>([]);
  const [isFinished, setIsFinished] = useState(false);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!threadId || wsRef.current) return;
    shouldReconnectRef.current = true;

    const ws = new WebSocket(`${WS_BASE}${withAppBasePath(`/api/v1/ws/game/${threadId}`)}`);

    ws.onopen = () => {
      setConnected(true);
      reconnectAttempt.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data);
        switch (msg.type) {
          case 'dialogue_chunk':
            setDialogueChunks(prev => [...prev, msg.content || '']);
            break;
          case 'dialogue_complete':
            break;
          case 'options':
            setOptions(msg.options || []);
            break;
          case 'end':
            setIsFinished(true);
            break;
          case 'error':
            console.error('WS error:', msg.message);
            break;
        }
      } catch {
        // Ignore malformed websocket messages.
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (wsRef.current === ws) {
        wsRef.current = null;
      }

      if (shouldReconnectRef.current && reconnectAttempt.current < 3) {
        reconnectAttempt.current++;
        reconnectTimerRef.current = window.setTimeout(() => {
          reconnectTimerRef.current = null;
          connectRef.current();
        }, 2000 * reconnectAttempt.current);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [threadId]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    clearReconnectTimer();
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, [clearReconnectTimer]);

  const sendMessage = useCallback((content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      setDialogueChunks([]);
      setOptions([]);
      wsRef.current.send(JSON.stringify({ type: 'input', content }));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    connected,
    dialogueChunks,
    fullDialogue: dialogueChunks.join(''),
    options,
    isFinished,
    sendMessage,
    disconnect,
  };
}
