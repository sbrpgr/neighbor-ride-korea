"""A4. 해외 주민 자가용 유상·실비 운송의 운영 실적(공식 1차 출처 원문 대조).

docs/overseas_cases.md에 정리한 핵심 수치를 원문 파일에서 다시 찾아 검증하고 표4를 만든다.
출력: data_clean/A4_overseas_values.csv, A4_table.csv, A4_results.json
"""
import html
import re

import pandas as pd
import pdfplumber

from common import CLEAN, RAW, save_json

OV = RAW / "overseas"
# id, 값, 설명, 파일, PDF 쪽(None=전체), 원문에서 찾을 문자열 목록(모두 있어야 통과)
CHECKS = [
    ("jp_orgs_2026", 865, "일본 교통공백지 자가용유상운송(公共ライドシェア) 단체 수, 2026.3 말",
     "JP_MLIT_public_rideshare_leaflet_R8-03_002008895.pdf", None, ["865", "6,307", "681"]),
    ("jp_vehicles_2026", 6307, "같은 제도 차량 수, 2026.3 말", "JP_MLIT_public_rideshare_leaflet_R8-03_002008895.pdf",
     None, ["6,307"]),
    ("jp_munis_2026", 681, "도입 시구정촌 수(전체 1,741곳 중), 2026.3 말",
     "JP_MLIT_public_rideshare_leaflet_R8-03_002008895.pdf", None, ["1,741", "681"]),
    ("jp_orgs_2022", 670, "같은 제도 단체 수, 2022.3 말", "JP_MLIT_LastOneMileMobility_status_2022_001460981.pdf",
     None, ["670"]),
    ("jp_munis_2022", 572, "도입 시구정촌 수, 2022.3 말", "JP_MLIT_LastOneMileMobility_status_2022_001460981.pdf",
     None, ["572"]),
    ("jp_welfare_orgs_2025", 2244, "일본 복지유상운송 단체 수, 2025.3 말",
     "JP_MLIT_catalog_driver_shortage_3rd_2025-05_001892264.pdf", None, ["2,244", "12,188"]),
    ("jp_welfare_vehicles_2025", 12188, "일본 복지유상운송 차량 수, 2025.3 말",
     "JP_MLIT_catalog_driver_shortage_3rd_2025-05_001892264.pdf", None, ["12,188"]),
    ("jp_rideshare_drivers_2025", 9518, "일본판 라이드셰어 등록 운전자, 2025.8.17",
     "JP_MLIT_rideshare_status_kanjikai5_2025-09-10_001909512.pdf", None, ["9,518"]),
    ("jp_rideshare_trips_2025", 958898, "일본판 라이드셰어 누적 운행 회수, 2025.8.17",
     "JP_MLIT_rideshare_status_kanjikai5_2025-09-10_001909512.pdf", None, ["958,898"]),
    ("jp_fare_80pct", 0.8, "요금 기준: 지역 택시요금의 약 8할", "JP_Chugoku-TB_fare_rule_koji_R6-04-26_000234279.pdf",
     None, ["タクシー運賃の約８割"]),
    ("jp_fatal_2024", 0, "공공 라이드셰어 2024년도 사망사고 건수", "JP_MLIT_public_rideshare_leaflet_R8-03_002008895.pdf",
     None, ["死亡事故：０件"]),
    ("jp_insurance_8000", 80_000_000, "대인배상 1인당 8,000만 엔 이상", "JP_MLIT_public_rideshare_leaflet_R8-03_002008895.pdf",
     None, ["8,000万円"]),
    ("uk_amap_55p", 0.55, "영국 자원봉사 운전자 비과세 마일리지 55p/마일(2026/27)",
     "UK_HMRC_EIM71155_volunteer_drivers_tax_threshold.html", None, ["55 pence"]),
    ("uk_cta_share_car_scheme", 0.41, "영국 지역사회교통 운영기관 중 자원봉사 차량제 운영 비율",
     "UK_CTA_Mapping_England_State_of_Sector_2024.pdf", None, ["41%"]),
    ("uk_bucks_drivers", 835, "버킹엄셔 자원봉사 운전자(추정)", "UK_HealthwatchBucks_HomeToHealth_volunteer_car_schemes_2017-05.pdf",
     None, ["835"]),
    ("uk_bucks_trips", 12375, "버킹엄셔 연 병원 이동(추정)", "UK_HealthwatchBucks_HomeToHealth_volunteer_car_schemes_2017-05.pdf",
     None, ["12,375"]),
    ("us_charity_14c", 0.14, "미국 자선 마일리지 14센트/마일(법정)", "US_IRS_IR-2025-128_2026_mileage_rates.html",
     None, ["14 cents per mile"]),
    ("us_mn_nemt_share", 1 / 3, "미네소타 비응급 의료이동 비용 중 자원봉사 운전자 상환 비중",
     "US_MnDOT_MCOTA_2018_annual_report_2019-01.pdf", None, ["88 million"]),
]


