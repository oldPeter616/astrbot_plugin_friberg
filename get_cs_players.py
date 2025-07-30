import requests
import re
import time
import json
from datetime import datetime
from bs4 import BeautifulSoup
import os # 导入os库来处理文件路径

# ==============================================================================
# CONSTANTS & CONFIGURATION
# ==============================================================================
API_URL = "https://liquipedia.net/counterstrike/api.php"
BASE_URL = "https://liquipedia.net"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0 "
        "(CSPlayerExporter/1.0; Contact: your-email@example.com)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
REQUEST_DELAY = 2

### MODIFICATION 2: Ensure output file is in the same directory as the script ###
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILENAME = os.path.join(SCRIPT_DIR, "players.json")

# ==============================================================================
# MAPPINGS
# ==============================================================================
MAJOR_TOURNAMENT_KEYWORDS = (
    'DreamHack 2013', 'Katowice 2014', 'Cologne 2014', 'DreamHack 2014',
    'Katowice 2015', 'Cologne 2015', 'Cluj-Napoca', 'MLG Columbus',
    'Cologne 2016', 'Atlanta 2017', 'Kraków 2017', 'Boston 2018',
    'London 2018', 'Katowice 2019', 'Berlin 2019', 'Stockholm 2021',
    'Antwerp 2022', 'Rio 2022', 'Paris 2023', 'Copenhagen 2024',
    'Shanghai 2024', 'Austin 2025'
)

### MODIFICATION 1: Expanded Country and Continent Mappings ###
COUNTRY_TO_CONTINENT = {
    # Europe
    "Austria": "Europe", "Belarus": "Europe", "Belgium": "Europe", "Bosnia and Herzegovina": "Europe",
    "Bulgaria": "Europe", "Croatia": "Europe", "Czech Republic": "Europe", "Denmark": "Europe",
    "Estonia": "Europe", "Finland": "Europe", "France": "Europe", "Germany": "Europe", "Greece": "Europe",
    "Hungary": "Europe", "Iceland": "Europe", "Ireland": "Europe", "Italy": "Europe", "Latvia": "Europe",
    "Lithuania": "Europe", "Monaco": "Europe", "Netherlands": "Europe", "North Macedonia": "Europe",
    "Norway": "Europe", "Poland": "Europe", "Portugal": "Europe", "Romania": "Europe", "Russia": "Europe",
    "Serbia": "Europe", "Slovakia": "Europe", "Spain": "Europe", "Sweden": "Europe", "Switzerland": "Europe",
    "Ukraine": "Europe", "United Kingdom": "Europe",
    # Asia
    "China": "Asia", "India": "Asia", "Indonesia": "Asia", "Israel": "Asia", "Japan": "Asia",
    "Jordan": "Asia", "Kazakhstan": "Asia", "Malaysia": "Asia", "Mongolia": "Asia", "Philippines": "Asia",
    "Saudi Arabia": "Asia", "South Korea": "Asia", "Thailand": "Asia", "Turkey": "Asia",
    "United Arab Emirates": "Asia", "Uzbekistan": "Asia", "Vietnam": "Asia",
    # North America
    "Canada": "North America", "Mexico": "North America", "United States": "North America",
    # South America
    "Argentina": "South America", "Brazil": "South America", "Chile": "South America",
    "Colombia": "South America", "Peru": "South America",
    # Oceania
    "Australia": "Oceania", "New Zealand": "Oceania",
    # Africa
    "Egypt": "Africa", "South Africa": "Africa",
}

