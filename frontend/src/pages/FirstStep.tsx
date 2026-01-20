import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, message, Modal } from 'antd';
import { 
  PlayCircleOutlined, 
  FileTextOutlined, 
  SettingOutlined, 
  LogoutOutlined 
} from '@ant-design/icons';
import backgroundImage from '@/assets/images/firstbackgound.jpg';
import LoadingScreen from '@/components/loading';
import { checkServerHealth } from '@/services/api';
import './FirstStep.css';

interface GameSave {
  threadId: string;
  characterId?: string;
  lastMessage?: string;
  timestamp: number;
}

function FirstStep() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('正在连接服务器...');

  // 读取玩家存档
  const loadGameSave = (): GameSave | null => {
    try {
      const saveData = localStorage.getItem('gameSave');
      if (saveData) {
        return JSON.parse(saveData);
      }
    } catch (error) {
      console.error('读取存档失败:', error);
    }
    return null;
  };

  // 继续游戏
  const handleContinueGame = async () => {
    const saveData = loadGameSave();
    
    if (!saveData) {
      message.warning('没有找到存档，请开始新的故事');
      return;
    }

    // 如果有 threadId，跳转到游戏页面并恢复存档
    if (saveData.threadId) {
      setLoading(true);
      setLoadingMessage('正在连接服务器...');
      
      try {
        // 检查后端服务是否可用
        const isHealthy = await checkServerHealth();
        
        if (isHealthy) {
          // 将存档信息存储到 sessionStorage，供 Game 页面使用
          sessionStorage.setItem('restoreThreadId', saveData.threadId);
          if (saveData.characterId) {
            sessionStorage.setItem('restoreCharacterId', saveData.characterId);
          }
          
          setLoadingMessage('正在加载存档...');
          // 短暂延迟以显示加载消息
          await new Promise(resolve => setTimeout(resolve, 500));
          navigate('/game');
        } else {
          message.error('无法连接到服务器，请检查后端服务是否运行');
        }
      } catch (error) {
        message.error('连接服务器失败，请稍后重试');
      } finally {
        setLoading(false);
      }
    } else {
      message.warning('存档数据不完整，请开始新的故事');
    }
  };

  // 新的故事
  const handleNewStory = () => {
    // 导航到角色设置页面
    navigate('/charactersetting');
  };

  // 设置
  const handleSettings = () => {
    Modal.info({
      title: '游戏设置',
      content: (
        <div>
          <p>设置功能开发中...</p>
          <p>未来将包含：</p>
          <ul>
            <li>音量调节</li>
            <li>画面设置</li>
            <li>快捷键设置</li>
            <li>语言选择</li>
          </ul>
        </div>
      ),
      okText: '确定',
      width: 400,
    });
  };

  // 退出
  const handleExit = () => {
    Modal.confirm({
      title: '确认退出',
      content: '确定要退出游戏吗？',
      okText: '退出',
      cancelText: '取消',
      okType: 'danger',
      onOk: () => {
        // 返回首页
        navigate('/');
      },
    });
  };

  if (loading) {
    return <LoadingScreen message={loadingMessage} />;
  }

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        minHeight: '100vh',
        backgroundImage: `url(${backgroundImage})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        justifyContent: 'center',
        padding: '40px 60px',
      }}
    >
      {/* 半透明遮罩层，增强按钮可读性 */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.1)',
          zIndex: 1,
        }}
      />

      {/* 樱花飘落动画 */}
      <div className="sakura-container">
        {Array.from({ length: 20 }).map((_, index) => (
          <div
            key={index}
            className="sakura-petal"
            style={{
              left: `${(index * 5) % 100}%`,
              animationDelay: `${index * 0.5}s`,
              animationDuration: `${8 + (index % 5)}s`,
            }}
          >
            <svg width="20" height="20" viewBox="0 0 20 20">
              <path
                d="M10 2C10 2 12 6 16 6C12 6 10 10 10 10C10 10 8 6 4 6C8 6 10 2 10 2Z"
                fill="#ffb3d9"
                opacity="0.8"
              />
            </svg>
          </div>
        ))}
      </div>

      {/* 按钮区域 */}
      <div
        style={{
          position: 'relative',
          zIndex: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: '24px',
          minWidth: '280px',
        }}
      >
        {/* 继续游戏按钮 */}
        <Button
          type="primary"
          size="large"
          icon={<FileTextOutlined />}
          onClick={handleContinueGame}
          className="continue-game-button"
          style={{
            fontSize: '20px',
            height: '60px',
            padding: '0 40px',
            background: 'linear-gradient(135deg, #ffd700 0%, #ffb347 100%)',
            border: '2px solid #ff8c00',
            borderRadius: '8px',
            fontWeight: 'bold',
            letterSpacing: '1px',
            boxShadow: '0 4px 15px rgba(255, 215, 0, 0.4), inset 0 2px 5px rgba(255, 255, 255, 0.3)',
            transition: 'all 0.3s ease',
            color: '#fff',
          }}
        >
          继续游戏
        </Button>

        {/* 新的故事按钮 */}
        <Button
          type="primary"
          size="large"
          icon={<PlayCircleOutlined />}
          onClick={handleNewStory}
          className="new-story-button"
          style={{
            fontSize: '20px',
            height: '60px',
            padding: '0 40px',
            background: 'linear-gradient(135deg, #ffd700 0%, #ffb347 100%)',
            border: '2px solid #ff8c00',
            borderRadius: '8px',
            fontWeight: 'bold',
            letterSpacing: '1px',
            boxShadow: '0 4px 15px rgba(255, 215, 0, 0.4), inset 0 2px 5px rgba(255, 255, 255, 0.3)',
            transition: 'all 0.3s ease',
            color: '#fff',
          }}
        >
          新的故事
        </Button>
      </div>

      {/* 左下角按钮区域 - 设置和退出 */}
      <div
        style={{
          position: 'absolute',
          bottom: '40px',
          left: '60px',
          zIndex: 2,
          display: 'flex',
          gap: '16px',
        }}
      >
        {/* 设置按钮 */}
        <Button
          type="default"
          size="large"
          icon={<SettingOutlined />}
          onClick={handleSettings}
          style={{
            fontSize: '16px',
            height: '50px',
            padding: '0 24px',
            background: 'rgba(255, 255, 255, 0.9)',
            border: '2px solid rgba(255, 140, 0, 0.5)',
            borderRadius: '8px',
            fontWeight: 'bold',
            letterSpacing: '1px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
            transition: 'all 0.3s ease',
            backdropFilter: 'blur(10px)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.05)';
            e.currentTarget.style.background = 'rgba(255, 255, 255, 1)';
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.3)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.9)';
            e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.2)';
          }}
        >
          设置
        </Button>

        {/* 退出按钮 */}
        <Button
          type="default"
          size="large"
          icon={<LogoutOutlined />}
          onClick={handleExit}
          style={{
            fontSize: '16px',
            height: '50px',
            padding: '0 24px',
            background: 'rgba(255, 255, 255, 0.9)',
            border: '2px solid rgba(255, 77, 79, 0.5)',
            borderRadius: '8px',
            fontWeight: 'bold',
            letterSpacing: '1px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
            transition: 'all 0.3s ease',
            backdropFilter: 'blur(10px)',
            color: '#ff4d4f',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.05)';
            e.currentTarget.style.background = 'rgba(255, 77, 79, 0.1)';
            e.currentTarget.style.borderColor = '#ff4d4f';
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(255, 77, 79, 0.3)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.9)';
            e.currentTarget.style.borderColor = 'rgba(255, 77, 79, 0.5)';
            e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.2)';
          }}
        >
          退出
        </Button>
      </div>
    </div>
  );
}

export default FirstStep;
