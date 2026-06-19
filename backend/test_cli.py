"""CLI 测试脚本 - 纯文本模式测试系统联通性"""
import os
import sys

# 禁用图片生成
os.environ['IMAGE_SAVE_ENABLED'] = 'false'

from game.story_engine import _get_text_gen
from api.services.game_service import GameService
from api.services.character_service import CharacterService

def test_system():
    """测试系统联通性"""
    print("=" * 60)
    print("NoEndStory 系统联通性测试（纯文本模式）")
    print("=" * 60)

    # 1. 测试 LLM 服务
    print("\n[1/4] 测试 LLM 文本生成服务...")
    try:
        text_gen = _get_text_gen()
        if text_gen and text_gen.enabled:
            print(f"  [OK] LLM 服务已启用")
            print(f"  提供商: {text_gen.llm_service.get_provider()}")
            print(f"  模型: {text_gen.llm_service.get_model()}")
        else:
            print("  [FAIL] LLM 服务未启用")
            return False
    except Exception as e:
        print(f"  [FAIL] LLM 服务初始化失败: {e}")
        return False

    # 2. 测试角色创建
    print("\n[2/4] 测试角色创建...")
    try:
        character_service = CharacterService()
        request_data = {
            'name': '测试角色',
            'gender': 'female',
            'appearance': {'keywords': ['二次元', '可爱']},
            'personality': {'keywords': ['温柔']},
            'background': {'style': 'fantasy'}
        }
        character_id = character_service.create_character(request_data)
        print(f"  [OK] 角色创建成功: ID={character_id}")
    except Exception as e:
        print(f"  [FAIL] 角色创建失败: {e}")
        return False

    # 3. 测试游戏服务初始化
    print("\n[3/4] 测试游戏服务...")
    try:
        game_service = GameService()
        print(f"  [OK] 游戏服务初始化成功")
    except Exception as e:
        print(f"  [FAIL] 游戏服务初始化失败: {e}")
        return False

    # 4. 测试故事初始化
    print("\n[4/4] 测试故事初始化...")
    try:
        import asyncio

        thread_id = f"test-cli-{os.getpid()}"
        result = asyncio.get_event_loop().run_until_complete(
            game_service.initialize_story(thread_id, character_id, 'school')
        )

        if result and 'character_dialogue' in result:
            print(f"  [OK] 故事初始化成功")
            print(f"  场景: {result.get('scene', 'unknown')}")
            print(f"  对话: {result.get('character_dialogue', '')[:50]}...")
            print(f"  选项数: {len(result.get('player_options', []))}")
        else:
            print(f"  [FAIL] 故事初始化返回异常: {result}")
            return False
    except Exception as e:
        print(f"  [FAIL] 故事初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("[OK] 所有测试通过！系统联通性正常。")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_system()
    sys.exit(0 if success else 1)
