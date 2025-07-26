import json
import random
from pathlib import Path
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("astrbot_plugin_friberg", "YourName", "一个猜选手名字的游戏插件", "1.0.0")
class PlayerGuesser(Star):
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

    async def initialize(self):
        """插件初始化时，加载并标准化选手数据。"""
        data_path = Path(__file__).parent / "players.json"
        if not data_path.exists():
            logger.error(f"选手数据文件未找到: {data_path}")
            return

        try:
            with open(data_path, "r", encoding="utf-8") as f:
                self.players_list = json.load(f)
            
            # 使用标准化后的选手名作为键，用于快速、模糊地查找
            self.players_map = {self._normalize_name(player['name']): player for player in self.players_list}
            logger.info(f"成功加载 {len(self.players_list)} 位选手数据。")

        except json.JSONDecodeError:
            logger.error(f"解析 players.json 文件失败，请检查文件格式是否正确。")
        except Exception as e:
            logger.error(f"加载选手数据时发生未知错误: {e}")

    @filter.command("弗一把")
    async def start_game(self, event: AstrMessageEvent):
        """开始一局新的猜选手游戏"""
        session_id = event.get_session_id()

        if not self.players_list:
            yield event.plain_result("插件数据未能成功加载，游戏无法开始。请检查后台日志。")
            return

        if session_id in self.active_games:
            yield event.plain_result("游戏已经开始了哦！请直接使用 `/我猜 <选手名>` 来猜吧。")
            return

        secret_player = random.choice(self.players_list)
        self.active_games[session_id] = secret_player
        
        logger.info(f"会话 {session_id} 开始新游戏，谜底: {secret_player['name']}")
        yield event.plain_result("游戏开始！我已经想好了一位选手，请使用 `/我猜 <选手名>` 来进行猜测吧！")

    @filter.command("我猜")
    async def make_guess(self, event: AstrMessageEvent):
        """进行一次选手猜测"""
        session_id = event.get_session_id()

        if session_id not in self.active_games:
            yield event.plain_result("游戏尚未开始，请先使用 `/弗一把` 来开始一局新游戏。")
            return

        # 获取原始输入
        raw_input = event.message_str.strip()
        
        # 为了健壮性，显式地处理输入中可能包含指令本身的情况
        if raw_input.startswith("我猜"):
            # 从 "我猜 Niko" 中提取 "Niko"
            guess_name = raw_input.replace("我猜", "", 1).strip()
        else:
            # 如果输入已经是 "Niko"，则直接使用
            guess_name = raw_input

        # 如果处理后为空，则认为输入无效
        if not guess_name:
            yield event.plain_result("请输入你要猜测的选手名称，例如：`/我猜 s1mple`")
            return

        # 使用标准化函数处理用户输入，以实现模糊匹配
        normalized_guess = self._normalize_name(guess_name)
        guessed_player = self.players_map.get(normalized_guess)

        if not guessed_player:
            yield event.plain_result(f"数据库中没有名为 “{guess_name}” 的选手哦，请检查一下输入。")
            return

        secret_player = self.active_games[session_id]
        
        feedback, is_win = self._generate_feedback(guessed_player, secret_player)

        # --- Begin Bug Fix ---
        if is_win:
            del self.active_games[session_id]
            # 移除Markdown的**符号，因为是纯文本发送
            final_message = f"✅ 正确！谜底就是 {secret_player['name']}！\n\n{feedback}"
            # 使用已知可用的 plain_result 方法
            yield event.plain_result(final_message)
        # --- End Bug Fix ---
        else:
            yield event.plain_result(feedback)

    @filter.command("提示")
    async def give_hint(self, event: AstrMessageEvent):
        """为当前游戏提供一个提示"""
        session_id = event.get_session_id()
        if session_id not in self.active_games:
            yield event.plain_result("当前没有正在进行的游戏，无法提供提示。")
            return
            
        secret_player = self.active_games[session_id]
        
        # 定义可以作为提示的属性
        hint_attributes = {
            "职责": secret_player.get('role'),
            "国籍": secret_player.get('nationality'),
            "俱乐部": secret_player.get('club'),
            "Major次数": secret_player.get('major_participations')
        }
        
        # 过滤掉值为空的属性
        valid_hints = {k: v for k, v in hint_attributes.items() if v is not None}
        
        if not valid_hints:
            yield event.plain_result("抱歉，这位选手没有可用的提示信息。")
            return

        # 随机选择一个属性作为提示
        hint_key, hint_value = random.choice(list(valid_hints.items()))
        
        yield event.plain_result(f"提示：这位选手的 {hint_key} 是 {hint_value}。")

    @filter.command("停止")
    async def stop_game(self, event: AstrMessageEvent):
        """停止当前游戏并公布答案"""
        session_id = event.get_session_id()
        if session_id not in self.active_games:
            yield event.plain_result("当前没有正在进行的游戏。")
            return
            
        secret_player = self.active_games.pop(session_id) # pop会移除并返回元素
        yield event.plain_result(f"游戏已停止。正确答案是：{secret_player['name']}。")
            
    def _generate_feedback(self, guessed_player: dict, secret_player: dict) -> (str, bool):
        """生成猜测反馈的核心逻辑"""
        feedback_parts = []
        is_win = True

        # 1. 年龄
        if guessed_player['age'] == secret_player['age']:
            feedback_parts.append(f"年龄: {guessed_player['age']}(√)")
        elif guessed_player['age'] > secret_player['age']:
            feedback_parts.append(f"年龄: {guessed_player['age']}(↓)")
            is_win = False
        else: # guessed_player['age'] < secret_player['age']
            feedback_parts.append(f"年龄: {guessed_player['age']}(↑)")
            is_win = False
            
        # 2. 职责 (Role)
        if guessed_player['role'] == secret_player['role']:
            feedback_parts.append(f"职责: {guessed_player['role']}(√)")
        else:
            feedback_parts.append(f"职责: {guessed_player['role']}(×)")
            is_win = False
            
        # 3. 国籍 & 大洲
        if guessed_player['nationality'] == secret_player['nationality']:
            feedback_parts.append(f"国籍: {guessed_player['nationality']}(√)")
        elif guessed_player['continent'] == secret_player['continent']:
            feedback_parts.append(f"国籍: {guessed_player['nationality']}(O)")
            is_win = False
        else:
            feedback_parts.append(f"国籍: {guessed_player['nationality']}(×)")
            is_win = False
            
        # 4. 俱乐部
        if guessed_player['club'] == secret_player['club']:
            feedback_parts.append(f"俱乐部: {guessed_player['club']}(√)")
        else:
            feedback_parts.append(f"俱乐部: {guessed_player['club']}(×)")
            is_win = False

        # 5. Major参与次数
        if guessed_player['major_participations'] == secret_player['major_participations']:
            feedback_parts.append(f"Major次数: {guessed_player['major_participations']}(√)")
        elif guessed_player['major_participations'] > secret_player['major_participations']:
            feedback_parts.append(f"Major次数: {guessed_player['major_participations']}(↓)")
            is_win = False
        else:
            feedback_parts.append(f"Major次数: {guessed_player['major_participations']}(↑)")
            is_win = False

        return " | ".join(feedback_parts), is_win

    async def terminate(self):
        """插件停用时清空状态"""
        self.active_games.clear()
        self.players_list.clear()
        self.players_map.clear()
        logger.info("PlayerGuesser 插件已卸载，所有状态已清空。")