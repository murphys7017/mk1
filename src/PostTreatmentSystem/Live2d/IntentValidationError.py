from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import json, re

EMOTIONS = {"neutral", "happy", "sad", "angry", "surprised", "shy", "thinking"}

@dataclass
class IntentValidationError(Exception):
    message: str
    raw_output: Optional[str] = None

def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _extract_json_obj(text: str) -> Dict[str, Any]:
    # 允许模型偶尔夹带一点点前后文本，但最终必须能解析出一个 {}
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return {}
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

def validate_and_fix_intent(
    llm_output_text: str,
    base_motion_names: List[str],
) -> Dict[str, Any]:
    if not base_motion_names:
        raise IntentValidationError("base_motion_names is empty.", llm_output_text)

    intent = _extract_json_obj(llm_output_text)
    if not intent:
        raise IntentValidationError("LLM output is not a valid JSON object.", llm_output_text)

    # ---- base_motion: 严格校验，不做选择 ----
    base_motion = str(intent.get("base_motion", "")).strip()
    if base_motion not in base_motion_names:
        raise IntentValidationError(
            f"Invalid base_motion='{base_motion}', must be one of candidates.",
            llm_output_text
        )

    # ---- duration ----
    duration = _clip(float(intent.get("duration", 2.8)), 1.2, 6.0)

    # ---- emotion ----
    emotion = str(intent.get("emotion", "neutral")).lower().strip()
    if emotion not in EMOTIONS:
        emotion = "neutral"

    # ---- intensity / energy ----
    intensity = _clip(float(intent.get("intensity", 0.5)), 0.0, 1.0)
    energy = _clip(float(intent.get("energy", 0.5)), 0.0, 1.0)

    # ---- booleans ----
    speaking = bool(intent.get("speaking", True))
    loop = bool(intent.get("loop", False))

    # ---- gaze ----
    gaze = intent.get("gaze") or {}
    gx = _clip(float(gaze.get("x", 0.0)), -1.0, 1.0)
    gy = _clip(float(gaze.get("y", 0.0)), -1.0, 1.0)

    # ---- blink_at: <=3, 0~duration, 去重、排序 ----
    blink_at = intent.get("blink_at") or []
    fixed_blink = []
    for t in blink_at[:3]:
        try:
            fixed_blink.append(round(_clip(float(t), 0.0, duration), 3))
        except Exception:
            pass
    fixed_blink = sorted(set(fixed_blink))
    if not fixed_blink:
        fixed_blink = [round(duration * 0.35, 3)]

    # ---- beats: <=3, t 裁剪，type 固定 emphasis ----
    beats = intent.get("beats") or []
    fixed_beats = []
    for b in beats[:3]:
        if not isinstance(b, dict):
            continue
        try:
            t = round(_clip(float(b.get("t", 0.0)), 0.0, duration), 3)
            fixed_beats.append({"t": t, "type": "emphasis"})
        except Exception:
            pass

    return {
        "base_motion": base_motion,
        "duration": round(duration, 3),
        "emotion": emotion,
        "intensity": round(intensity, 3),
        "speaking": speaking,
        "energy": round(energy, 3),
        "blink_at": fixed_blink,
        "beats": fixed_beats,
        "gaze": {"x": round(gx, 3), "y": round(gy, 3)},
        "loop": loop,
    }
