import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, App as AntdApp } from 'antd';
import backgroundImage from '@/assets/images/settingcharacterbackground.png';
import LoadingScreen from '@/components/loading';
import { checkServerHealth, getCharacterImages, removeCharacterBackground, getPresetVoices, setVoiceConfig, getVoicePreviewAudio, getStaticAssetUrl, type PresetVoiceItem } from '@/services/api';
import { ROUTES } from '@/config/routes';
import * as gameStorage from '@/storage/gameStorage';
import './CharacterSelection.css';

interface CharacterOption {
  id: string;
  name: string;
  imageUrl?: string;
  imageUrls?: string[];  // 组图URL列表（3张图片）
  gender: 'male' | 'female';
}

interface RemoveBackgroundResultPayload {
  transparent_url?: string;
  selected_image_url?: string;
  data?: {
    transparent_url?: string;
    selected_image_url?: string;
  };
}

function CharacterSelection() {
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('正在加载角色...');
  const [characters, setCharacters] = useState<CharacterOption[]>([]);
  const [selectedCharacter, setSelectedCharacter] = useState<string | null>(null);
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null);  // 选中的图片索引（0, 1, 2）

  // 步骤：选择人物图片 | 音色选择
  const [step, setStep] = useState<'image' | 'voice'>('image');
  const [presetVoices, setPresetVoices] = useState<PresetVoiceItem[]>([]);
  const [selectedVoiceId, setSelectedVoiceId] = useState<string | null>(null);
  const [voicesLoading, setVoicesLoading] = useState(false);
  const [previewingVoiceId, setPreviewingVoiceId] = useState<string | null>(null);


  // 进入音色选择时拉取预设音色（拉取全部，前端按性别分组展示）
  useEffect(() => {
    if (step !== 'voice') return;
    let cancelled = false;
    setVoicesLoading(true);
    getPresetVoices()
      .then((res) => {
        if (cancelled) return;
        let list: PresetVoiceItem[] = [];
        if (Array.isArray(res)) list = res;
        else if (res && typeof res === 'object' && !Array.isArray(res)) {
          const r = res as Record<string, PresetVoiceItem[]>;
          list = [...(r.female || []), ...(r.male || []), ...(r.neutral || [])];
        }
        setPresetVoices(list);
        if (list.length === 0) {
          message.warning('未获取到音色列表，请检查后端服务');
        }
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        const err = error as { response?: { status?: number }; message?: string };
        const is503 = err.response?.status === 503;
        if (is503) {
          message.warning('TTS 服务暂不可用，但您仍可选择音色（游戏中使用时需确保 TTS 服务已启用）');
        } else {
          message.error('获取音色列表失败，请检查后端服务');
        }
        setPresetVoices([]);
      })
      .finally(() => { if (!cancelled) setVoicesLoading(false); });
    return () => { cancelled = true; };
  }, [step, message]);

  // 试听音色
  const handlePreviewVoice = async (v: PresetVoiceItem) => {
    if (previewingVoiceId) return;
    setPreviewingVoiceId(v.id);
    try {
      const result = await getVoicePreviewAudio(v.id, v.preview_text || undefined);
      if (result?.audio_url) {
        const url = result.audio_url.startsWith('http') ? result.audio_url : `${window.location.origin}${result.audio_url}`;
        const audio = new Audio(url);
        audio.onended = () => setPreviewingVoiceId(null);
        audio.onerror = () => {
          setPreviewingVoiceId(null);
          message.warning('试听音频播放失败');
        };
        audio.play().catch(() => {
          setPreviewingVoiceId(null);
          message.warning('试听音频播放失败');
        });
      } else {
        setPreviewingVoiceId(null);
        message.warning('试听功能暂不可用（TTS 服务未启用），但您仍可选择此音色');
      }
    } catch (error: unknown) {
      setPreviewingVoiceId(null);
      const err = error as { response?: { status?: number; data?: { message?: string } }; message?: string };
      const is503 = err.response?.status === 503;
      // 使用后端返回的错误信息（已根据实际 TTS 提供商生成）
      const errorMsg = err.response?.data?.message || err.message || '试听失败';
      if (is503) {
        // 503 错误：显示后端返回的详细错误信息，并提示仍可选择音色
        message.warning(`${errorMsg}。您仍可选择此音色，游戏中使用时需确保 TTS 服务已启用。`);
      } else {
        message.warning(`试听失败：${errorMsg}`);
      }
    }
  };

  // 加载角色列表
  const loadCharacters = useCallback(async () => {
    setLoading(true);
    setLoadingMessage('正在加载角色...');
    
    try {
      const characterData = gameStorage.getCharacterData();
      const createdCharacterIdStr = gameStorage.getCreatedCharacterId();
      let characterOptions: CharacterOption[] = [];

      if (characterData) {
        console.log('[角色选择] 解析的characterData:', characterData);
        console.log('[角色选择] characterData.characterId:', characterData.characterId);
        
        // 优先使用createdCharacterId，其次使用characterData.characterId
        let createdCharacterId = createdCharacterIdStr || characterData.characterId;
        
        console.log('[角色选择] 获取到的characterId:', createdCharacterId);
        console.log('[角色选择] characterId类型:', typeof createdCharacterId);
        
        if (!createdCharacterId || createdCharacterId === 'undefined' || createdCharacterId === 'null' || String(createdCharacterId).trim() === '') {
          gameStorage.removeCharacterData();
          gameStorage.removeCreatedCharacterId();
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
            imageUrls = [characterData.transparentImageUrl!];
            gameStorage.setCharacterData({ ...characterData, image_urls: imageUrls, imageUrl: characterData.transparentImageUrl });
          }
        }
        characterOptions = [
          {
            id: createdCharacterId,
            name: characterData.name || '角色1',
            imageUrl: characterData.transparentImageUrl || characterData.imageUrl,
            imageUrls: imageUrls,
            gender: characterData.gender || 'female',
          },
        ];
      } else {
        message.warning('未找到角色数据，请先创建角色');
        setTimeout(() => navigate(ROUTES.CHARACTER_SETTING), 1500);
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
              if (imagesResponse?.images?.length) {
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
  }, [message, navigate]);

  useEffect(() => {
    void loadCharacters();
  }, [loadCharacters]);

  // 点击 CHOICE：仅保存选中的图片并进入音色选择界面
  const handleSelectImage = (characterId: string, imageIndex: number) => {
    const character = characters.find(c => c.id === characterId);
    if (!character) {
      console.warn('[角色选择] handleSelectImage: 未找到角色', characterId);
      return;
    }
    const selectedImageUrl = character.imageUrls?.[imageIndex];
    if (!selectedImageUrl && !character.imageUrl) {
      message.warning('图片数据异常，请刷新页面重试');
      return;
    }
    const urlToSave = selectedImageUrl || character.imageUrl;

    setSelectedCharacter(characterId);
    setSelectedImageIndex(imageIndex);

    const characterData = gameStorage.getCharacterData();
    if (characterData) {
      try {
        characterData.selectedCharacterId = characterId;
        characterData.imageUrl = urlToSave;
        characterData.selectedImageIndex = imageIndex;
        gameStorage.setCharacterData(characterData);
      } catch (e) {
        console.warn('[角色选择] 更新存储失败', e);
      }
    }
    // 先切换步骤，确保进入音色选择界面
    setStep('voice');
    console.log('[角色选择] 已选择图片，进入音色选择界面');
  };

  // 音色选择界面点击「确认」：去背、保存音色、跳转初遇
  const handleVoiceConfirm = async () => {
    const characterId = characters[0]?.id;
    const character = characters[0];
    if (!characterId || !character) {
      message.error('角色数据异常');
      return;
    }
    const imageIndex = selectedImageIndex ?? 0;
    const selectedImageUrl = character.imageUrls?.[imageIndex] ?? character.imageUrl;

    setLoading(true);
    setLoadingMessage('正在检查服务器连接...');
    try {
      const isHealthy = await checkServerHealth();
      if (!isHealthy) {
        message.error('无法连接到服务器，请检查后端服务是否运行');
        setLoading(false);
        return;
      }

      setLoadingMessage('正在保存选择...');
      try {
        const selectionResponse = await removeCharacterBackground(
          characterId,
          selectedImageUrl,
          character.imageUrls || [],
          imageIndex
        );
        const characterData = gameStorage.getCharacterData();
        if (characterData) {
          const selectionPayload = selectionResponse as RemoveBackgroundResultPayload;
          const transparentUrl = selectionPayload.transparent_url ?? selectionPayload.data?.transparent_url;
          const selectedUrl = selectionPayload.selected_image_url ?? selectionPayload.data?.selected_image_url;
          if (transparentUrl) {
            characterData.transparentImageUrl = transparentUrl;
            characterData.imageUrl = transparentUrl;
            characterData.image_urls = [transparentUrl];
          } else {
            if (selectedUrl) {
              characterData.selectedImageUrl = selectedUrl;
              characterData.originalImageUrl = selectedUrl;
            }
            const fallbackUrl = selectedUrl || characterData.imageUrl;
            if (fallbackUrl) {
              characterData.imageUrl = fallbackUrl;
              characterData.image_urls = [fallbackUrl];
            }
          }
          gameStorage.setCharacterData(characterData);
        }
        
        // 保存音色配置到角色数据和后端
        if (selectedVoiceId) {
          try {
            // 保存到后端
            await setVoiceConfig({
              character_id: Number(characterId),
              voice_type: 'preset',
              preset_voice_id: selectedVoiceId,
            });
            
            const characterData = gameStorage.getCharacterData();
            if (characterData) {
              const selectedVoice = presetVoices.find(v => v.id === selectedVoiceId);
              characterData.voiceConfig = {
                voice_type: 'preset',
                preset_voice_id: selectedVoiceId,
                voice_name: selectedVoice?.name || '未知音色',
                voice_description: selectedVoice?.description || '',
                voice_id: selectedVoice?.voice_id || ''
              };
              gameStorage.setCharacterData(characterData);
              console.log('[角色选择] 已保存音色配置:', characterData.voiceConfig);
            }
          } catch (e) {
            console.warn('[角色选择] 保存音色配置失败:', e);
          }
        }
        setLoadingMessage('选择完成，正在跳转...');
        await new Promise((r) => setTimeout(r, 500));
        navigate(ROUTES.FIRST_MEETING);
      } catch (bgError: unknown) {
        console.error('选择图片失败:', bgError);
        message.warning('选择图片失败，将使用原图继续');
        await new Promise((r) => setTimeout(r, 500));
        navigate(ROUTES.FIRST_MEETING);
      }
    } catch (error) {
      console.error('选择角色失败:', error);
      message.error('选择角色失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  if (loading && characters.length === 0) {
    return <LoadingScreen message={loadingMessage} />;
  }

  const selectedImageUrlForVoice = characters[0] && (selectedImageIndex != null && characters[0].imageUrls?.[selectedImageIndex])
    ? characters[0].imageUrls[selectedImageIndex]
    : characters[0]?.imageUrl;

  return (
    <div className="character-selection-container">
      {/* 背景图片 - 与设计图一致保持同一背景 */}
      <div
        className="character-selection-background"
        style={{
          backgroundImage: `url(${backgroundImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      />

      {step === 'voice' ? (
        /* 音色选择界面：左人物右音色（按性别分组），底部确认 */
        <div className="character-selection-content voice-selection-layout">
          <h2 className="voice-selection-title">音色设定</h2>
          <p className="voice-selection-hint">选择角色的语音风格，游戏中对话将使用该音色</p>
          <div className="voice-selection-panels">
            <div className="voice-selection-left">
              <div className="voice-character-panel">
                {selectedImageUrlForVoice ? (
                  <img
                    src={getStaticAssetUrl(selectedImageUrlForVoice)}
                    alt="人物"
                    className="voice-character-image"
                  />
                ) : (
                  <div className="voice-character-placeholder">
                    <span className="placeholder-text">人物</span>
                  </div>
                )}
              </div>
              {selectedVoiceId && (
                <div className="voice-current-selection">
                  <span className="voice-current-label">当前选择：</span>
                  <span className="voice-current-name">
                    {presetVoices.find((v) => v.id === selectedVoiceId)?.name ?? selectedVoiceId}
                  </span>
                </div>
              )}
            </div>
            <div className="voice-selection-right">
              {voicesLoading ? (
                <div className="voice-selection-loading">加载音色列表中...</div>
              ) : (
                <div className="voice-selection-grouped">
                  {[
                    { key: 'female' as const, title: '女声' },
                    { key: 'male' as const, title: '男声' },
                    { key: 'neutral' as const, title: '中性' },
                  ].map(({ key, title }) => {
                    const list = presetVoices.filter((v) => (v.gender || 'neutral') === key);
                    if (list.length === 0) return null;
                    return (
                      <div key={key} className="voice-group">
                        <h3 className="voice-group-title">{title}</h3>
                        <div className="voice-selection-grid">
                          {list.map((v) => (
                            <div
                              key={v.id}
                              className={`voice-selection-card ${selectedVoiceId === v.id ? 'selected' : ''}`}
                            >
                              <Button
                                className="voice-selection-card-main"
                                onClick={() => setSelectedVoiceId(v.id)}
                              >
                                <span className="voice-selection-card-name">{v.name}</span>
                                {v.description && (
                                  <span className="voice-selection-card-desc">{v.description}</span>
                                )}
                              </Button>
                              <Button
                                size="small"
                                className="voice-preview-btn"
                                onClick={(e) => { e.stopPropagation(); handlePreviewVoice(v); }}
                                disabled={previewingVoiceId !== null}
                                loading={previewingVoiceId === v.id}
                              >
                                {previewingVoiceId === v.id ? '播放中…' : '试听'}
                              </Button>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
          <div className="voice-selection-footer">
            <Button
              className="voice-back-button"
              onClick={() => setStep('image')}
            >
              返回
            </Button>
            <Button
              className="voice-confirm-button"
              onClick={handleVoiceConfirm}
              disabled={loading}
            >
              确认
            </Button>
          </div>
        </div>
      ) : (
      /* 主内容区域 - 选择人物图片 */
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
                      src={getStaticAssetUrl(imageUrl)} 
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
                
                {/* 选择按钮（点击即选择并进入音色选择界面） */}
                <Button
                  className="character-choice-button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleSelectImage(characters[0].id, index);
                  }}
                  disabled={loading}
                >
                  选择
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
                      src={getStaticAssetUrl(character.imageUrl)} 
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
                
                {/* 选择按钮（点击即选择并进入音色选择界面） */}
                <Button
                  className="character-choice-button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleSelectImage(character.id, 0);
                  }}
                  disabled={loading}
                >
                  选择
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
      )}

      {loading && characters.length > 0 && (
        <LoadingScreen message={loadingMessage} />
      )}
    </div>
  );
}

export default CharacterSelection;
