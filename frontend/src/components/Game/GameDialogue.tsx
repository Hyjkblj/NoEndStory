import { useEffect, useRef, useState } from 'react';
import { Button } from 'antd';
import type { PlayerOption } from '@/types/game';

export interface GameDialogueProps {
  currentDialogue: string;
  currentOptions: PlayerOption[];
  loading: boolean;
  onOptionSelect: (index: number) => void;
  characterName?: string;
  typeSpeed?: number;
}

function ActiveDialogue({
  currentDialogue,
  currentOptions,
  loading,
  onOptionSelect,
  typeSpeed = 30,
}: GameDialogueProps) {
  const [typedLength, setTypedLength] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isTyping = currentDialogue.length > 0 && typedLength < currentDialogue.length;
  const displayedText = currentDialogue.slice(0, typedLength);

  useEffect(() => {
    if (!currentDialogue) return;

    const timer = window.setInterval(() => {
      setTypedLength((prev) => {
        const next = Math.min(prev + 1, currentDialogue.length);
        if (next >= currentDialogue.length) {
          window.clearInterval(timer);
        }
        return next;
      });
    }, typeSpeed);

    return () => window.clearInterval(timer);
  }, [currentDialogue, typeSpeed]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [typedLength]);

  const handleSkipTyping = () => {
    setTypedLength(currentDialogue.length);
  };

  return (
    <>
      {currentDialogue && (
        <div className="game-dialogue-box" onClick={isTyping ? handleSkipTyping : undefined}>
          <div className="dialogue-content">
            {displayedText}
            {isTyping && <span className="typing-cursor">|</span>}
          </div>
          {isTyping && (
            <div className="dialogue-skip-hint">点击跳过</div>
          )}
        </div>
      )}

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
    </>
  );
}

export default function GameDialogue(props: GameDialogueProps) {
  return (
    <div className="game-dialogue-container">
      <ActiveDialogue key={props.currentDialogue} {...props} />
    </div>
  );
}