def text_of(fname, page):
    p = OV / fname
    if p.suffix == ".pdf":
        with pdfplumber.open(p) as pdf:
            pages = pdf.pages if page is None else [pdf.pages[page - 1]]
            return " ".join((pg.extract_text() or "") for pg in pages)
    s = p.read_text(encoding="utf-8", errors="ignore")
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def norm(s):
    return re.sub(r"\s+", "", s).replace("，", ",")


def main():
    cache, rows = {}, []
    for cid, val, desc, f, pg, needles in CHECKS:
        if (f, pg) not in cache:
            cache[(f, pg)] = norm(text_of(f, pg))
        found = all(norm(n) in cache[(f, pg)] for n in needles)
        rows.append({"id": cid, "value": val, "desc": desc, "file": f"overseas/{f}", "needles": "|".join(needles),
                     "verified": "ok" if found else "NOT FOUND"})
    df = pd.DataFrame(rows)
    df.to_csv(CLEAN / "A4_overseas_values.csv", index=False, encoding="utf-8-sig")
    v = dict(zip(df.id, df.value))
    gbp_krw = None  # 환율은 쓰지 않는다(본문은 원 단위 환산 없이 원 통화로 표기)

    table = pd.DataFrame([
        {"국가": "일본", "제도": "교통공백지 자가용 유상여객운송(공공 라이드셰어)",
         "운영 주체": "시정촌·NPO 등록 단체, 주민 자가용 반입 허용",
         "운전자 보상·요금": "실비 범위, 지역 택시요금의 약 80%",
         "보험·안전": "대인 1인 8,000만 엔 이상 의무, 1종 면허+대신 인정 강습",
         "규모": f"{int(v['jp_orgs_2026']):,}개 단체·{int(v['jp_vehicles_2026']):,}대, 시정촌 {int(v['jp_munis_2026']):,}곳({v['jp_munis_2026'] / 1741:.0%})",
         "기준": "2026.3"},
        {"국가": "일본", "제도": "일본판 라이드셰어(택시사업자 관리)",
         "운영 주체": "택시사업자가 일반 운전자·자가용 관리",
         "운전자 보상·요금": "택시요금 체계",
         "보험·안전": "택시사업자 책임",
         "규모": f"등록 운전자 {int(v['jp_rideshare_drivers_2025']):,}명·누적 {int(v['jp_rideshare_trips_2025']):,}회",
         "기준": "2025.8"},
        {"국가": "영국", "제도": "자원봉사 차량제(Volunteer car scheme)",
         "운영 주체": "자선단체·교구, 허가 불요(PPVA 1981 s.1(4))",
         "운전자 보상·요금": "실비 상환, 비과세 55p/마일(2026/27)",
         "보험·안전": "운전자 본인 보험, 신원조회(DBS)",
         "규모": f"지역사회교통 기관의 {v['uk_cta_share_car_scheme']:.0%} 운영",
         "기준": "2024"},
        {"국가": "미국", "제도": "자원봉사 운전자 프로그램",
         "운영 주체": "비영리·지자체(주 단위 규율)",
         "운전자 보상·요금": "실비 상환(연방 자선 14센트/마일 기준)",
         "보험·안전": "주별 상이",
         "규모": "미네소타 비응급 의료이동 비용의 약 1/3",
         "기준": "2018"},
    ])
    table.to_csv(CLEAN / "A4_table.csv", index=False, encoding="utf-8-sig")
    # 국내 운전자 자원: 경찰청 운전면허 소지자(2024년 말, 단일연령) 60~74세 합계
    lic_txt = (RAW / "cost_params" / "KOSIS_KNPA_DrivingLicenceHolders_2024_byAge_bySido.txt").read_text(encoding="utf-8")
    ages = {int(a): int(n.replace(",", "")) for a, n in re.findall(r"^(\d+)세=([\d,]+)$", lic_txt, re.M)}
    lic_total = int(re.search(r"^계=([\d,]+)$", lic_txt, re.M).group(1).replace(",", ""))
    lic_60_74 = sum(ages[a] for a in range(60, 75))
    res = {"values": v, "n_checks": len(df), "n_ok": int((df.verified == "ok").sum()),
           "license_60_74": lic_60_74, "license_total": lic_total, "license_60_74_share": lic_60_74 / lic_total,
           "jp_orgs_growth_2022_2026": v["jp_orgs_2026"] / v["jp_orgs_2022"] - 1,
           "jp_munis_share_2026": v["jp_munis_2026"] / 1741, "jp_munis_share_2022": v["jp_munis_2022"] / 1741}
    save_json(res, CLEAN / "A4_results.json")
    print(df[["id", "value", "verified"]].to_string())
    bad = df[df.verified != "ok"]
    if len(bad):
        raise SystemExit("원문 대조 실패: " + ", ".join(bad.id))


if __name__ == "__main__":
    main()
