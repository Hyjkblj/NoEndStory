"""AI图片生成服务"""
from typing import Dict, Any, Optional, List
import sys
import os
from datetime import datetime
import re

# 添加backend目录到路径，以便导入config
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config

# 尝试导入dashscope（用于通义万相图片生成）
try:
    import dashscope
    from dashscope import ImageSynthesis
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    print("[警告] dashscope未安装，通义万相图片生成功能将不可用。请运行: pip install dashscope")

# 尝试导入requests（用于火山引擎Seedream API调用）
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("[警告] requests未安装，火山引擎图片生成功能将不可用。请运行: pip install requests")


class ImageService:
    """AI图片生成服务"""
    
    def __init__(self):
        """初始化图片生成服务"""
        self.enabled = False
        self.provider = None
        self.volcengine_api_url = None
        
        # 优先检查火山引擎Seedream API（如果配置了）
        # 检查配置值（去除空格后判断）
        volcengine_key = config.VOLCENGINE_ARK_API_KEY.strip() if config.VOLCENGINE_ARK_API_KEY else ''
        
        if REQUESTS_AVAILABLE and volcengine_key:
            # 根据region构建API端点
            region_map = {
                'cn-beijing': 'ark.cn-beijing.volces.com',
                'cn-north-1': 'ark.cn-beijing.volces.com',  # 默认使用北京
            }
            host = region_map.get(config.VOLCENGINE_REGION, 'ark.cn-beijing.volces.com')
            self.volcengine_api_url = f"https://{host}/api/v3/images/generations"
            self.enabled = True
            self.provider = 'volcengine'
            print(f"[信息] AI图片生成服务已启用 - 使用服务: 火山引擎Seedream (VolcEngine)")
            print(f"[信息] API端点: {self.volcengine_api_url}")
            print(f"[信息] 模型: {config.VOLCENGINE_IMAGE_MODEL}")
            print(f"[信息] ARK API Key: {volcengine_key[:10]}...{volcengine_key[-4:] if len(volcengine_key) > 14 else ''} (已配置)")
        elif not REQUESTS_AVAILABLE:
            print("[警告] requests未安装，火山引擎图片生成功能不可用")
        elif not volcengine_key:
            print("[警告] 未配置VOLCENGINE_ARK_API_KEY或值为空，火山引擎图片生成功能不可用")
            print(f"[调试] 配置值: '{config.VOLCENGINE_ARK_API_KEY}' (长度: {len(config.VOLCENGINE_ARK_API_KEY) if config.VOLCENGINE_ARK_API_KEY else 0})")
        
        # 如果火山引擎不可用，检查通义万相
        if not self.enabled:
            if DASHSCOPE_AVAILABLE and config.DASHSCOPE_API_KEY:
                dashscope.api_key = config.DASHSCOPE_API_KEY
                self.enabled = True
                self.provider = 'dashscope'
                print(f"[信息] AI图片生成服务已启用 - 使用服务: 通义万相 (DashScope)")
            else:
                if not DASHSCOPE_AVAILABLE:
                    print("[警告] dashscope未安装，通义万相图片生成功能不可用")
                elif not config.DASHSCOPE_API_KEY:
                    print("[警告] 未配置DASHSCOPE_API_KEY，通义万相图片生成功能不可用")
        
        if not self.enabled:
            print("[警告] 所有图片生成服务均不可用，请配置至少一个服务")
    
    def generate_character_image_prompt(self, request_data: Dict[str, Any], generate_group: bool = True, group_count: int = 3) -> str:
        """根据前端接收的人物设定数据生成完整的图片生成prompt
        
        Args:
            request_data: 前端发送的角色创建请求数据
            generate_group: 是否生成组图（默认：True）
            group_count: 组图数量（默认：3）
            
        Returns:
            专业的中文图片生成prompt（简洁描述性文本，适合豆包Seedream模型）
        """
        name = request_data.get('name', '角色')
        gender = request_data.get('gender', '')
        age = request_data.get('age')
        
        # 解析外观数据
        appearance = request_data.get('appearance', {})
        appearance_keywords = []
        height = None
        weight = None
        
        if isinstance(appearance, dict):
            keywords = appearance.get('keywords', [])
            if isinstance(keywords, list):
                appearance_keywords = keywords
            height = appearance.get('height')
            weight = appearance.get('weight')
        
        # 解析性格数据
        personality = request_data.get('personality', {})
        personality_keywords = []
        if isinstance(personality, dict):
            keywords = personality.get('keywords', [])
            if isinstance(keywords, list):
                personality_keywords = keywords
        
        # 解析背景数据
        background = request_data.get('background', {})
        background_style = ''
        if isinstance(background, dict):
            background_style = background.get('style', '')
        
        # 构建prompt描述部分（类似示例风格：简洁、专业、描述性）
        prompt_parts = []
        
        # 0. 角色设定（在提示词开头）
        role_prompt = "你是一位游戏开发人员，负责开发一款二次元无限流剧情游戏，你负责的工作是根据玩家的要求生成他们内心的男神or女神图片"
        prompt_parts.append(role_prompt)
        
        # 1. 角色基础特征描述
        character_desc_parts = []
        
        # 性别和年龄
        if gender == 'male':
            gender_desc = '男性'
        elif gender == 'female':
            gender_desc = '女性'
        else:
            gender_desc = ''
        
        if gender_desc:
            if age:
                character_desc_parts.append(f'{age}岁{gender_desc}角色')
            else:
                character_desc_parts.append(f'{gender_desc}角色')
        elif age:
            character_desc_parts.append(f'{age}岁角色')
        
        # 外观特征（自然描述）
        if appearance_keywords:
            # 将关键词转换为自然描述，限制数量避免过长
            appearance_desc = '，'.join(appearance_keywords[:4])
            character_desc_parts.append(appearance_desc)
        
        if height:
            character_desc_parts.append(f'身高{height}cm')
        if weight:
            character_desc_parts.append(f'体重{weight}kg')
        
        if character_desc_parts:
            prompt_parts.append('，'.join(character_desc_parts))
        
        # 2. 性格特征（影响表情和姿态）
        if personality_keywords:
            personality_desc = '、'.join(personality_keywords[:3])
            prompt_parts.append(f'性格{personality_desc}')
        
        # 3. 风格描述
        if background_style:
            prompt_parts.append(f'{background_style}风格')
        
        # 4. 图片质量和技术要求（二次元动漫风格）
        quality_parts = [
            '二次元动漫风格',
            '高质量立绘',
            '全身像',
            '细节丰富',
            '精美插画',
            '专业画质',
            '8k分辨率',
            '柔和光线',
            '细腻笔触',
            '透明背景',
            'PNG格式'
        ]
        prompt_parts.extend(quality_parts)
        
        # 组合成完整的prompt（用逗号分隔，自然流畅的描述性文本）
        prompt = '，'.join(prompt_parts)
        
        # 如果启用组图生成，在提示词末尾添加组图指令
        if generate_group and group_count > 1:
            prompt += f'，返回一组图，一组为{group_count}张'
        
        return prompt
    
    def generate_scene_image_prompt(self, scene_data: Dict[str, Any]) -> str:
        """根据场景数据生成完整的场景图片生成prompt
        
        Args:
            scene_data: 场景数据，包含：
                - scene_id: 场景ID（如'school', 'library'等）
                - scene_name: 场景名称（可选）
                - scene_description: 场景描述（可选）
                - atmosphere: 氛围描述（可选）
                - time_of_day: 时间（如'白天', '夜晚'等，可选）
                - weather: 天气（如'晴天', '雨天'等，可选）
            
        Returns:
            专业的中文场景图片生成prompt（简洁描述性文本，适合豆包Seedream模型）
        """
        scene_id = scene_data.get('scene_id', '')
        scene_name = scene_data.get('scene_name', '')
        scene_description = scene_data.get('scene_description', '')
        atmosphere = scene_data.get('atmosphere', '')
        time_of_day = scene_data.get('time_of_day', '')
        weather = scene_data.get('weather', '')
        
        # 如果没有提供场景名称，尝试从场景ID获取
        if not scene_name and scene_id:
            try:
                from data.scenes import SCENES
                scene_info = SCENES.get(scene_id, {})
                scene_name = scene_info.get('name', scene_id)
                if not scene_description:
                    scene_description = scene_info.get('description', '')
            except:
                scene_name = scene_id
        
        # 构建prompt描述部分
        prompt_parts = []
        
        # 1. 场景基础信息
        scene_desc_parts = []
        
        if scene_name:
            scene_desc_parts.append(scene_name)
        
        if scene_description:
            scene_desc_parts.append(scene_description)
        
        if scene_desc_parts:
            prompt_parts.append('，'.join(scene_desc_parts))
        
        # 2. 时间和天气（影响场景氛围）
        time_weather_parts = []
        if time_of_day:
            time_weather_parts.append(time_of_day)
        if weather:
            time_weather_parts.append(weather)
        if time_weather_parts:
            prompt_parts.append('，'.join(time_weather_parts))
        
        # 3. 氛围描述
        if atmosphere:
            prompt_parts.append(f'氛围{atmosphere}')
        
        # 4. 图片质量和技术要求（场景图不需要透明背景）
        quality_parts = [
            '二次元动漫风格',
            '高质量场景图',
            '全景视角',
            '细节丰富',
            '精美插画',
            '专业画质',
            '8k分辨率',
            '柔和光线',
            '细腻笔触',
            '自然背景',
            '环境氛围感强'
        ]
        prompt_parts.extend(quality_parts)
        
        # 组合成完整的prompt
        prompt = '，'.join(prompt_parts)
        
        return prompt
    
    def generate_character_image(self, prompt: str, character_id: Optional[int] = None, 
                                 user_id: Optional[str] = None, image_type: str = 'portrait',
                                 generate_group: bool = True, group_count: int = 3) -> Optional[List[str]]:
        """生成角色图片（支持组图生成，供前端三选一）
        
        Args:
            prompt: 图片生成prompt
            character_id: 角色ID（可选，用于保存图片URL）
            user_id: 玩家ID（可选，用于文件命名）
            image_type: 图片类型（portrait=立绘, avatar=头像，默认：portrait）
            generate_group: 是否生成组图（默认：True，生成3张图片供前端选择）
            group_count: 组图数量（默认：3）
            
        注意：场景图片请使用 generate_scene_image() 方法
            
        Returns:
            图片URL列表（如果生成成功），否则返回None
        """
        if not self.enabled:
            print("[警告] 图片生成服务未启用，无法生成图片")
            return None
        
        try:
            if self.provider == 'volcengine':
                # 使用火山引擎生成图片（支持组图）
                return self._generate_with_volcengine(prompt, character_id, user_id, image_type, generate_group, group_count)
            elif self.provider == 'dashscope':
                # 使用通义万相生成图片（暂不支持组图，生成单张）
                result = self._generate_with_dashscope(prompt, character_id, user_id, image_type)
                return [result] if result else None
            else:
                print(f"[警告] 未知的图片生成服务提供商: {self.provider}")
                return None
        except Exception as e:
            print(f"[错误] 图片生成失败: {e}")
            return None
    
    def _generate_with_volcengine(self, prompt: str, character_id: Optional[int] = None,
                                  user_id: Optional[str] = None, image_type: str = 'portrait',
                                  generate_group: bool = True, group_count: int = 3) -> Optional[List[str]]:
        """使用火山引擎Seedream 4.0-4.5 API生成图片（支持组图）
        
        Args:
            prompt: 图片生成prompt
            character_id: 角色ID（可选）
            user_id: 玩家ID（可选，用于文件命名）
            image_type: 图片类型（portrait=立绘, avatar=头像）
            generate_group: 是否生成组图（默认：True）
            group_count: 组图数量（默认：3）
            
        Returns:
            图片URL列表，如果失败返回None
        """
        try:
            if generate_group:
                print(f"[AI生图] 正在使用火山引擎Seedream生成角色组图 (角色ID: {character_id}, 数量: {group_count}, 比例: 9:16, 无水印)")
            else:
                print(f"[AI生图] 正在使用火山引擎Seedream生成角色图片 (角色ID: {character_id}, 比例: 9:16, 无水印)")
            print(f"[AI生图] Prompt: {prompt[:100]}...")
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {config.VOLCENGINE_ARK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # 构建请求体
            # 人物图片使用9:16竖屏比例（适合人物立绘）
            # 火山引擎API支持格式：9:16（比例）或 1080x1920（具体像素）
            # 使用"9:16"比例，API会自动选择合适的分辨率
            character_image_size = "9:16"  # 9:16竖屏比例
            
            payload = {
                "model": config.VOLCENGINE_IMAGE_MODEL,
                "prompt": prompt,
                "size": character_image_size,  # 人物图片固定使用9:16比例
                "response_format": "url",
                "watermark": False,  # 不带水印（用户要求）
                "stream": False  # 非流式输出
            }
            
            # 组图生成已通过提示词实现（在prompt末尾添加"返回一组图 一组为3张"）
            # 不再使用API的sequential_image_generation参数，直接由提示词控制
            
            # 发送请求
            response = requests.post(
                self.volcengine_api_url,
                headers=headers,
                json=payload,
                timeout=180  # 组图生成可能需要更长时间
            )
            
            # 检查HTTP状态码
            if response.status_code != 200:
                print(f"[警告] 火山引擎API请求失败: HTTP {response.status_code}")
                print(f"[警告] 响应内容: {response.text[:200]}")
                return None
            
            # 解析响应
            resp_data = response.json()
            
            # 检查是否有错误
            if 'error' in resp_data:
                error_info = resp_data['error']
                error_msg = error_info.get('message', '未知错误')
                print(f"[警告] 火山引擎图片生成失败: {error_msg}")
                return None
            
            # 提取图片URL列表
            image_urls = []
            if 'data' in resp_data and len(resp_data['data']) > 0:
                # 提取所有图片URL
                for image_data in resp_data['data']:
                    image_url = image_data.get('url')
                    if image_url:
                        image_urls.append(image_url)
                
                if image_urls:
                    print(f"[AI生图] 图片生成成功: 共生成 {len(image_urls)} 张图片")
                    for i, url in enumerate(image_urls, 1):
                        print(f"[AI生图] 图片 {i}: {url}")
                    
                    # 保存图片到本地（如果启用）- 人物图片
                    if config.IMAGE_SAVE_ENABLED and character_id:
                        for idx, image_url in enumerate(image_urls):
                            local_path = self._save_image_to_local(
                                image_url, character_id, user_id, image_type,
                                image_index=idx + 1  # 图片索引（1, 2, 3）
                            )
                            if local_path:
                                print(f"[AI生图] 图片 {idx + 1} 已保存到本地: {local_path}")
                    
                    # TODO: 保存图片URL列表到数据库（关联到character_id）
                    if character_id:
                        # self._save_image_urls(character_id, image_urls)
                        pass
                    
                    return image_urls
                else:
                    print(f"[警告] 响应中未找到图片URL: {resp_data}")
                    return None
            else:
                print(f"[警告] 响应中未找到data字段或data为空: {resp_data}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"[错误] 火山引擎API请求异常: {e}")
            return None
        except Exception as e:
            print(f"[错误] 火山引擎图片生成异常: {e}")
            import traceback
            print(traceback.format_exc())
            return None
    
    def _generate_with_dashscope(self, prompt: str, character_id: Optional[int] = None,
                                 user_id: Optional[str] = None, image_type: str = 'portrait') -> Optional[str]:
        """使用通义万相生成图片
        
        Args:
            prompt: 图片生成prompt
            character_id: 角色ID（可选）
            
        Returns:
            图片URL，如果失败返回None
        """
        try:
            print(f"[AI生图] 正在生成角色图片 (角色ID: {character_id})")
            print(f"[AI生图] Prompt: {prompt[:100]}...")
            
            response = ImageSynthesis.call(
                model='wanx-v1',  # 通义万相模型
                prompt=prompt,
                n=1,  # 生成1张图片
                size='1024*1024'  # 图片尺寸
            )
            
            if response.status_code == 200:
                image_url = response.output.results[0].url
                print(f"[AI生图] 图片生成成功: {image_url}")
                
                # 保存图片到本地（如果启用）- 人物图片
                local_path = None
                if config.IMAGE_SAVE_ENABLED and character_id:
                    local_path = self._save_image_to_local(image_url, character_id, user_id, image_type)
                    if local_path:
                        print(f"[AI生图] 图片已保存到本地: {local_path}")
                
                # TODO: 保存图片URL到数据库（关联到character_id）
                if character_id:
                    # self._save_image_url(character_id, image_url, local_path)
                    pass
                
                return image_url
            else:
                print(f"[警告] 图片生成失败: {response.message}")
                return None
        except Exception as e:
            print(f"[错误] 通义万相图片生成异常: {e}")
            return None
    
    def generate_character_image_by_data(self, request_data: Dict[str, Any], character_id: Optional[int] = None,
                                         user_id: Optional[str] = None, image_type: str = 'portrait',
                                         generate_group: bool = True, group_count: int = 3) -> Optional[List[str]]:
        """根据角色数据生成人物图片（便捷方法，支持组图）
        
        Args:
            request_data: 前端发送的角色创建请求数据
            character_id: 角色ID（可选）
            user_id: 玩家ID（可选，用于文件命名）
            image_type: 图片类型（portrait=立绘, avatar=头像，默认：portrait）
            generate_group: 是否生成组图（默认：True，生成3张图片供前端选择）
            group_count: 组图数量（默认：3）
            
        Returns:
            图片URL列表，如果失败返回None
        """
        # 生成prompt（传递组图参数，提示词末尾会添加组图指令）
        prompt = self.generate_character_image_prompt(request_data, generate_group, group_count)
        
        # 生成图片
        return self.generate_character_image(prompt, character_id, user_id, image_type, generate_group, group_count)
    
    def generate_scene_image(self, scene_data: Dict[str, Any], scene_id: Optional[str] = None,
                            user_id: Optional[str] = None) -> Optional[str]:
        """生成场景图片
        
        Args:
            scene_data: 场景数据（包含scene_id, scene_name, scene_description等）
            scene_id: 场景ID（可选，如果scene_data中没有提供）
            user_id: 玩家ID（可选，用于文件命名）
            
        Returns:
            图片URL，如果失败返回None
        """
        if not self.enabled:
            print("[警告] 图片生成服务未启用，无法生成图片")
            return None
        
        # 确保scene_id存在
        if not scene_data.get('scene_id') and scene_id:
            scene_data['scene_id'] = scene_id
        
        # 生成场景图片prompt
        prompt = self.generate_scene_image_prompt(scene_data)
        
        # 获取场景信息用于文件命名
        scene_id_for_naming = scene_data.get('scene_id', scene_id or 'unknown')
        scene_name_for_naming = scene_data.get('scene_name', '')
        
        try:
            if self.provider == 'volcengine':
                # 使用火山引擎生成场景图片
                return self._generate_scene_with_volcengine(prompt, scene_id_for_naming, scene_name_for_naming, user_id)
            elif self.provider == 'dashscope':
                # 使用通义万相生成场景图片
                return self._generate_scene_with_dashscope(prompt, scene_id_for_naming, scene_name_for_naming, user_id)
            else:
                print(f"[警告] 未知的图片生成服务提供商: {self.provider}")
                return None
        except Exception as e:
            print(f"[错误] 场景图片生成失败: {e}")
            return None
    
    def _generate_scene_with_volcengine(self, prompt: str, scene_id: str, scene_name: str,
                                       user_id: Optional[str] = None) -> Optional[str]:
        """使用火山引擎生成场景图片
        
        Args:
            prompt: 场景图片生成prompt
            scene_id: 场景ID（用于文件命名）
            scene_name: 场景名称（用于文件命名）
            user_id: 玩家ID（可选）
            
        Returns:
            图片URL，如果失败返回None
        """
        try:
            print(f"[AI生图] 正在使用火山引擎Seedream生成场景图片 (场景ID: {scene_id})")
            print(f"[AI生图] Prompt: {prompt[:100]}...")
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {config.VOLCENGINE_ARK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # 构建请求体
            payload = {
                "model": config.VOLCENGINE_IMAGE_MODEL,
                "prompt": prompt,
                "size": config.VOLCENGINE_IMAGE_SIZE,
                "response_format": "url",
                "watermark": False,  # 场景图不需要水印
                "stream": False  # 非流式输出
            }
            
            # 发送请求
            response = requests.post(
                self.volcengine_api_url,
                headers=headers,
                json=payload,
                timeout=120  # 生图可能需要较长时间
            )
            
            # 检查HTTP状态码
            if response.status_code != 200:
                print(f"[警告] 火山引擎API请求失败: HTTP {response.status_code}")
                print(f"[警告] 响应内容: {response.text[:200]}")
                return None
            
            # 解析响应
            resp_data = response.json()
            
            # 检查是否有错误
            if 'error' in resp_data:
                error_info = resp_data['error']
                error_msg = error_info.get('message', '未知错误')
                print(f"[警告] 火山引擎场景图片生成失败: {error_msg}")
                return None
            
            # 提取图片URL
            if 'data' in resp_data and len(resp_data['data']) > 0:
                # 取第一张图片的URL
                image_data = resp_data['data'][0]
                image_url = image_data.get('url')
                
                if image_url:
                    print(f"[AI生图] 场景图片生成成功: {image_url}")
                    
                    # 保存图片到本地（如果启用）
                    local_path = None
                    if config.IMAGE_SAVE_ENABLED:
                        local_path = self._save_image_to_local(image_url, None, user_id, 'scene', 
                                                              scene_id, scene_name)
                        if local_path:
                            print(f"[AI生图] 场景图片已保存到本地: {local_path}")
                    
                    return image_url
                else:
                    print(f"[警告] 响应中未找到图片URL: {resp_data}")
                    return None
            else:
                print(f"[警告] 响应中未找到data字段或data为空: {resp_data}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"[错误] 火山引擎API请求异常: {e}")
            return None
        except Exception as e:
            print(f"[错误] 火山引擎场景图片生成异常: {e}")
            import traceback
            print(traceback.format_exc())
            return None
    
    def _generate_scene_with_dashscope(self, prompt: str, scene_id: str, scene_name: str,
                                      user_id: Optional[str] = None) -> Optional[str]:
        """使用通义万相生成场景图片
        
        Args:
            prompt: 场景图片生成prompt
            scene_id: 场景ID（用于文件命名）
            scene_name: 场景名称（用于文件命名）
            user_id: 玩家ID（可选）
            
        Returns:
            图片URL，如果失败返回None
        """
        try:
            print(f"[AI生图] 正在生成场景图片 (场景ID: {scene_id})")
            print(f"[AI生图] Prompt: {prompt[:100]}...")
            
            response = ImageSynthesis.call(
                model='wanx-v1',  # 通义万相模型
                prompt=prompt,
                n=1,  # 生成1张图片
                size='1024*1024'  # 图片尺寸
            )
            
            if response.status_code == 200:
                image_url = response.output.results[0].url
                print(f"[AI生图] 场景图片生成成功: {image_url}")
                
                # 保存图片到本地（如果启用）
                local_path = None
                if config.IMAGE_SAVE_ENABLED:
                    local_path = self._save_image_to_local(image_url, None, user_id, 'scene',
                                                          scene_id, scene_name)
                    if local_path:
                        print(f"[AI生图] 场景图片已保存到本地: {local_path}")
                
                return image_url
            else:
                print(f"[警告] 场景图片生成失败: {response.message}")
                return None
        except Exception as e:
            print(f"[错误] 通义万相场景图片生成异常: {e}")
            return None
    
    def _save_image_to_local(self, image_url: str, character_id: Optional[int] = None,
                            user_id: Optional[str] = None, image_type: str = 'portrait',
                            scene_id: Optional[str] = None, scene_name: Optional[str] = None,
                            image_index: Optional[int] = None) -> Optional[str]:
        """下载并保存图片到本地（使用详细命名规范）
        
        人物图片命名格式：{玩家ID}_{角色ID}_{角色名称}_{状态类型}_v{版本号}_{时间戳}.{扩展名}
        示例：USER001_0042_Alice_portrait_v1_20241220_143025.jpg
        
        场景图片命名格式：{玩家ID}_SCENE_{场景ID}_{场景名称}_scene_v{版本号}_{时间戳}.{扩展名}
        示例：USER001_SCENE_school_学校_scene_v1_20241220_143025.jpg
        
        Args:
            image_url: 图片URL
            character_id: 角色ID（人物图片必需，场景图片为None）
            user_id: 玩家ID（可选，如果未提供则使用'UNKNOWN'）
            image_type: 图片类型（portrait=立绘, avatar=头像, scene=场景图，默认：portrait）
            scene_id: 场景ID（场景图片必需，人物图片为None）
            scene_name: 场景名称（场景图片可选）
            
        Returns:
            本地文件路径，如果失败返回None
        """
        try:
            # 处理玩家ID
            if not user_id:
                user_id = 'UNKNOWN'
            # 清理玩家ID中的非法字符，限制长度
            safe_user_id = re.sub(r'[<>:"/\\|?*\s]', '_', user_id)[:20]
            
            # 创建保存目录（支持相对路径和绝对路径）
            if os.path.isabs(config.IMAGE_SAVE_DIR):
                save_dir = config.IMAGE_SAVE_DIR
            else:
                save_dir = os.path.join(backend_dir, config.IMAGE_SAVE_DIR)
            os.makedirs(save_dir, exist_ok=True)
            
            # 下载图片
            img_response = requests.get(image_url, timeout=30)
            if img_response.status_code != 200:
                print(f"[警告] 下载图片失败: HTTP {img_response.status_code}")
                return None
            
            # 确定文件扩展名（从Content-Type或URL）
            content_type = img_response.headers.get('Content-Type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'webp' in content_type:
                ext = '.webp'
            else:
                # 从URL推断
                if '.jpg' in image_url.lower() or '.jpeg' in image_url.lower():
                    ext = '.jpg'
                elif '.png' in image_url.lower():
                    ext = '.png'
                elif '.webp' in image_url.lower():
                    ext = '.webp'
                else:
                    ext = '.jpg'  # 默认使用jpg
            
            # 规范化图片类型
            image_type_map = {
                'portrait': 'portrait',  # 立绘
                'avatar': 'avatar',      # 头像
                'scene': 'scene',        # 场景图
                'fullbody': 'fullbody',  # 全身像
                'bust': 'bust'          # 半身像
            }
            normalized_type = image_type_map.get(image_type.lower(), 'portrait')
            
            # 根据图片类型生成不同的文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 如果是组图中的一张，添加索引
            index_suffix = f"_img{image_index}" if image_index else ""
            
            if image_type == 'scene':
                # 场景图片命名
                if not scene_id:
                    scene_id = 'unknown'
                if not scene_name:
                    # 尝试从场景ID获取名称
                    try:
                        from data.scenes import SCENES
                        scene_info = SCENES.get(scene_id, {})
                        scene_name = scene_info.get('name', scene_id)
                    except:
                        scene_name = scene_id
                
                # 清理场景名称
                safe_scene_name = re.sub(r'[<>:"/\\|?*\s]', '_', scene_name)
                safe_scene_name = safe_scene_name.strip()
                if not safe_scene_name:
                    safe_scene_name = '场景'
                
                # 清理场景ID
                safe_scene_id = re.sub(r'[<>:"/\\|?*\s]', '_', scene_id)[:30]
                
                base_filename = f"{safe_user_id}_SCENE_{safe_scene_id}_{safe_scene_name}_{normalized_type}{index_suffix}"
            else:
                # 人物图片命名
                if not character_id:
                    print("[警告] 人物图片需要character_id")
                    return None
                
                # 获取角色信息（用于文件名）
                character_info = self._get_character_info(character_id)
                character_name = character_info.get('name', f'角色{character_id}')
                
                # 清理角色名称中的非法字符
                safe_name = re.sub(r'[<>:"/\\|?*\s]', '_', character_name)
                safe_name = safe_name.strip()
                if not safe_name:
                    safe_name = '角色'
                
                base_filename = f"{safe_user_id}_{character_id:04d}_{safe_name}_{normalized_type}{index_suffix}"
            
            # 确定版本号（检查已存在的文件）
            version = self._get_next_version(save_dir, base_filename, ext)
            
            # 完整文件名
            filename = f"{base_filename}_v{version}_{timestamp}{ext}"
            filepath = os.path.join(save_dir, filename)
            
            # 保存文件
            with open(filepath, 'wb') as f:
                f.write(img_response.content)
            
            return filepath
            
        except Exception as e:
            print(f"[错误] 保存图片到本地失败: {e}")
            import traceback
            print(traceback.format_exc())
            return None
    
    def _get_next_version(self, save_dir: str, base_filename: str, ext: str) -> int:
        """获取下一个版本号
        
        检查目录中已存在的同名文件，返回下一个版本号
        
        Args:
            save_dir: 保存目录
            base_filename: 基础文件名（不含版本号和时间戳）
            ext: 文件扩展名
            
        Returns:
            下一个版本号（从1开始）
        """
        try:
            if not os.path.exists(save_dir):
                return 1
            
            # 构建匹配模式：{base_filename}_v{数字}_{时间戳}{ext}
            pattern = re.compile(rf"^{re.escape(base_filename)}_v(\d+)_\d{{8}}_\d{{6}}{re.escape(ext)}$")
            
            max_version = 0
            for filename in os.listdir(save_dir):
                match = pattern.match(filename)
                if match:
                    version = int(match.group(1))
                    max_version = max(max_version, version)
            
            return max_version + 1
        except Exception as e:
            print(f"[警告] 获取版本号失败: {e}，使用默认版本号1")
            return 1
    
    def _get_character_info(self, character_id: int) -> Dict[str, str]:
        """获取角色信息（用于文件命名）
        
        Args:
            character_id: 角色ID
            
        Returns:
            包含角色信息的字典
        """
        try:
            # 导入必要的模块
            from database.db_manager import DatabaseManager
            db_manager = DatabaseManager()
            character = db_manager.get_character(character_id)
            if character:
                return {
                    'name': character.name or f'角色{character_id}',
                    'gender': character.gender or ''
                }
        except Exception as e:
            print(f"[警告] 获取角色信息失败: {e}")
        
        return {
            'name': f'角色{character_id}',
            'gender': ''
        }
    
