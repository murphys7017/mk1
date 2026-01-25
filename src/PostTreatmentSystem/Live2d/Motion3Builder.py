#!/usr/bin/env python3
"""
Motion3Builder: encapsulate motion generation logic in a class
"""

from __future__ import annotations
import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from LLM.LLMManagement import LLMManagement
from PostTreatmentSystem.HandlerAbstract import Handler
from PostTreatmentSystem.Live2d.IntentValidationError import validate_and_fix_intent
from RawChatHistory.RawChatHistory import RawChatHistory


prompt = """
你是 Live2D 动作意图抽取器。
输入：用户文本的结构化分析（AnalyzeResult）+ 候选基础 motion 文件名列表。
输出：一个 JSON（intent.json），用于后续合成临时 motion3.json。
"""


@dataclass
class Key:
    t: float
    v: float
    interp: str = "linear"


class Motion3Builder(Handler):
    CORE_PARAMS = [
        "ParamAngleX", "ParamAngleY", "ParamAngleZ",
        "ParamEyeLOpen", "ParamEyeROpen",
        "ParamEyeBallX", "ParamEyeBallY",
        "ParamMouthOpenY", "ParamMouthForm",
        "ParamCheek",
    ]

    DEFAULT_RANGES = {
        "ParamAngleX": (-30.0, 30.0),
        "ParamAngleY": (-30.0, 30.0),
        "ParamAngleZ": (-30.0, 30.0),
        "ParamEyeLOpen": (0.0, 1.2),
        "ParamEyeROpen": (0.0, 1.2),
        "ParamEyeBallX": (-1.0, 1.0),
        "ParamEyeBallY": (-1.0, 1.0),
        "ParamMouthOpenY": (0.0, 1.0),
        "ParamMouthForm": (-2.0, 1.0),
        "ParamCheek": (0.0, 1.0),
    }

    def __init__(self,
                 llm_management: LLMManagement,
                  ranges: Optional[Dict[str, Tuple[float, float]]] = None):
        
        self.ranges = dict(ranges or self.DEFAULT_RANGES)
        self.llm_management = llm_management  # assume global instance
        
        self.exp_map: Dict[str, str] = {
            "Angry": json.loads(Path(r"src\PostTreatmentSystem\Live2d\Expressions\Angry.exp3.json").read_text(encoding="utf-8")),
            "Blush": json.loads(Path(r"src\PostTreatmentSystem\Live2d\Expressions\Blush.exp3.json").read_text(encoding="utf-8")),
            "Confused": json.loads(Path(r"src\PostTreatmentSystem\Live2d\Expressions\Confused.exp3.json").read_text(encoding="utf-8")),
            "Embarrassed": json.loads(Path(r"src\PostTreatmentSystem\Live2d\Expressions\Embarrassed.exp3.json").read_text(encoding="utf-8")),
        }
        
        self.motions_map: Dict[str, Any] = {
            '舒适': json.loads(Path(r"src\PostTreatmentSystem\Live2d\motions\舒适.motion3.json").read_text(encoding="utf-8")),
            '自然': json.loads(Path(r"src\PostTreatmentSystem\Live2d\motions\自然.motion3.json").read_text(encoding="utf-8")),
            '活泼': json.loads(Path(r"src\PostTreatmentSystem\Live2d\motions\活泼.motion3.json").read_text(encoding="utf-8")),
            '生气': json.loads(Path(r"src\PostTreatmentSystem\Live2d\motions\生气.motion3.json").read_text(encoding="utf-8")),
            '微笑': json.loads(Path(r"src\PostTreatmentSystem\Live2d\motions\微笑.motion3.json").read_text(encoding="utf-8")),
            '伤心': json.loads(Path(r"src\PostTreatmentSystem\Live2d\motions\伤心.motion3.json").read_text(encoding="utf-8")),
            '微笑-眨眼-右': json.loads(Path(r"src\PostTreatmentSystem\Live2d\motions\微笑-眨眼-右.motion3.json").read_text(encoding="utf-8")),
            '微笑-左偏头': json.loads(Path(r"src\PostTreatmentSystem\Live2d\motions\微笑-左偏头.motion3.json").read_text(encoding="utf-8")),
            # "base_motion_name": "path/to/motion3.json", json.loads(Path(base_motion_path).read_text(encoding="utf-8"))
        }  # cache for base motions

    @staticmethod
    def parse_parameter_curves(motion: dict) -> Dict[str, List[Key]]:
        curves = motion.get("Curves", [])
        out: Dict[str, List[Key]] = {}
        for c in curves:
            if c.get("Target") != "Parameter":
                continue
            pid = c.get("Id")
            segs = c.get("Segments", [])
            if not segs:
                continue

            i = 0
            t0 = float(segs[i]); v0 = float(segs[i+1]); i += 2
            keys = [Key(t=t0, v=v0, interp="linear")]
            while i < len(segs):
                seg_type = int(segs[i]); i += 1
                if seg_type == 0:  # linear: [0, t, v]
                    if i + 1 >= len(segs): break
                    t = float(segs[i]); v = float(segs[i+1]); i += 2
                    keys.append(Key(t=t, v=v, interp="linear"))
                elif seg_type == 1:  # bezier: [1, c1x, c1y, c2x, c2y, t, v]
                    if i + 5 >= len(segs): break
                    t = float(segs[i+4]); v = float(segs[i+5]); i += 6
                    keys.append(Key(t=t, v=v, interp="bezier"))
                elif seg_type == 2:  # stepped
                    if i + 1 >= len(segs): break
                    t = float(segs[i]); v = float(segs[i+1]); i += 2
                    keys.append(Key(t=t, v=v, interp="stepped"))
                elif seg_type == 3:  # inv_stepped
                    if i + 1 >= len(segs): break
                    t = float(segs[i]); v = float(segs[i+1]); i += 2
                    keys.append(Key(t=t, v=v, interp="inv_stepped"))
                else:
                    break

            keys.sort(key=lambda k: k.t)
            out[pid] = keys
        return out

    @staticmethod
    def eval_keys(keys: List[Key], t: float) -> float:
        if not keys:
            return 0.0
        if t <= keys[0].t:
            return keys[0].v
        if t >= keys[-1].t:
            return keys[-1].v

        for i in range(1, len(keys)):
            k0 = keys[i-1]
            k1 = keys[i]
            if t <= k1.t:
                if k1.interp == "stepped":
                    return k0.v
                if k1.interp == "inv_stepped":
                    return k1.v
                dt = (k1.t - k0.t)
                if dt <= 1e-9:
                    return k1.v
                a = (t - k0.t) / dt
                return (1.0 - a) * k0.v + a * k1.v
        return keys[-1].v

    @staticmethod
    def clamp(pid: str, v: float, ranges: Dict[str, Tuple[float, float]]) -> float:
        mn, mx = ranges.get(pid, (-1e9, 1e9))
        return max(mn, min(mx, v))

    @staticmethod
    def blink_multiplier(t: float, blink_at: List[float], close_dur: float = 0.08, open_dur: float = 0.10) -> float:
        for bt in blink_at:
            start = bt
            mid = bt + close_dur
            end = mid + open_dur
            if start <= t <= end:
                if t <= mid:
                    a = (t - start) / max(close_dur, 1e-6)
                    return 1.0 - a
                a = (t - mid) / max(open_dur, 1e-6)
                return a
        return 1.0

    @staticmethod
    def speech_mouth_open(t: float, speaking: bool, energy: float) -> float:
        if not speaking:
            return 0.0
        amp = 0.25 + 0.55 * max(0.0, min(1.0, energy))
        w1 = 2.0 * math.pi * 2.3
        w2 = 2.0 * math.pi * 3.7
        s = 0.55 * (math.sin(w1 * t) * 0.5 + 0.5) + 0.45 * (math.sin(w2 * t + 1.2) * 0.5 + 0.5)
        v = 0.10 + amp * s
        return max(0.0, min(1.0, v))

    @staticmethod
    def head_emphasis_delta(t: float, beats: List[dict], intensity: float) -> float:
        if not beats:
            return 0.0
        inten = max(0.0, min(1.0, intensity))
        delta = 0.0
        for b in beats:
            bt = float(b.get("t", 0.0))
            if abs(t - bt) <= 0.25:
                x = (t - bt) / 0.12
                delta += (math.exp(-0.5 * x * x) * 6.0) * inten
        return delta

    @staticmethod
    def build_linear_segments(keys: List[Tuple[float, float]]) -> List[float]:
        if not keys:
            return []
        out: List[float] = [float(keys[0][0]), float(keys[0][1])]
        for (t, v) in keys[1:]:
            out += [0, float(t), float(v)]
        return out

    def generate_temp_motion(self, base_motion: dict, intent: dict) -> dict:
        meta = base_motion.get("Meta", {})
        fps = float(meta.get("Fps", 30.0))
        duration = float(intent.get("duration", float(meta.get("Duration", 2.0))))
        duration = max(0.2, duration)

        intensity = max(0.0, min(1.0, float(intent.get("intensity", 0.6))))
        energy = max(0.0, min(1.0, float(intent.get("energy", 0.5))))
        speaking = bool(intent.get("speaking", False))
        blink_at = intent.get("blink_at", []) or []
        beats = intent.get("beats", []) or []
        gaze = intent.get("gaze", {}) or {}
        gaze_x = max(-1.0, min(1.0, float(gaze.get("x", 0.0))))
        gaze_y = max(-1.0, min(1.0, float(gaze.get("y", 0.0))))

        base_curves = self.parse_parameter_curves(base_motion)

        dt = 1.0 / fps
        n = int(math.ceil(duration / dt)) + 1
        times = [min(i * dt, duration) for i in range(n)]

        sampled: Dict[str, List[Tuple[float, float]]] = {pid: [] for pid in self.CORE_PARAMS}

        for t in times:
            for pid in self.CORE_PARAMS:
                bv = self.eval_keys(base_curves.get(pid, []), t) if pid in base_curves else 0.0
                v = bv

                if pid in ("ParamEyeLOpen", "ParamEyeROpen"):
                    m = self.blink_multiplier(t, blink_at)
                    v = min(bv, m) if base_curves.get(pid) else m

                elif pid == "ParamMouthOpenY":
                    sv = self.speech_mouth_open(t, speaking, energy)
                    v = max(bv, sv) if base_curves.get(pid) else sv

                elif pid == "ParamAngleY":
                    v = bv + self.head_emphasis_delta(t, beats, intensity)

                elif pid == "ParamEyeBallX":
                    v = (0.85 * bv + 0.15 * gaze_x) if base_curves.get(pid) else gaze_x

                elif pid == "ParamEyeBallY":
                    v = (0.85 * bv + 0.15 * gaze_y) if base_curves.get(pid) else gaze_y

                elif pid == "ParamMouthForm":
                    emo = (intent.get("emotion") or "neutral").lower()
                    target = 0.0
                    if emo in ("happy", "joy", "smile"):
                        target = 0.6
                    elif emo in ("angry", "mad"):
                        target = -0.8
                    elif emo in ("sad", "down"):
                        target = -0.3
                    v = (0.6 * bv + 0.4 * (target * intensity)) if base_curves.get(pid) else (target * intensity)

                elif pid == "ParamCheek":
                    emo = (intent.get("emotion") or "neutral").lower()
                    target = 0.0
                    if emo in ("happy", "joy", "smile", "shy"):
                        target = 0.6
                    v = max(bv, target * intensity) if base_curves.get(pid) else (target * intensity)

                v = self.clamp(pid, v, self.ranges)
                sampled[pid].append((t, v))

        out_curves = []
        for pid, keys in sampled.items():
            vals = [v for _, v in keys]
            if max(vals) - min(vals) < 1e-6 and pid not in ("ParamEyeLOpen", "ParamEyeROpen", "ParamMouthOpenY"):
                continue
            out_curves.append({
                "Target": "Parameter",
                "Id": pid,
                "Segments": self.build_linear_segments(keys),
            })

        out_meta = dict(meta)
        out_meta["Duration"] = float(duration)
        out_meta["Fps"] = float(fps)
        out_meta["Loop"] = bool(intent.get("loop", False))
        out_meta["CurveCount"] = len(out_curves)

        return {
            "Version": base_motion.get("Version", 3),
            "Meta": out_meta,
            "Curves": out_curves,
            "UserData": base_motion.get("UserData", []),
        }
    def render_base_motion_list(self, base_motion_names: list[str]) -> str:
        # 不要加复杂结构，直接可读列表，且保持“精确匹配字符串”可见
        lines = ["<BASE_MOTIONS>"]
        for n in base_motion_names:
            lines.append(f"- {n}")
        lines.append("</BASE_MOTIONS>")
        return "\n".join(lines)

    def build_motion_intent_inputs(self, res: dict, base_motion_names: list[str]) -> dict:
        """Build the `analyze_block` string from the `res` dict.

        Expected `res` format: {"response": str, "ollama": {...}, "ltp": {...}, ...}
        We create a readable block containing these sections so the LLM can consume them.
        """
        lines: List[str] = []
        # Response
        chat_history = res.get("chat_history")
        if chat_history is not None:
            lines.append("【User / Raw Response】")
            lines.append(str(chat_history))
            lines.append("")

        # Ollama analysis (lightweight structured analysis)
        ollama = res.get("ollama")
        if isinstance(ollama, dict) and ollama:
            lines.append("【Ollama 分析】")
            for k, v in ollama.items():
                lines.append(f"- {k}: {v}")
            lines.append("")

        # LTP analysis (tokens, keywords, frames, entities, relations)
        # ltp = res.get("ltp")
        # if isinstance(ltp, dict) and ltp:
        #     lines.append("【LTP 结构化分析】")
        #     # keywords
        #     kw = ltp.get("keywords")
        #     if kw:
        #         lines.append("- keywords: " + ", ".join(map(str, kw)))

        #     # tokens (show up to first 40 tokens to avoid verbosity)
        #     tokens = ltp.get("tokens")
        #     if tokens:
        #         try:
        #             tok_texts = [t[0] for t in tokens[:40]]
        #             lines.append("- tokens: " + ", ".join(tok_texts))
        #         except Exception:
        #             lines.append("- tokens: (unavailable)")

        #     # frames
        #     frames = ltp.get("frames")
        #     if frames:
        #         # frames may be objects; try to present succinct info
        #         try:
        #             frame_summaries = []
        #             for f in frames[:10]:
        #                 if hasattr(f, "predicate"):
        #                     pred = getattr(f, "predicate", "")
        #                 else:
        #                     pred = getattr(f, "text", str(f))
        #                 frame_summaries.append(str(pred))
        #             lines.append("- frames: " + ", ".join(frame_summaries))
        #         except Exception:
        #             lines.append("- frames: (unavailable)")

        #     # entities
        #     entities = ltp.get("entities")
        #     if entities:
        #         try:
        #             ent_texts = [e.text if hasattr(e, 'text') else str(e) for e in entities[:40]]
        #             lines.append("- entities: " + ", ".join(ent_texts))
        #         except Exception:
        #             lines.append("- entities: (unavailable)")

        #     # relations
        #     relations = ltp.get("relations")
        #     if relations:
        #         try:
        #             rel_texts = []
        #             for r in relations[:40]:
        #                 if hasattr(r, 'subject') and hasattr(r, 'obj'):
        #                     rel_texts.append(f"{r.subject}-{r.relation}-{r.obj}")
        #                 else:
        #                     rel_texts.append(str(r))
        #             lines.append("- relations: " + ", ".join(rel_texts))
        #         except Exception:
        #             lines.append("- relations: (unavailable)")

            # # normalized text
            # norm = ltp.get("normalized_text")
            # if norm:
            #     lines.append("- normalized_text: " + str(norm))

            # lines.append("")

        # Fallback: if no structured results, include raw res as JSON
        if not lines:
            try:
                analyze_block = json.dumps(res, ensure_ascii=False, indent=2)
            except Exception:
                analyze_block = str(res)
        else:
            analyze_block = "\n".join(lines)

        base_motion_list = self.render_base_motion_list(base_motion_names)
        return {"analyze_block": analyze_block, "base_motion_list": base_motion_list}

    def gen_motion_intent(
        self,
        res: dict,
        base_motion_names: list[str],
    ) -> dict:
        inputs = self.build_motion_intent_inputs(res, base_motion_names)

        # 如果你想要 OllamaFormated 返回 dict：就走 generate()
        raw = self.llm_management.generate("motion_intent", **inputs)

        # 但你的 OllamaFormated 很可能已经解析为 dict 了；
        # 这里建议统一走 “string -> validate”，更可控：
        # 如果 raw 已经是 dict，可以 json.dumps 再校验；否则直接当 str
        if isinstance(raw, dict):
            text = json.dumps(raw, ensure_ascii=False)
        else:
            text = str(raw)

        return validate_and_fix_intent(text, base_motion_names)


    def build(self, res: dict) -> dict:


        intent = self.gen_motion_intent(
            res=res,
            base_motion_names=list(self.motions_map.keys()),
        )
        if 'base_motion' in intent:
            base_motion = self.motions_map[intent["base_motion"]]
        else:
            base_motion = list(self.motions_map.values())[0]
            logger.error("intent must include 'base_motion_path'")


        return self.motions_map['微笑-眨眼-右']
    
    def handler(self, raw_history: RawChatHistory, res: dict) -> dict:
        temp_motion = self.build(res)
        res["motion3"] = temp_motion
        return res