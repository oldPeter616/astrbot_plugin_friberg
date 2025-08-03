import re
import json
import time
import random
import asyncio
from pathlib import Path
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("astrbot_plugin_friberg", "oldPeter", "一个猜选手名字的游戏插件", "1.6.0")
class PlayerGuesser(Star):
    DIFFICULTY_SETTINGS = {
        "普通": {"guesses": 10, "time": 300},
        "进阶": {"guesses": 12, "time": 300},
        "地狱": {"guesses": 15, "time": 420}
    }

    def __init__(self, context: Context):
        super().__init__(context)
        self.active_games = {}
        self.players_list = []
        self.players_map = {}
        self.top_30_teams = set()

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
            f"地区: {player.get('continent', '未知')}\n"
            f"俱乐部: {player.get('club', '未知')}\n"
            f"Major次数: {player.get('major_participations', '未知')}"
        )

    async def _game_timer(self, session_id: str, time_limit: int):
        """后台计时器任务，在超时后主动结束游戏。"""
        await asyncio.sleep(time_limit)

        if session_id in self.active_games:
            logger.info(f"会话 {session_id} 游戏超时，主动结束。")
            game_state = self.active_games.pop(session_id)
            secret_player = game_state['player']
            umo = game_state['umo']

            details = self._get_player_full_details(secret_player)
            final_message = f"⌛ 时间到！游戏已自动结束。\n正确答案是：{secret_player['name']}\n---\n{details}"
            
            message_chain = MessageChain().message(final_message)
            await self.context.send_message(umo, message_chain)

    async def initialize(self):
        """插件初始化时，加载选手和战队排名数据。"""
        players_path = Path(__file__).parent / "players.json"
        if not players_path.exists():
            logger.error(f"选手数据文件未找到: {players_path}")
            return
        try:
            with open(players_path, "r", encoding="utf-8") as f:
                self.players_list = json.load(f)
            self.players_map = {self._normalize_name(player['name']): player for player in self.players_list}
            logger.info(f"成功加载 {len(self.players_list)} 位选手数据。")
        except Exception as e:
            logger.error(f"加载 players.json 时发生错误: {e}")

        teams_path = Path(__file__).parent / "teams_top.json"
        if not teams_path.exists():
            logger.warning(f"战队排名文件未找到: {teams_path}。难度分级将受影响。")
            return
        try:
            with open(teams_path, "r", encoding="utf-8") as f:
                teams_data = json.load(f)
            self.top_30_teams = {team['team_name'] for team in teams_data if team['rank'] <= 30}
            logger.info(f"成功加载 {len(self.top_30_teams)} 支Top 30战队数据。")
        except Exception as e:
            logger.error(f"加载 teams_top.json 时发生错误: {e}")

    @filter.command("弗一把")
    async def start_game(self, event: AstrMessageEvent):
        """解析指令，分发到具体的游戏初始化函数。"""
        session_id = event.get_session_id()
        
        if session_id in self.active_games:
            yield event.plain_result("当前已有游戏正在进行中，请先完成后再开始新游戏！")
            return

        # --- Begin Bug Fix ---
        # 将消息字符串按空格分割，并取最后一个部分作为难度参数
        parts = event.message_str.strip().split()
        difficulty_arg = parts[-1] if parts else ""
        # --- End Bug Fix ---
        
        if difficulty_arg in self.DIFFICULTY_SETTINGS:
            difficulty = difficulty_arg
        else:
            difficulty = "普通"

        await self._initialize_new_game(event, difficulty)

    async def _initialize_new_game(self, event: AstrMessageEvent, difficulty: str):
        """根据指定的难度，初始化一局新游戏。"""
        session_id = event.get_session_id()

        player_pool = []
        if difficulty == "普通":
            player_pool = [p for p in self.players_list if p.get('club') in self.top_30_teams or p.get('name') == 'machineWJQ']
        elif difficulty == "进阶":
            normal_pool = [p for p in self.players_list if p.get('club') in self.top_30_teams or p.get('name') == 'machineWJQ']
            advanced_pool = [p for p in self.players_list if p.get('club') == 'Retired' and p.get('major_participations', 0) > 6]
            player_pool = normal_pool + advanced_pool
        elif difficulty == "地狱":
            player_pool = self.players_list

        if not player_pool:
            no_player_message = MessageChain().message(f"无法为“{difficulty}”难度找到任何符合条件的选手，游戏无法开始。")
            await event.send(no_player_message)
            return

        settings = self.DIFFICULTY_SETTINGS[difficulty]
        guess_limit = settings["guesses"]
        time_limit = settings["time"]
        
        if session_id in self.active_games:
            self.active_games[session_id]['timer_task'].cancel()

        secret_player = random.choice(player_pool)
        timer_task = asyncio.create_task(self._game_timer(session_id, time_limit))
        
        self.active_games[session_id] = {
            'player': secret_player,
            'given_hints': set(),
            'guess_count': 0,
            'start_time': time.time(),
            'timer_task': timer_task,
            'umo': event.unified_msg_origin,
            'guess_limit': guess_limit,
            'time_limit': time_limit
        }
        
        logger.info(f"会话 {session_id} 开始新游戏，难度: {difficulty}，谜底: {secret_player['name']}，计时器已启动。")
        
        time_limit_minutes = time_limit // 60
        instructions = f"""\
欢迎来到“猜选手”游戏！
已选择 **{difficulty}** 难度。你有 {guess_limit} 次机会 和 {time_limit_minutes}分钟内 猜出他是谁。

--- 游戏指南 ---
• 猜测: 请发送“我猜 [选手名]”或“猜 [选手名]”。
• 提示: 需要线索时，请发送“提示”。
• 放弃: 想结束当前这局，请发送“结束”或“停止”。
• 新游戏: 输入 /弗一把 或 /弗一把 <难度> (普通/进阶/地狱)。

--- 符号说明 ---
√:完全正确 ↑:谜底更大 ↓:谜底更小 ×:错误 O:部分正确"""

        message_chain = MessageChain().message(instructions)
        await event.send(message_chain)


    @filter.regex(r"^(?:我猜|猜)\s*(.+)")
    async def make_guess(self, event: AstrMessageEvent):
        """进行一次选手猜测，包含次数和时间限制。"""
        session_id = event.get_session_id()
        game_state = self.active_games.get(session_id)

        if not game_state:
            yield event.plain_result("游戏尚未开始，请先使用 `/弗一把` 来开始一局新游戏。")
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
            game_state['timer_task'].cancel()
            del self.active_games[session_id]
            final_message = f"✅ 正确！\n\n{feedback}"
            yield event.plain_result(final_message)
        else:
            game_state['guess_count'] += 1
            remaining_guesses = game_state['guess_limit'] - game_state['guess_count']

            if remaining_guesses > 0:
                feedback += f"\n---\n（你还有 {remaining_guesses} 次机会）"
                yield event.plain_result(feedback)
            else:
                game_state['timer_task'].cancel()
                del self.active_games[session_id]
                details = self._get_player_full_details(secret_player)
                final_message = f"❌ 机会已用完，游戏结束！\n正确答案是：{secret_player['name']}\n---\n{details}"
                yield event.plain_result(final_message)

    @filter.regex(r"^(?:提示)$")
    async def give_hint(self, event: AstrMessageEvent):
        """为当前游戏提供一个不重复的提示。"""
        session_id = event.get_session_id()
        game_state = self.active_games.get(session_id)

        if not game_state:
            yield event.plain_result("当前没有正在进行的游戏，无法提供提示。")
            return
        
        secret_player = game_state['player']
        given_hints = game_state['given_hints']
        
        hint_pool = {"职责", "国籍", "地区", "俱乐部", "Major次数"}
        available_hints = list(hint_pool - given_hints)
        
        if not available_hints:
            yield event.plain_result("所有提示均已用尽！")
            return

        hint_key_map = {
            "职责": "role", "国籍": "nationality", "地区": "continent", "俱乐部": "club", "Major次数": "major_participations"
        }
        chosen_key_cn = random.choice(available_hints)
        chosen_key_en = hint_key_map[chosen_key_cn]
        hint_value = secret_player.get(chosen_key_en, '未知')
        given_hints.add(chosen_key_cn)
        
        yield event.plain_result(f"提示：这位选手的 {chosen_key_cn} 是 {hint_value}。")

    @filter.regex(r"^(?:游戏停止|游戏结束|停止|结束)$")
    async def stop_game(self, event: AstrMessageEvent):
        """停止当前游戏，取消计时器并公布答案。"""
        session_id = event.get_session_id()
        game_state = self.active_games.get(session_id)

        if not game_state:
            yield event.plain_result("当前没有正在进行的游戏。")
            return
        
        game_state['timer_task'].cancel()
        secret_player = self.active_games.pop(session_id)['player']
        details = self._get_player_full_details(secret_player)
        final_message = f"游戏已停止。正确答案是：{secret_player['name']}\n---\n{details}"
        yield event.plain_result(final_message)
            
    def _generate_feedback(self, guessed_player: dict, secret_player: dict) -> (str, bool):
        """生成换行显示的猜测反馈，并包含猜测对象标题。"""
        header = f"猜测选手: {guessed_player['name']}\n---"
        feedback_parts = []
        is_win = True

        # 年龄
        if guessed_player.get('age') == secret_player.get('age'):
            feedback_parts.append(f"年龄: {guessed_player.get('age', '未知')}(√)")
        elif guessed_player.get('age', 0) > secret_player.get('age', 0):
            feedback_parts.append(f"年龄: {guessed_player.get('age', '未知')}(↓)")
            is_win = False
        else: 
            feedback_parts.append(f"年龄: {guessed_player.get('age', '未知')}(↑)")
            is_win = False

        # --- Begin Role Logic Change ---
        # 职责 (支持多职责字符串)
        guessed_role_str = guessed_player.get('role', "")
        secret_role_str = secret_player.get('role', "")

        guessed_roles_set = set(r.strip() for r in guessed_role_str.split(' / '))
        secret_roles_set = set(r.strip() for r in secret_role_str.split(' / '))
        
        roles_display_str = guessed_role_str if guessed_role_str else "无"

        if guessed_roles_set == secret_roles_set:
            feedback_parts.append(f"职责: {roles_display_str}(√)")
        elif guessed_roles_set.intersection(secret_roles_set):
            feedback_parts.append(f"职责: {roles_display_str}(O)")
            is_win = False
        else:
            feedback_parts.append(f"职责: {roles_display_str}(×)")
            is_win = False
        # --- End Role Logic Change ---
        
        # 国籍
        if guessed_player.get('nationality') == secret_player.get('nationality'):
            feedback_parts.append(f"国籍: {guessed_player.get('nationality', '未知')}(√)")
        else:
            feedback_parts.append(f"国籍: {guessed_player.get('nationality', '未知')}(×)")
            is_win = False
        
        # 地区
        if guessed_player.get('continent') == secret_player.get('continent'):
            feedback_parts.append(f"地区: {guessed_player.get('continent', '未知')}(√)")
        else:
            feedback_parts.append(f"地区: {guessed_player.get('continent', '未知')}(×)")
            is_win = False
            
        # 俱乐部
        if guessed_player.get('club') == secret_player.get('club'):
            feedback_parts.append(f"俱乐部: {guessed_player.get('club', '未知')}(√)")
        else:
            feedback_parts.append(f"俱乐部: {guessed_player.get('club', '未知')}(×)")
            is_win = False

        # Major次数
        if guessed_player.get('major_participations') == secret_player.get('major_participations'):
            feedback_parts.append(f"Major次数: {guessed_player.get('major_participations', '未知')}(√)")
        elif guessed_player.get('major_participations', 0) > secret_player.get('major_participations', 0):
            feedback_parts.append(f"Major次数: {guessed_player.get('major_participations', '未知')}(↓)")
            is_win = False
        else:
            feedback_parts.append(f"Major次数: {guessed_player.get('major_participations', '未知')}(↑)")
            is_win = False
        
        # 最终胜利判断：确保所有属性都为√
        # is_win 的值在上面已经被正确设置，但为了逻辑严谨，可以做一个最终确认
        # 查找feedback_parts中是否包含任何非√的标记
        all_correct = all('(√)' in part for part in feedback_parts)
        is_win = all_correct

        body = "\n".join(feedback_parts)
        full_feedback = f"{header}\n{body}"
        return full_feedback, is_win

    async def terminate(self):
        """插件停用时，清理所有正在运行的计时器任务。"""
        logger.info("PlayerGuesser 插件正在卸载，开始清理后台任务...")
        for session_id, game_state in list(self.active_games.items()):
            game_state['timer_task'].cancel()
            logger.info(f"已取消会话 {session_id} 的计时器任务。")
        self.active_games.clear()
        self.players_list.clear()
        self.players_map.clear()
        logger.info("PlayerGuesser 插件已卸载，所有状态已清空。")