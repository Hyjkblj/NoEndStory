import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, App as AntdApp } from 'antd';
import { BookOutlined, PlayCircleOutlined } from '@ant-design/icons';
import backgroundImage from '@/assets/images/image.png';
import LoadingScreen from '@/components/loading';
import { checkServerHealth } from '@/services/api';
import { ROUTES } from '@/config/routes';
import * as gameStorage from '@/storage/gameStorage';
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

function Home() {
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('故事正在展开...');
  const saveSummary = useMemo(
    () => getSaveSummary(gameStorage.getMainGameSave() as unknown as StoredMainSave | null),
    []
  );

  const handleBegin = async () => {
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

  const handleContinue = async () => {
    if (!saveSummary?.threadId) {
      navigate(ROUTES.FIRST_STEP);
      return;
    }

    setLoadingMessage('故事正在继续...');
    setLoading(true);
    try {
      const isHealthy = await checkServerHealth();
      if (!isHealthy) {
        message.error('故事暂时无法继续，请稍后再试。');
        return;
      }
      gameStorage.setRestoreThreadId(saveSummary.threadId);
      if (saveSummary.characterId) gameStorage.setRestoreCharacterId(saveSummary.characterId);
      navigate(ROUTES.GAME);
    } catch {
      message.error('故事暂时无法继续，请稍后再试。');
    } finally {
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
      </section>
    </main>
  );
}

export default Home;
