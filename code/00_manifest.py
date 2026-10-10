"""data_raw 원자료 목록(MANIFEST.csv)을 생성·검증한다.

각 파일의 출처 URL, 제공기관, 기준시점, 용도를 기록하고 SHA256을 계산한다.
등록되지 않은 파일이 data_raw에 있거나, 등록된 파일이 없으면 오류로 멈춘다.
"""
import hashlib
import sys

import pandas as pd

from common import RAW

# 경로(data_raw 기준), 자료명, 제공기관, 플랫폼, URL, 기준시점, 용도
ENTRIES = [
    ("molit_vehicle/molit_vehicle_registration_202608.xlsx", "자동차 등록자료 통계(2026년 8월)", "국토교통부",
     "국토교통 통계누리", "https://stat.molit.go.kr/portal/cate/statMetaView.do?hRsId=58", "2026-08 말", "A1"),
    ("mois_population/mois_household_population_sigungu_202608.csv", "주민등록 인구 및 세대현황(시군구)", "행정안전부",
     "주민등록 인구통계", "https://jumin.mois.go.kr/statMonth.do", "2026-08 말", "A1"),
    ("mois_population/mois_age5_sigungu_202608.csv", "주민등록 연령별 인구현황(시군구, 5세)", "행정안전부",
     "주민등록 인구통계", "https://jumin.mois.go.kr/ageStatMonth.do", "2026-08 말", "A1"),
    ("mois_depopulation/mois_depopulation_redesignation_20261007.pdf", "인구감소지역 재지정 보도자료", "행정안전부",
     "KDI 경제교육·정보센터", "https://eiec.kdi.re.kr/policy/materialView.do?num=287880", "2026-10-07", "A1"),
    ("ktdb/ktdb_avg_access_time_2025.xlsx", "2025년 교통접근성지표: 평균접근시간", "한국교통연구원",
     "국가교통DB(KTDB)", "https://www.ktdb.go.kr/www/selectBbsNttView.do?key=45&bbsNo=2&nttNo=3829", "2025", "A1·A5"),
    ("ktdb/ktdb_access_pop_ratio_2025.xlsx", "2025년 교통접근성지표: 접근가능인구비율", "한국교통연구원",
     "국가교통DB(KTDB)", "https://www.ktdb.go.kr/www/selectBbsNttView.do?key=45&bbsNo=2&nttNo=3829", "2025", "A1·A5"),
    ("ktdb/ktdb_access_indicator_method.pdf", "교통접근성지표 산정방법", "한국교통연구원",
     "국가교통DB(KTDB)", "https://www.ktdb.go.kr/downloadBbsFile.do?atchmnflNo=13963", "2025", "방법"),
    ("gokseong/gokseong_youth_stats_2022.pdf", "곡성군 청년통계 2022(자동차 개인소유자, 읍면별)", "곡성군",
     "곡성군청 홈페이지", "https://www.gokseong.go.kr/document/kr/stats/youth/2022/youth_2022.pdf", "2021-12-31", "A1"),
    ("gokseong/gokseong_youth_stats_2025.pdf", "곡성군 청년통계 2025(자동차 개인소유자)", "곡성군",
     "곡성군청 홈페이지", "https://www.gokseong.go.kr/document/kr/stats/youth/2025/youth_2025.pdf", "2024-12-31", "A1"),
    ("gokseong/gokseong_statbook2024_transport.xlsx", "곡성 통계연보 2024 교통", "곡성군",
     "곡성군청 홈페이지", "https://www.gokseong.go.kr/document/kr/stats/2024/11.xlsx", "2023-12-31", "A1"),
    ("gokseong/gokseong_bus_stops_20240119.csv", "전라남도 곡성군 버스정류소", "곡성군",
     "공공데이터포털", "https://www.data.go.kr/data/15110656/fileData.do", "2024-01-19", "참고"),
    ("gokseong/gokseong_hyodo_taxi_plan_20251126_excerpt.pdf", "민선8기 공약 실천계획(농촌 수요응답형 마을택시제)", "곡성군",
     "곡성군청 홈페이지", "https://www.gokseong.go.kr/document/gunsu/late_2024/plan1.pdf", "2025-11-26", "A2·A3"),
    ("gokseong/gokseong_pledge_progress_2025.pdf", "공약 이행실적 2025", "곡성군",
     "곡성군청 홈페이지", "https://www.gokseong.go.kr/document/gunsu/late_2024/plan1.pdf", "2025", "참고"),
    ("gokseong/gokseong_2026h1_council_report.html", "제279회 곡성군의회 본회의 회의록(2026 상반기 업무실적)", "곡성군의회",
     "곡성군의회 회의록", "https://assembly.gokseong.go.kr/minutes/cnts/mnt/mntsViewer.php?schSn=12461", "2026-07-13", "A2"),
    ("budget/gokseong_2024_settlement.pdf", "2024회계연도 결산서·성과보고서", "곡성군",
     "곡성군청 홈페이지", "https://www.gokseong.go.kr/document/kr/data/2025/2024_closing/2024_1.pdf", "2024", "A2"),
    ("budget/gokseong_2026_budget_expenditure.pdf", "2026년 본예산 세출사업명세서", "곡성군",
     "곡성군청 홈페이지", "https://www.gokseong.go.kr/document/kr/data/2026/01/11-0.pdf", "2026", "A2"),
    ("budget/wanju_2024_settlement_performance.pdf", "2024회계연도 성과보고서", "완주군",
     "완주군청 홈페이지", "https://www.wanju.go.kr/planweb/board/download.9is?boardUid=ff8080818b5bc68c018ba36562896d4d&fileUid=4028a602975891f70197a4effe0223ba", "2024", "A2"),
    ("budget/wanju_2024_supp4_road_transport.pdf", "2024년 제4회 추경 세출예산(도로교통과)", "완주군",
     "완주군청 홈페이지", "https://www.wanju.go.kr/www/file/budget/down/2024/4/2/20.pdf", "2024", "A2"),
    ("budget/wanju_2026_budget_road_transport.pdf", "2026년 본예산 세출예산(도로교통과)", "완주군",
     "완주군청 홈페이지", "https://www.wanju.go.kr/www/file/budget/down/2026/0/2/23.pdf", "2026", "A2"),
    ("budget/wanju_happy_callbus_info.html", "행복콜버스(농촌형버스) 안내", "완주군",
     "완주군청 홈페이지", "https://www.wanju.go.kr/index.9is?contentUid=ff8080818b024d8e018b274f75b92cbf", "2026-10-10 열람", "참고"),
    ("budget/paju_rural_ddokbus_2024q1.html", "파주시의회 예결특위 회의록(농촌형 똑버스)", "파주시의회",
     "파주시의회 회의록", "https://www.pajucouncil.go.kr/minutes/xcom/web/minutesViewer.php?id=3634&scode=7060", "2024-06-25", "참고"),
    ("taxi/yongin_happy_taxi_20251231.csv", "경기도 용인시 행복택시 운영현황", "용인시",
     "공공데이터포털", "https://www.data.go.kr/data/15126380/fileData.do", "2025-12-31", "A2"),
    ("taxi/gyeongju_happy_taxi_20260116.csv", "경상북도 경주시 행복택시 운행현황", "경주시",
     "공공데이터포털", "https://www.data.go.kr/data/15038219/fileData.do", "2026-01-16", "참고"),
    ("taxi/wanju_taxi_fare_notice_2023-78.hwp", "택시운임·요금 변경 고시(제2023-78호)", "완주군",
     "완주군청 홈페이지", "https://www.wanju.go.kr/atc/planweb/board/download.9is?fileUid=e95475057ba845a48dd12573f521b5a3&boardUid=ff8080818a49961a018ab011af3543bc", "2023-08-11", "A3"),
    ("taxi/wanju_taxi_fare_notice_2023-78.txt", "택시운임·요금 변경 고시(제2023-78호) 본문 텍스트", "완주군",
     "완주군청 홈페이지", "https://www.wanju.go.kr/atc/planweb/board/download.9is?fileUid=e95475057ba845a48dd12573f521b5a3&boardUid=ff8080818a49961a018ab011af3543bc", "2023-08-11", "A3"),
    ("drt/molit_drt_guideline_20251230.pdf", "수요응답형교통 도입·운영 가이드라인", "국토교통부",
     "ITS Korea 공개자료", "https://itskorea.kr/downloadFile.do?fileId=FILE_000000000107685&fileSn=0", "2025-12-30", "A2·A3"),
    ("drt/mafra_rural_transport_20260211.pdf", "농촌형 교통모델 2025 이용실태 보도자료", "농림축산식품부",
     "농림축산식품부 홈페이지", "https://www.mafra.go.kr/bbs/home/792/594703/download.do", "2026-02-11", "A2·A3"),
    ("drt/krei_rural_transport_2021.pdf", "농촌형·도시형 교통모델 개선 영향평가", "한국농촌경제연구원",
     "KREI 저장소", "https://repository.krei.re.kr/bitstream/2018.oak/28981/1/E20-2021-06.pdf", "2019 실적", "A2"),
    ("drt/kriti_cheongju_drt_2024.pdf", "운수산업연구 Vol.81(청주시 DRT 분석)", "한국운수산업연구원",
     "KRITI 홈페이지", "https://kriti.re.kr/bbs_sun/files/bus/bus_202403281315562.pdf", "2024", "참고"),
    ("drt/krila_jeonbuk_2025.pdf", "미래형 교통수단 도입을 통한 전북 공공교통서비스 확보 방안", "한국지방행정연구원",
     "KRILA 홈페이지", "https://krila.re.kr/download_report.php?idx=1977&type=pdf", "2025", "참고"),
    ("drt/ts_drt_registered_vehicles_20251231.csv", "한국교통안전공단 DRT 지원시스템 등록대수", "한국교통안전공단",
     "공공데이터포털", "https://www.data.go.kr/data/15064502/fileData.do", "2025-12-31", "참고"),
    ("japan_local/mlit_tohoku_jikayo_handbook_202410.pdf", "自家用有償旅客運送ハンドブック", "일본 국토교통성 도호쿠운수국",
     "국토교통성 홈페이지", "https://wwwtb.mlit.go.jp/tohoku/content/000348884.pdf", "2024-10", "A4"),
]

