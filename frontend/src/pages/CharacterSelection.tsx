import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, message } from 'antd';
import backgroundImage from '@/assets/images/settingcharacterbackground.png';
import LoadingScreen from '@/components/loading';
import { checkServerHealth, getCharacterImages, removeCharacterBackground } from '@/services/api';
import './CharacterSelection.css';

interface CharacterOption {
  id: string;
  name: string;
  imageUrl?: string;
  imageUrls?: string[];  // 组图URL列表（3张图片）
  gender: 'male' | 'female';
}

function CharacterSelection() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('正在加载角色...');
  const [characters, setCharacters] = useState<CharacterOption[]>([]);
  const [selectedCharacter, setSelectedCharacter] = useState<string | null>(null);
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null);  // 选中的图片索引（0, 1, 2）

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
      const createdCharacterIdStr = sessionStorage.getItem('createdCharacterId');
      
      console.log('[角色选择] sessionStorage检查:');
      console.log('  - characterData存在:', !!characterDataStr);
      console.log('  - createdCharacterId存在:', !!createdCharacterIdStr);
      console.log('  - createdCharacterId值:', createdCharacterIdStr);
      
      let characterOptions: CharacterOption[] = [];
      
      if (characterDataStr) {
        // 如果有角色数据，使用它
        const characterData = JSON.parse(characterDataStr);
        console.log('[角色选择] 解析的characterData:', characterData);
        console.log('[角色选择] characterData.characterId:', characterData.characterId);
        
        // 优先使用createdCharacterId，其次使用characterData.characterId
        let createdCharacterId = createdCharacterIdStr || characterData.characterId;
        
        console.log('[角色选择] 获取到的characterId:', createdCharacterId);
        console.log('[角色选择] characterId类型:', typeof createdCharacterId);
        
        // 验证characterId是否有效
        if (!createdCharacterId || createdCharacterId === 'undefined' || createdCharacterId === 'null' || String(createdCharacterId).trim() === '') {
          console.error('[角色选择] 无效的characterId:', createdCharacterId);
          console.error('[角色选择] characterData完整内容:', characterData);
          console.error('[角色选择] sessionStorage中的createdCharacterId:', createdCharacterIdStr);
          // 如果characterId无效，清空sessionStorage并显示错误
          sessionStorage.removeItem('characterData');
          sessionStorage.removeItem('createdCharacterId');
          message.error('角色数据无效，请重新创建角色');
          setLoading(false);
          return;
        }
        
        // 确保characterId是字符串
        createdCharacterId = String(createdCharacterId);
        
        // 获取图片URL列表
        let imageUrls = characterData.image_urls || [];
        
        // 如果已经有去除背景后的图片，优先使用它
        // 如果image_urls中包含已删除的图片（portrait_img1/img2/img3），且存在transparentImageUrl，则使用transparentImageUrl
        if (characterData.transparentImageUrl) {
          // 检查imageUrls中是否包含已删除的图片（portrait_img1/img2/img3）
          const hasDeletedImages = imageUrls.some((url: string) => 
            url && (url.includes('portrait_img1') || url.includes('portrait_img2') || url.includes('portrait_img3'))
          );
          
          if (hasDeletedImages) {
            // 如果包含已删除的图片，使用去除背景后的图片
            imageUrls = [characterData.transparentImageUrl];
            // 更新sessionStorage
            characterData.image_urls = imageUrls;
            characterData.imageUrl = characterData.transparentImageUrl;
            sessionStorage.setItem('characterData', JSON.stringify(characterData));
          }
        }
        
        characterOptions = [
          {
            id: createdCharacterId,
            name: characterData.name || '角色1',
            imageUrl: characterData.transparentImageUrl || characterData.imageUrl,  // 优先使用去除背景后的图片
            imageUrls: imageUrls,  // 组图URL列表（如果已去除背景，则只包含一张）
            gender: characterData.gender || 'female'
          }
        ];
        console.log('[角色选择] 从sessionStorage加载角色数据:', {
          characterId: createdCharacterId,
          name: characterData.name,
          imageUrl: characterData.imageUrl,
          image_urls: imageUrls,
          imageUrlsCount: imageUrls.length
        });
        
        // 如果图片URL列表为空，尝试从API获取
        if (imageUrls.length === 0) {
          console.warn('[角色选择] 图片URL列表为空，尝试从API获取');
        }
      } else {
        // 如果没有角色数据，提示用户需要先创建角色
        console.warn('[角色选择] sessionStorage中没有角色数据，用户需要先创建角色');
        message.warning('未找到角色数据，请先创建角色');
        // 延迟后跳转到角色设置页面
        setTimeout(() => {
          navigate('/charactersetting');
        }, 1500);
        setLoading(false);
        return;
      }

      // 为每个角色加载图片（如果没有组图，尝试从API获取）
      for (const character of characterOptions) {
        // 检查character.id是否有效（不能是undefined、null或空字符串）
        if (character.id && character.id !== 'undefined' && character.id !== 'null' && String(character.id).trim() !== '') {
          // 如果已经有组图URL列表，直接使用
          if (character.imageUrls && character.imageUrls.length > 0) {
            // 使用第一张作为默认显示
            character.imageUrl = character.imageUrls[0];
            console.log(`[角色选择] 角色 ${character.id} 使用组图URL列表，共 ${character.imageUrls.length} 张图片`);
            console.log(`[角色选择] 图片URL列表:`, character.imageUrls);
          } else {
            // 如果没有组图，尝试从API获取（兼容旧逻辑）
            try {
              const imagesResponse = await getCharacterImages(String(character.id));
              // 注意：响应拦截器已经提取了data字段
              if (imagesResponse?.images && imagesResponse.images.length > 0) {
                character.imageUrl = imagesResponse.images[0];
              }
            } catch (error) {
              console.warn(`获取角色 ${character.id} 的图片失败:`, error);
              // 继续处理，不中断流程
            }
          }
        } else {
          console.warn(`角色ID无效，跳过图片加载:`, character);
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

  // 选择图片并确认（点击CHOICE按钮即选择并跳转）
  const handleSelectImage = async (characterId: string, imageIndex: number) => {
    // 设置选中状态（用于UI高亮）
    setSelectedCharacter(characterId);
    setSelectedImageIndex(imageIndex);
    
    // 保存选中的图片URL
    const character = characters.find(c => c.id === characterId);
    if (character && character.imageUrls && character.imageUrls[imageIndex]) {
      const selectedImageUrl = character.imageUrls[imageIndex];
      
      // 更新sessionStorage中的图片URL
      const characterDataStr = sessionStorage.getItem('characterData');
      if (characterDataStr) {
        const characterData = JSON.parse(characterDataStr);
        characterData.selectedCharacterId = characterId;
        characterData.imageUrl = selectedImageUrl;  // 保存选中的图片URL
        characterData.selectedImageIndex = imageIndex;  // 保存选中的图片索引
        sessionStorage.setItem('characterData', JSON.stringify(characterData));
      }
      
      // 开始处理流程
      try {
        setLoading(true);
        setLoadingMessage('正在检查服务器连接...');
        
        // 检查后端服务是否可用
        const isHealthy = await checkServerHealth();
        
        if (!isHealthy) {
          message.error('无法连接到服务器，请检查后端服务是否运行');
          setLoading(false);
          return;
        }

        // 选择图片（只保存图片URL，不立即处理透明背景）
        setLoadingMessage('正在保存选择...');
        try {
          // 传递所有图片URL和选中的索引，用于删除未选中的图片
          const selectionResponse = await removeCharacterBackground(
            characterId, 
            selectedImageUrl,
            character.imageUrls,  // 所有图片URL列表
            imageIndex  // 选中的图片索引
          );
          
          if (selectionResponse.data?.transparent_url || selectionResponse.data?.selected_image_url) {
            // 保存透明背景图片URL和原始图片URL
            const characterDataStr = sessionStorage.getItem('characterData');
            if (characterDataStr) {
              const characterData = JSON.parse(characterDataStr);
              // 注意：响应拦截器已经提取了data字段
              const transparentUrl = selectionResponse.transparent_url || selectionResponse.data?.transparent_url;
              const selectedUrl = selectionResponse.selected_image_url || selectionResponse.data?.selected_image_url;
              
              if (transparentUrl) {
                characterData.transparentImageUrl = transparentUrl;  // 透明背景图片URL
                characterData.selectedImageUrl = selectedUrl;          // 原始图片URL
                characterData.originalImageUrl = selectedUrl;          // 原图URL
                characterData.imageUrl = transparentUrl;               // 使用透明背景图片
                // 更新image_urls，只保留透明背景图片（因为其他图片已被删除）
                characterData.image_urls = [transparentUrl];
              } else {
                // 如果没有透明背景URL，使用原始URL
                characterData.selectedImageUrl = selectedUrl;
                characterData.originalImageUrl = selectedUrl;
                characterData.imageUrl = selectedUrl;
                characterData.image_urls = [selectedUrl];
              }
              
              sessionStorage.setItem('characterData', JSON.stringify(characterData));
              
              // 同时更新本地状态
              setCharacters([{
                ...characters[0],
                imageUrl: transparentUrl || selectedUrl,
                imageUrls: [transparentUrl || selectedUrl]
              }]);
            }
            
            setLoadingMessage('选择完成，正在跳转...');
            // 短暂延迟，让用户看到完成消息
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // 跳转到初遇场景选择页面
            navigate('/firstmeeting');
          } else {
            message.warning('选择图片失败');
            setLoadingMessage('正在跳转...');
            await new Promise(resolve => setTimeout(resolve, 500));
            navigate('/firstmeeting');
          }
        } catch (bgError: any) {
          console.error('选择图片失败:', bgError);
          // 即使选择失败，也继续流程
          message.warning('选择图片失败，将使用原图继续');
          setLoadingMessage('正在跳转...');
          await new Promise(resolve => setTimeout(resolve, 500));
          navigate('/firstmeeting');
        }
      } catch (error) {
        console.error('选择角色失败:', error);
        message.error('选择角色失败，请稍后重试');
        setLoading(false);
      }
    } else {
      message.warning('图片数据异常，请刷新页面重试');
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
        
        {/* 角色选项列表 - 三选一组图 */}
        {characters.length > 0 && characters[0].imageUrls && characters[0].imageUrls.length >= 3 ? (
          // 如果有组图（3张图片），显示三选一界面
          <div className="character-options-grid">
            {characters[0].imageUrls.map((imageUrl, index) => (
              <div 
                key={index}
                className={`character-option-card ${selectedCharacter === characters[0].id && selectedImageIndex === index ? 'selected' : ''}`}
                onClick={() => handleSelectImage(characters[0].id, index)}
              >
                {/* 角色图片 */}
                <div className="character-image-container">
                  {imageUrl ? (
                    <img 
                      src={imageUrl} 
                      alt={`${characters[0].name} - 选项 ${index + 1}`}
                      className="character-image"
                      onLoad={() => {
                        console.log(`[角色选择] 图片 ${index + 1} 加载成功:`, imageUrl);
                      }}
                      onError={(e) => {
                        console.error(`[角色选择] 图片 ${index + 1} 加载失败:`, imageUrl);
                        console.error('[角色选择] 请检查图片URL是否正确，或静态文件服务是否已配置');
                        // 显示占位符
                        const target = e.target as HTMLImageElement;
                        target.style.display = 'none';
                        const placeholder = target.parentElement?.querySelector('.character-image-placeholder') as HTMLElement;
                        if (placeholder) {
                          placeholder.style.display = 'flex';
                        }
                      }}
                    />
                  ) : (
                    <div className="character-image-placeholder">
                      <span className="placeholder-text">人物</span>
                    </div>
                  )}
                </div>
                
                {/* 选择按钮（点击即选择并跳转） */}
                <Button
                  className="character-choice-button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelectImage(characters[0].id, index);
                  }}
                  disabled={loading}
                >
                  CHOICE
                </Button>
              </div>
            ))}
          </div>
        ) : (
          // 如果没有组图，使用旧逻辑（单张图片）
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
                      onLoad={() => {
                        console.log(`[角色选择] 角色 ${character.name} 图片加载成功:`, character.imageUrl);
                      }}
                      onError={(e) => {
                        console.error(`[角色选择] 角色 ${character.name} 图片加载失败:`, character.imageUrl);
                        console.error('[角色选择] 请检查图片URL是否正确，或静态文件服务是否已配置');
                        // 显示占位符
                        const target = e.target as HTMLImageElement;
                        target.style.display = 'none';
                        const placeholder = target.parentElement?.querySelector('.character-image-placeholder') as HTMLElement;
                        if (placeholder) {
                          placeholder.style.display = 'flex';
                        }
                      }}
                    />
                  ) : (
                    <div className="character-image-placeholder">
                      <span className="placeholder-text">人物</span>
                    </div>
                  )}
                </div>
                
                {/* 选择按钮（点击即选择并跳转） */}
                <Button
                  className="character-choice-button"
                  onClick={async () => {
                    await handleSelectImage(character.id, 0);
                  }}
                  disabled={loading}
                >
                  CHOICE
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      {loading && characters.length > 0 && (
        <LoadingScreen message={loadingMessage} />
      )}
    </div>
  );
}

export default CharacterSelection;
