import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, App as AntdApp } from 'antd';
import { BookOutlined, HeartOutlined, PlayCircleOutlined, UserOutlined } from '@ant-design/icons';
import backgroundImage from '@/assets/images/image.png';
import LoadingScreen from '@/components/loading';
import { useRouteTransition } from '@/hooks/useRouteTransition';
import { checkServerHealth } from '@/services/api';
import { ROUTES } from '@/config/routes';
import * as gameStorage from '@/storage/gameStorage';
import type { EndingRecord } from '@/types/game';
import './Home.css';

type StoredMainSave = {
  id?: string;
  threadId?: string;
  characterId?: string;
  characterName?: string;
  lastScene?: string;
  lastMessage?: string;
  lastPlayed?: string;
  timestamp?: number;
};

type SaveSummary = {
  characterName: string;
  lastScene: string;
  lastPlayed: string;
  excerpt?: string;
  threadId?: string;
  characterId?: string;
};

type EndingSummary = {
  characterName: string;
  title: string;
  typeLabel: string;
  lastPlayed: string;
  excerpt?: string;
};

const formatLastPlayed = (value?: string | number) => {
  if (!value) return '上次故事';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '上次故事';
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

const getSaveSummary = (save: StoredMainSave | null): SaveSummary | null => {
  if (!save) return null;
  return {
    characterName: save.characterName || '未命名角色',
    lastScene: save.lastScene || '故事进行中',
    lastPlayed: formatLastPlayed(save.lastPlayed || save.timestamp),
    excerpt: save.lastMessage,
    threadId: save.threadId || save.id,
    characterId: save.characterId,
  };
};

const getEndingSummary = (record?: EndingRecord): EndingSummary | null => {
  if (!record) return null;
  return {
    characterName: record.characterName || '未命名角色',
    title: record.title || '故事落幕',
    typeLabel: record.typeLabel || '特别结局',
    lastPlayed: formatLastPlayed(record.createdAt),
    excerpt: record.finalDialogue || record.description,
  };
};

function Home() {
  const navigate = useNavigate();
  const { transitionTo } = useRouteTransition();
  const { message, modal } = AntdApp.useApp();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('故事正在展开...');
  const [saveSummary, setSaveSummary] = useState<SaveSummary | null>(() =>
    getSaveSummary(gameStorage.getMainGameSave() as unknown as StoredMainSave | null)
  );
  const [endingSummary, setEndingSummary] = useState<EndingSummary | null>(() =>
    getEndingSummary(gameStorage.getEndingRecords()[0])
  );

  useEffect(() => {
    gameStorage.cleanupGuestOldGameData();
    setSaveSummary(getSaveSummary(gameStorage.getMainGameSave() as unknown as StoredMainSave | null));
    setEndingSummary(getEndingSummary(gameStorage.getEndingRecords()[0]));
  }, []);

  const enterStoryIndex = async () => {
    setLoadingMessage('故事正在展开...');
    setLoading(true);

    try {
      const isHealthy = await checkServerHealth();
      if (isHealthy) {
        navigate(ROUTES.FIRST_STEP);
      } else {
        message.error('故事暂时无法展开，请稍后再试。');
      }
    } catch {
      message.error('故事暂时无法展开，请稍后再试。');
    } finally {
      setLoading(false);
    }
  };

  const handleBegin = async () => {
    const hasGuestHistory = Boolean(saveSummary?.threadId || endingSummary);

    if (hasGuestHistory) {
      modal.confirm({
        title: '继续以游客身份开始新故事？',
        content: '游客模式只保留最新一局。再次开始后，当前游客身份下的角色、进度和结局记录可能会被覆盖。',
        okText: '继续开始',
        cancelText: '先不开始',
        className: 'home-guest-confirm-modal',
        icon: <PlayCircleOutlined className="home-guest-confirm-icon" />,
        onOk: enterStoryIndex,
      });
      return;
    }

    await enterStoryIndex();
  };

  const handleContinue = async () => {
    const restoreThreadId = saveSummary?.threadId;
    const restoreCharacterId = saveSummary?.characterId;
    if (!restoreThreadId) {
      navigate(ROUTES.FIRST_STEP);
      return;
    }

    setLoadingMessage('故事正在继续...');
    setLoading(true);
    try {
      const didNavigate = await transitionTo({
        to: ROUTES.GAME,
        variant: 'story',
        disableReadyFallback: true,
        work: async ({ animateTo, setProgress }) => {
          setProgress(16);
          const isHealthy = await checkServerHealth();
          if (!isHealthy) {
            message.error('故事暂时无法继续，请稍后再试。');
            return false;
          }
          await animateTo(52, 520);
          gameStorage.setRestoreThreadId(restoreThreadId);
          if (restoreCharacterId) gameStorage.setRestoreCharacterId(restoreCharacterId);
          await animateTo(88, 620);
        },
      });

      if (!didNavigate) {
        setLoading(false);
      }
    } catch {
      message.error('故事暂时无法继续，请稍后再试。');
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingScreen message={loadingMessage} />;
  }

  return (
    <main
      className="home-page"
      style={{ backgroundImage: `url(${backgroundImage})` }}
      aria-label="无尽故事首页"
    >
      <div className="home-overlay" />
      <div className="home-vignette" />
      <div className="home-guest-badge" aria-label="当前身份：游客登录">
        <UserOutlined aria-hidden="true" />
        <span>游客登录</span>
      </div>

      <section className="home-hero" aria-labelledby="home-title">
        <div className="home-title-block">
          <p className="home-kicker">No Ending Story</p>
          <h1 id="home-title" className="home-title">
            无尽故事
          </h1>
          <p className="home-subtitle">
            每一次选择，都会让故事偏离原来的结局。
          </p>
        </div>

        <Button
          type="primary"
          size="large"
          icon={<PlayCircleOutlined />}
          onClick={handleBegin}
          className="home-primary-button"
          aria-label="开始故事"
        >
          开始故事
        </Button>

        {saveSummary && (
          <button
            type="button"
            className="home-save-card"
            onClick={handleContinue}
            aria-label={`继续 ${saveSummary.characterName} 的故事`}
          >
            <span className="home-save-icon" aria-hidden="true">
              <BookOutlined />
            </span>
            <span className="home-save-copy">
              <span className="home-save-label">继续这段故事</span>
              <span className="home-save-title">{saveSummary.characterName}</span>
              <span className="home-save-meta">
                {saveSummary.lastScene} · {saveSummary.lastPlayed}
              </span>
              {saveSummary.excerpt && (
                <span className="home-save-excerpt">{saveSummary.excerpt}</span>
              )}
            </span>
          </button>
        )}

        {endingSummary && (
          <button
            type="button"
            className="home-save-card home-ending-card"
            onClick={() => navigate(ROUTES.ENDING_ARCHIVE)}
            aria-label={`查看 ${endingSummary.characterName} 的结局回忆`}
          >
            <span className="home-save-icon home-ending-icon" aria-hidden="true">
              <HeartOutlined />
            </span>
            <span className="home-save-copy">
              <span className="home-save-label">最近封存的结局</span>
              <span className="home-save-title">{endingSummary.title}</span>
              <span className="home-save-meta">
                {endingSummary.characterName} · {endingSummary.typeLabel} · {endingSummary.lastPlayed}
              </span>
              {endingSummary.excerpt && (
                <span className="home-save-excerpt">{endingSummary.excerpt}</span>
              )}
            </span>
          </button>
        )}
      </section>
    </main>
  );
}

export default Home;
