import { useEffect, useRef, useState } from 'react';
import { generateSpeech } from '@/services/api';
import { logger } from '@/utils/logger';

/** TTS 音频控制状态（全局共享） */
let _globalAudio: HTMLAudioElement | null = null;

const stripSpeakerPrefix = (text: string): string =>
  text.replace(/^[^:：]+[：:]/, '').trim();

const hasReadableTtsText = (text: string): boolean => /[\p{L}\p{N}]/u.test(text);

export function useTtsControls() {
  const [ttsEnabled, setTtsEnabled] = useState(() => {
    return localStorage.getItem('tts_enabled') !== 'false';
  });
  const [ttsVolume, setTtsVolume] = useState(() => {
    return parseFloat(localStorage.getItem('tts_volume') || '0.8');
  });

  useEffect(() => {
    localStorage.setItem('tts_enabled', String(ttsEnabled));
  }, [ttsEnabled]);

  useEffect(() => {
    localStorage.setItem('tts_volume', String(ttsVolume));
    if (_globalAudio) _globalAudio.volume = ttsVolume;
  }, [ttsVolume]);

  const stopTts = () => {
    if (_globalAudio) {
      _globalAudio.pause();
      _globalAudio.currentTime = 0;
      _globalAudio = null;
    }
  };

  return { ttsEnabled, setTtsEnabled, ttsVolume, setTtsVolume, stopTts };
}

/**
 * 当 currentDialogue / characterId 变化时，使用角色音色播放 TTS
 * 支持从后端响应中获取 emotion_params（语速/音调/情感）
 */
export function useGameTts(
  currentDialogue: string,
  characterId: string | null,
  options?: {
    enabled?: boolean;
    volume?: number;
    emotion_params?: Record<string, unknown> | null;
  }
) {
  const lastTtsDialogueRef = useRef('');
  const enabled = options?.enabled ?? true;
  const volume = options?.volume ?? 0.8;
  const emotionParams = options?.emotion_params ?? null;

  useEffect(() => {
    if (!enabled) return;
    if (!currentDialogue?.trim() || !characterId) return;
    if (currentDialogue === lastTtsDialogueRef.current) return;
    lastTtsDialogueRef.current = currentDialogue;

    const textForTts = stripSpeakerPrefix(currentDialogue) || currentDialogue.trim();
    if (!textForTts || !hasReadableTtsText(textForTts)) return;

    const charId = typeof characterId === 'string' ? characterId : String(characterId);
    if (charId === 'undefined' || charId === 'null' || charId === '') return;

    let cancelled = false;
    (async () => {
      // 停止上一段音频
      if (_globalAudio) {
        _globalAudio.pause();
        _globalAudio = null;
      }

      const result = await generateSpeech(textForTts, characterId, {
        emotion_params: emotionParams || undefined,
      });
      if (cancelled || !result?.audio_url) return;
      const url = result.audio_url.startsWith('http')
        ? result.audio_url
        : `${window.location.origin}${result.audio_url}`;
      const audio = new Audio(url);
      audio.volume = volume;
      _globalAudio = audio;
      audio.play().catch((e) => logger.warn('[游戏] TTS 播放失败:', e));
      audio.onended = () => {
        if (_globalAudio === audio) _globalAudio = null;
      };
    })();
    return () => {
      cancelled = true;
    };
  }, [currentDialogue, characterId, enabled, volume, emotionParams]);
}
