"""그림2. (가) 이용자 1명당 공공지출 비교, (나) 생활권 연간 수요별 연간 공공지출과 손익분기.

(가) 모든 막대는 '이용자 1명(연인원)당 공공지출'. 주민차량은 1회 공공지출을 곡성 효도택시 운행당 탑승인원으로 나눈다.
(나) DRT는 완주 행복콜버스 대당 운영비(2026)+차량 연할, 대당 연 이용 실적(2024)을 넘으면 1대씩 늘린다.
"""
import json

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch

from common import CLEAN, FIG
from figstyle import BLUE, GRAY, INK, INK2, MM, ORANGE, WIDTH, setup


def main():
    setup()
    a2 = json.loads((CLEAN / "A2_results.json").read_text(encoding="utf-8"))
    a3 = json.loads((CLEAN / "A3_results.json").read_text(encoding="utf-8"))
    be = pd.read_csv(CLEAN / "A3_breakeven.csv")
    pax = a3["pax_per_trip"]
    drt_low = a3["drt_fixed_per_vehicle"] / (a3["myeon_trips"] * pax)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(WIDTH, 70 * MM), gridspec_kw={"width_ratios": [1.05, 1]})

    rows = [
        ("주민차량(동행 왕복)", a3["round_trip"]["public"] / pax, BLUE),
        ("주민차량(빈차 귀가)", a3["base"]["public"] / pax, BLUE),
        ("완주 으뜸택시", a2["wanju_taxi_per_pax"], GRAY),
        ("농촌형 교통모델 전국", a2["mafra_public_per_user_2025"], GRAY),
        ("곡성 효도택시", a2["gokseong_taxi_per_pax"], GRAY),
        ("완주 행복콜버스(DRT)", a2["wanju_callbus_per_pax_incl_vehicle"], GRAY),
        ("DRT 1대를 곡성 면에", drt_low, ORANGE),
    ][::-1]
    y = list(range(len(rows)))
    ax1.barh(y, [r[1] for r in rows], height=0.58, color=[r[2] for r in rows])
    for i, (lab, v, c) in zip(y, rows):
        ax1.text(v + 500, i, f"{v:,.0f}", va="center", fontsize=6.3, color=INK)
    ax1.set_yticks(y)
    ax1.set_yticklabels([r[0] for r in rows], fontsize=6.5)
    ax1.set_xlim(0, 38000)
    ax1.set_xticks([0, 10000, 20000, 30000])
    ax1.xaxis.set_major_formatter(lambda x, _: f"{x / 1000:,.0f}천")
    ax1.grid(axis="y", visible=False)
    ax1.set_xlabel("이용자 1명당 공공지출(원)", fontsize=6.8)
    ax1.set_title("(가) 이용자 1명당 공공지출", loc="left", fontsize=7.8)
    ax1.legend(handles=[Patch(color=GRAY, label="기존 대안 실적"), Patch(color=ORANGE, label="같은 수요에 신규 차량"),
                        Patch(color=BLUE, label="주민차량(모형)")],
               loc="upper center", bbox_to_anchor=(0.42, -0.2), ncol=3, fontsize=6, handlelength=0.9,
               columnspacing=0.8)

    be = be[be.trips <= 16000]
    x = be.trips
    ax2.plot(x, be.drt / 1e8, color=ORANGE, lw=1.8, label="DRT 신규 투입", drawstyle="steps-post")
    ax2.fill_between(x, be.resident_round / 1e8, be.resident / 1e8, color=BLUE, alpha=0.12, lw=0)
    ax2.plot(x, be.resident / 1e8, color=BLUE, lw=1.8, label="주민차량(빈차 귀가)")
    ax2.plot(x, be.resident_round / 1e8, color=BLUE, lw=1.1, ls=(0, (1, 1.5)), label="주민차량(동행 왕복)")
    ax2.plot(x, be.taxi_type / 1e8, color=INK2, lw=0.9, ls=(0, (5, 3)), label="택시형(효도택시 단가)", zorder=4)
    m = a3["myeon_trips"]
    ax2.axvline(m, color=INK2, lw=0.5)
    ax2.text(m + 250, 1.75, f"곡성 면 평균\n연 {m:,.0f}회", fontsize=5.8, color=INK2, va="top", linespacing=1.1)
    q = a3["q_star_drt_trips"]
    ax2.plot([q], [a3["drt_fixed_per_vehicle"] / 1e8], "o", ms=4, color=INK, mec="white", mew=1, zorder=5)
    ax2.annotate(f"손익분기\n연 {q:,.0f}회", (q, a3["drt_fixed_per_vehicle"] / 1e8), xytext=(q + 1500, 0.45),
                 fontsize=5.8, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.5), linespacing=1.1)
    ax2.set_xlim(0, 16000)
    ax2.set_ylim(0, 2.3)
    ax2.set_xticks([0, 4000, 8000, 12000, 16000])
    ax2.xaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    ax2.yaxis.set_major_formatter(lambda v, _: f"{v:.1f}")
    ax2.tick_params(labelsize=6.3)
    ax2.set_xlabel("생활권 연간 운행 수요(회)", fontsize=6.8)
    ax2.set_ylabel("연간 공공지출(억 원)", fontsize=6.8)
    ax2.set_title("(나) 수요별 연간 공공지출", loc="left", fontsize=7.8)
    ax2.legend(loc="upper center", bbox_to_anchor=(0.45, -0.2), ncol=2, fontsize=6, handlelength=1.8,
               columnspacing=0.8)
    fig.tight_layout(w_pad=1.0)
    fig.savefig(FIG / "fig2_costs.png", bbox_inches="tight")
    print("saved fig2_costs")


if __name__ == "__main__":
    main()
