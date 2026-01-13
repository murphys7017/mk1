from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional


class DecisionType(str, Enum):
    SUMMARIZE = "summarize"
    SKIP = "skip"
    WAIT = "wait"


SummaryAction = Literal["merge", "new", "none"]


@dataclass(frozen=True, slots=True)
class SummaryDecision:
    """
    强约束返回值：
    - type=SUMMARIZE -> split_index 必须是 int 且 >= 0
    - type!=SUMMARIZE -> split_index 必须为 None
    - summary_action:
        - SUMMARIZE: 只能是 "merge" 或 "new"
        - SKIP: 只能是 "none"
        - WAIT: 可以为 None（或 "none" 也行，但我更建议 None）
    """

    type: DecisionType
    reason: str

    split_index: Optional[int] = None
    summary_action: Optional[SummaryAction] = None

    def __post_init__(self):
        # 统一 reason
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("SummaryDecision.reason must be a non-empty string")

        # split_index invariant
        if self.type is DecisionType.SUMMARIZE:
            if self.split_index is None:
                raise ValueError("SUMMARIZE decision requires split_index")
            if not isinstance(self.split_index, int):
                raise TypeError("split_index must be int")
            if self.split_index < 0:
                raise ValueError("split_index must be >= 0 for SUMMARIZE decision")
        else:
            if self.split_index is not None:
                raise ValueError("Non-SUMMARIZE decision must not have split_index")

        # summary_action invariant
        if self.type is DecisionType.SUMMARIZE:
            if self.summary_action not in ("merge", "new"):
                raise ValueError("SUMMARIZE decision summary_action must be 'merge' or 'new'")
        elif self.type is DecisionType.SKIP:
            if self.summary_action not in (None, "none"):
                raise ValueError("SKIP decision summary_action must be 'none' or None")
        elif self.type is DecisionType.WAIT:
            # WAIT 不需要 action（也可以允许 "none"，看你习惯）
            if self.summary_action not in (None, "none"):
                raise ValueError("WAIT decision summary_action must be None (or 'none')")
