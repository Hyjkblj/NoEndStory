import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Input, Modal, Slider, message } from 'antd';
import {
  CloseOutlined,
  LeftOutlined,
  ManOutlined,
  ReloadOutlined,
  RightOutlined,
  WomanOutlined,
} from '@ant-design/icons';
import backgroundImage from '@/assets/images/settingcharacterbackground.png';
import { useRouteTransition } from '@/hooks/useRouteTransition';
import { ROUTES } from '@/config/routes';
import { checkServerHealth, createCharacter } from '@/services/api';
import * as gameStorage from '@/storage/gameStorage';
import { preloadImages } from '@/utils/preload';
import './CharacterSetting.css';

const categories = ['外貌', '性格', '风格'];

const nameSamples = [
  '林清歌',
  '苏云舒',
  '沈知夏',
  '顾星阑',
  '叶令仪',
  '江望舟',
  '白听晚',
  '陆明川',
  '秦若棠',
  '周以宁',
  '许微言',
  '谢照晚',
  '韩停云',
  '程令安',
  '潘青崖',
  '邵徽柔',
  '傅砚修',
  '邓景行',
  '蔡青梧',
  '叶照临',
];

const appearanceOptions = [
  '高挑',
  '清秀',
  '文艺',
  '长发',
  '短发',
  '黑发',
  '棕发',
  '眼镜',
  '明亮眼神',
  '冷白皮',
  '健康肤色',
  '笑容温柔',
  '气质优雅',
  '运动感',
  '学院风',
  '简约风',
  '时尚感',
  '干练',
  '少年感',
  '成熟感',
  '发尾微卷',
  '马尾',
  '双马尾',
  '丸子头',
  '清冷感',
  '亲和力',
  '五官立体',
  '身材匀称',
  '气场强',
  '温婉',
];

const personalityOptions = [
  '外向',
  '内向',
  '温柔',
  '冷静',
  '热情',
  '理性',
  '感性',
  '幽默',
  '直率',
  '细腻',
  '勇敢',
  '谨慎',
  '自信',
  '慢热',
  '独立',
  '可靠',
  '善良',
  '体贴',
  '执着',
  '洒脱',
  '高冷',
  '阳光',
  '成熟',
  '单纯',
  '有主见',
  '共情力强',
  '行动力强',
  '好奇心强',
  '有责任感',
  '浪漫',
];

const styleOptions = [
  '简约现代，偏实用与干净利落。',
  '复古优雅，偏经典与怀旧质感。',
  '前卫时尚，关注潮流与个性表达。',
  '自然治愈，偏舒适与温暖氛围。',
  '都市精致，注重细节与品质。',
  '文艺清新，带有轻柔与诗意气息。',
  '运动活力，阳光直接、节奏轻快。',
  '神秘冷感，克制疏离、气场明显。',
];

