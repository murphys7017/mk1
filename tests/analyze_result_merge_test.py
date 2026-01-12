from __future__ import annotations


from DataClass.AnalyzeResult import AnalyzeResult


def test_merge_keeps_is_question_false():
    a = AnalyzeResult()
    b = AnalyzeResult(is_question=False)
    merged = AnalyzeResult.merge_analyze_results([a, b])
    assert merged.is_question is False


def test_merge_keeps_is_question_true_priority():
    a = AnalyzeResult(is_question=False)
    b = AnalyzeResult(is_question=True)
    merged = AnalyzeResult.merge_analyze_results([a, b])
    assert merged.is_question is True


def test_merge_keeps_is_self_reference():
    a = AnalyzeResult(is_self_reference=False)
    merged = AnalyzeResult.merge_analyze_results([a])
    assert merged.is_self_reference is False


def test_merge_emotion_cues_dedup_keep_order():
    a = AnalyzeResult(emotion_cues=["sad", " angry "])
    b = AnalyzeResult(emotion_cues=["sad", "happy"])
    merged = AnalyzeResult.merge_analyze_results([a, b])
    assert merged.emotion_cues == ["sad", "angry", "happy"]