ENGLISH_TO_CHINESE_COUNTRY = {
    # Europe
    "Austria": "奥地利", "Belarus": "白俄罗斯", "Belgium": "比利时", "Bosnia and Herzegovina": "波斯尼亚和黑塞哥维那",
    "Bulgaria": "保加利亚", "Croatia": "克罗地亚", "Czech Republic": "捷克", "Denmark": "丹麦", "Estonia": "爱沙尼亚",
    "Finland": "芬兰", "France": "法国", "Germany": "德国", "Greece": "希腊", "Hungary": "匈牙利", "Iceland": "冰岛",
    "Ireland": "爱尔兰", "Italy": "意大利", "Latvia": "拉脱维亚", "Lithuania": "立陶宛", "Monaco": "摩纳哥",
    "Netherlands": "荷兰", "North Macedonia": "北马其顿", "Norway": "挪威", "Poland": "波兰", "Portugal": "葡萄牙",
    "Romania": "罗马尼亚", "Russia": "俄罗斯", "Serbia": "塞尔维亚", "Slovakia": "斯洛伐克", "Spain": "西班牙",
    "Sweden": "瑞典", "Switzerland": "瑞士", "Ukraine": "乌克兰", "United Kingdom": "英国",
    # Asia
    "China": "中国", "India": "印度", "Indonesia": "印度尼西亚", "Israel": "以色列", "Japan": "日本",
    "Jordan": "约旦", "Kazakhstan": "哈萨克斯坦", "Malaysia": "马来西亚", "Mongolia": "蒙古", "Philippines": "菲律宾",
    "Saudi Arabia": "沙特阿拉伯", "South Korea": "韩国", "Thailand": "泰国", "Turkey": "土耳其",
    "United Arab Emirates": "阿拉伯联合酋长国", "Uzbekistan": "乌兹别克斯坦", "Vietnam": "越南",
    # North America
    "Canada": "加拿大", "Mexico": "墨西哥", "United States": "美国",
    # South America
    "Argentina": "阿根廷", "Brazil": "巴西", "Chile": "智利", "Colombia": "哥伦比亚", "Peru": "秘鲁",
    # Oceania
    "Australia": "澳大利亚", "New Zealand": "新西兰",
    # Africa
    "Egypt": "埃及", "South Africa": "南非",
}

ENGLISH_TO_CHINESE_CONTINENT = {
    "Europe": "欧洲", "Asia": "亚洲", "North America": "北美洲",
    "South America": "南美洲", "Oceania": "大洋洲", "Africa": "非洲", "Unknown": "未知"
}

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def get_wikitext(session: requests.Session, page_title: str) -> str | None:
    """Fetches the wikitext for a given page title via API."""
    params = {"action": "query", "format": "json", "titles": page_title, "prop": "revisions", "rvprop": "content", "redirects": 1}
    try:
        response = session.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        page_id = list(data["query"]["pages"].keys())[0]
        if page_id == "-1": return None
        return data["query"]["pages"][page_id]["revisions"][0]["*"]
    except:
        return None

def calculate_age(birth_date_str: str) -> int | None:
    match = re.search(r'(\d{4})\|(\d{1,2})\|(\d{1,2})', birth_date_str)
    if not match: return None
    year, month, day = map(int, match.groups())
    try:
        birth_date = datetime(year, month, day)
        today = datetime.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except ValueError:
        return None

def parse_player_info(session: requests.Session, page_title: str, main_wikitext: str) -> dict | None:
    player_data = {}
    infobox_match = re.search(r'\{\{Infobox player\s*\|([\s\S]*?)\}\}', main_wikitext, re.IGNORECASE)
    if not infobox_match: return None
    infobox_content = infobox_match.group(1)

    # --- Step 1: Parse basic info from Infobox ---
    patterns = { "name": r'id\s*=\s*([^|\n}]+)', "age_str": r'birth_date\s*=\s*([^{|]*\{\{[^}]+}}[^|\n]*)', "role": r'role\s*=\s*([^|\n}]+)', "nationality": r'nationality\s*=\s*([^|\n}]+)', "club": r'team\s*=\s*([^|\n}]+)',}
    name_match = re.search(patterns["name"], infobox_content, re.IGNORECASE)
    player_data["name"] = name_match.group(1).strip() if name_match else page_title.replace('_', ' ')
    age_str_match = re.search(patterns["age_str"], infobox_content, re.IGNORECASE)
    player_data["age"] = calculate_age(age_str_match.group(1).strip()) if age_str_match else None
    role_match = re.search(patterns["role"], infobox_content, re.IGNORECASE)
    if role_match:
        role_text = role_match.group(1).strip(); wikilink_match = re.search(r'\[\[[^|]+\|([^\]]+)\]\]', role_text)
        player_data["role"] = wikilink_match.group(1) if wikilink_match else role_text.replace('[[', '').replace(']]', '')
    else: player_data["role"] = None
    nationality_match = re.search(patterns["nationality"], infobox_content, re.IGNORECASE)
    if nationality_match:
        english_nationality = nationality_match.group(1).strip(); english_continent = COUNTRY_TO_CONTINENT.get(english_nationality, "Unknown")
        player_data["nationality"] = ENGLISH_TO_CHINESE_COUNTRY.get(english_nationality, english_nationality)
        player_data["continent"] = ENGLISH_TO_CHINESE_CONTINENT.get(english_continent, english_continent)
    else:
        player_data["nationality"] = None; player_data["continent"] = None
    club_match = re.search(patterns["club"], infobox_content, re.IGNORECASE)
    player_data["club"] = club_match.group(1).strip() if club_match else "N/A"

    # --- Step 2: The ultimate 3-tier Major parsing logic ---
    major_count = 0
    results_url = f"{BASE_URL}/counterstrike/{page_title}/Results"
    print(f"  -> [详情] 正在尝试获取HTML结果页: {results_url}")
    time.sleep(REQUEST_DELAY)

    try:
        response = session.get(results_url)
        if response.status_code == 200:
            print("  -> [详情] /Results 页面存在，切换至HTML表格解析模式。")
            soup = BeautifulSoup(response.text, 'html.parser')
            highlighted_rows = soup.find_all("tr", class_="valvemajor-highlighted")
            if highlighted_rows:
                print(f"  -> [详情] 模式A: 成功在/Results页找到 {len(highlighted_rows)} 个高亮Major标记。")
                major_count = len(highlighted_rows)
            else:
                print("  -> [详情] 模式B: /Results页无高亮标记，切换至表格关键字解析模式。")
                result_tables = soup.find_all("table", class_="wikitable")
                for table in result_tables:
                    for row in table.find_all("tr")[1:]:
                        cells = row.find_all("td")
                        if len(cells) > 6:
                            tournament_name = cells[6].get_text()
                            for keyword in MAJOR_TOURNAMENT_KEYWORDS:
                                if keyword in tournament_name:
                                    major_count += 1
                                    break
        else:
            print("  -> [详情] 模式C: /Results页面不存在，回退至主页Wikitext解析模式。")
            all_achievements = re.findall(r'\{\{Achievement\|.*?\}\}', main_wikitext, re.IGNORECASE)
            for achievement in all_achievements:
                for keyword in MAJOR_TOURNAMENT_KEYWORDS:
                    if keyword in achievement:
                        major_count += 1
                        break
    except requests.exceptions.RequestException as e:
        print(f"  -> 错误: 请求 '{results_url}' 时发生网络错误: {e}")

    player_data["major_participations"] = major_count
    return player_data

