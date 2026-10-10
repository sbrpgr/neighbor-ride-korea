"""A2. 기존 교통복지 대안의 비용구조.

결산서·예산서·보도자료의 수치를 '전사값 + 원문 위치 + 원문 대조'로 관리한다.
- 텍스트 PDF/HTML/CSV: 스크립트가 원문에서 해당 숫자 문자열을 직접 찾아 일치 여부를 검증한다.
- 이미지 쪽(완주 2024 성과보고서 951~953쪽): 쪽 이미지를 사람이 판독한 값이며 verified='image'로 표시한다.

출력
- data_clean/A2_source_values.csv     전사값과 원문 대조 결과
- data_clean/A2_alternative_costs.csv 대안별 도입비·운영비·이용 1건당 공공지출
- data_clean/A2_results.json
"""
import html
import re

import pandas as pd
import pdfplumber

from common import CLEAN, RAW, save_json

# (id, 값, 단위, 설명, 원문 파일, 쪽(1-base, PDF 기준), 원문에서 찾을 문자열 또는 None(이미지))
SOURCES = [
    ("gk_taxi_2024_exp", 317_592_000, "원", "곡성 농촌형 교통모델(효도택시) 2024 지출액",
     "budget/gokseong_2024_settlement.pdf", 108, "317,592,000"),
    ("gk_taxi_2024_trips", 24_959, "회", "곡성 효도택시 2024 운행횟수",
     "budget/gokseong_2024_settlement.pdf", 834, "24,959회"),
    ("gk_taxi_2024_pax", 32_199, "명", "곡성 효도택시 2024 이용인원",
     "budget/gokseong_2024_settlement.pdf", 834, "32,199명"),
    ("gk_taxi_target_villages", 47, "개", "곡성 효도택시 대상 마을(2024)",
     "budget/gokseong_2024_settlement.pdf", 686, "47개 마을(2,383명)"),
    ("gk_taxi_target_residents", 2_383, "명", "곡성 효도택시 대상 주민(2024)",
     "budget/gokseong_2024_settlement.pdf", 686, "2,383명"),
    ("gk_taxi_fee_myeon", 100, "원/대", "곡성 효도택시 본인부담: 마을회관-읍면 소재지",
     "budget/gokseong_2024_settlement.pdf", 686, "100원 / 대당"),
    ("gk_taxi_fee_zone", 1_200, "원/대", "곡성 효도택시 본인부담: 마을회관-생활권역 소재지",
     "budget/gokseong_2024_settlement.pdf", 686, "1,200원 / 대당"),
    ("gk_taxi_fleet_total", 50, "대", "곡성 관내 택시(면별 곡성읍24·오곡1·삼기0·석곡7·목사동1·죽곡0·고달0·옥과13·입2·겸1·오산1)",
     "gokseong/gokseong_hyodo_taxi_plan_20251126_excerpt.pdf", 1, "합계 50 24 1 - 7 1 - - 13 2 1 1"),
    ("gk_taxi_2026_budget", 450_000_000, "원", "곡성 효도택시 2026 총사업비",
     "gokseong/gokseong_2026h1_council_report.html", 1, "4억 5000만 원"),
    ("gk_taxi_2026h1_pax", 17_148, "명", "곡성 효도택시 2026 상반기 이용",
     "gokseong/gokseong_2026h1_council_report.html", 1, "1만 7148명"),
    ("gk_taxi_2026h1_exp", 199_000_000, "원", "곡성 효도택시 2026 상반기 운행지원금 집행",
     "gokseong/gokseong_2026h1_council_report.html", 1, "1억 9900만 원"),
    ("gk_bus_subsidy", 332_000_000, "원", "곡성 버스 재정지원금 2024",
     "budget/gokseong_2024_settlement.pdf", 686, "332백만 원"),
    ("gk_bus_remote_loss", 1_426_000_000, "원", "곡성 벽지·비수익 노선 손실보상 2024(49개 노선)",
     "budget/gokseong_2024_settlement.pdf", 686, "49개 노선 / 1,426백만 원"),
    ("gk_bus_flatfare_loss", 341_000_000, "원", "곡성 농어촌버스 단일요금제 손실보상 2024",
     "budget/gokseong_2024_settlement.pdf", 686, "341백만 원"),
    ("gk_bus_routes", 49, "개", "곡성 벽지·비수익 노선 수 2024",
     "budget/gokseong_2024_settlement.pdf", 686, "49개 노선"),
    ("wj_taxi_2024_exp", 177_317_000, "원", "완주 농촌형 택시(행복콜택시-으뜸택시) 2024 결산",
     "budget/wanju_2024_settlement_performance.pdf", 385, None),
    ("wj_taxi_2024_pax", 28_069, "명", "완주 행복콜택시 2024 이용자수",
     "budget/wanju_2024_settlement_performance.pdf", 383, None),
    ("wj_callbus_2024_pax", 89_298, "명", "완주 행복콜버스 2024 이용자수",
     "budget/wanju_2024_settlement_performance.pdf", 383, None),
    ("wj_callbus_2024_opex", 881_725_000, "원", "완주 행복콜버스 운영비 지원 2024 최종예산",
     "budget/wanju_2024_supp4_road_transport.pdf", 4, "881,725"),
    ("wj_callbus_2024_vehicle", 78_875_000, "원", "완주 행복콜버스 차량 구입 2024 최종예산",
     "budget/wanju_2024_supp4_road_transport.pdf", 4, "78,875"),
    ("wj_callbus_2026_opex", 954_600_000, "원", "완주 행복콜버스 운영비 지원 2026 본예산",
     "budget/wanju_2026_budget_road_transport.pdf", 6, "954,600"),
    ("wj_callbus_2025_fleet", 10, "대", "완주 행복콜버스 운행대수(농식품부 우수사례)",
     "drt/mafra_rural_transport_20260211.pdf", 4, "10대"),
    ("drt_guide_daily_cost", 558_380, "원/대·일", "국토부 DRT 가이드라인 이천 11인승 18시간 운송원가",
     "drt/molit_drt_guideline_20251230.pdf", 26, "558,380"),
    ("drt_guide_driver", 337_671, "원/대·일", "같은 원가 중 운전직 인건비",
     "drt/molit_drt_guideline_20251230.pdf", 26, "337,671"),
    ("drt_guide_platform", 48_000, "원/대·일", "같은 원가 중 플랫폼 운영비",
     "drt/molit_drt_guideline_20251230.pdf", 26, "48,000"),
    ("drt_guide_depreciation", 24_140, "원/대·일", "같은 원가 중 차량감가상각비",
     "drt/molit_drt_guideline_20251230.pdf", 26, "24,140"),
    ("drt_guide_insurance", 18_000, "원/대·일", "같은 원가 중 보험료",
     "drt/molit_drt_guideline_20251230.pdf", 26, "18,000"),
    ("mafra_2025_public", 53_200_000_000, "원", "농촌형 교통모델 2025 지원액(국비 50%)",
     "drt/mafra_rural_transport_20260211.pdf", 3, "532억원"),
    ("mafra_2025_users", 7_407_000, "명", "농촌형 교통모델 2025 이용자 수",
     "drt/mafra_rural_transport_20260211.pdf", 1, "7,407"),
    ("mafra_2025_counties", 81, "개", "농촌형 교통모델 2025 시행 군",
     "drt/mafra_rural_transport_20260211.pdf", 1, "81개 군"),
    ("mafra_2025_villages", 9_540, "개", "농촌형 교통모델 2025 지원 마을",
     "drt/mafra_rural_transport_20260211.pdf", 1, "9,540개 마을"),
    ("mafra_2026_budget", 57_982_000_000, "원", "농촌형 교통모델 2026 사업예산(국비 50%)",
     "drt/mafra_rural_transport_20260211.pdf", 3, "57,982백만원"),
    ("krei_2019_taxi_nat", 2_707.1, "원/인(국비)", "KREI 2019 택시형 이용인원당 국비",
     "drt/krei_rural_transport_2021.pdf", 42, "2,707.1"),
    ("krei_2019_bus_nat", 13_810.1, "원/인(국비)", "KREI 2019 버스형 이용인원당 국비",
     "drt/krei_rural_transport_2021.pdf", 42, "13,810.1"),
    ("krei_2019_bus_vehicle_share", 0.569, "비율", "KREI 2019 버스형 투입비용 중 차량구입 관련 비중",
     "drt/krei_rural_transport_2021.pdf", 42, "56.9%"),
]


