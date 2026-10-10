"""그림3. 분석결과 요약 인포그래픽(양식의 '분석결과 이미지(필수)' 칸).

네 개의 수치 타일: 차량 자원 / 접근 격차 / 택시형 대비 / 신규 공급 대비. 값은 모두 결과 JSON에서 읽는다.
"""
import json

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from common import CLEAN, FIG
from figstyle import BLUE, GRAY, INK, INK2, MM, MUTED, ORANGE, WIDTH, setup


def main():
    setup()
    a1 = json.loads((CLEAN / "A1_results.json").read_text(encoding="utf-8"))
    a3 = json.loads((CLEAN / "A3_results.json").read_text(encoding="utf-8"))
    a4 = json.loads((CLEAN / "A4_results.json").read_text(encoding="utf-8"))
    dep, nat = a1["groups"]["인구감소지역"], a1["groups"]["전국"]
    app = {r["scenario"]: r for r in a3["gokseong_application"]}
    m1 = app["면 1곳(연 2,496회)에 DRT 1대 신규 투입"]

    tiles = [
        ("차량 자원", f"{dep['agg_car_per_1000']:,.0f}대",
         ["인구감소지역 92곳", "인구 1천 명당 자가용 승용차", f"(전국 {nat['agg_car_per_1000']:,.0f}대)"], BLUE),
        ("의료 접근 격차", f"{dep['min_clinic_pt_median']:.0f}분 : {dep['min_clinic_car_median']:.0f}분",
         ["병·의원 평균 접근시간", "대중교통 : 승용차", "(인구감소지역 중앙값)"], ORANGE),
        ("택시형 대비", f"{a3['saving_vs_taxi_empty']*100:.0f}~{a3['saving_vs_taxi_round']*100:.0f}% 절감",
         ["주민차량 1회 공공지출", "곡성 효도택시 대비", "(빈차 귀가~동행 왕복)"], BLUE),
        ("신규 차량 투입 대비", f"{m1['saving_pct_empty']*100:.0f}~{m1['saving_pct_round']*100:.0f}% 절감",
         ["면 단위 수요에 DRT 1대", "신규 투입 대비", f"(손익분기 연 {a3['q_star_drt_trips']:,.0f}회)"], ORANGE),
    ]
    fig = plt.figure(figsize=(WIDTH, 62 * MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for i, (head, big, sub, color) in enumerate(tiles):
        x0 = i + 0.04
        ax.add_patch(FancyBboxPatch((x0, 0.22), 0.92, 0.74, boxstyle="round,pad=0,rounding_size=0.04",
                                    fc="#f6f6f4", ec="none"))
        ax.add_patch(FancyBboxPatch((x0, 0.93), 0.92, 0.03, boxstyle="square,pad=0", fc=color, ec="none"))
        ax.text(x0 + 0.46, 0.83, head, ha="center", va="center", fontsize=8, color=INK2, fontweight="bold")
        ax.text(x0 + 0.46, 0.64, big, ha="center", va="center", fontsize=12.5, color=INK, fontweight="bold")
        ax.text(x0 + 0.46, 0.38, chr(10).join(sub), ha="center", va="center", fontsize=6.4, color=INK2,
                linespacing=1.4)
    ax.text(2, 0.09, f"일본 교통공백지 자가용 유상운송: {int(a4['values']['jp_orgs_2026']):,}개 단체·"
            f"{int(a4['values']['jp_vehicles_2026']):,}대, 전체 시정촌의 {a4['jp_munis_share_2026']:.0%} 도입(2026.3)",
            ha="center", va="center", fontsize=7, color=INK)
    fig.savefig(FIG / "fig3_summary.png", dpi=300)
    print("saved fig3")


if __name__ == "__main__":
    main()
