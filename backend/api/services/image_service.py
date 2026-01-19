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

# 尝试导入PIL（用于图片合成）
try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[警告] Pillow未安装，图片合成功能将不可用。请运行: pip install Pillow")

# 尝试导入rembg（用于高质量背景去除）
try:
    from rembg import remove, new_session
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False
    print("[警告] rembg未安装，高质量背景去除功能将不可用。请运行: pip install rembg")


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
        
        # 初始化rembg会话（使用isnet-general-use模型）
        self.rembg_session = None
        if REMBG_AVAILABLE:
            try:
                # 使用isnet-general-use模型（高质量通用模型）
                self.rembg_session = new_session('isnet-general-use')
                print("[信息] rembg背景去除服务已初始化 - 使用模型: isnet-general-use")
            except Exception as e:
                print(f"[警告] rembg会话初始化失败: {e}")
                self.rembg_session = None
    
    def remove_background_with_rembg(self, image_path: str, output_path: Optional[str] = None, 
                                     character_id: Optional[int] = None, 
                                     rename_to_standard: bool = False) -> Optional[str]:
        """使用rembg的isnet-general-use模型去除图片背景（高质量）
        
        Args:
            image_path: 输入图片路径（本地文件路径或URL）
            output_path: 输出图片路径（可选，如果不提供则自动生成）
            character_id: 角色ID（用于文件命名）
            
        Returns:
            处理后的图片路径（PNG格式，透明背景），如果失败返回None
        """
        if not REMBG_AVAILABLE:
            print("[警告] rembg未安装，无法使用高质量背景去除")
            return None
        
        if not PIL_AVAILABLE:
            print("[警告] Pillow未安装，无法处理图片")
            return None
        
        if not self.rembg_session:
            print("[警告] rembg会话未初始化，无法去除背景")
            return None
        
        try:
            from io import BytesIO
            import requests
            
            # 读取输入图片
            input_bytes = None
            if image_path.startswith('http://') or image_path.startswith('https://'):
                # 从URL下载
                response = requests.get(image_path, timeout=30)
                if response.status_code == 200:
                    input_bytes = response.content
                else:
                    print(f"[警告] 下载图片失败: HTTP {response.status_code}")
                    return None
            else:
                # 本地文件路径
                if os.path.exists(image_path):
                    with open(image_path, 'rb') as f:
                        input_bytes = f.read()
                else:
                    print(f"[警告] 图片文件不存在: {image_path}")
                    return None
            
            # 使用rembg去除背景
            print(f"[背景去除] 开始处理图片: {image_path}")
            output_bytes = remove(input_bytes, session=self.rembg_session)
            
            # 确定输出路径
            if not output_path:
                # 自动生成输出路径（使用角色图片保存目录）
                # 处理相对路径和绝对路径
                if os.path.isabs(config.IMAGE_SAVE_DIR):
                    base_dir = config.IMAGE_SAVE_DIR
                else:
                    base_dir = os.path.join(backend_dir, config.IMAGE_SAVE_DIR)
                
                if character_id:
                    if rename_to_standard:
                        # 重命名为标准格式：{玩家ID}_{角色ID:04d}_{角色名称}_portrait_v{版本号}_{时间戳}.png
                        # 获取角色信息
                        character_info = self._get_character_info(character_id)
                        character_name = character_info.get('name', f'角色{character_id}')
                        safe_name = re.sub(r'[<>:"/\\|?*\s]', '_', character_name).strip()
                        if not safe_name:
                            safe_name = '角色'
                        
                        # 使用UNKNOWN作为默认用户ID（与_save_image_to_local保持一致）
                        safe_user_id = 'UNKNOWN'
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        
                        # 构建标准文件名（不包含_img索引，因为这是唯一图片）
                        base_filename = f"{safe_user_id}_{character_id:04d}_{safe_name}_portrait"
                        
                        # 确定版本号
                        version = self._get_next_version(base_dir, base_filename, '.png')
                        
                        # 完整文件名（标准格式）
                        filename = f"{base_filename}_v{version}_{timestamp}.png"
                        output_path = os.path.join(base_dir, filename)
                        print(f"[背景去除] 将重命名为标准格式: {filename}")
                    else:
                        # 使用原始文件名加_transparent后缀
                        base_name = os.path.splitext(os.path.basename(image_path))[0]
                        # 移除URL参数（如果有）
                        base_name = base_name.split('?')[0]
                        # 添加_transparent后缀
                        base_name = f"{base_name}_transparent"
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        output_path = os.path.join(base_dir, f"{base_name}_{timestamp}.png")
                else:
                    # 使用时间戳
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_path = os.path.join(base_dir, f"removed_bg_{timestamp}.png")
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存处理后的图片
            with open(output_path, 'wb') as f:
                f.write(output_bytes)
            
            print(f"[背景去除] 背景去除完成，保存到: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"[错误] 背景去除失败: {e}")
            import traceback
            print(traceback.format_exc())
            return None
    
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
            '纯白背景',
            '白色背景',
            'PNG格式'
        ]
        prompt_parts.extend(quality_parts)
        
        # 组合成完整的prompt（用逗号分隔，自然流畅的描述性文本）
        prompt = '，'.join(prompt_parts)
        
        # 不再在prompt中添加组图指令，改为通过多次API调用来生成组图
        
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
            专业的中文场景图片生成prompt（格式：生成一个XXX场景图片 二次元写实画风 图中无人物）
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
        
        # 构建场景描述（优先使用场景名称，如果没有则使用场景描述）
        scene_desc = scene_name if scene_name else (scene_description if scene_description else scene_id)
        
        # 构建完整的prompt（按照用户要求的格式）
        prompt = f"生成一个{scene_desc}场景图片"
        
        # 添加时间和天气信息（如果有）
        additional_info = []
        if time_of_day:
            additional_info.append(time_of_day)
        if weather:
            additional_info.append(weather)
        if atmosphere:
            additional_info.append(f"氛围{atmosphere}")
        
        if additional_info:
            prompt += f"，{''.join(additional_info)}"
        
        # 添加固定的风格和要求
        prompt += "，二次元写实画风，图中无人物"
        
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
            prompt: 图片生成prompt（基础prompt，会根据组图需求添加变体）
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
                print(f"[AI生图] 将调用 {group_count} 次API生成 {group_count} 张不同变体的图片")
            else:
                print(f"[AI生图] 正在使用火山引擎Seedream生成角色图片 (角色ID: {character_id}, 比例: 9:16, 无水印)")
            print(f"[AI生图] 基础Prompt: {prompt[:100]}...")
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {config.VOLCENGINE_ARK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # 人物图片使用9:16竖屏比例（适合人物立绘）
            # 火山引擎API要求格式：'WIDTHxHEIGHT'（如 '1440x2560'）或 '1k'、'2k'、'4k'
            # 最小像素要求：3,686,400 像素（1440x2560 = 3,686,400，正好满足要求）
            # 使用 1440x2560 分辨率（9:16比例，2K质量）
            character_image_size = "1440x2560"  # 9:16竖屏比例，2K分辨率（满足最小像素要求）
            
            # 如果生成组图，循环调用API生成多张不同变体的图片
            if generate_group and group_count > 1:
                image_urls = []
                
                # 定义每张图片的变体描述（让3张图片有差异）
                variant_descriptions = [
                    "正面全身像，微笑表情，自然站立姿势",
                    "正面全身像，温和表情，优雅姿态",
                    "正面半身像，自信表情，手部动作"
                ]
                
                # 如果组图数量超过预定义的变体数量，循环使用
                for i in range(group_count):
                    variant_idx = i % len(variant_descriptions)
                    variant_desc = variant_descriptions[variant_idx]
                    
                    # 为每张图片构建独特的prompt
                    variant_prompt = f"{prompt}，{variant_desc}"
                    
                    print(f"[AI生图] 正在生成第 {i + 1}/{group_count} 张图片...")
                    print(f"[AI生图] 变体Prompt: {variant_prompt[:120]}...")
                    
                    # 构建请求体
                    payload = {
                        "model": config.VOLCENGINE_IMAGE_MODEL,
                        "prompt": variant_prompt,
                        "size": character_image_size,
                        "response_format": "url",
                        "watermark": False,  # 不带水印（用户要求）
                        "stream": False  # 非流式输出
                    }
                    
                    # 发送请求
                    response = requests.post(
                        self.volcengine_api_url,
                        headers=headers,
                        json=payload,
                        timeout=120  # 单张图片生成超时时间
                    )
                    
                    # 检查HTTP状态码
                    if response.status_code != 200:
                        print(f"[警告] 第 {i + 1} 张图片生成失败: HTTP {response.status_code}")
                        print(f"[警告] 响应内容: {response.text[:200]}")
                        continue  # 继续生成下一张
                    
                    # 解析响应
                    resp_data = response.json()
                    
                    # 检查是否有错误
                    if 'error' in resp_data:
                        error_info = resp_data['error']
                        error_msg = error_info.get('message', '未知错误')
                        print(f"[警告] 第 {i + 1} 张图片生成失败: {error_msg}")
                        continue  # 继续生成下一张
                    
                    # 提取图片URL
                    if 'data' in resp_data and len(resp_data['data']) > 0:
                        image_data = resp_data['data'][0]  # 每次调用只生成一张图片
                        image_url = image_data.get('url')
                        if image_url:
                            image_urls.append(image_url)
                            print(f"[AI生图] 第 {i + 1} 张图片生成成功: {image_url}")
                            
                            # 保存图片到本地（如果启用）
                            if config.IMAGE_SAVE_ENABLED and character_id:
                                local_path = self._save_image_to_local(
                                    image_url, character_id, user_id, image_type,
                                    image_index=i + 1  # 图片索引（1, 2, 3）
                                )
                                if local_path:
                                    print(f"[AI生图] 第 {i + 1} 张图片已保存到本地: {local_path}")
                        else:
                            print(f"[警告] 第 {i + 1} 张图片响应中未找到URL")
                    else:
                        print(f"[警告] 第 {i + 1} 张图片响应中未找到data字段")
                
                # 检查是否成功生成了至少一张图片
                if image_urls:
                    print(f"[AI生图] 组图生成完成: 成功生成 {len(image_urls)}/{group_count} 张图片")
                    return image_urls
                else:
                    print(f"[警告] 组图生成失败: 未能生成任何图片")
                    return None
            else:
                # 单张图片生成（原有逻辑）
                payload = {
                    "model": config.VOLCENGINE_IMAGE_MODEL,
                    "prompt": prompt,
                    "size": character_image_size,
                    "response_format": "url",
                    "watermark": False,
                    "stream": False
                }
                
                # 发送请求
                response = requests.post(
                    self.volcengine_api_url,
                    headers=headers,
                    json=payload,
                    timeout=120
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
                
                # 提取图片URL
                if 'data' in resp_data and len(resp_data['data']) > 0:
                    image_data = resp_data['data'][0]
                    image_url = image_data.get('url')
                    if image_url:
                        print(f"[AI生图] 图片生成成功: {image_url}")
                        
                        # 保存图片到本地（如果启用）
                        if config.IMAGE_SAVE_ENABLED and character_id:
                            local_path = self._save_image_to_local(
                                image_url, character_id, user_id, image_type
                            )
                            if local_path:
                                print(f"[AI生图] 图片已保存到本地: {local_path}")
                        
                        return [image_url]
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
            # 场景图片使用16:9比例（2560x1440，满足最小像素要求 3,686,400）
            # 1920x1080 = 2,073,600 像素（不满足要求）
            # 2560x1440 = 3,686,400 像素（正好满足最小要求，16:9比例）
            scene_image_size = "2560x1440"  # 16:9 比例，2K分辨率
            
            payload = {
                "model": config.VOLCENGINE_IMAGE_MODEL,
                "prompt": prompt,
                "size": scene_image_size,  # 场景图片固定为16:9，2K分辨率
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
            
            # 场景图片使用16:9比例（1920x1080）
            scene_image_size = '1920*1080'  # 16:9 比例
            
            response = ImageSynthesis.call(
                model='wanx-v1',  # 通义万相模型
                prompt=prompt,
                n=1,  # 生成1张图片
                size=scene_image_size  # 场景图片固定为16:9
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
            # 人物图片固定使用PNG格式，场景图片保持原格式
            if character_id is not None:
                # 人物图片：固定使用PNG格式
                ext = '.png'
                print(f"[图片保存] 人物图片固定使用PNG格式")
            else:
                # 场景图片：根据Content-Type或URL推断
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
            # 如果是人物图片且需要转换为PNG，使用PIL进行转换
            if character_id is not None and ext == '.png':
                # 检查下载的图片是否已经是PNG格式
                content_type = img_response.headers.get('Content-Type', '')
                is_png = 'png' in content_type or image_url.lower().endswith('.png')
                
                if is_png:
                    # 如果已经是PNG，直接保存
                    with open(filepath, 'wb') as f:
                        f.write(img_response.content)
                else:
                    # 如果不是PNG，使用PIL转换为PNG
                    if PIL_AVAILABLE:
                        try:
                            from io import BytesIO
                            # 从响应内容创建PIL Image对象
                            img = Image.open(BytesIO(img_response.content))
                            
                            # 人物图片使用纯白背景，保存为PNG格式
                            # 保持原始模式（RGB或RGBA），PNG格式支持两种模式
                            # 合成时会自动去除白色背景
                            if img.mode == 'RGBA':
                                # 如果已经是RGBA，直接保存
                                img.save(filepath, 'PNG')
                            else:
                                # RGB模式，直接保存为PNG（PNG支持RGB模式）
                                # 纯白背景会在合成时被去除
                                img.save(filepath, 'PNG')
                            
                            print(f"[图片保存] 已将图片转换为PNG格式（纯白背景）: {filepath}")
                        except Exception as e:
                            print(f"[警告] 图片格式转换失败，使用原始格式保存: {e}")
                            # 转换失败，直接保存原始内容
                            with open(filepath, 'wb') as f:
                                f.write(img_response.content)
                    else:
                        # PIL不可用，直接保存原始内容（但文件名仍然是.png）
                        print(f"[警告] Pillow未安装，无法转换图片格式，直接保存原始内容")
                        with open(filepath, 'wb') as f:
                            f.write(img_response.content)
            else:
                # 场景图片或其他情况，直接保存
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
    
    def composite_scene_with_character(self, scene_image_path: str, character_image_path: str,
                                       character_id: Optional[int] = None, scene_id: Optional[str] = None,
                                       user_id: Optional[str] = None) -> Optional[str]:
        """将场景图和人物图合成（场景图作为背景，人物图叠加在上方）
        
        Args:
            scene_image_path: 场景图片本地路径或URL
            character_image_path: 人物图片本地路径或URL（纯白背景，合成时会自动去除）
            character_id: 角色ID（用于文件命名）
            scene_id: 场景ID（用于文件命名）
            user_id: 玩家ID（用于文件命名）
            
        Returns:
            合成后的图片本地路径，如果失败返回None
        """
        if not PIL_AVAILABLE:
            print("[警告] Pillow未安装，无法进行图片合成")
            return None
        
        try:
            # 处理玩家ID
            if not user_id:
                user_id = 'UNKNOWN'
            safe_user_id = re.sub(r'[<>:"/\\|?*\s]', '_', user_id)[:20]
            
            # 下载或读取场景图片
            scene_img = None
            if scene_image_path.startswith('http://') or scene_image_path.startswith('https://'):
                # 从URL下载
                scene_response = requests.get(scene_image_path, timeout=30)
                if scene_response.status_code == 200:
                    from io import BytesIO
                    scene_img = Image.open(BytesIO(scene_response.content))
                else:
                    print(f"[警告] 下载场景图片失败: HTTP {scene_response.status_code}")
                    return None
            else:
                # 本地文件路径
                if os.path.exists(scene_image_path):
                    scene_img = Image.open(scene_image_path)
                else:
                    print(f"[警告] 场景图片文件不存在: {scene_image_path}")
                    return None
            
            # 下载或读取人物图片
            character_img = None
            if character_image_path.startswith('http://') or character_image_path.startswith('https://'):
                # 从URL下载
                char_response = requests.get(character_image_path, timeout=30)
                if char_response.status_code == 200:
                    from io import BytesIO
                    character_img = Image.open(BytesIO(char_response.content))
                else:
                    print(f"[警告] 下载人物图片失败: HTTP {char_response.status_code}")
                    return None
            elif character_image_path.startswith('/static/'):
                # 静态文件URL路径，转换为实际文件系统路径
                # 例如：/static/images/characters/filename.png -> backend/images/characters/filename.png
                filename = os.path.basename(character_image_path)
                if '/images/characters/' in character_image_path:
                    # 角色图片
                    if os.path.isabs(config.IMAGE_SAVE_DIR):
                        actual_path = os.path.join(config.IMAGE_SAVE_DIR, filename)
                    else:
                        actual_path = os.path.join(backend_dir, config.IMAGE_SAVE_DIR, filename)
                elif '/images/scenes/' in character_image_path:
                    # 场景图片
                    if os.path.isabs(config.SCENE_IMAGE_SAVE_DIR):
                        actual_path = os.path.join(config.SCENE_IMAGE_SAVE_DIR, filename)
                    else:
                        actual_path = os.path.join(backend_dir, config.SCENE_IMAGE_SAVE_DIR, filename)
                else:
                    actual_path = None
                
                if actual_path and os.path.exists(actual_path):
                    character_img = Image.open(actual_path)
                    print(f"[图片合成] 从静态文件路径转换为实际路径: {character_image_path} -> {actual_path}")
                else:
                    print(f"[警告] 人物图片文件不存在: {character_image_path} (实际路径: {actual_path})")
                    return None
            else:
                # 本地文件路径
                if os.path.exists(character_image_path):
                    character_img = Image.open(character_image_path)
                else:
                    print(f"[警告] 人物图片文件不存在: {character_image_path}")
                    return None
            
            # 确保人物图片有透明通道（RGBA模式）
            if character_img.mode != 'RGBA':
                character_img = character_img.convert('RGBA')
            
            # 去除纯白背景：将纯白色像素转换为透明
            # 注意：人物图片现在使用纯白背景，合成时需要去除白色背景以便叠加到场景上
            if character_img.mode == 'RGBA':
                # 获取图片数据
                data = character_img.getdata()
                new_data = []
                
                # 阈值：RGB值都大于等于245的像素视为纯白背景（更精确的阈值）
                # 这样可以更准确地识别纯白色背景，避免误删人物边缘的浅色像素
                threshold = 245
                
                white_pixel_count = 0
                total_pixel_count = len(data)
                
                for item in data:
                    # 如果像素是纯白色或接近纯白色，设置为透明
                    if item[0] >= threshold and item[1] >= threshold and item[2] >= threshold:
                        new_data.append((255, 255, 255, 0))  # 透明
                        white_pixel_count += 1
                    else:
                        new_data.append(item)
                
                character_img.putdata(new_data)
                white_percentage = (white_pixel_count / total_pixel_count * 100) if total_pixel_count > 0 else 0
                print(f"[图片合成] 已去除白色背景: {white_pixel_count}/{total_pixel_count} 像素 ({white_percentage:.1f}%)")
            
            # 确保场景图片是RGB模式（合成后转换为RGBA）
            if scene_img.mode != 'RGB':
                scene_img = scene_img.convert('RGB')
            
            # 场景图尺寸（16:9，1920x1080）
            scene_width, scene_height = scene_img.size
            print(f"[图片合成] 场景图尺寸: {scene_width}x{scene_height}")
            
            # 调整人物图片大小（保持宽高比，高度约为场景高度的80-85%）
            # 放大人物，让人物在场景中更加突出
            target_character_height = int(scene_height * 0.85)
            char_width, char_height = character_img.size
            aspect_ratio = char_width / char_height
            target_character_width = int(target_character_height * aspect_ratio)
            
            # 如果人物宽度超过场景宽度，按宽度缩放
            if target_character_width > scene_width * 0.9:
                target_character_width = int(scene_width * 0.9)
                target_character_height = int(target_character_width / aspect_ratio)
            
            print(f"[图片合成] 人物图原始尺寸: {char_width}x{char_height}")
            print(f"[图片合成] 人物图调整后尺寸: {target_character_width}x{target_character_height}")
            
            # 调整人物图片大小（使用高质量重采样）
            character_img_resized = character_img.resize(
                (target_character_width, target_character_height),
                Image.Resampling.LANCZOS
            )
            
            # 创建合成画布（使用场景图作为背景）
            composite = Image.new('RGBA', (scene_width, scene_height))
            composite.paste(scene_img, (0, 0))
            
            # 计算人物图片在场景中的位置（完全居中）
            # 水平居中
            char_x = (scene_width - target_character_width) // 2
            # 垂直居中
            char_y = (scene_height - target_character_height) // 2
            
            print(f"[图片合成] 人物图位置: ({char_x}, {char_y})")
            
            # 将人物图片叠加到场景图上（使用alpha通道进行透明合成）
            # 第三个参数是mask，使用图片本身的alpha通道
            composite.paste(character_img_resized, (char_x, char_y), character_img_resized)
            
            # 转换为RGB模式（保存为JPEG格式）
            composite_rgb = composite.convert('RGB')
            
            # 创建保存目录
            if os.path.isabs(config.COMPOSITE_IMAGE_SAVE_DIR):
                save_dir = config.COMPOSITE_IMAGE_SAVE_DIR
            else:
                save_dir = os.path.join(backend_dir, config.COMPOSITE_IMAGE_SAVE_DIR)
            os.makedirs(save_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_scene_id = re.sub(r'[<>:"/\\|?*\s]', '_', scene_id or 'unknown')[:30]
            safe_character_id = f"{character_id:04d}" if character_id else "0000"
            
            filename = f"{safe_user_id}_{safe_character_id}_SCENE_{safe_scene_id}_composite_v1_{timestamp}.jpg"
            filepath = os.path.join(save_dir, filename)
            
            # 保存合成图片（JPEG格式，高质量）
            composite_rgb.save(filepath, 'JPEG', quality=95)
            
            print(f"[图片合成] 合成图片已保存: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"[错误] 图片合成失败: {e}")
            import traceback
            print(traceback.format_exc())
            return None
    
    def delete_unselected_character_images(self, character_id: int, image_urls: List[str], 
                                           selected_index: int) -> int:
        """删除未选中的角色图片
        
        Args:
            character_id: 角色ID
            image_urls: 所有图片URL列表（3张图片的URL）
            selected_index: 选中的图片索引（0, 1, 2）
            
        Returns:
            删除的图片数量
        """
        deleted_count = 0
        try:
            import config
            
            # 获取保存目录
            if os.path.isabs(config.IMAGE_SAVE_DIR):
                save_dir = config.IMAGE_SAVE_DIR
            else:
                save_dir = os.path.join(backend_dir, config.IMAGE_SAVE_DIR)
            
            if not os.path.exists(save_dir):
                return 0
            
            # 从URL中提取文件名（去除路径和参数）
            selected_url = image_urls[selected_index] if selected_index < len(image_urls) else None
            
            # 构建选中图片的文件名（从URL中提取）
            selected_filename = None
            if selected_url:
                # 从URL中提取文件名（可能是完整URL或相对路径）
                if '/static/images/characters/' in selected_url:
                    selected_filename = selected_url.split('/static/images/characters/')[-1].split('?')[0]
                elif '/characters/' in selected_url:
                    selected_filename = selected_url.split('/characters/')[-1].split('?')[0]
                else:
                    # 尝试从URL中提取文件名
                    selected_filename = os.path.basename(selected_url).split('?')[0]
            
            # 查找该角色的所有图片文件（包含_img索引的组图）
            character_id_str = f"{character_id:04d}"
            pattern = re.compile(rf"^[^_]+_{re.escape(character_id_str)}_[^_]+_portrait_img\d+_v\d+_\d{{8}}_\d{{6}}\.(png|jpg|jpeg|webp)$", re.IGNORECASE)
            
            for filename in os.listdir(save_dir):
                if pattern.match(filename):
                    filepath = os.path.join(save_dir, filename)
                    
                    # 检查是否是选中的图片
                    is_selected = False
                    if selected_filename:
                        # 通过文件名匹配（忽略时间戳和版本号，只匹配基础部分）
                        # 提取基础部分：{user_id}_{character_id}_{name}_portrait_img{index}
                        base_match = re.match(rf"^([^_]+_{re.escape(character_id_str)}_[^_]+_portrait_img\d+)_", filename)
                        if base_match:
                            base_part = base_match.group(1)
                            # 检查选中图片是否包含相同的基础部分
                            if base_part in selected_filename or selected_filename.startswith(base_part.split('_img')[0]):
                                # 进一步检查索引是否匹配
                                img_match = re.search(r'_img(\d+)', filename)
                                selected_img_match = re.search(r'_img(\d+)', selected_filename) if selected_filename else None
                                if img_match and selected_img_match:
                                    img_index = int(img_match.group(1)) - 1  # img1 -> index 0
                                    selected_img_index = int(selected_img_match.group(1)) - 1
                                    if img_index == selected_index and selected_img_index == selected_index:
                                        is_selected = True
                                elif filename == selected_filename:
                                    is_selected = True
                    
                    # 如果文件名包含_img，且不是选中的，则删除
                    if not is_selected and '_img' in filename:
                        try:
                            os.remove(filepath)
                            deleted_count += 1
                            print(f"[图片清理] 已删除未选中的图片: {filename}")
                        except Exception as e:
                            print(f"[警告] 删除图片失败 {filename}: {e}")
            
            return deleted_count
        except Exception as e:
            print(f"[错误] 删除未选中图片失败: {e}")
            import traceback
            print(traceback.format_exc())
            return deleted_count
    
    def get_latest_character_image_path(self, character_id: int) -> Optional[str]:
        """获取角色最新的图片本地路径
        
        Args:
            character_id: 角色ID
            
        Returns:
            最新图片的本地路径，如果不存在返回None
        """
        try:
            import config
            
            # 获取保存目录
            if os.path.isabs(config.IMAGE_SAVE_DIR):
                save_dir = config.IMAGE_SAVE_DIR
            else:
                save_dir = os.path.join(backend_dir, config.IMAGE_SAVE_DIR)
            
            if not os.path.exists(save_dir):
                return None
            
            # 构建匹配模式（人物图片现在固定为PNG格式，但兼容旧格式）
            character_id_str = f"{character_id:04d}"
            pattern = re.compile(rf"^[^_]+_{re.escape(character_id_str)}_[^_]+_portrait(?:_img\d+)?_v\d+_\d{{8}}_\d{{6}}\.(png|jpg|jpeg|webp)$", re.IGNORECASE)
            
            # 查找匹配的文件
            matching_files = []
            for filename in os.listdir(save_dir):
                if pattern.match(filename):
                    filepath = os.path.join(save_dir, filename)
                    matching_files.append((filepath, os.path.getmtime(filepath)))
            
            if not matching_files:
                return None
            
            # 按修改时间排序，返回最新的
            matching_files.sort(key=lambda x: x[1], reverse=True)
            return matching_files[0][0]
            
        except Exception as e:
            print(f"[警告] 获取角色图片路径失败: {e}")
            return None
    
    def get_latest_scene_image_path(self, scene_id: str) -> Optional[str]:
        """获取场景最新的图片本地路径
        
        Args:
            scene_id: 场景ID
            
        Returns:
            最新图片的本地路径，如果不存在返回None
        """
        try:
            import config
            
            # 获取保存目录
            if os.path.isabs(config.SCENE_IMAGE_SAVE_DIR):
                save_dir = config.SCENE_IMAGE_SAVE_DIR
            else:
                save_dir = os.path.join(backend_dir, config.SCENE_IMAGE_SAVE_DIR)
            
            if not os.path.exists(save_dir):
                return None
            
            # 构建匹配模式（支持多种命名格式）
            safe_scene_id = re.sub(r'[<>:"/\\|?*\s]', '_', scene_id)[:30]
            patterns = [
                re.compile(rf"^[^_]+_SCENE_{re.escape(safe_scene_id)}_[^_]+_scene_v\d+_\d{{8}}_\d{{6}}\.(jpg|jpeg|png|webp)$", re.IGNORECASE),
                re.compile(rf"^{re.escape(safe_scene_id)}_[^_]+\.(jpg|jpeg|png|webp)$", re.IGNORECASE),
                re.compile(rf"^{re.escape(safe_scene_id)}\.(jpg|jpeg|png|webp)$", re.IGNORECASE),
            ]
            
            # 查找匹配的文件
            matching_files = []
            for filename in os.listdir(save_dir):
                for pattern in patterns:
                    if pattern.match(filename):
                        filepath = os.path.join(save_dir, filename)
                        matching_files.append((filepath, os.path.getmtime(filepath)))
                        break
            
            if not matching_files:
                return None
            
            # 按修改时间排序，返回最新的
            matching_files.sort(key=lambda x: x[1], reverse=True)
            return matching_files[0][0]
            
        except Exception as e:
            print(f"[警告] 获取场景图片路径失败: {e}")
            return None
    