def page_text(rel, page):
    path = RAW / rel
    if path.suffix == ".pdf":
        with pdfplumber.open(path) as pdf:
            return pdf.pages[page - 1].extract_text() or ""
    s = path.read_text(encoding="utf-8", errors="ignore")
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def verify_sources():
    rows, cache = [], {}
    for sid, val, unit, desc, rel, page, needle in SOURCES:
        if needle is None:
            status = "image"
        else:
            key = (rel, page)
            if key not in cache:
                cache[key] = re.sub(r"\s+", " ", page_text(rel, page))
            status = "ok" if re.sub(r"\s+", " ", needle) in cache[key] else "NOT FOUND"
        rows.append({"id": sid, "value": val, "unit": unit, "desc": desc, "file": rel, "pdf_page": page,
                     "needle": needle, "verified": status})
    df = pd.DataFrame(rows)
    bad = df[df.verified == "NOT FOUND"]
    if len(bad):
        raise SystemExit(f"원문 대조 실패:\n{bad.to_string()}")
    return df


def yongin():
    d = pd.read_csv(RAW / "taxi" / "yongin_happy_taxi_20251231.csv", encoding="cp949")
    trips = d["월 평균 이용횟수"].sum() * 12
    subsidy = d["지원금(월 평균)"].sum() * 12
    fare = d["이용요금(월 평균)"].sum() * 12
    user = d["이용자부담금(월 평균)"].sum() * 12
    return {"villages": len(d), "trips_year": trips, "subsidy_year": subsidy, "fare_year": fare,
            "user_year": user, "subsidy_per_trip": subsidy / trips, "fare_per_trip": fare / trips}


