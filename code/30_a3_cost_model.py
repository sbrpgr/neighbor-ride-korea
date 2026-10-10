"""A3. 주민차량 운송의 건당 비용과 기존 대안 대비 경제성.

1건 = 승객을 태운 편도 차량 운행 1회(곡성 효도택시 '운행회'와 같은 단위).

  주민차량 건당 총비용 C = 차량실비 + 수고보상 + 운행보험 + 안전·등록비 + 정산·관리비
     차량실비   = 주행거리 x v           v = 유류비(시장가 환산) + 엔진오일 + 타이어 + 유지관리 (감가상각 제외)
     주행거리   = d x (1 + e)            d 승객 편도거리, e 빈차 귀가 비율(빈차 귀가 1, 동행 왕복 0)
     수고보상   = 최저임금 x 소요시간     소요시간 = 주행거리 / 속도 + 승하차·대기 t0
     운행보험   = 10분당 보험료 x 승객위험 가중 x 올림(소요시간/10)
     안전·등록  = 운전자 1인 연 비용 / 운전자 1인 연 운행건수
     정산·관리  = 건당 m
  공공지출 = C - 본인부담 f (효도택시 최저 본인부담 100원을 똑같이 적용)

비교 대안(관측): 곡성 효도택시 운행당 공공지출, 완주군 택시운임 고시, 완주 행복콜버스 대당 운영비
출력: A3_sources.csv, A3_params.csv, A3_cost_breakdown.csv, A3_sensitivity.csv,
      A3_distance_curve.csv, A3_breakeven.csv, A3_gokseong_application.csv, A3_results.json
"""
import itertools
import json
import math
import re

import numpy as np
import pandas as pd
import pdfplumber

from common import CLEAN, RAW, save_json

A2 = json.loads((CLEAN / "A2_results.json").read_text(encoding="utf-8"))

# ------------------------------------------------------------------ 원문 대조 대상
GUIDE = "cost_params/MOLIT_TransportFacilityInvestmentGuideline_8th_draft_2026-03-13.pdf"
SRC = [
    # id, 값, 단위, 설명, 파일, 쪽, 원문 문자열
    ("voc_dep_40", 262.0, "원/km", "승용차 감가상각비(40km/h, 2024년 기준)", GUIDE, 238, "40 262.0 115.6 10.5 10.7 26.4 425.2"),
    ("voc_fuel_40", 115.6, "원/km", "승용차 유류비(40km/h, 세금 제외)", GUIDE, 238, "40 262.0 115.6"),
    ("voc_oil_40", 10.5, "원/km", "승용차 엔진오일비(40km/h)", GUIDE, 238, "115.6 10.5"),
    ("voc_tire_40", 10.7, "원/km", "승용차 타이어마모비(40km/h)", GUIDE, 238, "10.5 10.7"),
    ("voc_maint_40", 26.4, "원/km", "승용차 유지관리비(40km/h)", GUIDE, 238, "10.7 26.4"),
    ("voc_total_40", 425.2, "원/km", "승용차 차량운행비용 합계(40km/h)", GUIDE, 238, "26.4 425.2"),
    ("voc_fuel_avg", 101.5, "원/km", "승용차 유류비 원단위(평균)", GUIDE, 235, "10.3 101.5"),
    ("car_fuel_eff", 10.3, "km/L", "승용차 평균 연비", GUIDE, 235, "승용 10.3"),
    ("vot_car_nonwork", 15_205, "원/인·시", "승용차 비업무통행 시간가치(참고)", GUIDE, 223, "15,205"),
    ("min_wage_2026", 10_320, "원/시간", "2026년 적용 최저임금", "cost_params/MOEL_MinimumWage2026_Notice2025-47.pdf", 1,
     "10,320원"),
    ("ins_onoff_10min", 178, "원/10분", "승용차 유상운송 단체(On-Off) 특약, 자기차량손해 포함",
     "cost_params/FSS_press_2020-07-23_private_car_paid_cargo_rider_premium.pdf", 3, "10분당 178원"),
    ("ins_personal_base", 650_000, "원/년", "개인용 자동차보험 평균(2019)",
     "cost_params/FSS_press_2020-07-23_private_car_paid_cargo_rider_premium.pdf", 2, "65만원 91만원"),
    ("ins_personal_rider", 910_000, "원/년", "유상운송 상시보장 특약 가입 시 평균(2019)",
     "cost_params/FSS_press_2020-07-23_private_car_paid_cargo_rider_premium.pdf", 3, "65만원 → 특약 가입시 : 91만원"),
    ("ins_no_small_car_rider", 6, "인승", "6인승 이하 승용차는 유상운송특약 가입불가(화물 특약 도입 전)",
     "cost_params/FSS_press_2020-07-23_private_car_paid_cargo_rider_premium.pdf", 2, "6인승 이하 승용차는 유상운송특약에 가입불가"),
    ("ins_daein1_cap", 150_000_000, "원", "특약 미가입 유상운송 사고 시 대인Ⅰ(사망 1.5억 원 한도)만 보상",
     "cost_params/FSS_press_2020-07-23_private_car_paid_cargo_rider_premium.pdf", 2, "대인Ⅰ(사망시 1.5억원 한도)만 보상"),
    ("taxi_base_fare", 5_000, "원", "완주군 중형택시 기본요금(2km)", "taxi/wanju_taxi_fare_notice_2023-78_converted.pdf", 1,
     "5,000원"),
    ("taxi_base_km", 2.0, "km", "기본거리", "taxi/wanju_taxi_fare_notice_2023-78_converted.pdf", 1, "2km까지"),
    ("taxi_unit_fare", 163, "원", "거리운임 단위요금", "taxi/wanju_taxi_fare_notice_2023-78_converted.pdf", 1, "163원"),
    ("taxi_unit_m", 134, "m", "거리운임 단위거리", "taxi/wanju_taxi_fare_notice_2023-78_converted.pdf", 1, "134m당"),
    ("taxi_outside_surcharge", 0.20, "비율", "사업구역 밖 시계외 할증", "taxi/wanju_taxi_fare_notice_2023-78_converted.pdf", 1,
     "사업구역외 20%"),
]


