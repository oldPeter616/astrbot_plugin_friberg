# get_cs_players.py (Version 5 - Feature: Filter by Majors)

import requests
import re
import time
import json
from datetime import datetime
from bs4 import BeautifulSoup
import os

# ==============================================================================
# CONSTANTS & CONFIGURATION
# ==============================================================================
API_URL = "https://liquipedia.net/counterstrike/api.php"
BASE_URL = "https://liquipedia.net"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Language": "en-US,en;q=0.5",
}
REQUEST_DELAY = 1

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILENAME = os.path.join(SCRIPT_DIR, "players.json")

# ==============================================================================
# AUTHORITATIVE DATA
# ==============================================================================
DEFINITIVE_MAJORS_LIST = {
    "DreamHack Winter 2013", "EMS One Katowice 2014", "ESL One: Cologne 2014", "DreamHack Winter 2014",
    "ESL One: Katowice 2015", "ESL One: Cologne 2015", "DreamHack Open Cluj-Napoca 2015", "MLG Major Championship: Columbus 2016",
    "ESL One: Cologne 2016", "ELEAGUE Major: Atlanta 2017", "PGL Major Kraków 2017", "ELEAGUE Major: Boston 2018",
    "FACEIT Major: London 2018", "IEM Katowice Major 2019", "StarLadder Berlin Major 2019", "PGL Major Stockholm 2021",
    "PGL Major Antwerp 2022", "IEM Rio Major 2022", "BLAST.tv Paris Major 2023", "PGL Major Copenhagen 2024",
    "Perfect World Shanghai Major 2024"
}

COUNTRY_TO_CONTINENT = {
    "Austria": "Europe", "Belarus": "Europe", "Belgium": "Europe", "Bosnia and Herzegovina": "Europe", "Bulgaria": "Europe",
    "Croatia": "Europe", "Czech Republic": "Europe", "Denmark": "Europe", "Estonia": "Europe", "Finland": "Europe", "France": "Europe",
    "Germany": "Europe", "Greece": "Europe", "Hungary": "Europe", "Iceland": "Europe", "Ireland": "Europe", "Italy": "Europe",
    "Latvia": "Europe", "Lithuania": "Europe", "Monaco": "Europe", "Netherlands": "Europe", "North Macedonia": "Europe", "Norway": "Europe",
    "Poland": "Europe", "Portugal": "Europe", "Romania": "Europe", "Russia": "Europe", "Serbia": "Europe", "Slovakia": "Europe",
    "Spain": "Europe", "Sweden": "Europe", "Switzerland": "Europe", "Ukraine": "Europe", "United Kingdom": "Europe",
    "China": "Asia", "India": "Asia", "Indonesia": "Asia", "Israel": "Asia", "Japan": "Asia", "Jordan": "Asia", "Kazakhstan": "Asia",
    "Malaysia": "Asia", "Mongolia": "Asia", "Philippines": "Asia", "Saudi Arabia": "Asia", "South Korea": "Asia", "Thailand": "Asia",
    "Turkey": "Asia", "United Arab Emirates": "Asia", "Uzbekistan": "Asia", "Vietnam": "Asia",
    "Canada": "North America", "Mexico": "North America", "United States": "North America",
    "Argentina": "South America", "Brazil": "South America", "Chile": "South America", "Colombia": "South America", "Peru": "South America",
    "Australia": "Oceania", "New Zealand": "Oceania",
    "Egypt": "Africa", "South Africa": "Africa",
}

ENGLISH_TO_CHINESE_COUNTRY = {
    "Austria": "奥地利", "Belarus": "白俄罗斯", "Belgium": "比利时", "Bosnia and Herzegovina": "波斯尼亚和黑塞哥维那", "Bulgaria": "保加利亚",
    "Croatia": "克罗地亚", "Czech Republic": "捷克", "Denmark": "丹麦", "Estonia": "爱沙尼亚", "Finland": "芬兰", "France": "法国",
    "Germany": "德国", "Greece": "希腊", "Hungary": "匈加利", "Iceland": "冰岛", "Ireland": "爱尔兰", "Italy": "意大利",
    "Latvia": "拉脱维亚", "Lithuania": "立陶宛", "Monaco": "摩纳哥", "Netherlands": "荷兰", "North Macedonia": "北马其顿",
    "Norway": "挪威", "Poland": "波兰", "Portugal": "葡萄牙", "Romania": "罗马尼亚", "Russia": "俄罗斯", "Serbia": "塞尔维亚",
    "Slovakia": "斯洛伐克", "Spain": "西班牙", "Sweden": "瑞典", "Switzerland": "瑞士", "Ukraine": "乌克兰", "United Kingdom": "英国",
    "China": "中国", "India": "印度", "Indonesia": "印度尼西亚", "Israel": "以色列", "Japan": "日本", "Jordan": "约旦",
    "Kazakhstan": "哈萨克斯坦", "Malaysia": "马来西亚", "Mongolia": "蒙古", "Philippines": "菲律宾", "Saudi Arabia": "沙特阿拉伯",
    "South Korea": "韩国", "Thailand": "泰国", "Turkey": "土耳其", "United Arab Emirates": "阿拉伯联合酋长国", "Uzbekistan": "乌兹别克斯坦",
    "Vietnam": "越南", "Canada": "加拿大", "Mexico": "墨西哥", "United States": "美国", "Argentina": "阿根廷", "Brazil": "巴西",
    "Chile": "智利", "Colombia": "哥伦比亚", "Peru": "秘鲁", "Australia": "澳大利亚", "New Zealand": "新西兰", "Egypt": "埃及",
    "South Africa": "南非",
}

