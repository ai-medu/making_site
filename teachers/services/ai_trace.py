"""마지막으로 응답한 AI 모델 이름을 요청 단위로 전달 (화면에 '어떤 모델이 작성했는지' 보여주기 위함)"""
import threading
import time

_local = threading.local()


def set_model(label):
    _local.label = label
    _local.at = time.monotonic()


def pop_model():
    """성공한 호출의 모델 이름을 돌려주고 비움 (오래된 값이면 None)"""
    label, at = getattr(_local, "label", None), getattr(_local, "at", 0)
    _local.label = None
    return label if label and time.monotonic() - at < 120 else None