def opinet_avg_2026():
    """오피넷 월간 보통휘발유 2026.1~9 평균(스냅샷 텍스트에서 계산)."""
    s = (RAW / "cost_params" / "Opinet_KNOC_avg_retail_fuel_prices_snapshot_2026-10-10.txt").read_text(encoding="utf-8")
    vals = [float(m.group(1).replace(",", "")) for m in
            re.finditer(r"2026년0[1-9]월\s+[\d,.]+\s+([\d,.]+)", s)]
    assert len(vals) == 9, vals
    y2025 = float(re.search(r"2025년\s+[\d,.]+\s+([\d,.]+)", s).group(1).replace(",", ""))
    peak = max(vals)
    return sum(vals) / len(vals), y2025, peak


def verify():
    rows, cache = [], {}
    for sid, val, unit, desc, rel, page, needle in SRC:
        key = (rel, page)
        if key not in cache:
            with pdfplumber.open(RAW / rel) as pdf:
                cache[key] = re.sub(r"\s+", " ", pdf.pages[page - 1].extract_text() or "")
        ok = re.sub(r"\s+", " ", needle) in cache[key]
        rows.append({"id": sid, "value": val, "unit": unit, "desc": desc, "file": rel, "pdf_page": page,
                     "needle": needle, "verified": "ok" if ok else "NOT FOUND"})
    df = pd.DataFrame(rows)
    if (df.verified != "ok").any():
        raise SystemExit("원문 대조 실패\n" + df[df.verified != "ok"].to_string())
    return df


SRCDF = verify()
V = dict(zip(SRCDF.id, SRCDF.value))
FUEL_2026, FUEL_2025, FUEL_PEAK = opinet_avg_2026()


def fuel_per_km(price, speed_factor=V["voc_fuel_40"] / V["voc_fuel_avg"]):
    """시장가 연료비(원/km) = 휘발유가 / 평균연비 x (40km/h 유류비 / 평균 유류비)."""
    return price / V["car_fuel_eff"] * speed_factor


