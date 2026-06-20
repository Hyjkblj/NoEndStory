import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Button, Popover, Slider } from 'antd';
import { CustomerServiceOutlined, SoundOutlined } from '@ant-design/icons';
import { useLocation } from 'react-router-dom';
import backgroundMusicUrl from '@/assets/Cafe in the Mist.mp3?url';
import { BackgroundMusicScopeContext } from '@/contexts/BackgroundMusicScopeContext';
import './BackgroundMusicProvider.css';

const MUSIC_VOLUME_KEY = 'background_music_volume';
const DEFAULT_VOLUME = 0.36;
const PRE_VOICE_PATHS = new Set(['/', '/firststep', '/charactersetting', '/characterselection']);

const clampVolume = (value: number) => Math.max(0, Math.min(1, value));

const getStoredVolume = () => {
  const stored = Number.parseFloat(localStorage.getItem(MUSIC_VOLUME_KEY) || '');
  return Number.isFinite(stored) ? clampVolume(stored) : DEFAULT_VOLUME;
};

const normalizePathname = (pathname: string) => {
  const value = pathname.replace(/\/+$/, '');
  return value || '/';
};

function BackgroundMusicProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lastPointerPlayAttemptRef = useRef(0);
  const [volume, setVolume] = useState(getStoredVolume);
  const initialVolumeRef = useRef(volume);
  const [scopeSuppressed, setScopeSuppressed] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isAwaitingGesture, setIsAwaitingGesture] = useState(false);

  const pathname = normalizePathname(location.pathname);
  const routeEnabled = PRE_VOICE_PATHS.has(pathname);
  const shouldPlay = routeEnabled && !scopeSuppressed && volume > 0;

  useEffect(() => {
    const audio = new Audio(backgroundMusicUrl);
    audio.loop = true;
    audio.preload = 'auto';
    audio.volume = initialVolumeRef.current;
    audioRef.current = audio;

    const handlePlaying = () => {
      setIsPlaying(true);
      setIsAwaitingGesture(false);
    };
    const handlePause = () => setIsPlaying(false);

    audio.addEventListener('playing', handlePlaying);
    audio.addEventListener('pause', handlePause);

    return () => {
      audio.pause();
      audio.removeEventListener('playing', handlePlaying);
      audio.removeEventListener('pause', handlePause);
      audioRef.current = null;
    };
  }, []);

  useEffect(() => {
    localStorage.setItem(MUSIC_VOLUME_KEY, String(volume));
    if (audioRef.current) audioRef.current.volume = volume;
  }, [volume]);

  const requestPlayback = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio || !shouldPlay) return;

    try {
      await audio.play();
      setIsAwaitingGesture(false);
    } catch {
      setIsAwaitingGesture(true);
    }
  }, [shouldPlay]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (!shouldPlay) {
      audio.pause();
      return;
    }

    const playTimer = window.setTimeout(() => {
      void requestPlayback();
    }, 0);

    return () => window.clearTimeout(playTimer);
  }, [requestPlayback, shouldPlay]);

  useEffect(() => {
    if (!shouldPlay || !isAwaitingGesture) return;

    const unlock = () => {
      void requestPlayback();
    };
    const unlockByPointer = () => {
      const now = Date.now();
      if (now - lastPointerPlayAttemptRef.current < 1200) return;
      lastPointerPlayAttemptRef.current = now;
      void requestPlayback();
    };

    document.documentElement.addEventListener('pointerenter', unlockByPointer);
    window.addEventListener('pointermove', unlockByPointer, { passive: true });
    window.addEventListener('mouseover', unlockByPointer, { passive: true });
    window.addEventListener('pointerdown', unlock, { once: true });
    window.addEventListener('keydown', unlock, { once: true });
    return () => {
      document.documentElement.removeEventListener('pointerenter', unlockByPointer);
      window.removeEventListener('pointermove', unlockByPointer);
      window.removeEventListener('mouseover', unlockByPointer);
      window.removeEventListener('pointerdown', unlock);
      window.removeEventListener('keydown', unlock);
    };
  }, [isAwaitingGesture, requestPlayback, shouldPlay]);

  const handleVolumeChange = (value: number | number[]) => {
    const nextValue = Array.isArray(value) ? value[0] : value;
    setVolume(clampVolume(nextValue / 100));
  };

  const panel = (
    <div className="background-music-panel">
      <span className="background-music-kicker">系统设置</span>
      <div className="background-music-heading">
        <SoundOutlined />
        <strong>背景音乐</strong>
      </div>
      <p>
        {scopeSuppressed
          ? '音色选择阶段已暂停背景音乐，避免干扰试听。'
          : isAwaitingGesture
            ? '点击页面任意位置后开始循环播放。'
            : isPlaying
              ? '正在循环播放 Cafe in the Mist。'
              : '当前页面暂停播放。'}
      </p>
      <div className="background-music-slider-row">
        <span>音量</span>
        <strong>{Math.round(volume * 100)}%</strong>
      </div>
      <Slider
        min={0}
        max={100}
        value={Math.round(volume * 100)}
        onChange={handleVolumeChange}
        tooltip={{ formatter: (value) => `${value ?? 0}%` }}
      />
    </div>
  );

  const shouldShowSettings = routeEnabled;

  return (
    <BackgroundMusicScopeContext.Provider value={setScopeSuppressed}>
      {children}
      {shouldShowSettings && (
        <div className="background-music-settings" aria-label="背景音乐设置">
          <Popover
            trigger="click"
            placement="topLeft"
            content={panel}
            overlayClassName="background-music-popover"
          >
            <Button
              type="text"
              icon={<CustomerServiceOutlined />}
              className={`background-music-button${isPlaying ? ' is-playing' : ''}`}
              onClick={() => void requestPlayback()}
            >
              音乐
            </Button>
          </Popover>
        </div>
      )}
    </BackgroundMusicScopeContext.Provider>
  );
}

export default BackgroundMusicProvider;
