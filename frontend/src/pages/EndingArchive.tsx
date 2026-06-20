import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Empty } from 'antd';
import { HomeOutlined, ReloadOutlined } from '@ant-design/icons';
import backgroundImage from '@/assets/images/image.png';
import { ROUTES } from '@/config/routes';
import { getStaticAssetUrl } from '@/services/api';
import * as gameStorage from '@/storage/gameStorage';
import type { EndingRecord } from '@/types/game';
import './EndingArchive.css';

const formatArchiveDate = (value: number) => new Intl.DateTimeFormat('zh-CN', {
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
}).format(new Date(value));

const formatMetricValue = (value: number | null | undefined) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null;
  return Math.round(Math.max(0, Math.min(100, value)));
};

function EndingArchive() {
  const navigate = useNavigate();
  const records = useMemo(() => gameStorage.getEndingRecords(), []);
  const [selectedId, setSelectedId] = useState(records[0]?.id);
  const selectedRecord = records.find((record) => record.id === selectedId) || records[0];

  const handleRestart = () => {
    gameStorage.cleanupGuestOldGameData({
      keepThreadId: null,
      keepLatestEnding: false,
      clearCharacterData: true,
      clearSession: true,
    });
    navigate(ROUTES.CHARACTER_SETTING);
  };

  if (!records.length) {
    return (
      <main
        className="ending-archive-page ending-archive-empty-page"
        style={{ backgroundImage: `url(${backgroundImage})` }}
        aria-label="结局回忆馆"
      >
        <div className="ending-archive-scrim" />
        <section className="ending-archive-empty">
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="还没有被封存的结局"
          />
          <p>完成一次故事后，最终关系、关键回忆和最后一句对白会保存在这里。</p>
          <div className="ending-archive-empty-actions">
            <Button type="primary" icon={<ReloadOutlined />} onClick={handleRestart}>
              开始新故事
            </Button>
            <Button icon={<HomeOutlined />} onClick={() => navigate(ROUTES.HOME)}>
              回到首页
            </Button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main
      className="ending-archive-page"
      style={{ backgroundImage: `url(${backgroundImage})` }}
      aria-label="结局回忆馆"
    >
      <div className="ending-archive-scrim" />

      <section className="ending-archive-shell">
        <header className="ending-archive-header">
          <div>
            <span>No End Story</span>
            <h1>结局回忆馆</h1>
          </div>
          <div className="ending-archive-header-actions">
            <Button icon={<HomeOutlined />} onClick={() => navigate(ROUTES.HOME)}>
              回到首页
            </Button>
            <Button type="primary" icon={<ReloadOutlined />} onClick={handleRestart}>
              再开一局
            </Button>
          </div>
        </header>

        <div className="ending-archive-grid">
          <aside className="ending-archive-list" aria-label="已保存结局列表">
            <div className="ending-archive-list-heading">
              <span>Saved Endings</span>
              <strong>{records.length} 段回忆</strong>
            </div>
            <div className="ending-archive-list-scroll">
              {records.map((record) => (
                <button
                  key={record.id}
                  type="button"
                  className={`ending-archive-item${record.id === selectedRecord.id ? ' active' : ''}`}
                  onClick={() => setSelectedId(record.id)}
                  aria-pressed={record.id === selectedRecord.id}
                >
                  <span>{record.typeLabel}</span>
                  <strong>{record.title}</strong>
                  <em>
                    {record.characterName} · {formatArchiveDate(record.createdAt)}
                  </em>
                </button>
              ))}
            </div>
          </aside>

          <EndingArchiveDetail record={selectedRecord} />
        </div>
      </section>
    </main>
  );
}

function EndingArchiveDetail({ record }: { record: EndingRecord }) {
  const sceneUrl = record.visual.compositeImageUrl || record.visual.sceneImageUrl;
  const shouldLayerCharacter = Boolean(record.visual.characterImageUrl && !record.visual.compositeImageUrl);

  return (
    <article className="ending-archive-detail">
      <div className="ending-archive-visual" aria-hidden="true">
        {sceneUrl ? (
          <img src={getStaticAssetUrl(sceneUrl)} alt="" className="ending-archive-scene" />
        ) : (
          <div className="ending-archive-visual-empty" />
        )}
        {shouldLayerCharacter && (
          <img
            src={getStaticAssetUrl(record.visual.characterImageUrl)}
            alt=""
            className="ending-archive-character"
          />
        )}
        <div className="ending-archive-visual-shade" />
      </div>

      <div className="ending-archive-copy">
        <span className="ending-archive-badge">{record.typeLabel}</span>
        <h2>{record.title}</h2>
        <p>{record.description}</p>

        {record.finalDialogue && (
          <blockquote>
            <span>{record.characterName}</span>
            <p>{record.finalDialogue}</p>
          </blockquote>
        )}

        <section className="ending-archive-section" aria-label="最终关系">
          <div className="ending-archive-section-title">
            <span>Final Relation</span>
            <strong>最终关系</strong>
          </div>
          <div className="ending-archive-metrics">
            {record.relationship.map((metric) => {
              const metricValue = formatMetricValue(metric.value);

              return (
                <div key={metric.key} className={`ending-archive-metric metric-${metric.tone || 'quiet'}`}>
                  <div>
                    <span>{metric.label}</span>
                    <strong>{metricValue == null ? '--' : metricValue}</strong>
                  </div>
                  <em>
                    <i style={{ width: `${metricValue ?? 0}%` }} />
                  </em>
                </div>
              );
            })}
          </div>
        </section>

        <section className="ending-archive-section" aria-label="关键回忆">
          <div className="ending-archive-section-title">
            <span>Memory Archive</span>
            <strong>关键回忆</strong>
          </div>
          <ol className="ending-archive-memories">
            {record.keyMemories.map((memory) => (
              <li key={`${memory.title}-${memory.description}`}>
                <span />
                <div>
                  <strong>{memory.title}</strong>
                  <p>{memory.description}</p>
                  {memory.choice && <em>{memory.choice}</em>}
                </div>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </article>
  );
}

export default EndingArchive;
