import re
import json
import time
import random
from pathlib import Path
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("astrbot_plugin_friberg", "oldPeter", "一个猜cs选手名字的游戏插件", "1.3.0")
class PlayerGuesser(Star):
    GUESS_LIMIT = 10
    TIME_LIMIT_SECONDS = 300  # 5分钟

    def __init__(self, context: Context):
        super().__init__(context)
        self.active_games = {}
        self.players_list = []
        self.players_map = {}

    def _normalize_name(self, name: str) -> str:
        """将名称标准化，用于模糊匹配。忽略大小写、o/0、i/1。"""
        if not isinstance(name, str):
            return ""
        return name.lower().replace('0', 'o').replace('1', 'i')
        
    def _get_player_full_details(self, player: dict) -> str:
        """格式化并返回选手的完整信息字符串。"""
        return (
            f"年龄: {player.get('age', '未知')}\n"
            f"职责: {player.get('role', '未知')}\n"
            f"国籍: {player.get('nationality', '未知')}\n"
            f"俱乐部: {player.get('club', '未知')}\n"
            f"Major次数: {player.get('major_participations', '未知')}"
        )

    async def _get_valid_game_state(self, event: AstrMessageEvent) -> dict | None:
        """检查并返回一个有效的游戏状态，处理游戏不存在或超时的情况。"""
        session_id = event.get_session_id()
        game_state = self.active_games.get(session_id)

        if not game_state:
            await event.yield_result(event.plain_result("游戏尚未开始，请先使用 `/弗一把` 来开始一局新游戏。"))
            return None

        time_elapsed = time.time() - game_state['start_time']
        if time_elapsed > self.TIME_LIMIT_SECONDS:
            secret_player = game_state['player']
            details = self._get_player_full_details(secret_player)
            final_message = f"⌛ 时间到！游戏已结束。\n正确答案是：{secret_player['name']}\n---\n{details}"
            await event.yield_result(event.plain_result(final_message))
            del self.active_games[session_id]
            return None
            
        return game_state

    async def initialize(self):
        """插件初始化时，加载并标准化选手数据。"""
        data_path = Path(__file__).parent / "players.json"
        if not data_path.exists():
            logger.error(f"选手数据文件未找到: {data_path}")
            return

        try:
            with open(data_path, "r", encoding="utf-8") as f:
                self.players_list = json.load(f)
            
            self.players_map = {self._normalize_name(player['name']): player for player in self.players_list}
            logger.info(f"成功加载 {len(self.players_list)} 位选手数据。")

        except json.JSONDecodeError:
            logger.error(f"解析 players.json 文件失败，请检查文件格式是否正确。")
        except Exception as e:
            logger.error(f"加载选手数据时发生未知错误: {e}")

    @filter.command("弗一把")
    async def start_game(self, event: AstrMessageEvent):
        """开始一局新的猜选手游戏，并发送游戏说明。"""
        session_id = event.get_session_id()

        if not self.players_list:
            yield event.plain_result("插件数据未能成功加载，游戏无法开始。请检查后台日志。")
            return

        secret_player = random.choice(self.players_list)
        self.active_games[session_id] = {
            'player': secret_player,
            'given_hints': set(),
            'guess_count': 0,
            'start_time': time.time()
        }
        
        logger.info(f"会话 {session_id} 开始新游戏，谜底: {secret_player['name']}")

        instructions = f"""\
欢迎来到“猜选手”游戏！
我已经想好了一位CS选手，请你在 {self.GUESS_LIMIT} 次机会 和 5分钟内 猜出他是谁。

--- 游戏指南 ---
• 猜测: 请发送“我猜 [选手名]”或“猜 [选手名]”。
• 提示: 需要线索时，请发送“提示”。每次都会给你一条不同的新线索哦！
• 放弃: 想结束当前这局，请发送“结束”或“停止”。
• 新游戏: 输入 /弗一把 随时开启新的一局。

--- 符号说明 ---
√ : 完全正确
↑ : 谜底选手的该项数值比你猜的更大
↓ : 谜底选手的该项数值比你猜的更小
× : 属性错误
O : (国籍) 虽然国家不对，但和谜底选手属于同一个大洲"""

        yield event.plain_result(instructions)

    @filter.regex(r"^(?:我猜|猜)\s*(.+)")
    async def make_guess(self, event: AstrMessageEvent):
        """进行一次选手猜测，包含次数和时间限制。"""
        game_state = await self._get_valid_game_state(event)
        if not game_state:
            return

        full_text = event.message_str.strip()
        match = re.match(r"^(?:我猜|猜)\s*(.+)", full_text)
        
        if not match:
            logger.error(f"make_guess被触发，但手动正则匹配失败，文本为: {full_text}")
            return
            
        guess_name = match.groups()[0].strip()
        if not guess_name:
            yield event.plain_result("请输入你要猜测的选手名称，例如：“猜 s1mple”")
            return

        normalized_guess = self._normalize_name(guess_name)
        guessed_player = self.players_map.get(normalized_guess)

        if not guessed_player:
            yield event.plain_result(f"数据库中没有名为 “{guess_name}” 的选手哦，请检查一下输入。")
            return

        secret_player = game_state['player']
        feedback, is_win = self._generate_feedback(guessed_player, secret_player)

        if is_win:
            del self.active_games[event.get_session_id()]
            final_message = f"✅ 正确！\n\n{feedback}"
            yield event.plain_result(final_message)
        else:
            game_state['guess_count'] += 1
            remaining_guesses = self.GUESS_LIMIT - game_state['guess_count']

            if remaining_guesses > 0:
                feedback += f"\n---\n（你还有 {remaining_guesses} 次机会）"
                yield event.plain_result(feedback)
            else:
                del self.active_games[event.get_session_id()]
                details = self._get_player_full_details(secret_player)
                final_message = f"❌ 机会已用完，游戏结束！\n正确答案是：{secret_player['name']}\n---\n{details}"
                yield event.plain_result(final_message)

    @filter.regex(r"^(?:提示)$")
    async def give_hint(self, event: AstrMessageEvent):
        """为当前游戏提供一个不重复的提示。"""
        game_state = await self._get_valid_game_state(event)
        if not game_state:
            return
            
        secret_player = game_state['player']
        given_hints = game_state['given_hints']
        
        hint_pool = {"职责", "国籍", "俱乐部", "Major次数"}
        available_hints = list(hint_pool - given_hints)
        
        if not available_hints:
            yield event.plain_result("所有提示均已用尽！")
            return

        hint_key_map = {
            "职责": "role", "国籍": "nationality", "俱乐部": "club", "Major次数": "major_participations"
        }
        chosen_key_cn = random.choice(available_hints)
        chosen_key_en = hint_key_map[chosen_key_cn]
        hint_value = secret_player.get(chosen_key_en, '未知')
        given_hints.add(chosen_key_cn)
        
        yield event.plain_result(f"提示：这位选手的 {chosen_key_cn} 是 {hint_value}。")

    @filter.regex(r"^(?:游戏停止|游戏结束|停止|结束)$")
    async def stop_game(self, event: AstrMessageEvent):
        """停止当前游戏并公布包含完整信息的答案。"""
        game_state = await self._get_valid_game_state(event)
        if not game_state:
            return
            
        secret_player = self.active_games.pop(event.get_session_id())['player']
        details = self._get_player_full_details(secret_player)
        final_message = f"游戏已停止。正确答案是：{secret_player['name']}\n---\n{details}"
        yield event.plain_result(final_message)
            
    def _generate_feedback(self, guessed_player: dict, secret_player: dict) -> (str, bool):
        """生成换行显示的猜测反馈，并包含猜测对象标题。"""
        header = f"猜测选手: {guessed_player['name']}\n---"
        feedback_parts = []
        is_win = True

        # ... (属性比较逻辑不变) ...
        if guessed_player['age'] == secret_player['age']:
            feedback_parts.append(f"年龄: {guessed_player['age']}(√)")
        elif guessed_player['age'] > secret_player['age']:
            feedback_parts.append(f"年龄: {guessed_player['age']}(↓)")
            is_win = False
        else: 
            feedback_parts.append(f"年龄: {guessed_player['age']}(↑)")
            is_win = False
            
        if guessed_player['role'] == secret_player['role']:
            feedback_parts.append(f"职责: {guessed_player['role']}(√)")
        else:
            feedback_parts.append(f"职责: {guessed_player['role']}(×)")
            is_win = False
            
        if guessed_player['nationality'] == secret_player['nationality']:
            feedback_parts.append(f"国籍: {guessed_player['nationality']}(√)")
        elif guessed_player['continent'] == secret_player['continent']:
            feedback_parts.append(f"国籍: {guessed_player['nationality']}(O)")
            is_win = False
        else:
            feedback_parts.append(f"国籍: {guessed_player['nationality']}(×)")
            is_win = False
            
        if guessed_player['club'] == secret_player['club']:
            feedback_parts.append(f"俱乐部: {guessed_player['club']}(√)")
        else:
            feedback_parts.append(f"俱乐部: {guessed_player['club']}(×)")
            is_win = False

        if guessed_player['major_participations'] == secret_player['major_participations']:
            feedback_parts.append(f"Major次数: {guessed_player['major_participations']}(√)")
        elif guessed_player['major_participations'] > secret_player['major_participations']:
            feedback_parts.append(f"Major次数: {guessed_player['major_participations']}(↓)")
            is_win = False
        else:
            feedback_parts.append(f"Major次数: {guessed_player['major_participations']}(↑)")
            is_win = False
        
        body = "\n".join(feedback_parts)
        full_feedback = f"{header}\n{body}"
        return full_feedback, is_win

    async def terminate(self):
        """插件停用时清空状态"""
        self.active_games.clear()
        self.players_list.clear()
        self.players_map.clear()
        logger.info("PlayerGuesser 插件已卸载，所有状态已清空。")