function CharacterSetting() {
  const navigate = useNavigate();
  const { transitionTo } = useRouteTransition();
  const [messageApi, messageContextHolder] = message.useMessage();
  const [loading, setLoading] = useState(false);

  const [name, setName] = useState('');
  const [height, setHeight] = useState(160);
  const [weight, setWeight] = useState(45);
  const [age, setAge] = useState(18);
  const [gender, setGender] = useState<'male' | 'female'>('male');
  const [currentCategory, setCurrentCategory] = useState(0);

  const [selectedAppearance, setSelectedAppearance] = useState<number[]>([]);
  const [selectedPersonality, setSelectedPersonality] = useState<number[]>([]);
  const [selectedStyle, setSelectedStyle] = useState<number | null>(null);
  const [isModalVisible, setIsModalVisible] = useState(false);

  const selectedAppearanceLabels = useMemo(
    () => selectedAppearance.map((index) => appearanceOptions[index]),
    [selectedAppearance],
  );

  const selectedPersonalityLabels = useMemo(
    () => selectedPersonality.map((index) => personalityOptions[index]),
    [selectedPersonality],
  );

  const selectedStyleLabel = selectedStyle !== null ? styleOptions[selectedStyle] : null;
  const displayName = name.trim() || '未命名角色';

  const impressionSentence = useMemo(() => {
    const appearanceText = selectedAppearanceLabels.slice(0, 3).join('、');
    const personalityText = selectedPersonalityLabels.slice(0, 3).join('、');
    const styleText = selectedStyleLabel ? selectedStyleLabel.replace('。', '') : '';

    if (!appearanceText && !personalityText && !styleText) {
      return '还没有落笔。先给这个人一点轮廓，故事就会开始向你靠近。';
    }

    const fragments = [
      appearanceText ? `带着${appearanceText}的第一印象` : '',
      personalityText ? `性格里有${personalityText}` : '',
      styleText ? `整体气质偏向${styleText}` : '',
    ].filter(Boolean);

    return `${displayName} ${fragments.join('，')}。`;
  }, [displayName, selectedAppearanceLabels, selectedPersonalityLabels, selectedStyleLabel]);

  const completionCount =
    (name.trim() ? 1 : 0) +
    selectedAppearance.length +
    selectedPersonality.length +
    (selectedStyle !== null ? 1 : 0);

  const completionPercent = Math.min(100, Math.round((completionCount / 12) * 100));

  const toggleAppearance = (index: number) => {
    setSelectedAppearance((prev) => {
      if (prev.includes(index)) return prev.filter((i) => i !== index);
      if (prev.length >= 5) {
        messageApi.warning('外貌关键词最多选择 5 个。');
        return prev;
      }
      return [...prev, index];
    });
  };

  const togglePersonality = (index: number) => {
    setSelectedPersonality((prev) => {
      if (prev.includes(index)) return prev.filter((i) => i !== index);
      if (prev.length >= 5) {
        messageApi.warning('性格关键词最多选择 5 个。');
        return prev;
      }
      return [...prev, index];
    });
  };

  const handleRandomName = () => {
    const randomIndex = Math.floor(Math.random() * nameSamples.length);
    setName(nameSamples[randomIndex]);
  };

  const pickRandomUniqueIndexes = (max: number, count: number) => {
    const pool = [...Array(max).keys()];
    const result: number[] = [];
    for (let i = 0; i < count && pool.length > 0; i++) {
      const randomIndex = Math.floor(Math.random() * pool.length);
      result.push(pool.splice(randomIndex, 1)[0]);
    }
    return result;
  };

  const handleRandomize = () => {
    handleRandomName();
    setHeight(Math.floor(Math.random() * (200 - 140 + 1)) + 140);
    setWeight(Math.floor(Math.random() * (100 - 35 + 1)) + 35);
    setAge(Math.floor(Math.random() * (30 - 18 + 1)) + 18);
    setGender(Math.random() > 0.5 ? 'male' : 'female');
    setSelectedAppearance(pickRandomUniqueIndexes(appearanceOptions.length, 5));
    setSelectedPersonality(pickRandomUniqueIndexes(personalityOptions.length, 5));
    setSelectedStyle(Math.floor(Math.random() * styleOptions.length));
  };

  const handleCategoryPrev = () => {
    setCurrentCategory((prev) => (prev > 0 ? prev - 1 : categories.length - 1));
  };

  const handleCategoryNext = () => {
    setCurrentCategory((prev) => (prev < categories.length - 1 ? prev + 1 : 0));
  };

  const handleBack = () => {
    navigate(ROUTES.FIRST_STEP);
  };

  const handleFinalConfirm = async () => {
    setIsModalVisible(false);
    setLoading(true);

    try {
      const didNavigate = await transitionTo({
        to: ROUTES.CHARACTER_SELECTION,
        variant: 'character',
        work: async ({ animateTo, setProgress }) => {
          setProgress(12);
          const isHealthy = await checkServerHealth();
          if (!isHealthy) {
            messageApi.error('无法连接到服务器，请检查后端服务是否运行。');
            return false;
          }

          await animateTo(28, 420);

          const appearanceData: Record<string, unknown> = {
            keywords: selectedAppearance.map((idx) => appearanceOptions[idx]),
            height,
            weight,
          };

          const personalityData: Record<string, unknown> = {
            keywords: selectedPersonality.map((idx) => personalityOptions[idx]),
          };

          const backgroundData: Record<string, unknown> = {
            style: selectedStyle !== null ? styleOptions[selectedStyle] : null,
          };

          await animateTo(42, 520);

          const response = await createCharacter({
            name: name || '未命名角色',
            appearance: appearanceData,
            personality: personalityData,
            background: backgroundData,
            gender,
            age,
          });

          await animateTo(72, 700);

          const characterId = response.character_id;
          const idStr = characterId != null ? String(characterId).trim() : '';
          if (!idStr || idStr === 'undefined' || idStr === 'null') {
            messageApi.error('创建角色失败：未获取到有效角色 ID。');
            return false;
          }

          const imageUrls = Array.isArray(response.image_urls)
            ? response.image_urls.filter((url): url is string => typeof url === 'string' && url.trim() !== '')
            : [];
          const imageUrl = typeof response.image_url === 'string' ? response.image_url : undefined;
          const responseName = typeof response.name === 'string' ? response.name : '未命名角色';

          const characterData = {
            characterId: idStr,
            name: responseName,
            height,
            weight,
            age,
            gender,
            appearance: selectedAppearance.map((idx) => appearanceOptions[idx]),
            personality: personalityData,
            personalityKeywords: selectedPersonality.map((idx) => personalityOptions[idx]),
            style: selectedStyle !== null ? styleOptions[selectedStyle] : null,
            imageUrl,
            image_urls: imageUrls,
          };

          gameStorage.cleanupGuestOldGameData({
            keepThreadId: null,
            keepLatestEnding: false,
            clearCharacterData: true,
            clearSession: true,
          });
          gameStorage.setCharacterData(characterData);
          gameStorage.removeRestoreIds();
          gameStorage.setCreatedCharacterId(idStr);

          await animateTo(84, 420);
          await preloadImages([imageUrl, ...imageUrls], 9000);
          await animateTo(89, 360);
        },
      });

      if (!didNavigate) {
        setLoading(false);
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      messageApi.error(err.response?.data?.detail || err.message || '创建角色失败，请稍后重试。');
      setLoading(false);
    }
  };

  const getSelectedAppearanceKeywords = () => {
    return selectedAppearance.map((index) => ({
      label: appearanceOptions[index],
      value: index,
      onRemove: () => setSelectedAppearance((prev) => prev.filter((i) => i !== index)),
    }));
  };

  const getSelectedPersonalityKeywords = () => {
    return selectedPersonality.map((index) => ({
      label: personalityOptions[index],
      value: index,
      onRemove: () => setSelectedPersonality((prev) => prev.filter((i) => i !== index)),
    }));
  };

  const getSelectedStyle = () => {
    if (selectedStyle === null) return null;
    return {
      label: styleOptions[selectedStyle],
      value: selectedStyle,
      onRemove: () => setSelectedStyle(null),
    };
  };

  const renderSelectedTags = (items: string[], emptyText: string) => {
    if (items.length === 0) {
      return <span className="character-empty-pill">{emptyText}</span>;
    }

    return items.map((item) => (
      <span className="character-summary-pill" key={item}>
        {item}
      </span>
    ));
  };

  return (
    <div className="character-setting-page">
      {messageContextHolder}

      <div
        className="character-setting-background"
        style={{
          backgroundImage: `url(${backgroundImage})`,
        }}
      />
      <div className="character-setting-overlay" />
      <div className="character-setting-vignette" />

      <main className="character-setting-shell">
        <section className="character-setting-intro" aria-labelledby="character-setting-title">
          <button type="button" className="character-back-button" onClick={handleBack} aria-label="返回上一步">
            <LeftOutlined aria-hidden="true" />
            <span>返回</span>
          </button>
          <p className="character-setting-kicker">Character Studio</p>
          <h1 className="character-setting-title" id="character-setting-title">
            角色工作室
          </h1>
          <p className="character-setting-subtitle">把一个模糊的人影，慢慢写成会与你相遇的人。</p>
        </section>

        <section className="character-workbench" aria-label="角色创建面板">
          <aside className="character-impression-panel" aria-label="角色印象预览">
            <div className="character-impression-header">
              <span className="character-panel-eyebrow">角色印象</span>
              <span className="character-progress-text">{completionPercent}%</span>
            </div>

            <div className="character-progress-track" aria-hidden="true">
              <div className="character-progress-fill" style={{ width: `${completionPercent}%` }} />
            </div>

            <div className="character-avatar-orbit" aria-hidden="true">
              <span className="character-avatar-core">{displayName.slice(0, 1)}</span>
            </div>

            <div className="character-profile-card">
              <span className="character-profile-label">姓名</span>
              <strong>{displayName}</strong>
            </div>

            <div className="character-profile-grid">
              <div>
                <span>性别</span>
                <strong>{gender === 'male' ? '男' : '女'}</strong>
              </div>
              <div>
                <span>年龄</span>
                <strong>{age} 岁</strong>
              </div>
              <div>
                <span>身高</span>
                <strong>{height} cm</strong>
              </div>
              <div>
                <span>体重</span>
                <strong>{weight} kg</strong>
              </div>
            </div>

            <p className="character-impression-copy">{impressionSentence}</p>

            <div className="character-summary-group">
              <span className="character-summary-label">外貌线索</span>
              <div className="character-summary-tags">
                {renderSelectedTags(selectedAppearanceLabels, '等待选择')}
              </div>
            </div>

            <div className="character-summary-group">
              <span className="character-summary-label">性格线索</span>
              <div className="character-summary-tags">
                {renderSelectedTags(selectedPersonalityLabels, '等待选择')}
              </div>
            </div>
          </aside>

          <section className="character-editor-panel" aria-label="角色设定表单">
            <div className="character-editor-topline">
              <div>
                <span className="character-panel-eyebrow">创作面板</span>
                <h2>写下第一眼的答案</h2>
              </div>
              <Button className="random-button" icon={<ReloadOutlined />} onClick={handleRandomize}>
                随机灵感
              </Button>
            </div>

            <div className="character-name-section">
              <label className="character-field-label" htmlFor="character-name">
                角色姓名
              </label>
              <Input
                id="character-name"
                className="name-input"
                placeholder="请输入角色姓名"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={20}
                suffix={
                  <Button
                    aria-label="随机生成角色姓名"
                    type="text"
                    icon={<ReloadOutlined />}
                    onClick={handleRandomName}
                    className="name-random-icon"
                    size="small"
                  />
                }
              />
            </div>

            <div className="character-basics-grid">
              <div className="slider-group">
                <div className="slider-heading">
                  <span className="slider-label">身高</span>
                  <span className="slider-value">{height}cm</span>
                </div>
                <Slider
                  min={140}
                  max={200}
                  value={height}
                  onChange={(value) => setHeight(Array.isArray(value) ? value[0] : value)}
                  tooltip={{ formatter: (value) => `${value}cm` }}
                />
              </div>

              <div className="slider-group">
                <div className="slider-heading">
                  <span className="slider-label">体重</span>
                  <span className="slider-value">{weight}kg</span>
                </div>
                <Slider
                  min={35}
                  max={100}
                  value={weight}
                  onChange={(value) => setWeight(Array.isArray(value) ? value[0] : value)}
                  tooltip={{ formatter: (value) => `${value}kg` }}
                />
              </div>

              <div className="slider-group">
                <div className="slider-heading">
                  <span className="slider-label">年龄</span>
                  <span className="slider-value">{age}岁</span>
                </div>
                <Slider
                  min={16}
                  max={60}
                  value={age}
                  onChange={(value) => setAge(Array.isArray(value) ? value[0] : value)}
                  tooltip={{ formatter: (value) => `${value}岁` }}
                />
              </div>

              <div className="gender-selector" role="group" aria-label="选择角色性别">
                <button
                  type="button"
                  className={`gender-option gender-option-male ${gender === 'male' ? 'selected' : ''}`}
                  aria-pressed={gender === 'male'}
                  onClick={() => setGender('male')}
                >
                  <ManOutlined />
                  男
                </button>
                <button
                  type="button"
                  className={`gender-option gender-option-female ${gender === 'female' ? 'selected' : ''}`}
                  aria-pressed={gender === 'female'}
                  onClick={() => setGender('female')}
                >
                  <WomanOutlined />
                  女
                </button>
              </div>
            </div>

            <div className="category-tabs" role="tablist" aria-label="角色设定分类">
              {categories.map((category, index) => (
                <button
                  key={category}
                  type="button"
                  className={`category-tab ${currentCategory === index ? 'active' : ''}`}
                  role="tab"
                  aria-selected={currentCategory === index}
                  onClick={() => setCurrentCategory(index)}
                >
                  {category}
                </button>
              ))}
            </div>

            <div className="character-choice-stage">
              <div className="choice-stage-header">
                <div>
                  <span className="character-panel-eyebrow">{categories[currentCategory]}</span>
                  <h3>
                    {currentCategory === 0 && '选择最多 5 个外貌线索'}
                    {currentCategory === 1 && '选择最多 5 个性格线索'}
                    {currentCategory === 2 && '选择一个整体风格'}
                  </h3>
                </div>
                <span className="choice-counter">
                  {currentCategory === 0 && `${selectedAppearance.length}/5`}
                  {currentCategory === 1 && `${selectedPersonality.length}/5`}
                  {currentCategory === 2 && (selectedStyle === null ? '0/1' : '1/1')}
                </span>
              </div>

              {currentCategory === 0 && (
                <div className="choice-chip-grid">
                  {appearanceOptions.map((option, index) => (
                    <button
                      key={option}
                      type="button"
                      className={`choice-chip ${selectedAppearance.includes(index) ? 'selected' : ''}`}
                      aria-pressed={selectedAppearance.includes(index)}
                      onClick={() => toggleAppearance(index)}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              )}

              {currentCategory === 1 && (
                <div className="choice-chip-grid">
                  {personalityOptions.map((option, index) => (
                    <button
                      key={option}
                      type="button"
                      className={`choice-chip ${selectedPersonality.includes(index) ? 'selected' : ''}`}
                      aria-pressed={selectedPersonality.includes(index)}
                      onClick={() => togglePersonality(index)}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              )}

              {currentCategory === 2 && (
                <div className="style-option-list">
                  {styleOptions.map((option, index) => (
                    <button
                      key={option}
                      type="button"
                      className={`style-option ${selectedStyle === index ? 'selected' : ''}`}
                      aria-pressed={selectedStyle === index}
                      onClick={() => setSelectedStyle(index)}
                    >
                      <span className="style-option-number">{String(index + 1).padStart(2, '0')}</span>
                      <span className="style-option-text">{option}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="category-navigation">
              <Button aria-label="上一个分类" className="nav-arrow-button" icon={<LeftOutlined />} onClick={handleCategoryPrev} />
              <Button aria-label="下一个分类" className="nav-arrow-button" icon={<RightOutlined />} onClick={handleCategoryNext} />
              <Button className="confirm-button" onClick={() => setIsModalVisible(true)}>
                生成角色
              </Button>
            </div>
          </section>
        </section>
      </main>

      <Modal
        title="确认角色档案"
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setIsModalVisible(false)}>
            再想想
          </Button>,
          <Button key="confirm" type="primary" onClick={handleFinalConfirm} disabled={loading}>
            确认生成
          </Button>,
        ]}
        width={680}
        className="character-confirm-modal"
      >
        <div className="modal-content">
          <div className="modal-section">
            <h4 className="modal-section-title">基础档案</h4>
            <div className="modal-info-grid">
              <div className="modal-info-item">
                <span className="info-label">姓名</span>
                <span className="info-value">{displayName}</span>
              </div>
              <div className="modal-info-item">
                <span className="info-label">性别</span>
                <span className="info-value">{gender === 'male' ? '男' : '女'}</span>
              </div>
              <div className="modal-info-item">
                <span className="info-label">年龄</span>
                <span className="info-value">{age}岁</span>
              </div>
              <div className="modal-info-item">
                <span className="info-label">身高</span>
                <span className="info-value">{height}cm</span>
              </div>
              <div className="modal-info-item">
                <span className="info-label">体重</span>
                <span className="info-value">{weight}kg</span>
              </div>
            </div>
          </div>

          <div className="modal-section">
            <h4 className="modal-section-title">已写下的线索</h4>

            <div className="keywords-group">
              <div className="keywords-group-title">外貌</div>
              {getSelectedAppearanceKeywords().length > 0 ? (
                <div className="keywords-tags">
                  {getSelectedAppearanceKeywords().map((keyword) => (
                    <div key={keyword.value} className="keyword-tag-item">
                      <span className="keyword-tag-label">{keyword.label}</span>
                      <Button
                        aria-label={`移除外貌线索 ${keyword.label}`}
                        type="text"
                        icon={<CloseOutlined />}
                        onClick={keyword.onRemove}
                        className="keyword-tag-remove"
                        size="small"
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-keywords-hint">暂未选择</div>
              )}
            </div>

            <div className="keywords-group">
              <div className="keywords-group-title">性格</div>
              {getSelectedPersonalityKeywords().length > 0 ? (
                <div className="keywords-tags">
                  {getSelectedPersonalityKeywords().map((keyword) => (
                    <div key={keyword.value} className="keyword-tag-item">
                      <span className="keyword-tag-label">{keyword.label}</span>
                      <Button
                        aria-label={`移除性格线索 ${keyword.label}`}
                        type="text"
                        icon={<CloseOutlined />}
                        onClick={keyword.onRemove}
                        className="keyword-tag-remove"
                        size="small"
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-keywords-hint">暂未选择</div>
              )}
            </div>

            {getSelectedStyle() && (
              <div className="keywords-group">
                <div className="keywords-group-title">风格</div>
                <div className="keywords-tags">
                  <div className="keyword-tag-item">
                    <span className="keyword-tag-label">{getSelectedStyle()!.label}</span>
                    <Button
                      aria-label="移除风格线索"
                      type="text"
                      icon={<CloseOutlined />}
                      onClick={getSelectedStyle()!.onRemove}
                      className="keyword-tag-remove"
                      size="small"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default CharacterSetting;
