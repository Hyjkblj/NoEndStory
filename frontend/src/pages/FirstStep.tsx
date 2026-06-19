import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { App as AntdApp, Button } from 'antd';
import {
  BookOutlined,
  HomeOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import backgroundImage from '@/assets/images/firstbackgound.jpg';
import LoadingScreen from '@/components/loading';
import { checkServerHealth } from '@/services/api';
import { ROUTES } from '@/config/routes';
import * as gameStorage from '@/storage/gameStorage';
import type { StoredMainSave } from '@/types/game';
import { getSaveSummary } from '@/utils/game';
import './FirstStep.css';

function FirstStep() {
  const navigate = useNavigate();
  const { message, modal } = AntdApp.useApp();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('故事正在继续...');
  const [saveSummary] = useState<SaveSummary | null>(() =>
    getSaveSummary(gameStorage.getMainGameSave() as unknown as StoredMainSave | null)
  );

  const hasSave = Boolean(saveSummary?.threadId);
  const petals = useMemo(() => Array.from({ length: 18 }), []);

  const handleContinueGame = async () => {
    if (!saveSummary?.threadId) return;

    setLoading(true);
    setLoadingMessage('故事正在继续...');
    try {
      const isHealthy = await checkServerHealth();
      if (isHealthy) {
        gameStorage.setRestoreThreadId(saveSummary.threadId);
        if (saveSummary.characterId) gameStorage.setRestoreCharacterId(saveSummary.characterId);
        setLoadingMessage('正在翻到上次停下的那一页...');
        await new Promise((r) => setTimeout(r, 500));
        navigate(ROUTES.GAME);
      } else {
        message.error('故事暂时无法继续，请稍后再试。');
      }
    } catch {
      message.error('故事暂时无法继续，请稍后再试。');
    } finally {
      setLoading(false);
    }
  };

  const handleNewStory = () => {
    navigate(ROUTES.CHARACTER_SETTING);
  };

  const handleExit = () => {
    modal.confirm({
      title: '要回到首页吗？',
      content: '你可以随时从首页重新进入故事。',
      okText: '回到首页',
      cancelText: '继续留在这里',
      className: 'first-step-confirm-modal',
      icon: <HomeOutlined className="first-step-confirm-icon" />,
      onOk: () => {
        navigate(ROUTES.HOME);
      },
    });
  };

  if (loading) return <LoadingScreen message={loadingMessage} />;

  return (
    <main
      className="first-step-page"
      style={{ backgroundImage: `url(${backgroundImage})` }}
      aria-label="故事目录"
    >
      <div className="first-step-overlay" />
      <div className="first-step-vignette" />

      <div className="sakura-container" aria-hidden="true">
        {petals.map((_, index) => (
          <div
            key={index}
            className="sakura-petal"
            style={{
              left: `${(index * 7) % 100}%`,
              animationDelay: `${index * 0.45}s`,
              animationDuration: `${9 + (index % 5)}s`,
            }}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" focusable="false">
              <path
                d="M10 2C10 2 12 6 16 6C12 6 10 10 10 10C10 10 8 6 4 6C8 6 10 2 10 2Z"
                fill="#ffb3d9"
                opacity="0.8"
              />
            </svg>
          </div>
        ))}
      </div>

      <section className="first-step-shell" aria-labelledby="first-step-title">
        <div className="first-step-copy">
          <p className="first-step-kicker">Story Index</p>
          <h1 id="first-step-title" className="first-step-title">
            故事目录
          </h1>
          <p className="first-step-subtitle">
            从上一次心跳继续，或让新的相遇重新开始。
          </p>
        </div>

        <div className="first-step-actions" aria-label="故事操作">
          <button
            type="button"
            className={`first-step-action-card first-step-action-card-save${hasSave ? '' : ' is-disabled'}`}
            onClick={handleContinueGame}
            disabled={!hasSave}
            aria-label={hasSave ? `继续 ${saveSummary?.characterName} 的故事` : '暂无存档'}
          >
            <span className="first-step-action-icon" aria-hidden="true">
              <BookOutlined />
            </span>
            <span className="first-step-action-copy">
              <span className="first-step-action-label">
                {hasSave ? '继续这段故事' : '暂无可继续的故事'}
              </span>
              <span className="first-step-action-title">
                {hasSave ? saveSummary?.characterName : '先开启新的故事'}
              </span>
              <span className="first-step-action-meta">
                {hasSave
                  ? `${saveSummary?.lastScene} · ${saveSummary?.lastPlayed}`
                  : '创建角色后，这里会保留最近的进度。'}
              </span>
              {saveSummary?.excerpt && <span className="first-step-action-excerpt">{saveSummary.excerpt}</span>}
            </span>
          </button>

          <button
            type="button"
            className="first-step-action-card first-step-action-card-new"
            onClick={handleNewStory}
            aria-label="开始新的故事"
          >
            <span className="first-step-action-icon" aria-hidden="true">
              <PlayCircleOutlined />
            </span>
            <span className="first-step-action-copy">
              <span className="first-step-action-label">新的故事</span>
              <span className="first-step-action-title">写下另一个开端</span>
              <span className="first-step-action-meta">重新塑造角色，并选择初遇发生的地方。</span>
            </span>
          </button>
        </div>

        <div className="first-step-utility" aria-label="辅助操作">
          <Button
            type="text"
            icon={<HomeOutlined />}
            onClick={handleExit}
            className="first-step-utility-button"
          >
            回到首页
          </Button>
        </div>
      </section>
    </main>
  );
}

export default FirstStep;
