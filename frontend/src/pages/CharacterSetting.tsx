import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Slider, message, Modal, Input } from 'antd';
import { 
  LeftOutlined, 
  RightOutlined,
  ManOutlined,
  WomanOutlined,
  CloseOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import backgroundImage from '@/assets/images/settingcharacterbackground.png';
import LoadingScreen from '@/components/loading';
import { checkServerHealth, createCharacter } from '@/services/api';
import './CharacterSetting.css';

function CharacterSetting() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('正在连接服务器...');
  
  // 角色属性状态
  const [name, setName] = useState('');
  const [height, setHeight] = useState(160);
  const [weight, setWeight] = useState(45);
  const [age, setAge] = useState(18);
  const [gender, setGender] = useState<'male' | 'female'>('male');
  const [currentCategory, setCurrentCategory] = useState(0);
  
  // 角色特征类别
  const categories = [
    '外貌', '性格', '风格'
  ];

  // 名字样本列表
  const nameSamples = [
    '林清漪', '苏云蘅', '沈疏桐', '顾砚秋', '叶令仪', '江望舒', '白鹤笙', '陆昭华',
    '秦砚知', '楚雪蘅', '周枕河', '许徽音', '谢照夜', '韩停云', '冯砚溪', '程令嫕',
    '蔡青梧', '潘漱玉', '袁既白', '于兰猗', '董砚初', '萧星遥', '邵徽柔', '曾照微',
    '吕云止', '黄怀瑾', '邓景行', '傅砚修', '彭既明', '鲁允执', '韦鹤声', '崔砚舟',
    '康昭明', '卢云崖', '蒋徽言', '蔡砚川', '余既和', '杜停岳', '叶照临', '魏砚声',
    '薛令闻', '潘青崖', '丁既安', '任徽猷', '范星野', '石砚北', '熊云澹', '金照野',
    '邱既同', '侯砚澂'
  ];

  // 外貌选项（关键词按钮）
  const appearanceOptions = [
    '高挑', '清秀', '文艺', '简约', '长发', '黑发', '眼镜', '修长',
    '温柔', '素雅', '清新', '棕发', '健壮', '阳光', '运动', '体操',
    '短发', '发带', '匀称', '开朗', '活力', '清爽', '马尾', '苗条',
    '高冷', '时尚', '潮流', '银发', '瘦削', '冷艳', '前卫', '暗黑',
    '卷发', '红发', '耳饰', '健美', '热情', '户外', '手套', '精致',
    '金发', '温婉', '围巾', '明朗', '帽饰', '双尾', '冷静', '极简',
    '日系', '齐刘', '健硕', '街头', '链饰', '内敛', '轻奢', '盘发',
    '清丽', '披发', '中发', '汗带', '神秘', '面纱', '都市', '耳环',
    '中卷', '校园', '工装', '手表', '娴雅', '明亮', '鲜艳', '花饰',
    '珠饰', '直率', '海风', '墨镜', '蓝发', '白发'
  ];

  // 性格选项（关键词按钮）
  const personalityOptions = [
    '外向', '内向', '温柔', '冷静', '热情', '沉稳', '活泼', '安静',
    '开朗', '内敛', '高冷', '明朗', '沉着', '坦率', '细腻', '粗犷',
    '谨慎', '果断', '善良', '体贴', '柔和', '冷漠', '幽默', '浪漫',
    '理性', '感性', '执着', '随性', '倔强', '温婉', '冷傲', '单纯',
    '敏锐', '聪慧', '自信', '自卑', '轻松', '放松', '勤奋', '懒散',
    '成熟', '稚气', '可靠', '谨严', '热忱', '仔细', '随和', '刻板',
    '豁达', '拘谨'
  ];

  // 风格选项
  const styleOptions = [
    '简约现代，追求简洁实用的设计风格',
    '复古怀旧，喜欢经典和传统元素',
    '前卫时尚，追求最新潮流和趋势',
    '自然田园，崇尚自然和舒适感',
    '奢华精致，注重品质和细节',
    '极简主义，追求极致的简洁和纯粹',
    '混搭风格，善于融合不同元素',
    '艺术创意，充满艺术气息和创造力'
  ];

  // 当前选择的选项状态（支持多选）
  const [selectedAppearance, setSelectedAppearance] = useState<number[]>([]);
  const [selectedPersonality, setSelectedPersonality] = useState<number[]>([]);
  const [selectedStyle, setSelectedStyle] = useState<number | null>(null);
  
  // 切换外貌关键词选择（最多5个）
  const toggleAppearance = (index: number) => {
    setSelectedAppearance(prev => {
      if (prev.includes(index)) {
        // 取消选择
        return prev.filter(i => i !== index);
      } else {
        // 检查是否已达到5个限制
        if (prev.length >= 5) {
          message.warning('最多只能选择5个外貌关键词');
          return prev;
        }
        return [...prev, index];
      }
    });
  };
  
  // 切换性格关键词选择（最多5个）
  const togglePersonality = (index: number) => {
    setSelectedPersonality(prev => {
      if (prev.includes(index)) {
        // 取消选择
        return prev.filter(i => i !== index);
      } else {
        // 检查是否已达到5个限制
        if (prev.length >= 5) {
          message.warning('最多只能选择5个性格关键词');
          return prev;
        }
        return [...prev, index];
      }
    });
  };
  
  // 弹窗状态
  const [isModalVisible, setIsModalVisible] = useState(false);

  // 随机生成名字
  const handleRandomName = () => {
    const randomIndex = Math.floor(Math.random() * nameSamples.length);
    setName(nameSamples[randomIndex]);
  };

  // 随机生成所有属性
  const handleRandomize = () => {
    // 随机姓名
    const randomNameIndex = Math.floor(Math.random() * nameSamples.length);
    setName(nameSamples[randomNameIndex]);
    
    // 随机身高 (140-200)
    setHeight(Math.floor(Math.random() * (200 - 140 + 1)) + 140);
    
    // 随机体重 (35-100)
    setWeight(Math.floor(Math.random() * (100 - 35 + 1)) + 35);
    
    // 随机年龄 (18-30)
    setAge(Math.floor(Math.random() * (30 - 18 + 1)) + 18);
    
    // 随机性别
    setGender(Math.random() > 0.5 ? 'male' : 'female');
    
    // 随机选择5个外貌关键词
    const randomAppearance: number[] = [];
    const appearanceIndices = [...Array(appearanceOptions.length).keys()];
    for (let i = 0; i < 5 && appearanceIndices.length > 0; i++) {
      const randomIndex = Math.floor(Math.random() * appearanceIndices.length);
      randomAppearance.push(appearanceIndices.splice(randomIndex, 1)[0]);
    }
    setSelectedAppearance(randomAppearance);
    
    // 随机选择5个性格关键词
    const randomPersonality: number[] = [];
    const personalityIndices = [...Array(personalityOptions.length).keys()];
    for (let i = 0; i < 5 && personalityIndices.length > 0; i++) {
      const randomIndex = Math.floor(Math.random() * personalityIndices.length);
      randomPersonality.push(personalityIndices.splice(randomIndex, 1)[0]);
    }
    setSelectedPersonality(randomPersonality);
    
    // 随机风格
    const randomStyleIndex = Math.floor(Math.random() * styleOptions.length);
    setSelectedStyle(randomStyleIndex);
  };

  // 性别切换
  const handleGenderToggle = () => {
    setGender(gender === 'male' ? 'female' : 'male');
  };

  // 类别导航
  const handleCategoryPrev = () => {
    setCurrentCategory((prev) => (prev > 0 ? prev - 1 : categories.length - 1));
  };

  const handleCategoryNext = () => {
    setCurrentCategory((prev) => (prev < categories.length - 1 ? prev + 1 : 0));
  };

  // 显示确认弹窗
  const handleConfirm = () => {
    setIsModalVisible(true);
  };

  // 取消弹窗
  const handleModalCancel = () => {
    setIsModalVisible(false);
  };

  // 最终确认创建角色
  const handleFinalConfirm = async () => {
    setIsModalVisible(false);
    setLoading(true);
    setLoadingMessage('创建人物中...');
    
    try {
      // 检查后端服务是否可用
      const isHealthy = await checkServerHealth();
      
      if (!isHealthy) {
        message.error('无法连接到服务器，请检查后端服务是否运行');
        setLoading(false);
        return;
      }

      // 准备角色数据
      const appearanceData: Record<string, any> = {
        keywords: selectedAppearance.length > 0 ? selectedAppearance.map(idx => appearanceOptions[idx]) : [],
        height,
        weight,
      };

      const personalityData: Record<string, any> = {
        keywords: selectedPersonality.length > 0 ? selectedPersonality.map(idx => personalityOptions[idx]) : [],
      };

      const backgroundData: Record<string, any> = {
        style: selectedStyle !== null ? styleOptions[selectedStyle] : null,
      };

      // 更新加载消息，提示用户图片生成需要时间
      setLoadingMessage('等待你的专属陪伴角色');
      
      // 发送JSON数据到后端服务器（包含AI图片生成，超时时间已设置为180秒）
      const response = await createCharacter({
        name: name || '未命名角色',
        appearance: appearanceData,
        personality: personalityData,
        background: backgroundData,
        gender: gender === 'male' ? 'male' : 'female',
        age: age,
      });

      // 保存角色信息到 sessionStorage
      // 注意：响应拦截器返回的是 response.data，即 {code, message, data}
      // 所以需要访问 response.data 来获取实际数据
      console.log('[角色设置] 后端响应数据（拦截器处理后）:', response);
      
      // 处理响应数据：拦截器返回的是 {code, message, data}，需要提取 data 字段
      const responseData = response?.data || response;
      console.log('[角色设置] 提取的responseData:', responseData);
      console.log('[角色设置] responseData.character_id:', responseData.character_id);
      console.log('[角色设置] responseData.image_urls:', responseData.image_urls);
      
      // 验证character_id是否有效
      const characterId = responseData.character_id;
      if (!characterId || characterId === 'undefined' || characterId === 'null' || String(characterId).trim() === '') {
        console.error('[角色设置] 无效的character_id:', characterId);
        console.error('[角色设置] 完整响应:', JSON.stringify(response, null, 2));
        console.error('[角色设置] responseData:', JSON.stringify(responseData, null, 2));
        message.error('创建角色失败：未获取到有效的角色ID，请检查后端服务');
        setLoading(false);
        return;
      }
      
      // 验证image_urls是否存在且不为空
      const imageUrls = responseData.image_urls || [];
      console.log('[角色设置] 图片URL列表:', imageUrls);
      console.log('[角色设置] 图片URL数量:', imageUrls.length);
      
      if (imageUrls.length === 0) {
        console.warn('[角色设置] 警告：未获取到图片URL列表，但继续流程');
      }
      
      const characterData = {
        characterId: String(characterId), // 确保是字符串
        name: responseData.name || '未命名角色',
        height,
        weight,
        age,
        gender,
        appearance: selectedAppearance.length > 0 ? selectedAppearance.map(idx => appearanceOptions[idx]) : [],
        personality: selectedPersonality.length > 0 ? selectedPersonality.map(idx => personalityOptions[idx]) : [],
        style: selectedStyle !== null ? styleOptions[selectedStyle] : null,
        imageUrl: responseData.image_url, // 从后端响应中获取图片URL（单张，兼容旧逻辑）
        image_urls: imageUrls, // 组图URL列表（3张图片，供三选一）
        timestamp: Date.now(),
      };
      
      console.log('[角色设置] 保存到sessionStorage的角色数据:', characterData);
      console.log('[角色设置] characterId类型:', typeof characterData.characterId);
      console.log('[角色设置] characterId值:', characterData.characterId);
      
      sessionStorage.setItem('characterData', JSON.stringify(characterData));
      
      // 清除之前的存档信息
      sessionStorage.removeItem('restoreThreadId');
      sessionStorage.removeItem('restoreCharacterId');
      
      // 保存角色ID用于后续获取图片
      sessionStorage.setItem('createdCharacterId', String(characterId));
      console.log('[角色设置] 已保存createdCharacterId:', characterId);
      
      // 验证保存是否成功
      const savedData = sessionStorage.getItem('characterData');
      const savedId = sessionStorage.getItem('createdCharacterId');
      console.log('[角色设置] 验证保存结果 - characterData存在:', !!savedData);
      console.log('[角色设置] 验证保存结果 - createdCharacterId存在:', !!savedId);
      if (savedData) {
        const parsed = JSON.parse(savedData);
        console.log('[角色设置] 验证保存结果 - characterId字段:', parsed.characterId);
      }
      
      setLoadingMessage('正在加载角色图片...');
      // 短暂延迟以显示加载消息
      await new Promise(resolve => setTimeout(resolve, 500));
      navigate('/characterselection');
    } catch (error: any) {
      console.error('创建角色失败:', error);
      message.error(error.response?.data?.detail || error.message || '创建角色失败，请稍后重试');
      setLoading(false);
    }
  };

  // 获取已选择的外貌关键词
  const getSelectedAppearanceKeywords = () => {
    return selectedAppearance.map(index => ({
      label: appearanceOptions[index],
      value: index,
      onRemove: () => {
        setSelectedAppearance(prev => prev.filter(i => i !== index));
      }
    }));
  };
  
  // 获取已选择的性格关键词
  const getSelectedPersonalityKeywords = () => {
    return selectedPersonality.map(index => ({
      label: personalityOptions[index],
      value: index,
      onRemove: () => {
        setSelectedPersonality(prev => prev.filter(i => i !== index));
      }
    }));
  };
  
  // 获取已选择的风格
  const getSelectedStyle = () => {
    if (selectedStyle !== null) {
      return {
        label: styleOptions[selectedStyle],
        value: selectedStyle,
        onRemove: () => setSelectedStyle(null)
      };
    }
    return null;
  };

  if (loading) {
    return <LoadingScreen message={loadingMessage} />;
  }

  return (
    <div className="character-setting-container">
      {/* 背景图片 */}
      <div 
        className="character-setting-background"
        style={{
          backgroundImage: `url(${backgroundImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      />

      {/* 主内容区域 */}
      <div className="character-setting-content">
        {/* 姓名输入框和随机按钮 */}
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
          <Button
            className="random-button"
            onClick={handleRandomize}
          >
            随机一下
          </Button>
        </div>

        {/* 顶部控制区域 */}
        <div className="character-setting-top">
          {/* 身高滑块 */}
          <div className="slider-group">
            <span className="slider-label">身高</span>
            <Slider
              min={140}
              max={200}
              value={height}
              onChange={setHeight}
              style={{ flex: 1, minWidth: 120 }}
              tooltip={{ formatter: (value) => `${value}cm` }}
            />
            <div className="slider-value">{height}cm</div>
          </div>

          {/* 体重滑块 */}
          <div className="slider-group">
            <span className="slider-label">体重</span>
            <Slider
              min={35}
              max={100}
              value={weight}
              onChange={setWeight}
              style={{ flex: 1, minWidth: 120 }}
              tooltip={{ formatter: (value) => `${value}kg` }}
            />
            <div className="slider-value">{weight}kg</div>
          </div>

          {/* 年龄滑块 */}
          <div className="slider-group">
            <span className="slider-label">年龄</span>
            <Slider
              min={1}
              max={100}
              value={age}
              onChange={setAge}
              style={{ flex: 1, minWidth: 120 }}
              tooltip={{ formatter: (value) => `${value}岁` }}
            />
            <div className="slider-value">{age}岁</div>
          </div>

          {/* 性别选择 */}
          <Button
            className="gender-button"
            onClick={handleGenderToggle}
            icon={gender === 'male' ? <ManOutlined /> : <WomanOutlined />}
          >
            性别: {gender === 'male' ? ' 男' : ' 女'}
          </Button>
        </div>

        {/* 中部内容区域 */}
        <div className="character-setting-middle">
          {/* 左侧选项按钮 */}
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

          {/* 中央预览区 */}
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

        {/* 类别导航箭头和确认按钮 */}
        <div className="category-navigation">
          <Button
            className="nav-arrow-button"
            icon={<LeftOutlined />}
            onClick={handleCategoryPrev}
          />
          <Button
            className="nav-arrow-button"
            icon={<RightOutlined />}
            onClick={handleCategoryNext}
          />
          <Button
            className="confirm-button"
            onClick={handleConfirm}
          >
            confirm
          </Button>
        </div>
      </div>

      {/* 确认弹窗 */}
      <Modal
        title="确认角色信息"
        open={isModalVisible}
        onCancel={handleModalCancel}
        footer={[
          <Button key="cancel" onClick={handleModalCancel}>
            取消
          </Button>,
          <Button key="confirm" type="primary" onClick={handleFinalConfirm}>
            确认创建
          </Button>
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
            <h4 className="modal-section-title">已选择的关键词</h4>
            
            {/* 外貌关键词 */}
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
            
            {/* 性格关键词 */}
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
            
            {/* 风格 */}
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
