import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, message } from 'antd';
import { LeftOutlined, RightOutlined } from '@ant-design/icons';
import backgroundImage from '@/assets/images/firstbackgound.jpg';
import LoadingScreen from '@/components/loading';
import { checkServerHealth, initGame, initializeStory, getScenes } from '@/services/api';
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
  const [sceneOptions, setSceneOptions] = useState<SceneOption[]>([]);
  
  // 用于防抖的 ref（防止滚动过快导致频繁切换）
  const wheelTimeoutRef = useRef<number | null>(null);
  const isWheelingRef = useRef(false);

  // 从后端API加载大场景列表
  useEffect(() => {
    const loadScenes = async () => {
      try {
        setLoading(true);
        setLoadingMessage('正在加载场景...');
        
        // 检查后端服务是否可用
        const isHealthy = await checkServerHealth();
        if (!isHealthy) {
          message.error('无法连接到服务器，请检查后端服务是否运行');
          setLoading(false);
          return;
        }
        
        // 从后端API获取大场景列表
        // 注意：响应拦截器已经提取了data字段，所以response本身就是data内容
        // 后端返回格式：{code: 200, message: 'success', data: {scenes: [...]}}
        // 拦截器提取后：{code: 200, message: 'success', data: {scenes: [...]}}
        const response = await getScenes();
        console.log('[场景加载] API响应:', response);
        console.log('[场景加载] response.data:', response?.data);
        const scenesData = response?.data?.scenes || [];
        console.log('[场景加载] 场景数据:', scenesData);
        console.log('[场景加载] 场景数量:', scenesData.length);
        
        if (scenesData.length === 0) {
          console.warn('[场景加载] 场景列表为空，可能的原因：');
          console.warn('  1. 后端服务未运行');
          console.warn('  2. API路径不正确');
          console.warn('  3. 后端场景数据加载失败');
          message.warning('暂无可用场景');
          setSceneOptions([]);
          setLoading(false);
          return;
        }
        
        // 转换为前端使用的场景选项格式
        const scenes: SceneOption[] = scenesData.map((scene: any) => {
          // 处理图片URL：确保不为null或空字符串
          let imageUrl = scene.imageUrl;
          if (!imageUrl || imageUrl === 'null' || imageUrl === '') {
            imageUrl = undefined;
          }
          
          const sceneOption: SceneOption = {
            id: scene.id,  // 大场景ID
            name: scene.name,
            description: scene.description,
            imageUrl: imageUrl,
          };
          
          console.log(`[场景加载] 大场景: ${scene.name} (${scene.id})`);
          console.log(`[场景加载] 原始图片URL: ${scene.imageUrl}`);
          console.log(`[场景加载] 处理后的图片URL: ${imageUrl}`);
          console.log(`[场景加载] 初遇事件数量: ${scene.openingEventsCount || 0}`);
          
          return sceneOption;
        });
        
        console.log('[场景加载] 从API加载大场景列表:', scenes);
        setSceneOptions(scenes);
        setLoading(false);
      } catch (error: any) {
        console.error('加载场景失败:', error);
        message.error(error.response?.data?.message || '加载场景失败，请稍后重试');
        setLoading(false);
        // 如果加载失败，使用默认场景
        setSceneOptions([
          {
            id: 'school',
            name: '学校',
            description: '一个充满青春气息的校园场景',
            imageUrl: undefined,
          },
        ]);
      }
    };

    loadScenes();
  }, []);

  // 获取当前场景（在所有条件返回之前计算，确保 Hooks 调用顺序一致）
  const currentScene = sceneOptions.length > 0 ? sceneOptions[currentSceneIndex] : null;
  
  // 调试信息（必须在所有条件返回之前调用，确保 Hooks 调用顺序一致）
  useEffect(() => {
    if (currentScene) {
      console.log('[场景显示] 当前场景:', currentScene);
      console.log('[场景显示] 图片URL:', currentScene.imageUrl);
      console.log('[场景显示] 场景索引:', currentSceneIndex);
    }
  }, [currentScene, currentSceneIndex]);

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

  // 处理鼠标滚轮事件（带防抖）
  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    // 防止页面滚动
    e.preventDefault();
    
    // 如果正在处理滚动，忽略本次事件
    if (isWheelingRef.current) {
      return;
    }
    
    // 设置滚动标志
    isWheelingRef.current = true;
    
    // 向下滚动（deltaY > 0）切换到下一个场景
    // 向上滚动（deltaY < 0）切换到上一个场景
    if (e.deltaY > 50) {
      handleNextScene();
    } else if (e.deltaY < -50) {
      handlePreviousScene();
    }
    
    // 300ms 后重置标志，允许下一次滚动切换
    if (wheelTimeoutRef.current) {
      window.clearTimeout(wheelTimeoutRef.current);
    }
    wheelTimeoutRef.current = window.setTimeout(() => {
      isWheelingRef.current = false;
    }, 300);
  };
  
  // 清理定时器
  useEffect(() => {
    return () => {
      if (wheelTimeoutRef.current) {
        window.clearTimeout(wheelTimeoutRef.current);
      }
    };
  }, []);

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

      // 注意：响应拦截器已经提取了data字段，所以initResponse是 {code, message, data}
      // 后端返回格式：{code: 200, message: 'success', data: {thread_id: ..., user_id: ..., game_mode: ...}}
      console.log('[游戏初始化] initResponse:', initResponse);
      const threadId = initResponse?.data?.thread_id;
      console.log('[游戏初始化] threadId:', threadId);
      
      if (!threadId) {
        throw new Error('初始化游戏失败：未获取到 thread_id');
      }
      
      setLoadingMessage('正在生成场景图片...');
      
      // 从sessionStorage获取用户选择的图片URL（透明背景将在后端处理）
      let characterImageUrl: string | undefined = undefined;
      if (characterData.selectedImageUrl) {
        characterImageUrl = characterData.selectedImageUrl;
        console.log('[初遇场景] 使用用户选择的角色图片（将在后端处理透明背景）:', characterImageUrl);
      } else if (characterData.originalImageUrl) {
        // 如果没有selectedImageUrl，使用originalImageUrl
        characterImageUrl = characterData.originalImageUrl;
        console.log('[初遇场景] 使用原图:', characterImageUrl);
      } else if (characterData.imageUrl) {
        // 最后尝试使用imageUrl
        characterImageUrl = characterData.imageUrl;
        console.log('[初遇场景] 使用imageUrl:', characterImageUrl);
      }
      
      // 初始化故事（触发初遇场景），传递选定的场景ID和用户选择的图片URL
      // 注意：此过程包括AI生图和图片合成，可能需要较长时间
      const selectedSceneId = selectedScene.id;
      setLoadingMessage('正在生成场景图片并合成角色...（这可能需要1-2分钟）');
      const storyResponse = await initializeStory(threadId, characterId, selectedSceneId, characterImageUrl);
      
      // 保存初始游戏数据到sessionStorage，供Game组件使用
      // 注意：响应拦截器已经提取了data字段，所以storyResponse本身就是data内容
      const storyData = storyResponse as any;
      sessionStorage.setItem('initialGameData', JSON.stringify({
        character_dialogue: storyData.character_dialogue,
        player_options: storyData.player_options,
        composite_image_url: storyData.composite_image_url,
        scene_image_url: storyData.scene_image_url,  // 保存场景图片URL（小场景图片）
        scene: storyData.scene  // 小场景ID（后端随机选择的小场景）
      }));

      // 保存 threadId 到 sessionStorage，供 Game 组件使用
      sessionStorage.setItem('gameThreadId', threadId);
      sessionStorage.setItem('gameCharacterId', characterId);

      navigate('/game');
    } catch (error: any) {
      console.error('选择场景失败:', error);
      let errorMessage = '选择场景失败，请稍后重试';
      if (error.message && error.message.includes('超时')) {
        errorMessage = '初始化故事超时，图片生成可能需要更长时间。请稍后重试，或检查网络连接。';
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      }
      message.error(errorMessage);
      setLoading(false);
    }
  };

  // 如果正在加载场景列表，显示加载界面
  if (loading && sceneOptions.length === 0) {
    return <LoadingScreen message={loadingMessage} />;
  }

  // 如果没有场景，显示错误提示
  if (sceneOptions.length === 0) {
    return (
      <div className="first-meeting-selection-container">
        <div className="first-meeting-content">
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <p>暂无可用场景</p>
            <Button onClick={() => navigate('/charactersetting')}>
              返回角色设置
            </Button>
          </div>
        </div>
      </div>
    );
  }

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
        <div 
          className="scene-display-area"
          onWheel={handleWheel}
        >
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
            {currentScene?.imageUrl ? (
              <img 
                key={`scene-img-${currentScene.id}-${currentSceneIndex}`}
                src={currentScene.imageUrl} 
                alt={currentScene.name}
                className="scene-image"
                style={{ display: 'none' }}
                onLoad={(e) => {
                  console.log('[场景图片] 图片加载成功:', currentScene.imageUrl);
                  // 显示图片，隐藏占位符
                  const img = e.target as HTMLImageElement;
                  img.style.display = 'block';
                  const placeholder = img.parentElement?.querySelector('.scene-placeholder') as HTMLElement;
                  if (placeholder) {
                    placeholder.style.display = 'none';
                  }
                }}
                onError={(e) => {
                  // 如果图片加载失败，隐藏图片，显示占位符
                  console.error('[场景图片] 图片加载失败，URL:', currentScene.imageUrl);
                  console.error('[场景图片] 请检查图片路径是否正确，或静态文件服务是否已配置');
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  const placeholder = target.parentElement?.querySelector('.scene-placeholder') as HTMLElement;
                  if (placeholder) {
                    placeholder.style.display = 'flex';
                  }
                }}
              />
            ) : null}
            <div 
              className="scene-placeholder"
              style={{ 
                display: (currentScene?.imageUrl ? 'none' : 'flex'),
              }}
            >
              <span className="placeholder-text">{currentScene?.name || '邂逅'}</span>
              {currentScene?.description && (
                <span className="placeholder-description">{currentScene.description}</span>
              )}
            </div>
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