# ------------------------------------------------------------------ 매개변수
P = {
    "fuel_price": dict(v=FUEL_2026, unit="원/L", kind="관측", src="오피넷 보통휘발유 2026.1~9월 평균"),
    "nonfuel": dict(v=V["voc_oil_40"] + V["voc_tire_40"] + V["voc_maint_40"], unit="원/km", kind="관측",
                    src="투자평가지침 엔진오일+타이어+유지관리(40km/h)"),
    "depreciation": dict(v=0.0, unit="원/km", kind="원칙", src="기존 보유 차량: 구입비 성격의 감가상각 제외(민감도에서 포함)"),
    "wage": dict(v=V["min_wage_2026"], unit="원/시간", kind="관측", src="2026년 최저임금"),
    "speed": dict(v=40.0, unit="km/h", kind="가정", src="농촌 지방도·군도 평균 주행속도(지침 원단위 속도와 일치)"),
    "t0": dict(v=10.0, unit="분/건", kind="가정", src="승하차 보조·대기"),
    "empty": dict(v=1.0, unit="배", kind="가정", src="빈차 귀가 1(보수), 동행 왕복 0"),
    "ins_10min": dict(v=V["ins_onoff_10min"], unit="원/10분", kind="관측", src="금감원 On-Off형 단체특약(자차 포함)"),
    "ins_mult": dict(v=2.0, unit="배", kind="가정", src="화물 특약 대비 승객 운송 위험 가중"),
    "safety": dict(v=50_000.0, unit="원/인·년", kind="가정", src="안전교육·차량점검·자격조회"),
    "trips_per_driver": dict(v=120.0, unit="건/인·년", kind="가정", src="월 10건(원제안 상한 월 30회의 1/3)"),
    "mgmt": dict(v=500.0, unit="원/건", kind="가정", src="정산·운행기록(효도택시 콜센터 공용)"),
    "fee": dict(v=100.0, unit="원/건", kind="관측", src="곡성 효도택시 최저 본인부담"),
}
TAXI = {"base_fare": V["taxi_base_fare"], "base_km": V["taxi_base_km"], "unit_fare": V["taxi_unit_fare"],
        "unit_m": V["taxi_unit_m"], "outside": V["taxi_outside_surcharge"]}


def resident_cost(d, **over):
    q = {k: v["v"] for k, v in P.items()}
    q.update(over)
    km = d * (1 + q["empty"])
    v = fuel_per_km(q["fuel_price"]) + q["nonfuel"] + q["depreciation"]
    minutes = km / q["speed"] * 60 + q["t0"]
    if "ins_annual" in q:
        ins = q["ins_annual"] / q["trips_per_driver"]
    else:
        ins = q["ins_10min"] * q["ins_mult"] * math.ceil(minutes / 10)
    parts = {"vehicle": km * v, "effort": q["wage"] * minutes / 60, "insurance": ins,
             "safety": q["safety"] / q["trips_per_driver"], "mgmt": q["mgmt"]}
    total = sum(parts.values())
    return {**parts, "total": total, "public": total - q["fee"], "km": km, "minutes": minutes, "v_per_km": v}


def taxi_fare(d, outside=False):
    t = TAXI
    extra = max(0.0, d - t["base_km"]) * 1000 / t["unit_m"] * t["unit_fare"]
    return (t["base_fare"] + extra) * (1 + (t["outside"] if outside else 0))


def implied_distance(total_fare):
    t = TAXI
    return t["base_km"] + (total_fare - t["base_fare"]) / t["unit_fare"] * t["unit_m"] / 1000


