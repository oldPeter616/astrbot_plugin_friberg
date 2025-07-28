# playerinfosearch.py (同步模式)

from utils import load_config, save_to_json
from scraper import LiquipediaScraper # 名字已更新
import sys
from pathlib import Path

def main():
    """
    程序主函数 (同步版本)
    """
    print("🚀 CS选手信息搜索程序启动 (Liquipedia源)...")
    config = {}
    try:
        script_dir = Path(__file__).resolve().parent
        config_path = script_dir / 'config.txt'
        config = load_config(str(config_path))
    except Exception as e:
        print(f"❌ 错误: 加载配置文件失败: {e}")
        sys.exit(1)

    scraper = LiquipediaScraper(config)
    
    try:
        all_players = scraper.fetch_all_players()
        
        if not all_players:
            print("\n⚠️ 未找到任何符合条件的选手数据。")
        else:
            output_filename = config.get('OUTPUT_FILENAME', 'players.json')
            output_path = script_dir / output_filename
            save_to_json(all_players, str(output_path))

    except Exception as e:
        print(f"\n❌ 程序运行时发生严重错误: {e}")

    print("\n👋 程序运行结束。")

if __name__ == '__main__':
    main()