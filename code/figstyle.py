"""보고서 그림 공통 스타일(인쇄용 정적 PNG, 본문 폭 150mm 기준).

dataviz 기본 팔레트 앞 3색(검증 통과: CVD ΔE 9.2, 정상시 ΔE 27.6)과 회색 맥락색만 쓴다.
텍스트는 데이터 색을 입히지 않고 잉크 색으로 쓴다.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GRAY, GRAY_LIGHT = "#a8a7a2", "#d9d8d3"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
GRID = "#e6e5e0"
SURFACE = "#ffffff"

MM = 1 / 25.4
WIDTH = 150 * MM


def setup():
    names = {f.name for f in font_manager.fontManager.ttflist}
    family = "Pretendard" if "Pretendard" in names else "Malgun Gothic"
    plt.rcParams.update({
        "font.family": family,
        "font.size": 7.5,
        "axes.titlesize": 8.5,
        "axes.titleweight": "bold",
        "axes.labelsize": 7.5,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK2,
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.5,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "legend.frameon": False,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.dpi": 300,
        "axes.unicode_minus": False,
    })


def won(x, unit="원"):
    return f"{x:,.0f}{unit}"
