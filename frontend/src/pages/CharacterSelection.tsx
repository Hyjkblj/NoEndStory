import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, message } from 'antd';
import backgroundImage from '@/assets/images/settingcharacterbackground.png';
import LoadingScreen from '@/components/loading';
import { checkServerHealth, getCharacterImages } from '@/services/api';
import './CharacterSelection.css';

interface CharacterOption {
  id: string;
  name: string;
  imageUrl?: string;
  gender: 'male' | 'female';
}

function CharacterSelection() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('正在加载角色...');
  const [characters, setCharacters] = useState<CharacterOption[]>([]);
  const [selectedCharacter, setSelectedCharacter] = useState<string | null>(null);

  useEffect(() => {
    loadCharacters();
  }, []);

  // 加载角色列表
  const loadCharacters = async () => {
    setLoading(true);
    setLoadingMessage('正在加载角色...');
    
    try {
      // 尝试从 sessionStorage 获取创建的角色信息（可选）
      const characterDataStr = sessionStorage.getItem('characterData');
      let characterOptions: CharacterOption[] = [];
      
      if (characterDataStr) {
        // 如果有角色数据，使用它
        const characterData = JSON.parse(characterDataStr);
        const createdCharacterId = sessionStorage.getItem('createdCharacterId') || characterData.characterId;
        
        characterOptions = [
          {
            id: createdCharacterId,
            name: characterData.name || '角色1',
            imageUrl: characterData.imageUrl,
            gender: characterData.gender || 'female'
          }
        ];
      } else {
        // 如果没有角色数据，创建默认角色选项（用于测试）
        characterOptions = [
          {
            id: '1',
            name: '角色1',
            imageUrl: undefined,
            gender: 'female'
          },
          {
            id: '2',
            name: '角色2',
            imageUrl: undefined,
            gender: 'male'
          },
          {
            id: '3',
            name: '角色3',
            imageUrl: undefined,
            gender: 'female'
          }
        ];
      }

      // 为每个角色加载图片
      for (const character of characterOptions) {
        if (character.id) {
          try {
            const imagesResponse = await getCharacterImages(character.id);
            if (imagesResponse.data?.images && imagesResponse.data.images.length > 0) {
              character.imageUrl = imagesResponse.data.images[0];
            }
          } catch (error) {
            console.warn(`获取角色 ${character.id} 的图片失败:`, error);
            // 继续处理，不中断流程
          }
        }
      }

      setCharacters(characterOptions);
      setLoading(false);
    } catch (error) {
      console.error('加载角色失败:', error);
      message.error('加载角色失败，请稍后重试');
      setLoading(false);
    }
  };

  // 选择角色
  const handleSelectCharacter = async (characterId: string) => {
    setSelectedCharacter(characterId);
    
    try {
      // 检查后端服务是否可用
      const isHealthy = await checkServerHealth();
      
      if (!isHealthy) {
        message.error('无法连接到服务器，请检查后端服务是否运行');
        return;
      }

      // 保存选中的角色ID
      const characterDataStr = sessionStorage.getItem('characterData');
      if (characterDataStr) {
        const characterData = JSON.parse(characterDataStr);
        characterData.selectedCharacterId = characterId;
        sessionStorage.setItem('characterData', JSON.stringify(characterData));
      }

      // 跳转到初遇场景选择页面
      navigate('/firstmeeting');
    } catch (error) {
      console.error('选择角色失败:', error);
      message.error('选择角色失败，请稍后重试');
      setLoading(false);
    }
  };

  if (loading && characters.length === 0) {
    return <LoadingScreen message={loadingMessage} />;
  }

  return (
    <div className="character-selection-container">
      {/* 背景图片 */}
      <div 
        className="character-selection-background"
        style={{
          backgroundImage: `url(${backgroundImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      />

      {/* 主内容区域 */}
      <div className="character-selection-content">
        <h2 className="selection-title">选择角色</h2>
        
        {/* 角色选项列表 */}
        <div className="character-options-grid">
          {characters.map((character) => (
            <div 
              key={character.id} 
              className={`character-option-card ${selectedCharacter === character.id ? 'selected' : ''}`}
            >
              {/* 角色图片 */}
              <div className="character-image-container">
                {character.imageUrl ? (
                  <img 
                    src={character.imageUrl} 
                    alt={character.name}
                    className="character-image"
                  />
                ) : (
                  <div className="character-image-placeholder">
                    <span className="placeholder-text">人物</span>
                  </div>
                )}
              </div>
              
              {/* 选择按钮 */}
              <Button
                className="character-choice-button"
                onClick={() => handleSelectCharacter(character.id)}
                disabled={loading}
              >
                choice
              </Button>
            </div>
          ))}
        </div>
      </div>

      {loading && characters.length > 0 && (
        <LoadingScreen message={loadingMessage} />
      )}
    </div>
  );
}

export default CharacterSelection;