ENGLISH_TO_CHINESE_CONTINENT = {
    "Europe": "欧洲", "Asia": "亚洲", "North America": "北美洲", "South America": "南美洲", "Oceania": "大洋洲", "Africa": "非洲", "Unknown": "未知"
}

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def get_page_html(session: requests.Session, url: str) -> BeautifulSoup | None:
    try:
        response = session.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"  -> 错误: 请求 '{url}' 时发生网络错误: {e}")
        return None

def parse_player_info(session: requests.Session, page_title: str) -> dict | None:
    player_url = f"{BASE_URL}/counterstrike/{page_title}"
    soup = get_page_html(session, player_url)
    if not soup:
        return None

    infobox = soup.select_one('div.fo-nttax-infobox')
    if not infobox:
        return None

    player_data = {}

    def get_info_value(label_text):
        label_element = infobox.find('div', class_='infobox-description', string=lambda t: t and label_text in t)
        if label_element and label_element.find_next_sibling('div'):
            return label_element.find_next_sibling('div').get_text(strip=True)
        return None

    player_data["name"] = get_info_value("Game ID") or page_title.replace('_', ' ')
    
    birth_date_str = get_info_value("Born")
    player_data["age"] = None
    if birth_date_str:
        age_match = re.search(r'\(age\s*(\d+)\)', birth_date_str)
        if age_match:
            try:
                player_data["age"] = int(age_match.group(1))
            except (ValueError, IndexError):
                pass

    player_data["role"] = get_info_value("Role") or "Unknown"

    english_nationality = get_info_value("Nationality")
    if english_nationality:
        english_continent = COUNTRY_TO_CONTINENT.get(english_nationality, "Unknown")
        player_data["nationality"] = ENGLISH_TO_CHINESE_COUNTRY.get(english_nationality, english_nationality)
        player_data["continent"] = ENGLISH_TO_CHINESE_CONTINENT.get(english_continent, english_continent)
    else:
        player_data["nationality"] = "Unknown"; player_data["continent"] = "Unknown"

    player_data["club"] = get_info_value("Team") or "N/A"

    results_url = f"{player_url}/Results"
    results_soup = get_page_html(session, results_url)
    major_count = 0

    if results_soup:
        count_from_highlight = 0
        highlighted_rows = results_soup.select("tr.valvemajor-highlighted")
        if highlighted_rows:
            for row in highlighted_rows:
                cells = row.find_all("td")
                if len(cells) > 2 and "S-Tier" in cells[2].get_text(strip=True):
                    count_from_highlight += 1
        
        if count_from_highlight > 0:
            major_count = count_from_highlight
        else:
            all_rows = results_soup.select("table.wikitable tr")
            found_majors = set()
            for row in all_rows[1:]:
                cells = row.find_all("td")
                if len(cells) > 6:
                    tournament_name = cells[6].get_text(strip=True)
                    if tournament_name in DEFINITIVE_MAJORS_LIST:
                        found_majors.add(tournament_name)
            major_count = len(found_majors)
    
    player_data["major_participations"] = major_count
    return player_data

# ==============================================================================
# MAIN EXECUTION LOGIC
# ==============================================================================
def main():
    print("开始获取所有CS选手页面列表...")
    session = requests.Session()
    session.headers.update(HEADERS)
    
    all_player_pages = []
    params = {"action": "query", "format": "json", "list": "categorymembers", "cmtitle": "Category:Players", "cmlimit": "500"}

    while True:
        try:
            print("正在请求选手列表分页数据...")
            response = session.get(API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            for page in data["query"]["categorymembers"]:
                if ":" not in page["title"] and not page["title"].endswith("/Results"):
                    all_player_pages.append(page["title"])
            if "continue" in data:
                params["cmcontinue"] = data["continue"]["cmcontinue"]
                time.sleep(REQUEST_DELAY)
            else:
                break
        except Exception as e:
            print(f"请求选手列表时发生错误: {e}")
            break

    print(f"成功获取 {len(all_player_pages)} 位选手的页面标题。现在开始逐一解析...")
    print("-" * 30)
    
    all_players_data = []
    for i, page_title in enumerate(all_player_pages):
        print(f"正在处理选手 {i+1}/{len(all_player_pages)}: {page_title}")
        player_info = parse_player_info(session, page_title)
        
        if player_info:
            # [NEW FEATURE] Filter players by major participations
            if player_info.get("major_participations", 0) > 0:
                all_players_data.append(player_info)
                print(f"  -> [成功] 已添加: {player_info.get('name', 'N/A')}, Majors: {player_info.get('major_participations')}")
            else:
                # For players who don't meet the criteria, print a skip message
                print(f"  -> [跳过] {player_info.get('name', 'N/A')} 未参加过Major。")
        else:
            print(f"  -> 警告: 未能从 '{page_title}' 解析出选手信息框。")
        time.sleep(REQUEST_DELAY)

    print("-" * 30)
    print(f"所有选手处理完毕。共解析了 {len(all_player_pages)} 位选手，其中 {len(all_players_data)} 位参加过Major。")
    
    try:
        all_players_data.sort(key=lambda p: (p.get('name') or '').lower())
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(all_players_data, f, ensure_ascii=False, indent=2)
        print(f"数据已成功保存到文件: {OUTPUT_FILENAME}")
    except IOError as e:
        print(f"保存文件时发生错误: {e}")

if __name__ == "__main__":
    main()