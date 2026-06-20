import { useState, useEffect, useRef } from 'react';
import { Button } from 'antd';
import type { PlayerOption, GameMessage } from '@/types/game';

export interface GameDialogueProps {
  currentDialogue: string;
  currentOptions: PlayerOption[];
  loading: boolean;
  onOptionSelect: (index: number) => void;
  messages?: GameMessage[];
  characterName?: string;
  /** 打字机速度（ms/字），默认 30 */
  typeSpeed?: number;
}

export default function GameDialogue({
  currentDialogue,
  currentOptions,
  loading,
  onOptionSelect,
  messages = [],
  characterName = '角色',
  typeSpeed = 30,
}: GameDialogueProps) {
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const typingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 打字机效果
  useEffect(() => {
    if (!currentDialogue) {
      setDisplayedText('');
      setIsTyping(false);
      return;
    }

    setIsTyping(true);
    setDisplayedText('');
    let i = 0;

    typingTimerRef.current = setInterval(() => {
      i++;
      setDisplayedText(currentDialogue.slice(0, i));
      if (i >= currentDialogue.length) {
        if (typingTimerRef.current) clearInterval(typingTimerRef.current);
        setIsTyping(false);
      }
    }, typeSpeed);

    return () => {
      if (typingTimerRef.current) clearInterval(typingTimerRef.current);
    };
  }, [currentDialogue, typeSpeed]);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [displayedText, messages]);

  const handleSkipTyping = () => {
    if (typingTimerRef.current) clearInterval(typingTimerRef.current);
    setDisplayedText(currentDialogue);
    setIsTyping(false);
  };

  // 过滤掉当前对话，只显示历史
  const historyMessages = messages.filter(
    (msg) => msg.role === 'story_background' || msg.role === 'character' || msg.role === 'user'
  );

  return (
    <div className="game-dialogue-container">
      {/* 对话历史 */}
      {historyMessages.length > 0 && (
        <div className="dialogue-history">
          {historyMessages.map((msg, idx) => (
            <div key={idx} className={`history-message history-${msg.role}`}>
              {msg.role === 'story_background' && (
                <div className="history-story-bg">{msg.content}</div>
              )}
              {msg.role === 'character' && (
                <div className="history-char">
                  <span className="history-speaker">{characterName}</span>
                  <span className="history-text">{msg.content}</span>
                </div>
              )}
              {msg.role === 'user' && (
                <div className="history-user">{msg.content}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 当前对话（打字机效果） */}
      {currentDialogue && (
        <div className="game-dialogue-box" onClick={isTyping ? handleSkipTyping : undefined}>
          <div className="dialogue-header">{characterName}</div>
          <div className="dialogue-content">
            {displayedText}
            {isTyping && <span className="typing-cursor">|</span>}
          </div>
          {isTyping && (
            <div className="dialogue-skip-hint">点击跳过</div>
          )}
        </div>
      )}

      {/* 玩家选项 */}
      {currentOptions.length > 0 && !isTyping && (
        <div className="game-options-container">
          {currentOptions.map((option, index) => (
            <Button
              key={option.id}
              className="game-option-button"
              onClick={() => onOptionSelect(index)}
              disabled={loading}
            >
              {index + 1}. {option.text}
            </Button>
          ))}
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}
