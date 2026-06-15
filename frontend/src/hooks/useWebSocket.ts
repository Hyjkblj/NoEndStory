/** W13: WebSocket 连接管理 Hook */
import { useEffect, useRef, useCallback, useState } from 'react';

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
  const [connected, setConnected] = useState(false);
  const [dialogueChunks, setDialogueChunks] = useState<string[]>([]);
  const [options, setOptions] = useState<Array<{ id: number; text: string }>>([]);
  const [isFinished, setIsFinished] = useState(false);
  const reconnectAttempt = useRef(0);

  const connect = useCallback(() => {
    if (!threadId || wsRef.current) return;

    const ws = new WebSocket(`${WS_BASE}/api/v1/ws/game/${threadId}`);

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
            // full dialogue assembled
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
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      // 自动重连（最多3次）
      if (reconnectAttempt.current < 3) {
        reconnectAttempt.current++;
        setTimeout(connect, 2000 * reconnectAttempt.current);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [threadId]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, []);

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
