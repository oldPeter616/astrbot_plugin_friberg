from utils import load_config, save_to_json
from scraper import HLTVScraper
import sys

def main():
    """
    程序主函数
    """
    print("🚀 CS选手信息搜索程序启动...")
    try:
        config = load_config()
    except FileNotFoundError:
        print("❌ 错误: 配置文件 'config.txt' 未找到。请确保该文件存在于同一目录下。")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: 加载配置文件时发生未知错误: {e}")
        sys.exit(1)

    scraper = HLTVScraper(config)
    
    try:
        all_players = scraper.fetch_all_players()
        
        if not all_players:
            print("\n⚠️ 未找到任何符合条件的选手数据。可能是HLTV网站结构已变更或网络问题。")
        else:
            save_to_json(all_players, config.get('OUTPUT_FILENAME', 'players.json'))

    except Exception as e:
        print(f"\n❌ 程序运行时发生严重错误: {e}")
        print("   这可能是由于网络中断或HLTV网站结构发生重大变化。")

    print("\n👋 程序运行结束。")


if __name__ == '__main__':
    main()