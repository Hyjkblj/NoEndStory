import { useEffect, useState } from 'react';
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
import { checkServerHealth, getGuestEndingStatus, type GuestEndingStatus } from '@/services/api';
import { ROUTES } from '@/config/routes';
import * as gameStorage from '@/storage/gameStorage';
import type { SaveSummary, StoredMainSave } from '@/types/game';
import { getSaveSummary } from '@/utils/game';
import './FirstStep.css';

const formatStatusTime = (value?: string | null) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';

  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const formatCooldown = (seconds?: number) => {
  if (!seconds || seconds <= 0) return '额度即将恢复';
  const hours = Math.ceil(seconds / 3600);
  if (hours >= 24) return '约 24 小时后可再开新局';
  return `约 ${hours} 小时后可再开新局`;
};

function FirstStep() {
  const navigate = useNavigate();
  const { transitionTo } = useRouteTransition();
  const { message, modal } = AntdApp.useApp();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('故事正在继续...');
  const [saveSummary] = useState<SaveSummary | null>(() =>
    getSaveSummary(gameStorage.getMainGameSave() as unknown as StoredMainSave | null)
  );
  const [guestEndingStatus, setGuestEndingStatus] = useState<GuestEndingStatus | null>(null);
  const [guestEndingStatusLoading, setGuestEndingStatusLoading] = useState(true);

  const hasSave = Boolean(saveSummary?.threadId);
  const hasGuestEndingRecord = Boolean(guestEndingStatus?.limited);
  const canContinueSave = hasSave && !hasGuestEndingRecord;
  const saveCardDisabled = !canContinueSave && !hasGuestEndingRecord;
  const endingCooldownText = formatCooldown(guestEndingStatus?.expires_in_seconds);

  useEffect(() => {
    let mounted = true;

    setGuestEndingStatusLoading(true);
    getGuestEndingStatus()
      .then((status) => {
        if (mounted) setGuestEndingStatus(status);
      })
      .catch(() => {
        if (mounted) setGuestEndingStatus(null);
      })
      .finally(() => {
        if (mounted) setGuestEndingStatusLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const refreshGuestEndingStatus = async () => {
    setGuestEndingStatusLoading(true);
    try {
      const status = await getGuestEndingStatus();
      setGuestEndingStatus(status);
      return status;
    } catch {
      message.error('暂时无法确认游客额度，请稍后再试。');
      return null;
    } finally {
      setGuestEndingStatusLoading(false);
    }
  };

  const showEndingLimitModal = (status?: GuestEndingStatus | null) => {
    const endedAt = formatStatusTime(status?.ended_at);
    const expiresAt = formatStatusTime(status?.expires_at);

    modal.confirm({
      title: '这次游客体验已经完成',
      content: (
        <div className="first-step-ending-limit-content">
          <p>当前访问 IP 在过去 24 小时内已经完成过一个完整结局，继续开新局会被拦截。</p>
          <dl className="first-step-ending-limit-record">
            <div>
              <dt>查询字段</dt>
              <dd>{status?.lookup_key || 'guest_ending_log.client_ip'}</dd>
            </div>
            <div>
              <dt>当前 IP</dt>
              <dd>{status?.client_ip_masked || '当前访问 IP'}</dd>
            </div>
            {endedAt && (
              <div>
                <dt>结局时间</dt>
                <dd>{endedAt}</dd>
              </div>
            )}
            {expiresAt && (
              <div>
                <dt>恢复时间</dt>
                <dd>{expiresAt}</dd>
              </div>
            )}
          </dl>
        </div>
      ),
      okText: '查看结局',
      cancelText: '回到首页',
      className: 'first-step-confirm-modal first-step-ending-limit-modal',
      icon: <ExclamationCircleOutlined className="first-step-confirm-icon" />,
      maskClosable: false,
      onOk: () => {
        navigate(ROUTES.ENDING_ARCHIVE);
      },
      onCancel: () => {
        navigate(ROUTES.HOME);
      },
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

  const handleViewEnding = () => {
    navigate(ROUTES.ENDING_ARCHIVE);
  };

  const handleNewStory = async () => {
    const latestGuestStatus = await refreshGuestEndingStatus();
    if (!latestGuestStatus) return;
    if (latestGuestStatus.limited) {
      showEndingLimitModal(latestGuestStatus);
      return;
    }

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
            className={[
              'first-step-action-card first-step-action-card-save',
              hasGuestEndingRecord ? 'first-step-action-card-ending' : '',
              saveCardDisabled ? 'is-disabled' : '',
            ].filter(Boolean).join(' ')}
            onClick={hasGuestEndingRecord ? handleViewEnding : handleContinueGame}
            disabled={saveCardDisabled}
            aria-label={
              hasGuestEndingRecord
                ? '查看最近的游客结局'
                : hasSave
                  ? `继续 ${saveSummary?.characterName} 的故事`
                  : '暂无存档'
            }
            data-lookup-key={guestEndingStatus?.lookup_key || 'guest_ending_log.client_ip'}
            data-client-ip={guestEndingStatus?.client_ip_masked || undefined}
          >
            <span className="first-step-action-icon" aria-hidden="true">
              <BookOutlined />
            </span>
            <span className="first-step-action-copy">
              <span className="first-step-action-label">
                {hasGuestEndingRecord
                  ? '已完成的游客结局'
                  : hasSave
                    ? '继续这段故事'
                    : guestEndingStatusLoading
                      ? '正在确认游客记录'
                      : '暂无可继续的故事'}
              </span>
              <span className="first-step-action-title">
                {hasGuestEndingRecord
                  ? '查看最近的结局'
                  : hasSave
                    ? saveSummary?.characterName
                    : '先开启新的故事'}
              </span>
              <span className="first-step-action-meta">
                {hasGuestEndingRecord
                  ? `按当前访问 IP ${guestEndingStatus?.client_ip_masked || ''} 记录 · ${endingCooldownText}`
                  : hasSave
                  ? `${saveSummary?.lastScene} · ${saveSummary?.lastPlayed}`
                  : '创建角色后，这里会保留最近的进度。'}
              </span>
              {hasGuestEndingRecord && (
                <span className="first-step-action-excerpt">
                  查询字段：{guestEndingStatus?.lookup_key || 'guest_ending_log.client_ip'}
                </span>
              )}
              {!hasGuestEndingRecord && saveSummary?.excerpt && (
                <span className="first-step-action-excerpt">{saveSummary.excerpt}</span>
              )}
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
