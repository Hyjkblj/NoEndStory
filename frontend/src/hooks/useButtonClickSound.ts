import { useEffect, useRef } from 'react';

type BrowserAudioWindow = Window & typeof globalThis & {
  webkitAudioContext?: typeof AudioContext;
};

const buttonSelector = 'button, .ant-btn, [role="button"], a[href]';

function isDisabledButton(element: Element) {
  const button = element.closest('button');
  return (
    (button instanceof HTMLButtonElement && button.disabled) ||
    element.getAttribute('aria-disabled') === 'true' ||
    element.closest('[aria-disabled="true"], .ant-btn-disabled, .ant-btn-loading') !== null
  );
}

function playClickTone(audioContext: AudioContext) {
  const now = audioContext.currentTime;
  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();

  oscillator.type = 'sine';
  oscillator.frequency.setValueAtTime(560, now);
  oscillator.frequency.exponentialRampToValueAtTime(860, now + 0.055);

  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.linearRampToValueAtTime(0.045, now + 0.006);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.095);

  oscillator.connect(gain);
  gain.connect(audioContext.destination);
  oscillator.start(now);
  oscillator.stop(now + 0.105);
}

export function useButtonClickSound() {
  const audioContextRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    const getAudioContext = () => {
      const AudioContextConstructor = window.AudioContext ?? (window as BrowserAudioWindow).webkitAudioContext;
      if (!AudioContextConstructor) return null;

      audioContextRef.current ??= new AudioContextConstructor();
      return audioContextRef.current;
    };

    const handleClick = (event: MouseEvent) => {
      if (!(event.target instanceof Element)) return;

      const targetButton = event.target.closest(buttonSelector);
      if (!targetButton || isDisabledButton(targetButton)) return;

      const audioContext = getAudioContext();
      if (!audioContext) return;

      if (audioContext.state === 'suspended') {
        void audioContext.resume().then(() => playClickTone(audioContext));
        return;
      }

      playClickTone(audioContext);
    };

    window.addEventListener('click', handleClick, true);

    return () => {
      window.removeEventListener('click', handleClick, true);
    };
  }, []);
}
