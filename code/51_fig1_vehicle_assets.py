"""그림1. 차량은 있다, 대중교통은 멀다.

(가) 전국 230개 시군구: x=병·의원 대중교통 평균접근시간(낮 12~14시), y=인구 1천 명당 자가용 승용차
(나) 곡성군 읍면: 병·의원 접근시간(승용차 vs 대중교통) + 개인소유 차량 대수
"""
import json

import matplotlib.pyplot as plt
import pandas as pd

from common import CLEAN, FIG
from figstyle import AQUA, BLUE, GRAY, GRAY_LIGHT, INK, INK2, MM, MUTED, ORANGE, WIDTH, setup


def main():
    setup()
    df = pd.read_csv(CLEAN / "A1_sigungu.csv")
    emd = pd.read_csv(CLEAN / "A1_gokseong_emd.csv")
    res = json.loads((CLEAN / "A1_results.json").read_text(encoding="utf-8"))
    nat = res["groups"]["전국"]["agg_car_per_1000"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(WIDTH, 72 * MM), gridspec_kw={"width_ratios": [1.15, 1]})

    # (가) 산점도
    styles = [("기타 지역", GRAY, 9, "기타 시군구"),
              ("인구감소관심지역", BLUE, 12, "인구감소관심지역(18)"),
              ("인구감소지역", ORANGE, 14, "인구감소지역(92)")]
    for key, color, size, label in styles:
        g = df[df.area_type == key]
        n = len(g) if key == "기타 지역" else None
        ax1.scatter(g.min_clinic_pt, g.car_per_1000, s=size, c=color, linewidths=0.6, edgecolors="white",
                    label=label if key != "기타 지역" else f"기타 시군구({len(g)})", zorder=3 if key != "기타 지역" else 2)
    ax1.axhline(nat, color=INK2, lw=0.8, zorder=1)
    ax1.text(118, nat + 8, f"전국 {nat:,.0f}대", ha="right", va="bottom", color=INK2, fontsize=6.5)
    gk = df[(df.sido == "전남광주") & (df.sigungu == "곡성군")].iloc[0]
    ax1.annotate("곡성군", (gk.min_clinic_pt, gk.car_per_1000), xytext=(gk.min_clinic_pt + 14, gk.car_per_1000 + 95),
                 fontsize=6.5, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.5))
    ax1.set_xlim(0, 120)
    ax1.set_ylim(150, 750)
    ax1.set_xlabel("병·의원까지 대중교통·도보 평균 접근시간(분, 낮 시간대)")
    ax1.set_ylabel("인구 1천 명당 자가용 승용차(대)")
    ax1.set_title("(가) 전국 230개 시군구", loc="left")
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, handletextpad=0.1,
               columnspacing=0.8, markerscale=1.3)

    # (나) 곡성 읍면: 접근시간 막대 + 차량 대수 라벨
    e = emd.copy()
    e = e[e.emd != "오곡면"].sort_values("min_clinic_pt")  # 오곡면은 승용차 시간이 대중교통보다 긴 이상값이라 제외
    y = range(len(e))
    h = 0.36
    ax2.barh([i + h / 2 for i in y], e.min_clinic_pt, height=h, color=ORANGE, label="대중교통·도보")
    ax2.barh([i - h / 2 for i in y], e.min_clinic_car, height=h, color=BLUE, label="승용차")
    for i, (_, r) in zip(y, e.iterrows()):
        pt = ">120분" if r.cens_clinic_pt else f"{r.min_clinic_pt:.0f}분"
        ax2.text(min(r.min_clinic_pt, 120) + 2, i + h / 2, pt, va="center", fontsize=6, color=INK2)
        ax2.text(180, i, f"{r.private_vehicles_2021:,.0f}대", va="center", ha="right", fontsize=6.3, color=INK)
    ax2.text(180, len(e) - 0.5, "개인소유 차량\n(2021년 말)", va="bottom", ha="right", fontsize=5.8,
             color=MUTED, linespacing=1.0)
    ax2.set_yticks(list(y))
    ax2.set_yticklabels(e.emd)
    ax2.set_xlim(0, 182)
    ax2.set_xticks([0, 30, 60, 90, 120])
    ax2.grid(axis="y", visible=False)
    ax2.set_xlabel("병·의원까지 평균 접근시간(분)")
    ax2.set_title("(나) 곡성군 읍면", loc="left")
    ax2.legend(loc="upper center", bbox_to_anchor=(0.4, -0.2), ncol=2, handlelength=1.0)

    fig.tight_layout(w_pad=1.2)
    out = FIG / "fig1_vehicle_assets.png"
    fig.savefig(out, bbox_inches="tight")
    print("saved", out)


if __name__ == "__main__":
    main()
