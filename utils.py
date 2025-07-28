import json
from typing import Dict, List, Any
from data_models import Player

def load_config(path: str = 'config.txt') -> Dict[str, Any]:
    """
    从.txt文件加载配置。
    文件格式应为 KEY=VALUE，支持#注释。
    """
    config = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # 尝试将纯数字的字符串转换为整数
                if value.isdigit():
                    config[key] = int(value)
                else:
                    config[key] = value
    return config

def get_continent_from_nationality(nationality: str) -> str:
    """
    根据国籍映射到大洲。
    """
    # 这个映射可以根据需要持续扩充
    mapping = {
        # 欧洲
        'Denmark': 'Europe', 'France': 'Europe', 'Russia': 'Europe', 'Sweden': 'Europe',
        'Ukraine': 'Europe', 'Poland': 'Europe', 'Germany': 'Europe', 'Finland': 'Europe',
        'Norway': 'Europe', 'Bosnia and Herzegovina': 'Europe', 'Netherlands': 'Europe',
        'Belgium': 'Europe', 'Slovakia': 'Europe', 'Spain': 'Europe', 'Portugal': 'Europe',
        'United Kingdom': 'Europe', 'North Macedonia': 'Europe', 'Romania': 'Europe', 'Hungary': 'Europe',
        'Latvia': 'Europe', 'Lithuania': 'Europe', 'Estonia': 'Europe', 'Bulgaria': 'Europe',
        # 亚洲
        'China': 'Asia', 'Mongolia': 'Asia', 'Israel': 'Asia', 'Jordan': 'Asia', 'Kazakhstan': 'Asia',
        # 北美
        'Canada': 'North America', 'United States': 'North America',
        # 南美
        'Brazil': 'South America',
        # 大洋洲
        'Australia': 'Oceania'
    }
    return mapping.get(nationality, 'Unknown')

def save_to_json(players: List[Player], path: str) -> None:
    """
    将选手列表保存为格式化的JSON文件。
    """
    # 将Player对象列表转换为字典列表
    players_dicts = [player.__dict__ for player in players]
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(players_dicts, f, ensure_ascii=False, indent=4)
    print(f"\n✅ 数据成功保存到文件: {path}")