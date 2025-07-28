from dataclasses import dataclass
from typing import Optional

@dataclass
class Player:
    """
    用于存储选手信息的数据类。
    """
    name: str
    age: int
    role: str
    nationality: str
    continent: str
    club: Optional[str]  # 退役选手可能没有俱乐部
    major_participations: int