ENTRIES += [
    ("taxi/wanju_taxi_fare_notice_2023-78_converted.pdf", "완주군 고시 제2023-78호 택시운임·요금(한컴 PDF 변환본)", "완주군",
     "완주군청 홈페이지", "https://www.wanju.go.kr/atc/planweb/board/download.9is?fileUid=e95475057ba845a48dd12573f521b5a3&boardUid=ff8080818a49961a018ab011af3543bc", "2023-08-11", "A3"),
    ("cost_params/MOLIT_TransportFacilityInvestmentGuideline_8th_Notice2026-204_effective2026-04-21.hwp",
     "교통시설 투자평가지침(국토교통부고시 제2026-204호)", "국토교통부", "국가법령정보센터",
     "https://www.law.go.kr/LSW/flDownload.do?flSeq=164151329", "2026-04-21 시행", "A3"),
    ("cost_params/MOLIT_TransportFacilityInvestmentGuideline_8th_draft_2026-03-13.pdf",
     "교통시설 투자평가지침 제8차 개정안(쪽 대조용, 승용차 원단위 확정본과 동일)", "국토교통부", "국토교통부 홈페이지",
     "https://www.molit.go.kr/mtc/USR/law/m_37141/dtl.jsp?r_id=9786", "2026-03-13", "A3"),
    ("cost_params/MOLIT_Guideline8_VOC_VOT_tables_text_extract.txt", "투자평가지침 표 4-4·4-21·4-22·4-26 텍스트 추출", "국토교통부",
     "국가법령정보센터", "https://www.law.go.kr/LSW/flDownload.do?flSeq=164151329", "2024년 가격", "A3"),
    ("cost_params/Opinet_KNOC_avg_retail_fuel_prices_snapshot_2026-10-10.txt", "석유제품 평균판매가격(일간·월간·연간) 화면 전사",
     "한국석유공사", "오피넷", "https://www.opinet.co.kr/user/dopospdrg/dopOsPdrgSelect.do", "2026-10-10 조회", "A3"),
    ("cost_params/MOEL_MinimumWage2026_Notice2025-47.pdf", "2026년 적용 최저임금 고시(제2025-47호)", "고용노동부",
     "국가법령정보센터", "https://www.law.go.kr/LSW/flDownload.do?flSeq=155278071", "2026", "A3·A5"),
    ("cost_params/FSS_press_2020-07-23_private_car_paid_cargo_rider_premium.pdf", "자동차보험 유상운송 특약 도입 보도참고자료",
     "금융감독원", "금융감독원 홈페이지", "https://www.fss.or.kr/fss/bbs/B0000188/view.do?nttId=15852&menuNo=200218", "2020-07-23", "A3"),
    ("cost_params/MAFRA_2026_Budget_and_Fund_Plan_Overview_2026-01.pdf", "2026년 농림축산식품부 예산 및 기금운용계획 개요",
     "농림축산식품부", "농림축산식품부 홈페이지", "https://www.mafra.go.kr/bbs/home/780/593603/download.do", "2026", "A2"),
    ("cost_params/MAFRA_press_2025-12-25_AI_DRT_Pyeongchang_budget2025_26.6bn.pdf", "농촌 수요응답형 교통 동정자료",
     "농림축산식품부", "농림축산식품부 홈페이지", "https://www.mafra.go.kr/bbs/home/792/592964/download.do", "2025-12-25", "참고"),
    ("cost_params/MAFRA_press_2026-07-26_AI_DRT_pilot_5gun_and_RuralTransportModel_overview.pdf",
     "농촌 특화 수요맞춤형 교통모델 실증 보도자료", "농림축산식품부", "농림축산식품부 홈페이지",
     "https://www.mafra.go.kr/bbs/home/792/599088/download.do", "2026-07-26", "A2"),
    ("cost_params/Law_PassengerTransportAct_Art81_Act21710_eff2026-07-01.txt", "여객자동차 운수사업법 제81조(법률 제21710호)",
     "법제처", "국가법령정보센터", "https://www.law.go.kr/법령/여객자동차운수사업법/제81조", "2026-07-01 시행", "정책"),
    ("cost_params/Law_PassengerTransportAct_EnfRule_Art103_MOLITOrd1621_eff2026-09-15.txt",
     "여객자동차 운수사업법 시행규칙 제103조(국토교통부령 제1621호)", "법제처", "국가법령정보센터",
     "https://www.law.go.kr/법령/여객자동차운수사업법시행규칙/제103조", "2026-09-15 시행", "정책"),
    ("cost_params/KOSIS_KNPA_DrivingLicenceHolders_2024_byAge_bySido.txt", "운전면허 소지자 현황(연령별·지역별) 전사", "경찰청",
     "국가통계포털(KOSIS)", "https://kosis.kr/statHtml/statHtml.do?orgId=132&tblId=DT_13201_A002", "2024년 말", "A4"),
]


