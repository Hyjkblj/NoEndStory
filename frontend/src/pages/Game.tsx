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
  
  // 标记是否应该使用合成图片（后端返回了composite_image_url）
  const [shouldUseComposite, setShouldUseComposite] = useState<boolean>(false);
  
  // 当前角色对话（用于对话框显示）
  const [currentDialogue, setCurrentDialogue] = useState<string>('');

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // 工具函数：从 sessionStorage 获取角色图片（按优先级）
  const getCharacterImageFromStorage = (): string | undefined => {
    const characterDataStr = sessionStorage.getItem('characterData');
    if (!characterDataStr) return undefined;
    
    try {
      const characterData = JSON.parse(characterDataStr);
      
      // 优先使用去除背景后的图片
      if (characterData.transparentImageUrl) {
        return characterData.transparentImageUrl;
      }
      
      // 检查imageUrl是否包含已删除的图片标识（portrait_img1/img2/img3）
      const imageUrl = characterData.imageUrl;
      if (imageUrl && (imageUrl.includes('portrait_img1') || imageUrl.includes('portrait_img2') || imageUrl.includes('portrait_img3'))) {
        // 如果imageUrl是已删除的图片，且存在originalImageUrl且不是已删除的图片，使用originalImageUrl
        if (characterData.originalImageUrl && !characterData.originalImageUrl.includes('portrait_img')) {
          return characterData.originalImageUrl;
        }
        // 如果都不存在或都是已删除的图片，返回undefined，让API获取
        return undefined;
      }
      
      // 使用originalImageUrl或imageUrl（如果它们不是已删除的图片）
      return characterData.originalImageUrl || imageUrl;
    } catch (e) {
      console.error('[游戏] 解析characterData失败:', e);
      return undefined;
    }
  };

  // 工具函数：从 API 加载角色图片
  const loadCharacterImageFromAPI = (characterId: string | null) => {
    if (!characterId || characterId === 'undefined' || characterId === 'null' || String(characterId).trim() === '') {
      return;
    }
    
    getCharacterImages(String(characterId))
      .then((imagesResponse) => {
        // 注意：响应拦截器已经提取了data字段
        const images = imagesResponse?.data?.images || imagesResponse?.images;
        if (images && Array.isArray(images) && images.length > 0) {
          setCharacterImageUrl(images[0]);
        }
      })
      .catch((error) => {
        console.warn('[游戏] 获取角色图片失败:', error.message || error);
      });
  };

  // 工具函数：设置角色图片（优先从 sessionStorage，否则从 API）
  const setCharacterImage = (characterId: string | null) => {
    // 优先从 sessionStorage 获取
    const imageUrl = getCharacterImageFromStorage();
    if (imageUrl) {
      setCharacterImageUrl(imageUrl);
      return;
    }
    
    // 如果 sessionStorage 中没有，从 API 获取
    loadCharacterImageFromAPI(characterId);
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

  // 获取场景所属的大场景ID（用于查找大场景图片）
  const getMajorSceneId = (sceneId: string): string => {
    // 小场景到大场景的映射
    const majorSceneMap: Record<string, string> = {
      'library': 'school',
      'classroom': 'school',
      'cafeteria': 'school',
      'playground': 'school',
      'dormitory': 'school',
      'campus_path': 'school',
      'school_gate': 'school',
      'rooftop': 'school',
      'gym': 'school',
      'cafe_nearby': 'school',
      'bookstore': 'school',
      'study_room': 'school',
      'basketball_court': 'school',
      'swimming_pool': 'school',
      'student_union': 'school',
      'canteen_terrace': 'school',
      'school_garden': 'school',
      'lab': 'school',
      'art_room': 'school',
      'music_room': 'school',
      'office_desk': 'company',
      'meeting_room': 'company',
      'break_room': 'company',
      'reception': 'company',
      'elevator': 'company',
      'parking_lot': 'company',
      'company_cafeteria': 'company',
      'lounge': 'company',
      'copy_room': 'company',
      'coffee_corner': 'company',
      'training_room': 'company',
      'office_balcony': 'company',
      'convenience_store': 'dailylife',
      'residential_area': 'dailylife',
      'community_park': 'dailylife',
      'supermarket': 'dailylife',
      'pharmacy': 'dailylife',
      'bank': 'dailylife',
      'post_office': 'dailylife',
      'bus_stop': 'dailylife',
      'subway_station': 'dailylife',
      'park': 'dailylife',
      'square': 'dailylife',
      'mall': 'dailylife',
      'cinema': 'leisure',
      'karaoke': 'leisure',
      'game_center': 'leisure',
      'sports_club': 'leisure',
      'fitness_center': 'leisure',
      'swimming_pool_leisure': 'leisure',
      'spa': 'leisure',
      'beauty_salon': 'leisure',
      'cafe': 'leisure',
      'bar': 'leisure',
      'restaurant': 'leisure',
      'zoo': 'nature',
      'aquarium': 'nature',
      'amusement_park': 'nature',
      'beach': 'nature',
      'mountain': 'nature',
      'forest': 'nature',
      'lake': 'nature',
      'river': 'nature',
      'garden': 'nature',
      'park_nature': 'nature',
      'library_cultural': 'cultural',
      'museum': 'cultural',
      'art_gallery': 'cultural',
      'theater': 'cultural',
      'concert_hall': 'cultural',
      'exhibition_hall': 'cultural',
      'cultural_center': 'cultural',
      'bookstore_cultural': 'cultural',
      'reading_room': 'cultural',
      'studio': 'cultural',
    };
    return majorSceneMap[sceneId] || 'school';  // 默认返回school
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
          
          // 尝试从sessionStorage获取初始游戏数据（如果FirstMeetingSelection保存了）
          const initialGameData = sessionStorage.getItem('initialGameData');
          if (initialGameData) {
            try {
              const gameData = JSON.parse(initialGameData);
              
              // 优先使用后端返回的小场景ID和名称（第一幕）
              if (gameData.scene) {
                // 使用后端返回的小场景ID（不是大场景ID）
                setCurrentScene(gameData.scene);
                previousSceneRef.current = gameData.scene;
                // 显示第一幕转场动画，使用小场景名称
                setTransitionSceneName(getSceneName(gameData.scene));
                setActNumber(1);
                setShowTransition(true);
              } else if (characterDataStr) {
                // 如果没有后端返回的场景，使用前端选择的大场景（兼容旧逻辑）
                const characterData = JSON.parse(characterDataStr);
                const selectedScene = characterData.selectedScene;
                if (selectedScene && selectedScene.id) {
                  setCurrentScene(selectedScene.id);
                  previousSceneRef.current = selectedScene.id;
                  setTransitionSceneName(selectedScene.name || getSceneName(selectedScene.id));
                  setActNumber(1);
                  setShowTransition(true);
                }
              }
              
              if (gameData.character_dialogue) {
                setCurrentDialogue(gameData.character_dialogue);
              }
              if (gameData.player_options && Array.isArray(gameData.player_options)) {
                setCurrentOptions(gameData.player_options);
              }
              if (gameData.composite_image_url) {
                setCompositeImageUrl(gameData.composite_image_url);
                setShouldUseComposite(true);
                setSceneImageUrl(null);
                setCharacterImageUrl(null);
              } else if (gameData.scene_image_url) {
                setShouldUseComposite(false);
                // 优先使用后端返回的场景图片URL（已正确编码，可能是smallscenes目录）
                setSceneImageUrl(gameData.scene_image_url);
              } else if (gameData.scene) {
                // 如果后端没有返回场景图片URL，优先尝试从smallscenes目录查找小场景图片
                const sceneName = getSceneName(gameData.scene);
                const encodedSceneName = encodeURIComponent(sceneName);
                
                // 优先尝试smallscenes目录（小场景图片）
                const possibleSceneUrls = [
                  `/static/images/smallscenes/UNKNOWN_SCENE_${gameData.scene}_${encodedSceneName}_scene_v1.jpg`,
                  `/static/images/smallscenes/UNKNOWN_SCENE_${gameData.scene}_${encodedSceneName}_scene_v1.jpeg`,
                  `/static/images/smallscenes/UNKNOWN_SCENE_${gameData.scene}_${encodedSceneName}_scene_v1.png`,
                  // 备选：尝试scenes目录
                  `/static/images/scenes/${gameData.scene}_${encodedSceneName}.jpeg`,
                  `/static/images/scenes/${gameData.scene}_${encodedSceneName}.jpg`,
                ];
                setSceneImageUrl(possibleSceneUrls[0]);
              }
              
              // 设置角色图片（优先从 sessionStorage，否则从 API）
              if (!characterImageUrl) {
                setCharacterImage(gameCharacterId);
              }
              
              sessionStorage.removeItem('initialGameData');
            } catch (e) {
              console.error('解析初始游戏数据失败:', e);
            }
          } else if (characterDataStr) {
            // 如果没有保存的数据，重新调用initializeStory获取
            try {
              const characterData = JSON.parse(characterDataStr);
              const selectedScene = characterData.selectedScene;
              if (selectedScene && selectedScene.id) {
                setCurrentScene(selectedScene.id);
                previousSceneRef.current = selectedScene.id;
                // 显示第一幕转场动画（临时使用大场景名称，等待后端返回后更新）
                setTransitionSceneName(selectedScene.name || getSceneName(selectedScene.id));
                setActNumber(1);
                setShowTransition(true);
              }
              
              // 如果没有保存的数据，重新调用initializeStory获取
              if (selectedScene && selectedScene.id) {
                // 如果没有保存的数据，重新调用initializeStory获取
                // 注意：这里需要知道scene_id，从selectedScene获取
                if (selectedScene && selectedScene.id) {
                  // 从 sessionStorage 获取用户选择的图片URL（用于传递给后端）
                  const characterImageUrlForInit = getCharacterImageFromStorage();
                  // 确保参数不为undefined
                  if (!gameThreadId || !gameCharacterId) {
                    console.error('[游戏] 缺少必要参数:', { gameThreadId, gameCharacterId });
                    message.error('缺少必要参数，无法初始化故事');
                    return;
                  }
                  
                  initializeStory(gameThreadId, gameCharacterId, selectedScene?.id, characterImageUrlForInit)
                    .then((storyResponse) => {
                      // 注意：响应拦截器已经提取了data字段，所以storyResponse本身就是data内容
                      const storyData = storyResponse;
                      
                      // 使用后端返回的小场景ID和名称更新过场动画
                      if (storyData.scene) {
                        setCurrentScene(storyData.scene);  // 小场景ID
                        previousSceneRef.current = storyData.scene;
                        setTransitionSceneName(getSceneName(storyData.scene));  // 小场景名称
                        setActNumber(1);
                        setShowTransition(true);
                      }
                      
                      if (storyData.character_dialogue) {
                        setCurrentDialogue(storyData.character_dialogue);
                      }
                      if (storyData.player_options && Array.isArray(storyData.player_options)) {
                        setCurrentOptions(storyData.player_options);
                      }
                      if (storyData.composite_image_url) {
                        setCompositeImageUrl(storyData.composite_image_url);
                        setShouldUseComposite(true);
                        setSceneImageUrl(null);
                        setCharacterImageUrl(null);
                      } else if (storyData.scene_image_url) {
                        setShouldUseComposite(false);
                        setSceneImageUrl(storyData.scene_image_url);
                      } else if (storyData.scene) {
                        // 优先尝试smallscenes目录
                        const sceneName = getSceneName(storyData.scene);
                        const encodedSceneName = encodeURIComponent(sceneName);
                        const possibleSceneUrls = [
                          `/static/images/smallscenes/UNKNOWN_SCENE_${storyData.scene}_${encodedSceneName}_scene_v1.jpg`,
                          `/static/images/smallscenes/UNKNOWN_SCENE_${storyData.scene}_${encodedSceneName}_scene_v1.jpeg`,
                          `/static/images/scenes/${storyData.scene}_${encodedSceneName}.jpeg`,
                        ];
                        setSceneImageUrl(possibleSceneUrls[0]);
                      }
                      
                      // 设置角色图片
                      if (!characterImageUrl) {
                        setCharacterImage(gameCharacterId);
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
              
              // 注意：响应拦截器已经提取了data字段，所以initResponse是 {code, message, data}
              // 后端返回格式：{code: 200, message: 'success', data: {thread_id: ..., user_id: ..., game_mode: ...}}
              const newThreadId = initResponse?.data?.thread_id;
              setThreadId(newThreadId || null);
              
              // 初始化故事（触发初遇场景）
              // 从 sessionStorage 获取用户选择的图片URL（用于传递给后端）
              const characterImageUrlForInit = getCharacterImageFromStorage();
              
              // 确保参数不为undefined
              if (!newThreadId || !charId) {
                console.error('[游戏] 缺少必要参数:', { newThreadId, charId });
                message.error('缺少必要参数，无法初始化故事');
                return;
              }
              
              const storyResponse = await initializeStory(newThreadId, charId, undefined, characterImageUrlForInit);
              
              // 添加初始故事背景和角色对话
              // 注意：响应拦截器已经提取了data字段，所以storyResponse是 {code, message, data}
              // 后端返回格式：{code: 200, message: 'success', data: {...}}
              const storyData = storyResponse?.data || storyResponse;  // 优先使用response.data，如果没有则使用response本身（兼容旧代码）
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
                setShouldUseComposite(true);
                setSceneImageUrl(null);
                setCharacterImageUrl(null);
              } else if (storyData.scene_image_url) {
                setShouldUseComposite(false);
                // 优先使用后端返回的场景图片URL（已正确编码）
                setSceneImageUrl(storyData.scene_image_url);
                
                // 设置角色图片（即使有场景图片，也需要显示角色）
                if (!characterImageUrl) {
                  setCharacterImage(charId);
                }
              } else if (storyData.scene) {
                // 如果后端没有返回场景图片URL，优先尝试从smallscenes目录查找小场景图片
                const sceneName = getSceneName(storyData.scene);
                const encodedSceneName = encodeURIComponent(sceneName);
                
                // 优先尝试smallscenes目录（小场景图片）
                const possibleSceneUrls = [
                  `/static/images/smallscenes/UNKNOWN_SCENE_${storyData.scene}_${encodedSceneName}_scene_v1.jpg`,
                  `/static/images/smallscenes/UNKNOWN_SCENE_${storyData.scene}_${encodedSceneName}_scene_v1.jpeg`,
                  `/static/images/smallscenes/UNKNOWN_SCENE_${storyData.scene}_${encodedSceneName}_scene_v1.png`,
                  // 备选：尝试scenes目录
                  `/static/images/scenes/${storyData.scene}_${encodedSceneName}.jpeg`,
                  `/static/images/scenes/${storyData.scene}_${encodedSceneName}.jpg`,
                  `/static/images/scenes/${storyData.scene}_${encodedSceneName}.png`,
                ];
                setSceneImageUrl(possibleSceneUrls[0]);
                
                // 设置角色图片（优先从 sessionStorage，否则从 API）
                if (!characterImageUrl) {
                  setCharacterImage(charId);
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
      // 注意：响应拦截器已经提取了data字段，所以response是 {code, message, data}
      // 后端返回格式：{code: 200, message: 'success', data: {thread_id: ..., ...}}
      const responseThreadId = response?.data?.thread_id;
      if (responseThreadId && responseThreadId !== threadId) {
        setThreadId(responseThreadId);
        message.info('游戏会话已恢复');
      }

      handleGameResponse(response);
    } catch (error: any) {
      console.error('处理选项失败:', error);
      let errorMessage = '处理选项失败，请稍后重试';
      
      // 检查是否是会话过期错误
      const errorMsg = error.response?.data?.message || error.message || '';
      if (errorMsg.includes('会话已过期') || errorMsg.includes('not found') || errorMsg.includes('无法恢复')) {
        errorMessage = '游戏会话已过期。正在尝试恢复...';
        message.warning(errorMessage);
        
        // 尝试重新初始化游戏
        const charId = characterId || sessionStorage.getItem('currentCharacterId');
        if (charId) {
          try {
            console.log('[游戏恢复] 尝试重新初始化游戏，characterId:', charId);
            const initResponse = await initGame({
              game_mode: 'solo',
              character_id: charId,
            });
            
            const newThreadId = initResponse?.data?.thread_id;
            if (newThreadId) {
              setThreadId(newThreadId);
              sessionStorage.setItem('gameThreadId', newThreadId);
              message.success('游戏会话已恢复，请重新选择选项');
              return;
            }
          } catch (recoverError) {
            console.error('[游戏恢复] 恢复失败:', recoverError);
            errorMessage = '游戏会话已过期且无法恢复，请返回重新开始游戏';
            message.error(errorMessage);
            // 可以选择跳转到角色选择页面
            // navigate('/charactersetting');
          }
        } else {
          errorMessage = '游戏会话已过期，请返回重新开始游戏';
          message.error(errorMessage);
        }
      } else if (error.message && error.message.includes('超时')) {
        errorMessage = '处理选项超时，AI生成可能需要更长时间。请稍后重试，或检查网络连接。';
        message.error(errorMessage);
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
        message.error(errorMessage);
      } else {
        message.error(errorMessage);
      }
      
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
  // 注意：响应拦截器已经提取了data字段，所以response是 {code, message, data}
  // 后端返回格式：{code: 200, message: 'success', data: {...}}
  const handleGameResponse = (response: any) => {
    const responseData = response?.data || response;  // 优先使用response.data，如果没有则使用response本身（兼容旧代码）

    // 检测场景变化
    if (responseData.scene && responseData.scene !== currentScene) {
      handleSceneChange(responseData.scene);
    }

    // 更新合成图片URL（如果场景切换时已生成）
    if (responseData.composite_image_url) {
      setCompositeImageUrl(responseData.composite_image_url);
      setShouldUseComposite(true);
      setSceneImageUrl(null); // 清除分别的图片URL
      setCharacterImageUrl(null);
    } else if (responseData.scene_image_url) {
      setShouldUseComposite(false);
      // 优先使用后端返回的场景图片URL（已正确编码）
      setSceneImageUrl(responseData.scene_image_url);
    } else if (responseData.scene) {
      // 如果后端没有返回场景图片URL，尝试从场景配置中查找
      const sceneConfig = SCENE_CONFIGS.find(s => s.id === responseData.scene);
      if (sceneConfig) {
        // 使用场景配置构建图片URL
        const sceneUrl = getSceneImageUrl(sceneConfig);
        if (sceneUrl) {
          setSceneImageUrl(sceneUrl);
        } else {
          // 如果getSceneImageUrl返回null，尝试多个扩展名
          const extensions = sceneConfig.imageExtensions || ['.jpeg', '.jpg', '.png', '.webp'];
          const firstUrl = buildSceneImageUrl(sceneConfig.id, sceneConfig.name, extensions[0]);
          setSceneImageUrl(firstUrl);
        }
      } else {
        // 如果场景不在配置中，优先尝试从smallscenes目录查找小场景图片
        const sceneName = getSceneName(responseData.scene);
        const encodedSceneName = encodeURIComponent(sceneName);
        
        // 优先尝试smallscenes目录（小场景图片）
        const possibleSceneUrls = [
          `/static/images/smallscenes/UNKNOWN_SCENE_${responseData.scene}_${encodedSceneName}_scene_v1.jpg`,
          `/static/images/smallscenes/UNKNOWN_SCENE_${responseData.scene}_${encodedSceneName}_scene_v1.jpeg`,
          `/static/images/smallscenes/UNKNOWN_SCENE_${responseData.scene}_${encodedSceneName}_scene_v1.png`,
          // 备选：尝试scenes目录
          `/static/images/scenes/${responseData.scene}_${encodedSceneName}.jpeg`,
          `/static/images/scenes/${responseData.scene}_${encodedSceneName}.jpg`,
          `/static/images/scenes/${responseData.scene}_${encodedSceneName}.png`,
        ];
        setSceneImageUrl(possibleSceneUrls[0]);
      }
      
      // 设置角色图片（优先从 sessionStorage，否则从 API）
      if (!characterImageUrl) {
        const charId = characterId || sessionStorage.getItem('currentCharacterId');
        setCharacterImage(charId);
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
      // 注意：响应拦截器已经提取了data字段，所以response是 {code, message, data}
      // 后端返回格式：{code: 200, message: 'success', data: {thread_id: ..., ...}}
      const responseThreadId = response?.data?.thread_id;
      if (responseThreadId && responseThreadId !== threadId) {
        setThreadId(responseThreadId);
        message.info('游戏会话已恢复');
      }

      handleGameResponse(response);

    } catch (error: any) {
      console.error('处理输入失败:', error);
      let errorMessage = '处理输入失败，请稍后重试';
      
      // 检查是否是会话过期错误
      const errorMsg = error.response?.data?.message || error.message || '';
      if (errorMsg.includes('会话已过期') || errorMsg.includes('not found') || errorMsg.includes('无法恢复')) {
        errorMessage = '游戏会话已过期。正在尝试恢复...';
        message.warning(errorMessage);
        
        // 尝试重新初始化游戏
        const charId = characterId || sessionStorage.getItem('currentCharacterId');
        if (charId) {
          try {
            console.log('[游戏恢复] 尝试重新初始化游戏，characterId:', charId);
            const initResponse = await initGame({
              game_mode: 'solo',
              character_id: charId,
            });
            
            const newThreadId = initResponse?.data?.thread_id;
            if (newThreadId) {
              setThreadId(newThreadId);
              sessionStorage.setItem('gameThreadId', newThreadId);
              message.success('游戏会话已恢复，请重新输入');
              return;
            }
          } catch (recoverError) {
            console.error('[游戏恢复] 恢复失败:', recoverError);
            errorMessage = '游戏会话已过期且无法恢复，请返回重新开始游戏';
            message.error(errorMessage);
            // 可以选择跳转到角色选择页面
            // navigate('/charactersetting');
          }
        } else {
          errorMessage = '游戏会话已过期，请返回重新开始游戏';
          message.error(errorMessage);
        }
      } else if (error.message && error.message.includes('超时')) {
        errorMessage = '处理输入超时，AI生成可能需要更长时间。请稍后重试，或检查网络连接。';
        message.error(errorMessage);
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
        message.error(errorMessage);
      } else {
        message.error(errorMessage);
      }
      
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
              <Text>思考中...</Text>
            </div>
          </div>
        </div>
      )}
      
      {/* 场景图片背景 */}
      <div className="game-scene-background">
        {(() => {
          // 如果应该使用合成图片但没有，报错返回
          if (shouldUseComposite && !compositeImageUrl) {
            const errorMsg = '[游戏] 错误：后端返回了composite_image_url，但合成图片URL为空';
            console.error(errorMsg);
            message.error('合成图片加载失败，请刷新页面重试');
            return (
              <div className="scene-placeholder-fallback" style={{ display: 'flex' }}>
                <Text style={{ color: '#ff4d4f', fontSize: '24px' }}>合成图片加载失败</Text>
              </div>
            );
          }
          
          // 如果有合成图片URL，必须显示合成图片
          if (compositeImageUrl) {
            return (
              <img 
                src={compositeImageUrl} 
                alt="游戏场景" 
                className="composite-scene-image"
                onError={(e) => {
                  const errorMsg = `[游戏] 错误：合成图片加载失败，URL: ${compositeImageUrl}`;
                  console.error(errorMsg);
                  message.error('合成图片加载失败，请刷新页面重试');
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  // 显示错误占位符
                  const placeholder = target.parentElement?.querySelector('.scene-placeholder-fallback') as HTMLElement;
                  if (placeholder) {
                    placeholder.style.display = 'flex';
                    placeholder.innerHTML = '<span style="color: #ff4d4f; font-size: 24px;">合成图片加载失败</span>';
                  }
                }}
              />
            );
          }
          
          // 如果没有合成图片，显示分别的场景和人物图片
          return (
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
          );
        })()}
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
