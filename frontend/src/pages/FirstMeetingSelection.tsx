import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, message } from 'antd';
import { LeftOutlined, RightOutlined } from '@ant-design/icons';
import backgroundImage from '@/assets/images/firstbackgound.jpg';
import LoadingScreen from '@/components/loading';
import { checkServerHealth, initGame, initializeStory } from '@/services/api';
import './FirstMeetingSelection.css';

interface SceneOption {
  id: string;
  name: string;
  description: string;
  imageUrl?: string;
}

function FirstMeetingSelection() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('正在加载场景...');
  const [currentSceneIndex, setCurrentSceneIndex] = useState(0);

  // 初遇场景选项列表（可以从后端获取）
  const sceneOptions: SceneOption[] = [
    {
      id: '1',
      name: '樱花街道',
      description: '在樱花飞舞的街道上初次相遇',
      imageUrl: undefined, // 从后端获取
    },
    {
      id: '2',
      name: '咖啡厅',
      description: '在温馨的咖啡厅里偶然邂逅',
      imageUrl: undefined,
    },
    {
      id: '3',
      name: '图书馆',
      description: '在安静的图书馆中不期而遇',
      imageUrl: undefined,
    },
    {
      id: '4',
      name: '公园',
      description: '在春日的公园里初次见面',
      imageUrl: undefined,
    },
  ];

  // 切换到上一个场景
  const handlePreviousScene = () => {
    setCurrentSceneIndex((prev) => 
      prev === 0 ? sceneOptions.length - 1 : prev - 1
    );
  };

  // 切换到下一个场景
  const handleNextScene = () => {
    setCurrentSceneIndex((prev) => 
      prev === sceneOptions.length - 1 ? 0 : prev + 1
    );
  };

  // 选择场景
  const handleSelectScene = async () => {
    const selectedScene = sceneOptions[currentSceneIndex];
    
    try {
      // 检查后端服务是否可用
      const isHealthy = await checkServerHealth();
      
      if (!isHealthy) {
        message.error('无法连接到服务器，请检查后端服务是否运行');
        return;
      }

      // 保存选中的场景信息
      const characterDataStr = sessionStorage.getItem('characterData');
      if (!characterDataStr) {
        message.error('角色信息不存在，请重新创建角色');
        navigate('/charactersetting');
        return;
      }

      const characterData = JSON.parse(characterDataStr);
      const characterId = characterData.characterId;

      if (!characterId) {
        message.error('角色ID不存在，请重新创建角色');
        navigate('/charactersetting');
        return;
      }

      characterData.selectedScene = selectedScene;
      sessionStorage.setItem('characterData', JSON.stringify(characterData));

      setLoading(true);
      setLoadingMessage('正在初始化游戏...');
      
      // 初始化游戏
      const initResponse = await initGame({
        game_mode: 'solo',
        character_id: characterId,
      });

      const threadId = initResponse.data.thread_id;
      
      setLoadingMessage('正在初始化故事...');
      
      // 初始化故事（触发初遇场景）
      await initializeStory(threadId, characterId);

      // 保存 threadId 到 sessionStorage，供 Game 组件使用
      sessionStorage.setItem('gameThreadId', threadId);
      sessionStorage.setItem('gameCharacterId', characterId);

      navigate('/game');
    } catch (error: any) {
      console.error('选择场景失败:', error);
      message.error(error.response?.data?.message || '选择场景失败，请稍后重试');
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingScreen message={loadingMessage} />;
  }

  const currentScene = sceneOptions[currentSceneIndex];

  return (
    <div className="first-meeting-selection-container">
      {/* 背景图片 */}
      <div 
        className="first-meeting-background"
        style={{
          backgroundImage: `url(${backgroundImage})`,
        }}
      />

      {/* 主内容区域 */}
      <div className="first-meeting-content">
        {/* 标题横幅 */}
        <div className="meeting-title-banner">
          <span className="title-text">初遇</span>
        </div>

        {/* 场景显示区域 */}
        <div className="scene-display-area">
          {/* 左侧导航箭头 */}
          <button 
            className="scene-nav-arrow scene-nav-left"
            onClick={handlePreviousScene}
            aria-label="上一个场景"
          >
            <LeftOutlined />
          </button>

          {/* 场景内容 */}
          <div className="scene-content">
            {currentScene.imageUrl ? (
              <img 
                src={currentScene.imageUrl} 
                alt={currentScene.name}
                className="scene-image"
              />
            ) : (
              <div className="scene-placeholder">
                <span className="placeholder-text">邂逅</span>
              </div>
            )}
          </div>

          {/* 右侧导航箭头 */}
          <button 
            className="scene-nav-arrow scene-nav-right"
            onClick={handleNextScene}
            aria-label="下一个场景"
          >
            <RightOutlined />
          </button>
        </div>

        {/* 选择按钮 */}
        <div className="scene-choice-button-container">
          <Button
            className="scene-choice-button"
            onClick={handleSelectScene}
            disabled={loading}
          >
            邂逅
          </Button>
        </div>
      </div>
    </div>
  );
}

export default FirstMeetingSelection;
