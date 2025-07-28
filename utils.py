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
    # 对于跨大陆国家，如俄罗斯和土耳其，根据其在CS领域的归属习惯划分为欧洲
    mapping = {
        # --- 欧洲 (Europe) ---
        'Albania': 'Europe', 'Andorra': 'Europe', 'Armenia': 'Europe', 'Austria': 'Europe',
        'Belarus': 'Europe', 'Belgium': 'Europe', 'Bosnia and Herzegovina': 'Europe',
        'Bulgaria': 'Europe', 'Croatia': 'Europe', 'Cyprus': 'Europe', 'Czech Republic': 'Europe',
        'Denmark': 'Europe', 'Estonia': 'Europe', 'Finland': 'Europe', 'France': 'Europe',
        'Georgia': 'Europe', 'Germany': 'Europe', 'Greece': 'Europe', 'Hungary': 'Europe',
        'Iceland': 'Europe', 'Ireland': 'Europe', 'Italy': 'Europe', 'Kosovo': 'Europe',
        'Latvia': 'Europe', 'Liechtenstein': 'Europe', 'Lithuania': 'Europe', 'Luxembourg': 'Europe',
        'Malta': 'Europe', 'Moldova': 'Europe', 'Monaco': 'Europe', 'Montenegro': 'Europe',
        'Netherlands': 'Europe', 'North Macedonia': 'Europe', 'Norway': 'Europe', 'Poland': 'Europe',
        'Portugal': 'Europe', 'Romania': 'Europe', 'Russia': 'Europe', 'San Marino': 'Europe',
        'Serbia': 'Europe', 'Slovakia': 'Europe', 'Slovenia': 'Europe', 'Spain': 'Europe',
        'Sweden': 'Europe', 'Switzerland': 'Europe', 'Turkey': 'Europe', 'Ukraine': 'Europe',
        'United Kingdom': 'Europe', 'Vatican City': 'Europe',

        # --- 亚洲 (Asia) ---
        'Afghanistan': 'Asia', 'Bahrain': 'Asia', 'Bangladesh': 'Asia', 'Bhutan': 'Asia',
        'Brunei': 'Asia', 'Cambodia': 'Asia', 'China': 'Asia', 'Hong Kong': 'Asia',
        'India': 'Asia', 'Indonesia': 'Asia', 'Iran': 'Asia', 'Iraq': 'Asia',
        'Israel': 'Asia', 'Japan': 'Asia', 'Jordan': 'Asia', 'Kazakhstan': 'Asia',
        'Kuwait': 'Asia', 'Kyrgyzstan': 'Asia', 'Laos': 'Asia', 'Lebanon': 'Asia',
        'Macau': 'Asia', 'Malaysia': 'Asia', 'Maldives': 'Asia', 'Mongolia': 'Asia',
        'Myanmar': 'Asia', 'Nepal': 'Asia', 'North Korea': 'Asia', 'Oman': 'Asia',
        'Pakistan': 'Asia', 'Palestine': 'Asia', 'Philippines': 'Asia', 'Qatar': 'Asia',
        'Saudi Arabia': 'Asia', 'Singapore': 'Asia', 'South Korea': 'Asia', 'Sri Lanka': 'Asia',
        'Syria': 'Asia', 'Taiwan': 'Asia', 'Tajikistan': 'Asia', 'Thailand': 'Asia',
        'Turkmenistan': 'Asia', 'United Arab Emirates': 'Asia', 'Uzbekistan': 'Asia', 'Vietnam': 'Asia',
        'Yemen': 'Asia',

        # --- 北美洲 (North America) ---
        'Antigua and Barbuda': 'North America', 'Bahamas': 'North America', 'Barbados': 'North America',
        'Belize': 'North America', 'Canada': 'North America', 'Costa Rica': 'North America',
        'Cuba': 'North America', 'Dominica': 'North America', 'Dominican Republic': 'North America',
        'El Salvador': 'North America', 'Grenada': 'North America', 'Guatemala': 'North America',
        'Haiti': 'North America', 'Honduras': 'North America', 'Jamaica': 'North America',
        'Mexico': 'North America', 'Nicaragua': 'North America', 'Panama': 'North America',
        'Saint Kitts and Nevis': 'North America', 'Saint Lucia': 'North America',
        'Saint Vincent and the Grenadines': 'North America', 'Trinidad and Tobago': 'North America',
        'United States': 'North America',

        # --- 南美洲 (South America) ---
        'Argentina': 'South America', 'Bolivia': 'South America', 'Brazil': 'South America',
        'Chile': 'South America', 'Colombia': 'South America', 'Ecuador': 'South America',
        'Guyana': 'South America', 'Paraguay': 'South America', 'Peru': 'South America',
        'Suriname': 'South America', 'Uruguay': 'South America', 'Venezuela': 'South America',

        # --- 非洲 (Africa) ---
        'Algeria': 'Africa', 'Angola': 'Africa', 'Benin': 'Africa', 'Botswana': 'Africa',
        'Burkina Faso': 'Africa', 'Burundi': 'Africa', 'Cabo Verde': 'Africa', 'Cameroon': 'Africa',
        'Central African Republic': 'Africa', 'Chad': 'Africa', 'Comoros': 'Africa',
        'Congo, Republic of the': 'Africa', 'Congo, Democratic Republic of the': 'Africa',
        'Djibouti': 'Africa', 'Egypt': 'Africa', 'Equatorial Guinea': 'Africa', 'Eritrea': 'Africa',
        'Eswatini': 'Africa', 'Ethiopia': 'Africa', 'Gabon': 'Africa', 'Gambia': 'Africa',
        'Ghana': 'Africa', 'Guinea': 'Africa', 'Guinea-Bissau': 'Africa', 'Ivory Coast': 'Africa',
        'Kenya': 'Africa', 'Lesotho': 'Africa', 'Liberia': 'Africa', 'Libya': 'Africa',
        'Madagascar': 'Africa', 'Malawi': 'Africa', 'Mali': 'Africa', 'Mauritania': 'Africa',
        'Mauritius': 'Africa', 'Morocco': 'Africa', 'Mozambique': 'Africa', 'Namibia': 'Africa',
        'Niger': 'Africa', 'Nigeria': 'Africa', 'Rwanda': 'Africa', 'Sao Tome and Principe': 'Africa',
        'Senegal': 'Africa', 'Seychelles': 'Africa', 'Sierra Leone': 'Africa', 'Somalia': 'Africa',
        'South Africa': 'Africa', 'South Sudan': 'Africa', 'Sudan': 'Africa', 'Tanzania': 'Africa',
        'Togo': 'Africa', 'Tunisia': 'Africa', 'Uganda': 'Africa', 'Zambia': 'Africa',
        'Zimbabwe': 'Africa',

        # --- 大洋洲 (Oceania) ---
        'Australia': 'Oceania', 'Fiji': 'Oceania', 'Kiribati': 'Oceania', 'Marshall Islands': 'Oceania',
        'Micronesia': 'Oceania', 'Nauru': 'Oceania', 'New Zealand': 'Oceania', 'Palau': 'Oceania',
        'Papua New Guinea': 'Oceania', 'Samoa': 'Oceania', 'Solomon Islands': 'Oceania',
        'Tonga': 'Oceania', 'Tuvalu': 'Oceania', 'Vanuatu': 'Oceania'
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