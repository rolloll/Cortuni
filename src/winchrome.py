"""tkinter가 직접 다루지 못하는 Windows 전용 창 동작 두 가지: DPI 인식, DWM 타이틀바 색.

tkinter는 OS 타이틀바(최소화/최대화/닫기 버튼이 있는 그 부분)를 직접 그리지
않는다. 그래서 앱 내부 테마를 라이트/다크로 바꿔도 타이틀바만 항상 OS 기본색
(밝은 흰색)으로 남아, 다크 모드나 새 배색과 어긋나 보인다. DWM의 확장 창 속성
(Windows 10 2004+/11)으로 타이틀바 배경·글자색을 앱 토큰에 맞춰 재도색한다.
지원하지 않는 OS/빌드에서는 호출이 조용히 실패하도록 반환값을 확인하지 않는다.

DPI 인식(enable_dpi_awareness)도 마찬가지로 tkinter가 대신 해주지 않는 부분이다 -
이걸 켜지 않으면(기본값) 100% 배율이 아닌 화면에서 Windows가 창 전체를 비트맵으로
확대해서 그리므로, 한글 글꼴을 포함한 모든 텍스트가 흐릿/뭉개져 보인다.
"""

import ctypes
import sys
from ctypes import wintypes

_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_CAPTION_COLOR = 35
_DWMWA_TEXT_COLOR = 36
_SPI_GETWORKAREA = 0x0030


def get_work_area():
    """작업 표시줄을 뺀 주 모니터의 작업 영역을(가로, 세로) 픽셀로 반환한다.

    비-Windows거나 API 호출이 실패하면 None - 호출하는 쪽에서 안전한 기본값으로
    대체해야 한다(예: 창 기본 크기가 화면보다 커서 아래쪽이 잘리는 것을 막을 때).
    """
    if sys.platform != "win32":
        return None
    try:
        rect = wintypes.RECT()
        ok = ctypes.windll.user32.SystemParametersInfoW(_SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
        if not ok:
            return None
        return rect.right - rect.left, rect.bottom - rect.top
    except Exception:
        return None


def enable_dpi_awareness():
    """창별(모니터별) DPI 인식을 요청한다 - 반드시 첫 Tk 창을 만들기 '전에' 호출해야 한다.

    Windows 버전에 따라 지원하는 API가 다르므로 최신 것부터 순서대로 시도한다:
    PER_MONITOR_AWARE_V2(10 1703+) -> PER_MONITOR_DPI_AWARE(8.1+) -> SYSTEM_DPI_AWARE(Vista+).
    """
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)  # PER_MONITOR_AWARE_V2
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()  # PROCESS_SYSTEM_DPI_AWARE
    except Exception:
        pass


def _colorref(hex_color):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return r | (g << 8) | (b << 16)


def apply_titlebar_theme(hwnd, dark, bg_hex, text_hex):
    """hwnd의 타이틀바를 다크/라이트 및 배경·글자색에 맞춘다."""
    if sys.platform != "win32" or not hwnd:
        return
    try:
        dwmapi = ctypes.windll.dwmapi
    except OSError:
        return

    def _set(attr, value):
        c = ctypes.c_int(value)
        dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), attr, ctypes.byref(c), ctypes.sizeof(c))

    try:
        _set(_DWMWA_USE_IMMERSIVE_DARK_MODE, 1 if dark else 0)
        _set(_DWMWA_CAPTION_COLOR, _colorref(bg_hex))
        _set(_DWMWA_TEXT_COLOR, _colorref(text_hex))
    except Exception:
        pass