def main():
    src = verify_sources()
    src.to_csv(CLEAN / "A2_source_values.csv", index=False, encoding="utf-8-sig")
    v = dict(zip(src.id, src.value))
    yi = yongin()

    drt_annual_guide = v["drt_guide_daily_cost"] * 365          # 18시간·연중 운행 기준
    wj_drt_per_vehicle = v["wj_callbus_2026_opex"] / v["wj_callbus_2025_fleet"]
    rows = [
        # 대안, 사례, 기준, 공공지출(원), 이용량, 이용 단위, 건당 공공지출, 신규 차량, 상시 인력, 비고
        dict(mode="택시형(행복택시)", case="전남 곡성 효도택시", basis="2024 결산",
             public=v["gk_taxi_2024_exp"], usage=v["gk_taxi_2024_trips"], unit="차량 운행회",
             per_unit=v["gk_taxi_2024_exp"] / v["gk_taxi_2024_trips"],
             per_pax=v["gk_taxi_2024_exp"] / v["gk_taxi_2024_pax"],
             new_vehicle="불필요(기존 택시)", staff="공무직 1명(콜센터)", note="이용자 부담 100·1,200원/대 별도"),
        dict(mode="택시형(행복택시)", case="전북 완주 으뜸택시", basis="2024 결산",
             public=v["wj_taxi_2024_exp"], usage=v["wj_taxi_2024_pax"], unit="이용자(연인원)",
             per_unit=v["wj_taxi_2024_exp"] / v["wj_taxi_2024_pax"],
             per_pax=v["wj_taxi_2024_exp"] / v["wj_taxi_2024_pax"],
             new_vehicle="불필요(기존 택시)", staff="-", note="이용요금 500원/승차"),
        dict(mode="택시형(행복택시)", case="경기 용인 행복택시", basis="2025 월평균x12",
             public=yi["subsidy_year"], usage=yi["trips_year"], unit="이용횟수",
             per_unit=yi["subsidy_per_trip"], per_pax=None,
             new_vehicle="불필요(기존 택시)", staff="-", note=f"{yi['villages']}개 마을"),
        dict(mode="수요응답형 버스(DRT)", case="전북 완주 행복콜버스", basis="2024 최종예산·이용실적",
             public=v["wj_callbus_2024_opex"], usage=v["wj_callbus_2024_pax"], unit="이용자(연인원)",
             per_unit=v["wj_callbus_2024_opex"] / v["wj_callbus_2024_pax"],
             per_pax=(v["wj_callbus_2024_opex"] + v["wj_callbus_2024_vehicle"]) / v["wj_callbus_2024_pax"],
             new_vehicle="필요(2024 7,888만원)", staff="전담 운전기사",
             note="per_pax는 차량구입 포함"),
        dict(mode="수요응답형 버스(DRT)", case="전북 완주 행복콜버스(대당)", basis="2026 본예산/10대",
             public=wj_drt_per_vehicle, usage=None, unit="대·년", per_unit=wj_drt_per_vehicle, per_pax=None,
             new_vehicle="필요(대당 4,000만원)", staff="전담 운전기사", note="차량 1대 연 운영비"),
        dict(mode="수요응답형 버스(DRT)", case="국토부 가이드라인(이천 11인승)", basis="2025 공고 원가",
             public=drt_annual_guide, usage=None, unit="대·년(18시간·365일)",
             per_unit=drt_annual_guide, per_pax=None,
             new_vehicle="필요(감가상각 일 24,140원)", staff="운전직 인건비 일 337,671원",
             note="원가 중 인건비 60%"),
        dict(mode="노선버스(벽지·비수익)", case="전남 곡성 농어촌버스", basis="2024 결산",
             public=v["gk_bus_remote_loss"] + v["gk_bus_subsidy"] + v["gk_bus_flatfare_loss"],
             usage=v["gk_bus_routes"], unit="벽지·비수익 노선",
             per_unit=v["gk_bus_remote_loss"] / v["gk_bus_routes"], per_pax=None,
             new_vehicle="필요(버스 20대 보유)", staff="전담 운전기사",
             note="per_unit=노선당 손실보상"),
        dict(mode="농촌형 교통모델 전체", case="전국 81개 군", basis="2025 지원액(국비 50%)",
             public=v["mafra_2025_public"], usage=v["mafra_2025_users"], unit="이용자(연인원)",
             per_unit=v["mafra_2025_public"] / v["mafra_2025_users"],
             per_pax=v["mafra_2025_public"] / v["mafra_2025_users"],
             new_vehicle="버스형 필요", staff="버스형 필요", note="택시형+버스형 평균"),
    ]
    alt = pd.DataFrame(rows)
    alt.to_csv(CLEAN / "A2_alternative_costs.csv", index=False, encoding="utf-8-sig")

    res = {
        "gokseong_taxi_per_trip": v["gk_taxi_2024_exp"] / v["gk_taxi_2024_trips"],
        "gokseong_taxi_per_pax": v["gk_taxi_2024_exp"] / v["gk_taxi_2024_pax"],
        "gokseong_pax_per_trip": v["gk_taxi_2024_pax"] / v["gk_taxi_2024_trips"],
        "gokseong_trips_per_village": v["gk_taxi_2024_trips"] / v["gk_taxi_target_villages"],
        "gokseong_trips_per_myeon": v["gk_taxi_2024_trips"] / 10,
        "gokseong_bus_total_support": v["gk_bus_remote_loss"] + v["gk_bus_subsidy"] + v["gk_bus_flatfare_loss"],
        "gokseong_bus_loss_per_route": v["gk_bus_remote_loss"] / v["gk_bus_routes"],
        "wanju_taxi_per_pax": v["wj_taxi_2024_exp"] / v["wj_taxi_2024_pax"],
        "wanju_callbus_per_pax_opex": v["wj_callbus_2024_opex"] / v["wj_callbus_2024_pax"],
        "wanju_callbus_per_pax_incl_vehicle": (v["wj_callbus_2024_opex"] + v["wj_callbus_2024_vehicle"]) / v["wj_callbus_2024_pax"],
        "wanju_callbus_opex_per_vehicle_2026": wj_drt_per_vehicle,
        "drt_guide_annual_per_vehicle": drt_annual_guide,
        "drt_guide_driver_share": v["drt_guide_driver"] / v["drt_guide_daily_cost"],
        "yongin": yi,
        "mafra_public_per_user_2025": v["mafra_2025_public"] / v["mafra_2025_users"],
        "mafra_2025_public": v["mafra_2025_public"], "mafra_2025_users": v["mafra_2025_users"],
        "krei_2019_taxi_nat": v["krei_2019_taxi_nat"], "krei_2019_bus_nat": v["krei_2019_bus_nat"],
        "n_sources": len(src), "n_text_verified": int((src.verified == "ok").sum()),
        "n_image_verified": int((src.verified == "image").sum()),
        "src": v,
    }
    save_json(res, CLEAN / "A2_results.json")
    print(src[["id", "value", "verified"]].to_string())
    print(alt[["mode", "case", "basis", "per_unit", "per_pax", "unit"]].round(0).to_string())


if __name__ == "__main__":
    main()