def main():
    SRCDF.to_csv(CLEAN / "A3_sources.csv", index=False, encoding="utf-8-sig")
    gk_trip = A2["gokseong_taxi_per_trip"]
    pax = A2["gokseong_pax_per_trip"]
    fee = P["fee"]["v"]
    d0 = implied_distance(gk_trip + fee)

    base = resident_cost(d0)
    rt = resident_cost(d0, empty=0.0)

    brk = pd.DataFrame([
        {"item": "차량 실비(유류·엔진오일·타이어·유지관리)", "empty_return": base["vehicle"], "round_trip": rt["vehicle"]},
        {"item": "수고보상(최저임금 x 소요시간)", "empty_return": base["effort"], "round_trip": rt["effort"]},
        {"item": "운행보험(단체 On-Off형 x 2)", "empty_return": base["insurance"], "round_trip": rt["insurance"]},
        {"item": "안전교육·점검·자격조회", "empty_return": base["safety"], "round_trip": rt["safety"]},
        {"item": "정산·운행기록", "empty_return": base["mgmt"], "round_trip": rt["mgmt"]},
        {"item": "합계(총비용)", "empty_return": base["total"], "round_trip": rt["total"]},
        {"item": "공공지출(본인부담 100원 차감)", "empty_return": base["public"], "round_trip": rt["public"]},
    ])
    brk.to_csv(CLEAN / "A3_cost_breakdown.csv", index=False, encoding="utf-8-sig")

    # 민감도: 운행형태 x 연료가 x 감가상각 x 보험방식 x 속도 x 시급배수
    rows = []
    fuel_opts = {"2025 평균": FUEL_2025, "2026 평균": FUEL_2026, "2026 최고": FUEL_PEAK}
    ins_opts = {"On-Off x1": dict(ins_mult=1.0), "On-Off x2": dict(ins_mult=2.0),
                "개인 상시특약": dict(ins_annual=V["ins_personal_rider"] - V["ins_personal_base"])}
    for e, (fk, fp), dep, (ik, io), sp, wm in itertools.product(
            [1.0, 0.0], fuel_opts.items(), [0.0, V["voc_dep_40"]], ins_opts.items(), [30.0, 40.0, 50.0], [1.0, 1.5]):
        r = resident_cost(d0, empty=e, fuel_price=fp, depreciation=dep, speed=sp, wage=P["wage"]["v"] * wm, **io)
        rows.append({"mode": "빈차 귀가" if e else "동행 왕복", "fuel": fk, "depreciation": dep > 0, "insurance": ik,
                     "speed": sp, "wage_mult": wm, "total": r["total"], "public": r["public"],
                     "saving_vs_taxi": 1 - r["public"] / gk_trip})
    sens = pd.DataFrame(rows)
    sens.to_csv(CLEAN / "A3_sensitivity.csv", index=False, encoding="utf-8-sig")
    # 핵심 가정만 바꾼 표(본문 표3용)
    one_way = {
        "기본값": resident_cost(d0)["public"],
        "감가상각 포함(262원/km)": resident_cost(d0, depreciation=V["voc_dep_40"])["public"],
        "연료가 2026년 최고(5월)": resident_cost(d0, fuel_price=FUEL_PEAK)["public"],
        "보험 개인 상시특약(연 26만 원)": resident_cost(
            d0, ins_annual=V["ins_personal_rider"] - V["ins_personal_base"])["public"],
        "수고보상 1.5배": resident_cost(d0, wage=P["wage"]["v"] * 1.5)["public"],
        "운전자 월 30건(원제안 상한)": resident_cost(d0, trips_per_driver=360)["public"],
    }
    oat = pd.DataFrame([{"case": k, "empty_return": v, "round_trip": resident_cost(
        d0, empty=0.0, **({"depreciation": V["voc_dep_40"]} if "감가" in k else
                          {"fuel_price": FUEL_PEAK} if "연료" in k else
                          {"ins_annual": V["ins_personal_rider"] - V["ins_personal_base"]} if "보험" in k else
                          {"wage": P["wage"]["v"] * 1.5} if "수고" in k else
                          {"trips_per_driver": 360} if "월 30" in k else {}))["public"]}
        for k, v in one_way.items()])
    oat["vs_taxi_empty"] = 1 - oat.empty_return / gk_trip
    oat["vs_taxi_round"] = 1 - oat.round_trip / gk_trip
    oat.to_csv(CLEAN / "A3_one_at_a_time.csv", index=False, encoding="utf-8-sig")

    # 거리별 곡선
    curve = pd.DataFrame([{"d_km": d, "resident_empty": resident_cost(d)["total"],
                           "resident_round": resident_cost(d, empty=0.0)["total"],
                           "taxi": taxi_fare(d), "taxi_outside": taxi_fare(d, outside=True)}
                          for d in np.arange(1, 25.5, 0.5)])
    curve.to_csv(CLEAN / "A3_distance_curve.csv", index=False, encoding="utf-8-sig")
    cross = curve[curve.resident_empty < curve.taxi].d_km.min()

    # 손익분기: DRT 1대 신규 투입(완주 행복콜버스 2026 대당 운영비 + 차량 4,000만 원/7년)
    drt_fixed = A2["wanju_callbus_opex_per_vehicle_2026"] + 40_000_000 / 7
    cap_pax = 89_298 / 8   # 완주 2024 대당 연 이용(8대 운행 기준)
    be = []
    for Q in range(0, 20_001, 100):
        n = max(1, math.ceil(Q * pax / cap_pax))
        be.append({"trips": Q, "resident": Q * base["public"], "resident_round": Q * rt["public"],
                   "taxi_type": Q * gk_trip, "drt": n * drt_fixed})
    be = pd.DataFrame(be)
    be.to_csv(CLEAN / "A3_breakeven.csv", index=False, encoding="utf-8-sig")
    q_star = drt_fixed / base["public"]
    q_star_rt = drt_fixed / rt["public"]

    # 곡성 적용
    trips = 24_959
    exp = 317_592_000
    myeon = trips / 10
    # 등록 택시 1대 이하 7개 면(오곡·삼기·목사동·죽곡·고달·겸·오산) 인구 비중(2021 청년통계)
    emd = pd.read_csv(CLEAN / "A1_gokseong_emd.csv")
    low = ["오곡면", "삼기면", "목사동면", "죽곡면", "고달면", "겸면", "오산면"]
    share_low = emd[emd.emd.isin(low)].pop_2021.sum() / emd[emd.emd != "곡성읍"].pop_2021.sum()
    trips_low = trips * share_low
    app = pd.DataFrame([
        {"scenario": "택시 1대 이하 7개 면에 DRT를 1대씩 신규 투입", "trips": trips_low,
         "alt_cost": 7 * drt_fixed, "res_cost_empty": trips_low * base["public"], "res_cost_round": trips_low * rt["public"]},
        {"scenario": "면 1곳(연 2,496회)에 DRT 1대 신규 투입", "trips": myeon,
         "alt_cost": drt_fixed, "res_cost_empty": myeon * base["public"], "res_cost_round": myeon * rt["public"]},
        {"scenario": "효도택시 2024 운행 전량(택시형 유지와 비교)", "trips": trips,
         "alt_cost": exp, "res_cost_empty": trips * base["public"], "res_cost_round": trips * rt["public"]},
    ])
    for m in ["empty", "round"]:
        app[f"saving_{m}"] = app.alt_cost - app[f"res_cost_{m}"]
        app[f"saving_pct_{m}"] = app[f"saving_{m}"] / app.alt_cost
    app.to_csv(CLEAN / "A3_gokseong_application.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame([{"key": k, **v} for k, v in P.items()]).to_csv(CLEAN / "A3_params.csv", index=False,
                                                                   encoding="utf-8-sig")
    # 운전자 측: 건당 수고보상, 월 10·30건
    res = {
        "fuel_2026_avg": FUEL_2026, "fuel_2025_avg": FUEL_2025, "fuel_2026_peak": FUEL_PEAK,
        "v_per_km": base["v_per_km"], "fuel_per_km": fuel_per_km(FUEL_2026), "nonfuel_per_km": P["nonfuel"]["v"],
        "d_base_km": d0, "taxi_total_fare": gk_trip + fee, "TAXI": TAXI,
        "base": base, "round_trip": rt, "gk_public_trip": gk_trip, "pax_per_trip": pax,
        "saving_vs_taxi_empty": 1 - base["public"] / gk_trip, "saving_vs_taxi_round": 1 - rt["public"] / gk_trip,
        "crossover_km_vs_taxi": cross,
        "sens_n": len(sens), "sens_public_min": sens.public.min(), "sens_public_max": sens.public.max(),
        "sens_share_le_taxi": float((sens.public <= gk_trip).mean()),
        "sens_share_le_taxi_empty": float((sens[sens["mode"] == "빈차 귀가"].public <= gk_trip).mean()),
        "sens_share_le_taxi_round": float((sens[sens["mode"] == "동행 왕복"].public <= gk_trip).mean()),
        "drt_fixed_per_vehicle": drt_fixed, "drt_cap_pax": cap_pax,
        "q_star_drt_trips": q_star, "q_star_drt_trips_round": q_star_rt,
        "myeon_trips": myeon, "share_low_taxi_myeon_pop": share_low,
        "gokseong_application": app.to_dict("records"),
        "driver_month_10": 10 * base["effort"], "driver_month_30": 30 * base["effort"],
        "driver_hourly_check": base["effort"] / base["minutes"] * 60,
        "src": V, "n_sources": len(SRCDF),
        "oat": oat.to_dict("records"),
        "max_gap_vs_taxi_empty_pct": float((1 - curve.resident_empty / curve.taxi).max()),
        "min_gap_vs_taxi_empty_pct": float((1 - curve.resident_empty / curve.taxi).min()),
        "budget_350m_trips_empty": 350_000_000 / base["public"], "budget_350m_trips_round": 350_000_000 / rt["public"],
    }
    save_json(res, CLEAN / "A3_results.json")
    print(brk.round(0).to_string())
    print(oat.round(3).to_string())
    print(app.round(3).to_string())
    print(json.dumps({k: res[k] for k in ["d_base_km", "v_per_km", "saving_vs_taxi_empty", "saving_vs_taxi_round",
                                          "crossover_km_vs_taxi", "q_star_drt_trips", "q_star_drt_trips_round",
                                          "sens_share_le_taxi_empty", "sens_share_le_taxi_round",
                                          "share_low_taxi_myeon_pop", "drt_fixed_per_vehicle"]},
                     ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
