import { useState, useRef, useEffect } from 'react';
import { Input, Button, Card, Typography, Empty, Spin, Space, Avatar, message } from 'antd';
import { SendOutlined, UserOutlined, RobotOutlined } from '@ant-design/icons';
import { processGameInput, initGame, initializeStory, getCharacterImages } from '@/services/api';
import SceneTransition from '@/components/SceneTransition';
import { SCENE_CONFIGS, getSceneImageUrl, buildSceneImageUrl } from '@/config/scenes';
import './Game.css';

const { TextArea } = Input;
const { Text } = Typography;

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface PlayerOption {
  id: number;
  text: string;
  type: string;
  state_changes?: Record<string, number>;
}

interface GameSave {
  threadId: string;
  characterId?: string;
  messages: Message[];
  lastMessage?: string;
  timestamp: number;
}

function Game() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [characterId, setCharacterId] = useState<string | null>(null);
  const [currentOptions, setCurrentOptions] = useState<PlayerOption[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // 场景和幕数管理
  const [currentScene, setCurrentScene] = useState<string | null>(null);
  const [actNumber, setActNumber] = useState(1); // 初遇为第一幕
  const [showTransition, setShowTransition] = useState(false);
  const [transitionSceneName, setTransitionSceneName] = useState('');
  const previousSceneRef = useRef<string | null>(null);
  
  // 合成图片管理（场景+人物）
  const [compositeImageUrl, setCompositeImageUrl] = useState<string | null>(null);
  
  // 分别的场景和人物图片URL（当合成图片不存在时使用）
  const [sceneImageUrl, setSceneImageUrl] = useState<string | null>(null);
  const [characterImageUrl, setCharacterImageUrl] = useState<string | null>(null);
  
  // 当前角色对话（用于对话框显示）
  const [currentDialogue, setCurrentDialogue] = useState<string>('');

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // 获取场景名称（从场景ID转换为中文名称）
  const getSceneName = (sceneId: string): string => {
    const sceneNameMap: Record<string, string> = {
      'school': '学校',
      'library': '图书馆',
      'classroom': '教室',
      'cafeteria': '食堂',
      'playground': '操场',
      'dormitory': '宿舍',
      'campus_path': '校园小径',
      'school_gate': '校门口',
      'rooftop': '天台',
      'gym': '体育馆',
      'cafe_nearby': '咖啡厅',
      'bookstore': '书店',
      'restaurant': '餐厅',
      'convenience_store': '便利店',
      'company': '公司',
      'zoo': '动物园',
      'aquarium': '水族馆',
      'amusement_park': '游乐园',
      'badminton_court': '羽毛球场',
      'study_room': '自习室',
      'street': '马路',
    };
    return sceneNameMap[sceneId] || sceneId;
  };

  // 初始化：检查是否需要恢复存档或初始化新游戏
  useEffect(() => {
    const initializeGame = async () => {
      const restoreThreadId = sessionStorage.getItem('restoreThreadId');
      const characterDataStr = sessionStorage.getItem('characterData');
      
      if (restoreThreadId) {
        // 恢复存档
        loadGameSave(restoreThreadId);
        setThreadId(restoreThreadId);
        sessionStorage.removeItem('restoreThreadId');
        sessionStorage.removeItem('restoreCharacterId');
      } else {
        // 检查是否有已初始化的游戏（从 FirstMeetingSelection 跳转过来）
        const gameThreadId = sessionStorage.getItem('gameThreadId');
        const gameCharacterId = sessionStorage.getItem('gameCharacterId');
        
        if (gameThreadId && gameCharacterId) {
          // 使用已初始化的游戏
          setThreadId(gameThreadId);
          setCharacterId(gameCharacterId);
          // 保存characterId到sessionStorage，用于会话恢复
          sessionStorage.setItem('currentCharacterId', gameCharacterId);
          
          // 获取初始场景信息（从characterData中获取选中的场景）
          if (characterDataStr) {
            try {
              const characterData = JSON.parse(characterDataStr);
              const selectedScene = characterData.selectedScene;
              if (selectedScene && selectedScene.id) {
                setCurrentScene(selectedScene.id);
                previousSceneRef.current = selectedScene.id;
                // 显示第一幕转场动画
                setTransitionSceneName(selectedScene.name || getSceneName(selectedScene.id));
                setActNumber(1);
                setShowTransition(true);
              }
              
              // 尝试从sessionStorage获取初始游戏数据（如果FirstMeetingSelection保存了）
              const initialGameData = sessionStorage.getItem('initialGameData');
              if (initialGameData) {
                try {
                  const gameData = JSON.parse(initialGameData);
                  if (gameData.character_dialogue) {
                    setCurrentDialogue(gameData.character_dialogue);
                  }
                  if (gameData.player_options && Array.isArray(gameData.player_options)) {
                    setCurrentOptions(gameData.player_options);
                  }
                  if (gameData.composite_image_url) {
                    setCompositeImageUrl(gameData.composite_image_url);
                    setSceneImageUrl(null);
                    setCharacterImageUrl(null);
                  } else if (gameData.scene) {
                    // 如果合成图片不存在，设置场景图片
                    const sceneName = getSceneName(gameData.scene);
                    const possibleSceneUrls = [
                      `/static/images/scenes/${gameData.scene}_${sceneName}.jpeg`,
                      `/static/images/scenes/${gameData.scene}_${sceneName}.jpg`,
                    ];
                    setSceneImageUrl(possibleSceneUrls[0]);
                    
                    // 获取角色图片
                    if (gameCharacterId) {
                      getCharacterImages(gameCharacterId)
                        .then((imagesResponse) => {
                          if (imagesResponse.data?.images && imagesResponse.data.images.length > 0) {
                            setCharacterImageUrl(imagesResponse.data.images[0]);
                          }
                        })
                        .catch((error) => {
                          console.warn('[游戏] 获取角色图片失败:', error);
                        });
                    }
                  }
                  sessionStorage.removeItem('initialGameData');
                } catch (e) {
                  console.error('解析初始游戏数据失败:', e);
                }
              } else {
                // 如果没有保存的数据，重新调用initializeStory获取
                // 注意：这里需要知道scene_id，从selectedScene获取
                if (selectedScene && selectedScene.id) {
                  // 尝试从sessionStorage获取用户选择的图片URL
                  const characterDataStr = sessionStorage.getItem('characterData');
                  const characterImageUrl = characterDataStr ? JSON.parse(characterDataStr).transparentImageUrl : undefined;
                  initializeStory(gameThreadId, gameCharacterId, selectedScene.id, characterImageUrl)
                    .then((storyResponse) => {
                      const storyData = storyResponse.data;
                      if (storyData.character_dialogue) {
                        setCurrentDialogue(storyData.character_dialogue);
                      }
                      if (storyData.player_options && Array.isArray(storyData.player_options)) {
                        setCurrentOptions(storyData.player_options);
                      }
                      if (storyData.composite_image_url) {
                        setCompositeImageUrl(storyData.composite_image_url);
                      }
                    })
                    .catch((error) => {
                      console.error('获取初始游戏数据失败:', error);
                    });
                }
              }
            } catch (e) {
              console.error('解析场景信息失败:', e);
            }
          }
          
          // 清除临时存储（但保留characterId用于恢复）
          sessionStorage.removeItem('gameThreadId');
        } else if (characterDataStr) {
          // 新游戏，需要初始化
          try {
            const characterData = JSON.parse(characterDataStr);
            const charId = characterData.characterId;
            
            if (charId) {
              setCharacterId(charId);
              sessionStorage.setItem('currentCharacterId', charId);
              
              // 初始化游戏
              const initResponse = await initGame({
                game_mode: 'solo',
                character_id: charId,
              });
              
              const newThreadId = initResponse.data.thread_id;
              setThreadId(newThreadId);
              
              // 初始化故事（触发初遇场景）
              // 尝试从sessionStorage获取用户选择的图片URL
              const characterDataStr = sessionStorage.getItem('characterData');
              const characterImageUrl = characterDataStr ? JSON.parse(characterDataStr).transparentImageUrl : undefined;
              const storyResponse = await initializeStory(newThreadId, charId, undefined, characterImageUrl);
              
              // 添加初始故事背景和角色对话
              const storyData = storyResponse.data;
              const initialMessages: Message[] = [];
              
              // 设置初始场景（初遇场景）
              if (storyData.scene) {
                setCurrentScene(storyData.scene);
                previousSceneRef.current = storyData.scene;
                // 显示第一幕转场动画
                setTransitionSceneName(getSceneName(storyData.scene));
                setActNumber(1);
                setShowTransition(true);
              }
              
              // 设置合成图片URL（如果已生成）
              if (storyData.composite_image_url) {
                setCompositeImageUrl(storyData.composite_image_url);
                setSceneImageUrl(null);
                setCharacterImageUrl(null);
                console.log('[游戏] 初始合成图片URL:', storyData.composite_image_url);
              } else if (storyData.scene) {
                // 如果合成图片不存在，设置场景图片URL
                const sceneConfig = SCENE_CONFIGS.find(s => s.id === storyData.scene);
                if (sceneConfig) {
                  const sceneUrl = getSceneImageUrl(sceneConfig);
                  if (sceneUrl) {
                    setSceneImageUrl(sceneUrl);
                    console.log('[游戏] 初始场景图片URL:', sceneUrl);
                  } else {
                    const extensions = sceneConfig.imageExtensions || ['.jpeg', '.jpg', '.png', '.webp'];
                    const firstUrl = buildSceneImageUrl(sceneConfig.id, sceneConfig.name, extensions[0]);
                    setSceneImageUrl(firstUrl);
                    console.log('[游戏] 使用默认初始场景图片URL:', firstUrl);
                  }
                } else {
                  const sceneName = getSceneName(storyData.scene);
                  const possibleSceneUrls = [
                    `/static/images/scenes/${storyData.scene}_${sceneName}.jpeg`,
                    `/static/images/scenes/${storyData.scene}_${sceneName}.jpg`,
                    `/static/images/scenes/${storyData.scene}_${sceneName}.png`,
                  ];
                  setSceneImageUrl(possibleSceneUrls[0]);
                  console.log('[游戏] 使用备用初始场景图片URL:', possibleSceneUrls[0]);
                }
                
                // 获取角色图片
                if (charId) {
                  getCharacterImages(charId)
                    .then((imagesResponse) => {
                      if (imagesResponse.data?.images && imagesResponse.data.images.length > 0) {
                        setCharacterImageUrl(imagesResponse.data.images[0]);
                        console.log('[游戏] 初始角色图片URL:', imagesResponse.data.images[0]);
                      }
                    })
                    .catch((error) => {
                      console.warn('[游戏] 获取初始角色图片失败:', error);
                    });
                }
              }
              
              if (storyData.story_background) {
                initialMessages.push({
                  role: 'assistant',
                  content: storyData.story_background,
                });
              }
              
              if (storyData.character_dialogue) {
                // 设置初始对话
                setCurrentDialogue(storyData.character_dialogue);
                
                initialMessages.push({
                  role: 'assistant',
                  content: storyData.character_dialogue,
                });
              }
              
              setMessages(initialMessages);
              
              // 设置初始选项
              if (storyData.player_options && Array.isArray(storyData.player_options)) {
                setCurrentOptions(storyData.player_options);
              }
            }
          } catch (error) {
            console.error('初始化游戏失败:', error);
            message.error('初始化游戏失败，请稍后重试');
          }
        }
      }
    };
    
    initializeGame();
  }, []);

  // 加载存档
  const loadGameSave = (threadId: string) => {
    try {
      const saveData = localStorage.getItem(`gameSave_${threadId}`);
      if (saveData) {
        const save: GameSave = JSON.parse(saveData);
        if (save.messages && save.messages.length > 0) {
          setMessages(save.messages);
          message.success('存档加载成功');
        }
      }
    } catch (error) {
      console.error('加载存档失败:', error);
      message.error('加载存档失败');
    }
  };

  // 保存游戏进度
  const saveGameProgress = (threadId: string, messages: Message[], characterId?: string) => {
    try {
      const saveData: GameSave = {
        threadId,
        characterId,
        messages,
        lastMessage: messages.length > 0 ? messages[messages.length - 1].content : undefined,
        timestamp: Date.now(),
      };
      
      // 保存到 localStorage
      localStorage.setItem(`gameSave_${threadId}`, JSON.stringify(saveData));
      
      // 同时保存到主存档位置（用于"继续游戏"功能）
      localStorage.setItem('gameSave', JSON.stringify({
        threadId,
        characterId,
        lastMessage: saveData.lastMessage,
        timestamp: saveData.timestamp,
      }));
    } catch (error) {
      console.error('保存游戏失败:', error);
    }
  };

  useEffect(() => {
    scrollToBottom();
    // 自动保存游戏进度
    if (threadId && messages.length > 0) {
      saveGameProgress(threadId, messages);
    }
  }, [messages, threadId]);

  // 处理选项选择
  const handleOptionSelect = async (optionId: number) => {
    if (loading || !threadId) return;

    const selectedOption = currentOptions[optionId];
    if (!selectedOption) return;

    // 添加用户选择的消息
    const userMessage: Message = { role: 'user', content: selectedOption.text };
    setMessages((prev) => [...prev, userMessage]);
    setCurrentOptions([]); // 清除选项
    setCurrentDialogue(''); // 清除当前对话（等待新对话）
    setLoading(true);

    try {
      // 调用后端API处理选项选择（使用 option: 格式）
      const response = await processGameInput({
        thread_id: threadId,
        user_input: `option:${optionId + 1}`, // 转换为1-based索引
        character_id: characterId || sessionStorage.getItem('currentCharacterId') || undefined,
      });

      // 如果会话被恢复，更新threadId
      if (response.data?.thread_id && response.data.thread_id !== threadId) {
        setThreadId(response.data.thread_id);
        message.info('游戏会话已恢复');
      }

      handleGameResponse(response);
    } catch (error: any) {
      console.error('处理选项失败:', error);
      message.error(error.response?.data?.message || '处理选项失败，请稍后重试');
      setMessages((prev) => prev.filter((msg, idx) => idx !== prev.length - 1 || msg.role !== 'user'));
    } finally {
      setLoading(false);
    }
  };

  // 处理场景切换
  const handleSceneChange = (newScene: string | null) => {
    if (!newScene) return;
    
    // 如果场景发生变化，显示转场动画
    if (previousSceneRef.current !== newScene && previousSceneRef.current !== null) {
      // 场景切换，幕数+1
      setActNumber((prev) => prev + 1);
      setTransitionSceneName(getSceneName(newScene));
      setShowTransition(true);
    }
    
    previousSceneRef.current = newScene;
    setCurrentScene(newScene);
  };

  // 转场动画完成回调
  const handleTransitionComplete = () => {
    setShowTransition(false);
  };

  // 处理游戏响应
  const handleGameResponse = (response: any) => {
    const responseData = response.data;

    // 检测场景变化
    if (responseData.scene && responseData.scene !== currentScene) {
      handleSceneChange(responseData.scene);
    }

    // 更新合成图片URL（如果场景切换时已生成）
    if (responseData.composite_image_url) {
      setCompositeImageUrl(responseData.composite_image_url);
      setSceneImageUrl(null); // 清除分别的图片URL
      setCharacterImageUrl(null);
      console.log('[游戏] 更新合成图片URL:', responseData.composite_image_url);
    } else if (responseData.scene) {
      // 如果合成图片不存在，尝试获取场景和人物图片
      // 从场景配置中查找场景信息
      const sceneConfig = SCENE_CONFIGS.find(s => s.id === responseData.scene);
      if (sceneConfig) {
        // 使用场景配置构建图片URL
        const sceneUrl = getSceneImageUrl(sceneConfig);
        if (sceneUrl) {
          setSceneImageUrl(sceneUrl);
          console.log('[游戏] 设置场景图片URL:', sceneUrl);
        } else {
          // 如果getSceneImageUrl返回null，尝试多个扩展名
          const extensions = sceneConfig.imageExtensions || ['.jpeg', '.jpg', '.png', '.webp'];
          const firstUrl = buildSceneImageUrl(sceneConfig.id, sceneConfig.name, extensions[0]);
          setSceneImageUrl(firstUrl);
          console.log('[游戏] 使用默认场景图片URL:', firstUrl);
        }
      } else {
        // 如果场景不在配置中，使用场景ID和名称构建URL
        const sceneName = getSceneName(responseData.scene);
        const possibleSceneUrls = [
          `/static/images/scenes/${responseData.scene}_${sceneName}.jpeg`,
          `/static/images/scenes/${responseData.scene}_${sceneName}.jpg`,
          `/static/images/scenes/${responseData.scene}_${sceneName}.png`,
          `/static/images/scenes/${responseData.scene}.jpeg`,
          `/static/images/scenes/${responseData.scene}.jpg`,
        ];
        setSceneImageUrl(possibleSceneUrls[0]);
        console.log('[游戏] 使用备用场景图片URL:', possibleSceneUrls[0]);
      }
      
      // 人物图片URL需要从characterId获取（通过API）
      const charId = characterId || sessionStorage.getItem('currentCharacterId');
      if (charId && !characterImageUrl) {
        // 通过API获取角色图片
        getCharacterImages(charId)
          .then((imagesResponse) => {
            if (imagesResponse.data?.images && imagesResponse.data.images.length > 0) {
              // 使用第一张图片
              setCharacterImageUrl(imagesResponse.data.images[0]);
              console.log('[游戏] 获取角色图片成功:', imagesResponse.data.images[0]);
            }
          })
          .catch((error) => {
            console.warn('[游戏] 获取角色图片失败:', error);
          });
      }
    }

    // 添加角色对话
    if (responseData.character_dialogue) {
      // 更新当前对话（用于对话框显示）
      setCurrentDialogue(responseData.character_dialogue);
      
      // 同时添加到消息历史（用于滚动查看）
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: responseData.character_dialogue },
      ]);
    }

    // 更新选项
    if (responseData.player_options && Array.isArray(responseData.player_options)) {
      setCurrentOptions(responseData.player_options);
    } else {
      setCurrentOptions([]);
    }

    // 检查游戏是否结束
    if (responseData.is_game_finished) {
      message.info('游戏结束');
    }
  };

  const handleSubmit = async () => {
    if (!input.trim() || loading || !threadId) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    const userInput = input;
    setInput('');
    setCurrentOptions([]); // 清除选项
    setLoading(true);

    try {
      // 调用后端API处理玩家输入
      const response = await processGameInput({
        thread_id: threadId,
        user_input: userInput,
        character_id: characterId || sessionStorage.getItem('currentCharacterId') || undefined,
      });

      // 如果会话被恢复，更新threadId
      if (response.data?.thread_id && response.data.thread_id !== threadId) {
        setThreadId(response.data.thread_id);
        message.info('游戏会话已恢复');
      }

      handleGameResponse(response);

    } catch (error: any) {
      console.error('处理输入失败:', error);
      message.error(error.response?.data?.message || '处理输入失败，请稍后重试');
      
      // 移除用户消息（因为处理失败）
      setMessages((prev) => prev.filter((msg, idx) => idx !== prev.length - 1 || msg.role !== 'user'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="game-scene-container">
      {/* 转场动画 */}
      {showTransition && (
        <SceneTransition
          sceneName={transitionSceneName}
          actNumber={actNumber}
          onComplete={handleTransitionComplete}
        />
      )}
      
      {/* 加载状态 */}
      {loading && (
        <div className="game-loading-overlay">
          <div className="game-loading-content">
            <Spin size="large" />
            <div style={{ marginTop: '16px' }}>
              <Text>AI正在思考...</Text>
            </div>
          </div>
        </div>
      )}
      
      {/* 场景图片背景 */}
      <div className="game-scene-background">
        {compositeImageUrl ? (
          // 显示合成图片（场景+人物已合成）
          <img 
            src={compositeImageUrl} 
            alt="游戏场景" 
            className="composite-scene-image"
            onError={(e) => {
              console.error('[游戏] 合成图片加载失败:', compositeImageUrl);
              const target = e.target as HTMLImageElement;
              target.style.display = 'none';
            }}
          />
        ) : (
          // 分别显示场景和人物图片（叠加显示）
          <>
            {/* 场景图片作为背景（必须显示，即使加载失败也显示占位符） */}
            {sceneImageUrl ? (
              <img 
                src={sceneImageUrl} 
                alt="场景背景" 
                className="scene-background-image"
                onError={(e) => {
                  console.error('[游戏] 场景图片加载失败，URL:', sceneImageUrl);
                  // 不隐藏图片，而是显示占位符背景
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  // 显示占位符
                  const placeholder = target.parentElement?.querySelector('.scene-placeholder-fallback') as HTMLElement;
                  if (placeholder) {
                    placeholder.style.display = 'flex';
                  }
                }}
              />
            ) : (
              <div className="scene-placeholder-fallback" style={{ display: 'flex' }}>
                <Text style={{ color: '#fff', fontSize: '24px' }}>加载场景中...</Text>
              </div>
            )}
            {/* 人物图片居中叠加在场景之上 */}
            {characterImageUrl && (
              <img 
                src={characterImageUrl} 
                alt="角色" 
                className="character-overlay-image"
                onError={(e) => {
                  console.error('[游戏] 角色图片加载失败:', characterImageUrl);
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                }}
              />
            )}
          </>
        )}
      </div>
      
      {/* 对话框和选项区域（固定在底部） */}
      <div className="game-dialogue-container">
        {/* 角色对话框 */}
        {currentDialogue && (
          <div className="game-dialogue-box">
            <div className="dialogue-header">角色对话</div>
            <div className="dialogue-content">{currentDialogue}</div>
          </div>
        )}
        
        {/* 玩家选项按钮 */}
        {currentOptions.length > 0 && (
          <div className="game-options-container">
            {currentOptions.map((option, index) => (
              <Button
                key={option.id}
                className="game-option-button"
                onClick={() => handleOptionSelect(index)}
                disabled={loading}
              >
                {option.text}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Game;