# ==============================================================================
# MAIN EXECUTION LOGIC
# ==============================================================================
def main():
    print("开始获取所有CS选手页面列表（这将需要一些时间）...")
    session = requests.Session(); session.headers.update(HEADERS)
    all_player_pages = []
    params = {"action": "query", "format": "json", "list": "categorymembers", "cmtitle": "Category:Players", "cmlimit": "500"}

    while True:
        try:
            print(f"正在请求选手列表分页数据...")
            response = session.get(API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            for page in data["query"]["categorymembers"]:
                all_player_pages.append(page["title"])
            if "continue" in data:
                params["cmcontinue"] = data["continue"]["cmcontinue"]
                time.sleep(REQUEST_DELAY)
            else: break
        except: print(f"请求选手列表时发生错误，可能已结束。"); break
    print(f"成功获取 {len(all_player_pages)} 位选手的页面标题。现在开始逐一解析和筛选...")
    print("-" * 30)
    all_players_data = []
    for i, page_title in enumerate(all_player_pages):
        print(f"正在处理选手 {i+1}/{len(all_player_pages)}: {page_title}")
        main_wikitext = get_wikitext(session, page_title)
        if not main_wikitext:
            print(f"  -> 警告: 未能获取页面 '{page_title}' 的内容, 跳过。")
            time.sleep(REQUEST_DELAY); continue
        player_info = parse_player_info(session, page_title, main_wikitext)
        if player_info and player_info.get("major_participations", 0) > 0:
            all_players_data.append(player_info)
            print(f"  -> [保留] 成功解析 (Majors > 0): {player_info.get('name', 'N/A')}, Majors: {player_info.get('major_participations')}")
        elif player_info:
            print(f"  -> [过滤] 已解析但Major参赛次数为0: {player_info.get('name', 'N/A')}")
        else:
            print(f"  -> 警告: 未能从 '{page_title}' 解析出选手信息框。")

    print("-" * 30)
    print(f"所有选手处理完毕。共筛选出 {len(all_players_data)} 位参加过Major的选手。")
    try:
        all_players_data.sort(key=lambda p: p.get('major_participations', 0), reverse=True)
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(all_players_data, f, ensure_ascii=False, indent=4)
        print(f"数据已成功保存到文件: {OUTPUT_FILENAME}")
    except IOError as e:
        print(f"保存文件时发生错误: {e}")

if __name__ == "__main__":
    main()