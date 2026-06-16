import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Slider, message, Modal, Input } from 'antd';
import {
  LeftOutlined,
  RightOutlined,
  ManOutlined,
  WomanOutlined,
  CloseOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import backgroundImage from '@/assets/images/settingcharacterbackground.png';
import LoadingScreen from '@/components/loading';
import { checkServerHealth, createCharacter } from '@/services/api';
import { ROUTES } from '@/config/routes';
import * as gameStorage from '@/storage/gameStorage';
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
  const [messageApi, messageContextHolder] = message.useMessage();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('正在连接服务器...');

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

  const handleGenderToggle = () => {
    setGender((prev) => (prev === 'male' ? 'female' : 'male'));
  };

  const handleCategoryPrev = () => {
    setCurrentCategory((prev) => (prev > 0 ? prev - 1 : categories.length - 1));
  };

  const handleCategoryNext = () => {
    setCurrentCategory((prev) => (prev < categories.length - 1 ? prev + 1 : 0));
  };

  const handleFinalConfirm = async () => {
    setIsModalVisible(false);
    setLoading(true);
    setLoadingMessage('正在创建角色...');

    try {
      const isHealthy = await checkServerHealth();
      if (!isHealthy) {
        messageApi.error('无法连接到服务器，请检查后端服务是否运行。');
        setLoading(false);
        return;
      }

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

      setLoadingMessage('正在生成你的专属角色...');

      const response = await createCharacter({
        name: name || '未命名角色',
        appearance: appearanceData,
        personality: personalityData,
        background: backgroundData,
        gender,
        age,
      });

      const characterId = response.character_id;
      const idStr = characterId != null ? String(characterId).trim() : '';
      if (!idStr || idStr === 'undefined' || idStr === 'null') {
        messageApi.error('创建角色失败：未获取到有效角色 ID。');
        setLoading(false);
        return;
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
        personality: selectedPersonality.map((idx) => personalityOptions[idx]),
        style: selectedStyle !== null ? styleOptions[selectedStyle] : null,
        imageUrl,
        image_urls: imageUrls,
      };

      gameStorage.setCharacterData(characterData);
      gameStorage.removeRestoreIds();
      gameStorage.setCreatedCharacterId(idStr);

      setLoadingMessage('正在加载角色图片...');
      await new Promise((r) => setTimeout(r, 500));
      navigate(ROUTES.CHARACTER_SELECTION);
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

  if (loading) {
    return (
      <>
        {messageContextHolder}
        <LoadingScreen message={loadingMessage} />
      </>
    );
  }

  return (
    <div className="character-setting-container">
      {messageContextHolder}

      <div
        className="character-setting-background"
        style={{
          backgroundImage: `url(${backgroundImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      />

      <div className="character-setting-content">
        <div className="character-name-section">
          <div className="character-name-input">
            <span className="name-label">姓名:</span>
            <Input
              className="name-input"
              placeholder="请输入角色姓名"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={20}
              suffix={
                <Button
                  type="text"
                  icon={<ReloadOutlined />}
                  onClick={handleRandomName}
                  className="name-random-icon"
                  size="small"
                />
              }
            />
          </div>
          <Button className="random-button" onClick={handleRandomize}>
            随机一组
          </Button>
        </div>

        <div className="character-setting-top">
          <div className="slider-group">
            <span className="slider-label">身高</span>
            <Slider
              min={140}
              max={200}
              value={height}
              onChange={(value) => setHeight(Array.isArray(value) ? value[0] : value)}
              style={{ flex: 1, minWidth: 120 }}
              tooltip={{ formatter: (value) => `${value}cm` }}
            />
            <div className="slider-value">{height}cm</div>
          </div>

          <div className="slider-group">
            <span className="slider-label">体重</span>
            <Slider
              min={35}
              max={100}
              value={weight}
              onChange={(value) => setWeight(Array.isArray(value) ? value[0] : value)}
              style={{ flex: 1, minWidth: 120 }}
              tooltip={{ formatter: (value) => `${value}kg` }}
            />
            <div className="slider-value">{weight}kg</div>
          </div>

          <div className="slider-group">
            <span className="slider-label">年龄</span>
            <Slider
              min={16}
              max={60}
              value={age}
              onChange={(value) => setAge(Array.isArray(value) ? value[0] : value)}
              style={{ flex: 1, minWidth: 120 }}
              tooltip={{ formatter: (value) => `${value}岁` }}
            />
            <div className="slider-value">{age}岁</div>
          </div>

          <Button
            className="gender-button"
            onClick={handleGenderToggle}
            icon={gender === 'male' ? <ManOutlined /> : <WomanOutlined />}
          >
            性别: {gender === 'male' ? '男' : '女'}
          </Button>
        </div>

        <div className="character-setting-middle">
          <div className="character-options">
            {Array.from({ length: 3 }).map((_, index) => (
              <Button
                key={index}
                className={`option-button ${currentCategory === index ? 'active' : ''}`}
                onClick={() => setCurrentCategory(index)}
              >
                {categories[index] || `选项${index + 1}`}
              </Button>
            ))}
          </div>

          <div className="character-preview">
            <div className="preview-content">
              {currentCategory === 0 && (
                <div className="category-content">
                  <div className="appearance-grid">
                    {appearanceOptions.map((option, index) => (
                      <button
                        key={index}
                        type="button"
                        className={`appearance-button ${selectedAppearance.includes(index) ? 'selected' : ''}`}
                        onClick={() => toggleAppearance(index)}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {currentCategory === 1 && (
                <div className="category-content">
                  <div className="personality-grid">
                    {personalityOptions.map((option, index) => (
                      <button
                        key={index}
                        type="button"
                        className={`personality-button ${selectedPersonality.includes(index) ? 'selected' : ''}`}
                        onClick={() => togglePersonality(index)}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {currentCategory === 2 && (
                <div className="category-content">
                  <div className="options-list">
                    {styleOptions.map((option, index) => (
                      <div
                        key={index}
                        className={`option-item ${selectedStyle === index ? 'selected' : ''}`}
                        onClick={() => setSelectedStyle(index)}
                      >
                        <span className="option-number">{index + 1}.</span>
                        <span className="option-text">{option}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="category-navigation">
          <Button className="nav-arrow-button" icon={<LeftOutlined />} onClick={handleCategoryPrev} />
          <Button className="nav-arrow-button" icon={<RightOutlined />} onClick={handleCategoryNext} />
          <Button className="confirm-button" onClick={() => setIsModalVisible(true)}>
            确认
          </Button>
        </div>
      </div>

      <Modal
        title="确认角色信息"
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setIsModalVisible(false)}>
            取消
          </Button>,
          <Button key="confirm" type="primary" onClick={handleFinalConfirm}>
            确认创建
          </Button>,
        ]}
        width={620}
        className="character-confirm-modal"
      >
        <div className="modal-content">
          <div className="modal-section">
            <h4 className="modal-section-title">基本信息</h4>
            <div className="modal-info-item">
              <span className="info-label">姓名:</span>
              <span className="info-value">{name || '未填写'}</span>
            </div>
            <div className="modal-info-item">
              <span className="info-label">身高:</span>
              <span className="info-value">{height}cm</span>
            </div>
            <div className="modal-info-item">
              <span className="info-label">体重:</span>
              <span className="info-value">{weight}kg</span>
            </div>
            <div className="modal-info-item">
              <span className="info-label">年龄:</span>
              <span className="info-value">{age}岁</span>
            </div>
            <div className="modal-info-item">
              <span className="info-label">性别:</span>
              <span className="info-value">{gender === 'male' ? '男' : '女'}</span>
            </div>
          </div>

          <div className="modal-section">
            <h4 className="modal-section-title">已选择关键词</h4>

            <div className="keywords-group">
              <div className="keywords-group-title">外貌</div>
              {getSelectedAppearanceKeywords().length > 0 ? (
                <div className="keywords-tags">
                  {getSelectedAppearanceKeywords().map((keyword, index) => (
                    <div key={index} className="keyword-tag-item">
                      <span className="keyword-tag-label">{keyword.label}</span>
                      <Button
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
                  {getSelectedPersonalityKeywords().map((keyword, index) => (
                    <div key={index} className="keyword-tag-item">
                      <span className="keyword-tag-label">{keyword.label}</span>
                      <Button
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

