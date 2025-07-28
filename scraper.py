import requests
from bs4 import BeautifulSoup, Tag
import time
import re
import random # 导入random库
from typing import List, Dict, Any, Optional, Set

from data_models import Player
from utils import get_continent_from_nationality

class LiquipediaScraper:
    def __init__(self, config: Dict[str, Any]):
        self.base_url = config['BASE_URL']
        # self.delay 不再是主要延迟手段，但可作为基础值
        self.delay = config['REQUEST_DELAY_SECONDS']
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config['USER_AGENT']})
        self.processed_player_urls: Set[str] = set()

    def _get_soup(self, url: str, max_retries: int = 3) -> Optional[BeautifulSoup]:
        """
        使用requests发起请求并返回Soup对象。
        内置了随机延迟、指数退避和自动重试机制。
        """
        full_url = self.base_url + url
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # 随机延迟，模拟人类行为
                # 基础延迟 + 0到2秒的随机额外延迟
                sleep_time = self.delay + random.uniform(0, 2)
                time.sleep(sleep_time)

                print(f"   - 正在请求 (尝试 {attempt + 1}/{max_retries}): {full_url}")
                response = self.session.get(full_url, timeout=20)
                
                # 如果是429错误，则进行指数退避
                if response.status_code == 429:
                    # 从响应头获取建议的等待时间，如果没有则自己计算
                    retry_after = int(response.headers.get("Retry-After", 30 * (attempt + 1)))
                    print(f"   - ⚠️ 收到 429 速率限制警告。将退避 {retry_after} 秒...")
                    time.sleep(retry_after)
                    last_exception = requests.RequestException(f"Gave up after 429, attempt {attempt + 1}")
                    continue # 继续下一次循环尝试

                response.raise_for_status() # 对其他错误(如404, 500)则直接抛出异常
                return BeautifulSoup(response.text, 'lxml')

            except requests.RequestException as e:
                last_exception = e
                print(f"   - ❌ 请求中发生错误: {e}")
                # 对于非429的连接错误，也进行短暂等待后重试
                time.sleep(5 * (attempt + 1))
                continue
        
        print(f"   - ❌ 在 {max_retries} 次尝试后，请求彻底失败: {full_url}")
        print(f"   - 最终错误: {last_exception}")
        return None

    def _get_infobox_value(self, infobox: Tag, key: str) -> Optional[str]:
        cell = infobox.find('div', class_='infobox-cell-1', string=re.compile(f'\\b{key}\\b', re.I))
        if cell and cell.find_next_sibling('div', class_='infobox-cell-2'):
            return cell.find_next_sibling('div').text.strip()
        return None

    def _parse_player_profile(self, player_url: str) -> Optional[Player]:
        print(f"   - 正在解析选手: {player_url}")
        soup = self._get_soup(player_url)
        if not soup: return None
        name = soup.find('h1', class_='firstHeading').text.strip()
        infobox = soup.find('div', class_='infobox-cs')
        if not infobox: return None
        try:
            born_text = self._get_infobox_value(infobox, 'Born') or ''
            age_match = re.search(r'\(age\s+(\d+)\)', born_text)
            age = int(age_match.group(1)) if age_match else 0
            nationality = self._get_infobox_value(infobox, 'Nationality') or 'N/A'
            role = self._get_infobox_value(infobox, 'Role') or 'Rifler'
            club = self._get_infobox_value(infobox, 'Team')
            major_count = 0
            results_table = soup.find('table', class_='wikitable-striped')
            if results_table:
                rows = results_table.find_all('tr')
                for row in rows:
                    if row.find('th'): continue
                    tier_cell = row.select_one('td:nth-of-type(1) a')
                    event_cell = row.select_one('td:nth-of-type(4)')
                    if tier_cell and event_cell:
                        tier = tier_cell.get('title', '').lower()
                        event_name = event_cell.text.lower()
                        if 's-tier' in tier and 'major' in event_name:
                            major_count += 1
            return Player(name=name, age=age, role=role, nationality=nationality, continent=get_continent_from_nationality(nationality), club=club, major_participations=major_count)
        except Exception as e:
            print(f"   - ❌ 解析选手页面HTML失败: {player_url} - {e}")
            return None

    def _scrape_player_category(self, category_url: str, limit: int = 50) -> List[Player]:
        players = []
        next_page_url = category_url
        while next_page_url and len(players) < limit:
            soup = self._get_soup(next_page_url)
            if not soup: break
            player_group = soup.find('div', class_='mw-category-group')
            if not player_group: break
            for player_tag in player_group.select('ul > li > a'):
                player_url = player_tag['href']
                if player_url.startswith('/counterstrike/index.php?title='): continue
                if player_url in self.processed_player_urls: continue
                player_data = self._parse_player_profile(player_url)
                if player_data and player_data.major_participations > 0:
                    players.append(player_data)
                self.processed_player_urls.add(player_url)
                if len(players) >= limit: break
            pagination_links = soup.select('div.mw-category-generated a')
            next_page_url = None
            for link in pagination_links:
                if 'next page' in link.text:
                    next_page_url = link['href']
                    break
        return players

    def get_retired_legends(self) -> List[Player]:
        print("\n🔍 开始获取【已退役】的Major八强选手...")
        category_url = '/counterstrike/index.php?title=Category:Retired_Players'
        players = self._scrape_player_category(category_url)
        print(f"   ✔️ 找到 {len(players)} 名符合条件的退役选手。")
        return players

    def get_active_major_players(self) -> List[Player]:
        print("\n🔍 开始获取【现役】的Major参赛选手...")
        category_url = '/counterstrike/index.php?title=Category:Active_Players'
        players = self._scrape_player_category(category_url)
        print(f"   ✔️ 找到 {len(players)} 名符合条件的现役选手。")
        return players

    def fetch_all_players(self) -> List[Player]:
        all_players = []
        all_players.extend(self.get_retired_legends())
        all_players.extend(self.get_active_major_players())
        return all_players