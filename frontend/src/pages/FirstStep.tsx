import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { App as AntdApp, Button } from 'antd';
import {
  BookOutlined,
  ExclamationCircleOutlined,
  HomeOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import backgroundImage from '@/assets/images/firstbackgound.jpg';
import LoadingScreen from '@/components/loading';
import SakuraSway from '@/components/SakuraSway';
import { useRouteTransition } from '@/hooks/useRouteTransition';
import { checkServerHealth, initGame, isGuestEndingLimitError } from '@/services/api';
import { ROUTES } from '@/config/routes';
import * as gameStorage from '@/storage/gameStorage';
import type { SaveSummary, StoredMainSave } from '@/types/game';
import { getSaveSummary } from '@/utils/game';
import './FirstStep.css';

function FirstStep() {
  const navigate = useNavigate();
  const { transitionTo } = useRouteTransition();
  const { message, modal } = AntdApp.useApp();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('故事正在继续...');
  const [saveSummary] = useState<SaveSummary | null>(() =>
    getSaveSummary(gameStorage.getMainGameSave() as unknown as StoredMainSave | null)
  );

  const hasSave = Boolean(saveSummary?.threadId);

  const showEndingLimitModal = (messageText?: string) => {
    modal.info({
      title: '这次游客体验已经完成',
      content: (
        <div className="first-step-ending-limit-content">
          <p>{messageText || '游客在24小时内只能完成一次完整故事，之后可以继续开启新的相遇。'}</p>
          <ul>
            <li>注册账号后可解锁更多旅程</li>
            <li>保存更多结局与回忆</li>
            <li>后续可同步不同设备的故事进度</li>
          </ul>
        </div>
      ),
      okText: '我知道了',
      className: 'first-step-confirm-modal first-step-ending-limit-modal',
      icon: <ExclamationCircleOutlined className="first-step-confirm-icon" />,
    });
  };

  const handleContinueGame = async () => {
    const restoreThreadId = saveSummary?.threadId;
    const restoreCharacterId = saveSummary?.characterId;
    if (!restoreThreadId) return;

    setLoading(true);
    setLoadingMessage('故事正在继续...');
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
          setLoadingMessage('正在翻到上次停下的那一页...');
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

  const handleNewStory = async () => {
    const hasEnding = gameStorage.getEndingRecords().length > 0;
    const startNewStory = () => {
      gameStorage.cleanupGuestOldGameData({
        keepThreadId: null,
        keepLatestEnding: false,
        clearCharacterData: true,
        clearSession: true,
      });
      navigate(ROUTES.CHARACTER_SETTING);
    };

    if (hasEnding) {
      try {
        await initGame({ game_mode: 'solo', character_id: '__guest_limit_probe__' });
      } catch (error: unknown) {
        if (isGuestEndingLimitError(error)) {
          showEndingLimitModal(error.message);
          return;
        }
      }
    }

    if (!hasSave && !hasEnding) {
      startNewStory();
      return;
    }

    modal.confirm({
      title: '开启新的游客故事？',
      content: '游客模式只保留最新一局。开始新故事后，上一局的角色、进度和结局会被覆盖。',
      okText: '开始新故事',
      cancelText: '先不开始',
      className: 'first-step-confirm-modal',
      icon: <PlayCircleOutlined className="first-step-confirm-icon" />,
      onOk: startNewStory,
    });
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
      <SakuraSway />

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
