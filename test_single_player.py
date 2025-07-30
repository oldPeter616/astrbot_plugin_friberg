# test_single_player.py (Version 2)

"""
测试脚本：用于单独测试对 Liquipedia 上指定 CS 选手的页面解析功能。

本脚本会从 `get_cs_players.py` 中导入核心的解析函数 `parse_player_info`，
并通过API搜索功能自动处理用户输入的大小写问题，实现精准测试。

用法:
    python test_single_player.py <player_id>

示例:
    python test_single_player.py dupreeh
    python test_single_player.py s1mple
"""

import sys
import json
import requests

# 尝试从主脚本导入必要的函数和常量
# (新增了 API_URL 的导入)
try:
    from get_cs_players import parse_player_info, HEADERS, API_URL
except ImportError:
    print("错误: 无法导入 'get_cs_players.py'。")
    print("请确保本脚本与 `get_cs_players.py` 存放在同一目录下。")
    sys.exit(1)

def test_player(player_id: str) -> None:
    """
    对指定的选手ID执行解析测试。
    新增了API搜索步骤来获取官方的、大小写正确的页面标题。

    Args:
        player_id: 要测试的选手页面ID (例如 'dupreeh', 's1mple')。
    """
    print(f"[*] 接收到测试ID: '{player_id}'")

    # 初始化 requests session
    session = requests.Session()
    session.headers.update(HEADERS)

    # --- 新增步骤: 使用API搜索来获取规范的页面标题 ---
    print("[*] 正在通过API搜索规范的页面标题...")
    search_params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": player_id
    }
    try:
        response = session.get(API_URL, params=search_params)
        response.raise_for_status()
        search_data = response.json()
        
        search_results = search_data.get("query", {}).get("search", [])
        if not search_results:
            print(f"[!] API搜索失败: 未找到与 '{player_id}' 相关的任何选手页面。")
            return
        
        # 采用第一个搜索结果作为最可能的正确标题
        correct_title = search_results[0]['title']
        print(f"[+] 成功找到标准标题: '{correct_title}'")

    except requests.exceptions.RequestException as e:
        print(f"[!] API搜索请求时发生网络错误: {e}")
        return
    except json.JSONDecodeError:
        print("[!] API搜索响应无法解析为JSON。")
        return

    # --- 使用获取到的正确标题进行解析 ---
    player_data = parse_player_info(session, correct_title)

    print("-" * 30)
    if player_data:
        print(f"[+] 成功解析页面 '{correct_title}'！选手信息如下:")
        formatted_json = json.dumps(player_data, indent=2, ensure_ascii=False)
        print(formatted_json)
    else:
        print(f"[!] 解析失败。")
        print(f"未能从页面 '{correct_title}' 提取有效的选手信息框。")
    print("-" * 30)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法错误！", __doc__)
        sys.exit(1)
    
    target_player_id = sys.argv[1]
    test_player(target_player_id)