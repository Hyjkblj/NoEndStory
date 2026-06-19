import './RouteLoadingTransition.css';

export type RouteLoadingVariant = 'story' | 'character';

interface RouteLoadingTransitionProps {
  variant: RouteLoadingVariant;
  progress: number;
  exiting?: boolean;
  errorMessage?: string | null;
  onBackToStory?: () => void;
  onBackHome?: () => void;
}

const storySymbols = ['opening', 'memory', 'voice', 'choice', 'heart', 'gate', 'story'];
const characterSymbols = ['intent', 'line', 'tone', 'color', 'detail', 'check', 'wait'];

const storyStages = [
  {
    title: '正在唤醒初遇场景',
    copy: '把背景、光线和第一眼的距离慢慢铺开',
    label: '01',
  },
  {
    title: '正在整理角色形象',
    copy: '让故事里的轮廓从雾面里显影',
    label: '02',
  },
  {
    title: '正在校准情绪语气',
    copy: '为第一句对白预留一点心跳的空白',
    label: '03',
  },
  {
    title: '即将进入故事',
    copy: '把这一刻交给你',
    label: '04',
  },
];

const characterStages = [
  {
    title: '正在理解角色设定',
    copy: '把性格、年龄感和第一眼的气质整理成画面',
    label: '设定',
  },
  {
    title: '正在勾勒人物轮廓',
    copy: '先让剪影站稳，再把视线和表情慢慢描出来',
    label: '线稿',
  },
  {
    title: '正在铺开服饰与发色',
    copy: '把颜色压低一点，等角色从暖光里显现',
    label: '上色',
  },
  {
    title: '正在检查细节一致性',
    copy: '确认姿态、相框和故事气质没有跑偏',
    label: '校验',
  },
  {
    title: '生成仍在继续',
    copy: '再等一小会儿，角色很快会走到你面前',
    label: '等待',
  },
];

const getStageIndex = (progress: number, stageCount: number) => {
  if (progress >= 96) return stageCount - 1;
  return Math.min(stageCount - 1, Math.floor((Math.max(0, progress) / 100) * stageCount));
};

function RouteLoadingTransition({
  variant,
  progress,
  exiting = false,
  errorMessage,
  onBackToStory,
  onBackHome,
}: RouteLoadingTransitionProps) {
  const normalizedProgress = Math.max(0, Math.min(100, Math.round(progress)));
  const stages = variant === 'story' ? storyStages : characterStages;
  const symbols = variant === 'story' ? storySymbols : characterSymbols;
  const activeStage = getStageIndex(normalizedProgress, stages.length);
  const stage = errorMessage
    ? {
        title: '画面准备失败',
        copy: errorMessage,
        label: '停止',
      }
    : stages[activeStage];
  const litOffset = variant === 'story' ? 2 : 1;

  return (
    <div
      className={`route-loading-transition route-loading-${variant}${exiting ? ' is-exiting' : ''}${errorMessage ? ' has-error' : ''}`}
      role="status"
      aria-live="polite"
      aria-label={`${stage.title}，${normalizedProgress}%`}
    >
      <section className="route-loading-stage" data-stage={activeStage}>
        <div className="route-loading-symbols" aria-hidden="true">
          {symbols.map((symbol, index) => (
            <span key={symbol} className={index <= activeStage + litOffset ? 'is-lit' : undefined} />
          ))}
        </div>

        <div className="route-loading-copy" key={stage.title}>
          <span className="route-loading-kicker">{variant === 'story' ? 'No End Story' : 'Character Draft'}</span>
          <h1>{stage.title}</h1>
          <p>{stage.copy}</p>
        </div>

        <div className="route-loading-progress">
          <strong className="route-loading-progress-value">{normalizedProgress}%</strong>
          <div className="route-loading-progress-track" aria-hidden="true">
            <div className="route-loading-progress-fill" style={{ width: `${normalizedProgress}%` }} />
          </div>
          <div className="route-loading-stage-line">
            <span>{stage.label}</span>
            <strong>{stage.title}</strong>
          </div>
        </div>

        {errorMessage && (
          <div className="route-loading-error-actions" aria-label="加载失败操作">
            <button type="button" onClick={onBackToStory}>
              返回故事目录
            </button>
            <button type="button" onClick={onBackHome}>
              回到首页
            </button>
          </div>
        )}
      </section>
    </div>
  );
}

export default RouteLoadingTransition;