def overseas_entries():
    """docs/overseas_cases.md의 'URL: ... — file: `파일명`' 짝을 읽어 해외 원자료를 등록한다."""
    import re
    from common import ROOT
    md = (ROOT / "docs" / "overseas_cases.md").read_text(encoding="utf-8")
    out = {}
    for line in md.splitlines():
        files = re.findall(r"`([A-Z]{2}_[^`]+?\.(?:pdf|html|xml))`", line)
        urls = re.findall(r"https?://[^\s,`]+", line)
        for f in files:
            if f not in out and urls:
                out[f] = urls[0]
    out.setdefault("UK_HMRC_EIM71153_volunteer_drivers_mileage_payments.html",
                   "https://www.gov.uk/hmrc-internal-manuals/employment-income-manual/eim71153")
    out.setdefault("UK_HMRC_EIM71160_volunteer_drivers_profit_calc.html",
                   "https://www.gov.uk/hmrc-internal-manuals/employment-income-manual/eim71160")
    out.setdefault("US_26USC170_LII-mirror_section170i_14cents.html", "https://www.law.cornell.edu/uscode/text/26/170")
    ents = []
    for f in sorted((RAW / "overseas").iterdir()):
        country = {"JP": "일본", "UK": "영국", "US": "미국"}[f.name[:2]]
        ents.append((f"overseas/{f.name}", f.stem, country + " 공공기관", "기관 공식 홈페이지",
                     out.get(f.name, ""), "", "A4"))
    return ents


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    rows = []
    for rel, name, org, plat, url, ref, use in ENTRIES + overseas_entries():
        p = RAW / rel
        if not p.exists():
            sys.exit(f"누락: {rel}")
        rows.append({"file": rel, "name": name, "provider": org, "platform": plat, "url": url,
                     "reference": ref, "use": use, "bytes": p.stat().st_size, "sha256": sha256(p)})
    listed = {r["file"] for r in rows}
    extra = pd.read_csv(RAW / "MANIFEST_extra.csv") if (RAW / "MANIFEST_extra.csv").exists() else pd.DataFrame()
    if len(extra):
        listed |= set(extra["file"])
        for _, r in extra.iterrows():
            p = RAW / r["file"]
            if not p.exists():
                sys.exit(f"누락: {r['file']}")
            d = r.to_dict()
            d.update({"bytes": p.stat().st_size, "sha256": sha256(p)})
            rows.append(d)
    on_disk = {str(p.relative_to(RAW)).replace("\\", "/") for p in RAW.rglob("*") if p.is_file()
               and not p.name.startswith("MANIFEST")}
    unlisted = sorted(on_disk - listed)
    df = pd.DataFrame(rows)
    df.to_csv(RAW / "MANIFEST.csv", index=False, encoding="utf-8-sig")
    print(f"{len(df)} files listed")
    if unlisted:
        print("미등록 파일:", *unlisted, sep="\n  ")
        sys.exit(1)


if __name__ == "__main__":
    main()
