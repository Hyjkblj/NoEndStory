import { useState, useRef, useEffect } from 'react';
import { Input, Button, Card, Typography, Empty, Spin, Space, Avatar, message } from 'antd';
import { SendOutlined, UserOutlined, RobotOutlined } from '@ant-design/icons';
import { processGameInput, initGame, initializeStory } from '@/services/api';

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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
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
              const storyResponse = await initializeStory(newThreadId, charId);
              
              // 添加初始故事背景和角色对话
              const storyData = storyResponse.data;
              const initialMessages: Message[] = [];
              
              if (storyData.story_background) {
                initialMessages.push({
                  role: 'assistant',
                  content: storyData.story_background,
                });
              }
              
              if (storyData.character_dialogue) {
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

  // 处理游戏响应
  const handleGameResponse = (response: any) => {
    const responseData = response.data;

    // 添加角色对话
    if (responseData.character_dialogue) {
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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', padding: '24px' }}>
      <Card
        title="游戏界面"
        style={{ 
          flex: 1, 
          display: 'flex', 
          flexDirection: 'column',
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(10px)',
        }}
        bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '16px' }}
      >
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px',
            background: '#fafafa',
            borderRadius: '8px',
            marginBottom: '16px',
          }}
        >
          {messages.length === 0 ? (
            <Empty
              description="开始你的故事吧！输入你的选择或行动..."
              style={{ marginTop: '100px' }}
            />
          ) : (
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              {messages.map((msg, index) => (
                <div
                  key={index}
                  style={{
                    display: 'flex',
                    justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  }}
                >
                  <Card
                    size="small"
                    style={{
                      maxWidth: '70%',
                      background: msg.role === 'user' ? '#1890ff' : 'white',
                      borderColor: msg.role === 'user' ? '#1890ff' : '#d9d9d9',
                    }}
                    bodyStyle={{
                      padding: '12px 16px',
                      color: msg.role === 'user' ? 'white' : 'inherit',
                    }}
                  >
                    <Space>
                      <Avatar
                        icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                        style={{
                          background: msg.role === 'user' ? 'rgba(255,255,255,0.3)' : '#1890ff',
                        }}
                      />
                      <Text style={{ color: msg.role === 'user' ? 'white' : 'inherit' }}>
                        {msg.content}
                      </Text>
                    </Space>
                  </Card>
                </div>
              ))}
              {loading && (
                <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                  <Card size="small" style={{ background: 'white' }}>
                    <Space>
                      <Avatar icon={<RobotOutlined />} style={{ background: '#1890ff' }} />
                      <Spin size="small" />
                      <Text type="secondary">AI正在思考...</Text>
                    </Space>
                  </Card>
                </div>
              )}
              <div ref={messagesEndRef} />
            </Space>
          )}
        </div>
        
        {/* 显示选项按钮 */}
        {currentOptions.length > 0 && (
          <div style={{ marginBottom: '16px' }}>
            <Text type="secondary" style={{ display: 'block', marginBottom: '8px' }}>
              请选择你的回复：
            </Text>
            <Space direction="vertical" style={{ width: '100%' }}>
              {currentOptions.map((option, index) => (
                <Button
                  key={option.id}
                  block
                  onClick={() => handleOptionSelect(index)}
                  disabled={loading}
                  style={{
                    textAlign: 'left',
                    height: 'auto',
                    padding: '12px 16px',
                    whiteSpace: 'normal',
                    wordBreak: 'break-word',
                  }}
                >
                  {option.text}
                </Button>
              ))}
            </Space>
          </div>
        )}
        
        <Space.Compact style={{ width: '100%' }}>
          <TextArea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入你的选择..."
            disabled={loading}
            autoSize={{ minRows: 1, maxRows: 4 }}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            style={{ resize: 'none' }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSubmit}
            disabled={loading || !input.trim()}
            style={{ height: 'auto' }}
          >
            发送
          </Button>
        </Space.Compact>
      </Card>
    </div>
  );
}

export default Game;
