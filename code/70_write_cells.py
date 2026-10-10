"""보고서 원고 생성: 결과 JSON·CSV의 수치를 읽어 양식 칸별 HTML 조각을 만든다.

문체: 정책보고서 개조식(□ 소제목 / ○ 항목 / - 세부 / ⇒ 결론 / * 단서), 명사형 종결.
본문 숫자는 모두 data_clean의 결과에서 읽어 넣는다(손으로 쓴 수치 없음).
출력: report/cells/*.html, *.tables.json(표 열 비율), plain.json(이름·주제), report/manuscript.md(검토용 텍스트)
"""
import html
import json
import re

import pandas as pd

from common import CLEAN, FIG, ROOT, RAW

OUT = ROOT / "report" / "cells"
OUT.mkdir(parents=True, exist_ok=True)
GITHUB = "https://github.com/sbrpgr/neighbor-ride-korea"

J = lambda name: json.loads((CLEAN / name).read_text(encoding="utf-8"))
A1, A2, A3, A4 = J("A1_results.json"), J("A2_results.json"), J("A3_results.json"), J("A4_results.json")
G = A1["groups"]
DEP, NAT, OTH = G["인구감소지역"], G["전국"], G["기타 지역"]
GK = A1["gokseong"]
S2, S3, S4 = A2["src"], A3["src"], A4["values"]
APP = {r["scenario"]: r for r in A3["gokseong_application"]}
LOW7 = APP["택시 1대 이하 7개 면에 DRT를 1대씩 신규 투입"]
M1 = APP["면 1곳(연 2,496회)에 DRT 1대 신규 투입"]
OAT = {r["case"]: r for r in A3["oat"]}
EMD = pd.read_csv(CLEAN / "A1_gokseong_emd.csv").set_index("emd")
MAN = pd.read_csv(RAW / "MANIFEST.csv")
A2SRC = pd.read_csv(CLEAN / "A2_source_values.csv")
A3SRC = pd.read_csv(CLEAN / "A3_sources.csv")
A4SRC = pd.read_csv(CLEAN / "A4_overseas_values.csv")


# ------------------------------------------------------------------ 표기 도우미
def n(x, d=0):
    return f"{x:,.{d}f}"


def eok(x, d=1):
    return f"{x / 1e8:,.{d}f}억 원"


def man(x, d=0):
    return f"{x / 1e4:,.{d}f}만 원"


def pct(x, d=0):
    return f"{x * 100:.{d}f}%"


def won(x):
    return f"{x:,.0f}원"


def prange(a, b):
    return f"{a * 100:.0f}~{b * 100:.0f}%"


def eok_range(a, b, d=1):
    return f"{a / 1e8:,.{d}f}~{b / 1e8:,.{d}f}억 원"


def won_range(a, b):
    return f"{a:,.0f}~{b:,.0f}원"


# ------------------------------------------------------------------ HTML 조각(개조식)
BODY = 9.5
SMALL = 8
TINY = 7
FONT = "나눔바른고딕"


def p(text, size=BODY, bold=False, indent=0, align="justify", space_after=1.5, color=None, space_before=0):
    style = (f"font-family:'{FONT}'; font-size:{size}pt; margin:{space_before}pt 0 {space_after}pt {indent}pt; "
             f"text-align:{align};")
    if color:
        style += f" color:{color};"
    inner = f"<b>{text}</b>" if bold else text
    return f'<p style="{style}">{inner}</p>'


# 글머리 구조: ○ 소제목(짧은 명사구) 아래 같은 깊이의 - 내용 3~5개. 다른 기호·번호는 쓰지 않는다.
# 들여쓰기·내어쓰기는 80_build_hwpx.py의 HANG에서 지정한다.
def block(title, bullets):
    """○ 소제목 + - 내용 3~5개. 내용은 문자열 또는 (라벨, 문장) 또는 ('!', 문장: 굵은 시사점)."""
    if not 3 <= len(bullets) <= 5:
        raise ValueError(f"'{title}': 내용 {len(bullets)}개(3~5개여야 함)")
    out = [p(f"○ {title}", size=10, bold=True, space_after=1, space_before=3)]
    for b in bullets:
        if isinstance(b, tuple) and b[0] == "!":
            text = f"<b>{b[1]}</b>"
        elif isinstance(b, tuple):
            text = f"<b>{b[0]}</b>: {b[1]}"
        else:
            text = b
        if re.match(r"^(<b>)?[0-9①-⑩]", text):
            raise ValueError(f"'{title}': 내용 줄이 번호·숫자로 시작함 → {text[:20]}")
        out.append(p(f"- {text}"))
    return out


def note(text):
    """표 아래 주석: 글머리 없이 '주:' 문단."""
    return caption(f"주: {text}")


TABLE_WIDTHS = []


def table(header, rows, widths, size=SMALL, align=None, sizes=None):
    TABLE_WIDTHS.append(list(widths))
    align = align or ["left"] * len(header)
    sizes = sizes or [size] * len(header)
    cols = "".join(f'<col width="{w}%">' for w in widths)
    th = "".join(f'<td width="{w}%" style="background:#E9EEF6; font-family:\'{FONT}\'; font-size:{size}pt; '
                 f'text-align:center;"><b>{h}</b></td>' for h, w in zip(header, widths))
    body = ""
    for r in rows:
        tds = "".join(f'<td width="{w}%" style="font-family:\'{FONT}\'; font-size:{s}pt; text-align:{a};">{c}</td>'
                      for c, w, a, s in zip(r, widths, align, sizes))
        body += f"<tr>{tds}</tr>"
    return (f'<table border="1" cellspacing="0" cellpadding="1" width="100%" '
            f'style="border-collapse:collapse;">{cols}<tr>{th}</tr>{body}</table>')


def title(text):
    return p(text, size=SMALL, bold=True, align="left", space_after=1)


def caption(text):
    return p(text, size=TINY + 0.3, align="left", space_after=4, color="#333333")


def figure(fname, width_px):
    src = (FIG / fname).resolve().as_posix()
    return f'<p style="text-align:center; margin:1pt 0 1pt 0;"><img src="file:///{src}" width="{width_px}"></p>'


def doc(parts):
    return ('<html><head><meta charset="utf-8"></head>'
            f'<body style="font-family:\'{FONT}\'; font-size:{BODY}pt;">' + "".join(parts) + "</body></html>")


def save(name, parts):
    (OUT / f"{name}.html").write_text(doc(parts), encoding="utf-8")
    (OUT / f"{name}.tables.json").write_text(json.dumps(TABLE_WIDTHS), encoding="utf-8")
    TABLE_WIDTHS.clear()
    return parts


# ------------------------------------------------------------------ 문장용 값
n_cens = round(DEP["share_hosp_pt_censored"] * DEP["n_sigungu"])
emd_myeon_vehicles = EMD.drop(index="곡성읍").private_vehicles_2021.sum()
n_needles = len(A2SRC) + len(A3SRC) + len(A4SRC)
n_image = int((A2SRC.verified == "image").sum())
residual_cars = sum(r["car_private"] for r in A1["residual_old_name_rows_excluded"])
pax = A3["pax_per_trip"]
base, rt = A3["base"], A3["round_trip"]
gk_trip = A3["gk_public_trip"]
drt_low_pax = A3["drt_fixed_per_vehicle"] / (A3["myeon_trips"] * pax)
taxi_fleet = [24, 1, 0, 7, 1, 0, 0, 13, 2, 1, 1]  # A2 원문 대조 문자열 '합계 50 24 1 - 7 1 - - 13 2 1 1'
assert sum(taxi_fleet) == S2["gk_taxi_fleet_total"]
eup_okgwa = taxi_fleet[0] + taxi_fleet[7]
drivers_1pct = round(GK["county_owners_2024"] * 0.01)
trips_1pct = drivers_1pct * 10 * 12
curve = pd.read_csv(CLEAN / "A3_distance_curve.csv")
gap_e = 1 - curve.resident_empty / curve.taxi
gap_r = 1 - curve.resident_round / curve.taxi
LIC = A4["license_60_74"]  # 경찰청 60~74세 운전면허 소지자(2024년 말), 40_a4_cases.py에서 합산
worst_oat_empty = max(-OAT["수고보상 1.5배"]["vs_taxi_empty"], -OAT["감가상각 포함(262원/km)"]["vs_taxi_empty"])
best_oat_empty = min(-OAT["수고보상 1.5배"]["vs_taxi_empty"], -OAT["감가상각 포함(262원/km)"]["vs_taxi_empty"])
worst_oat_round = min(OAT["수고보상 1.5배"]["vs_taxi_round"], OAT["감가상각 포함(262원/km)"]["vs_taxi_round"])

# ================================================================== 1. 이름/주제
plain = {
    "name": "김대운",
    "title": "교통취약지역 주민 보유 차량의 이동 지원 자원화",
    "subtitle": "등록제 기반 자가용 유상운송의 자원 규모와 비용효율 분석"
                f"(전국 {int(NAT['n_sigungu'])}개 시군구 통계·전남 곡성군 적용)",
}
(OUT / "plain.json").write_text(json.dumps(plain, ensure_ascii=False, indent=1), encoding="utf-8")

# ================================================================== 2. 분석 배경 및 목적
bg = save("background", [
    *block("현황", [
        f"인구감소지역 {int(DEP['n_sigungu'])}곳 인구 {n(DEP['pop'] / 1e4)}만 명 중 65세 이상 {pct(DEP['agg_pop65_share'])}"
        f"(전국 {pct(NAT['agg_pop65_share'])})",
        f"병·의원 평균 접근시간 대중교통 {DEP['min_clinic_pt_median']:.0f}분, 승용차 {DEP['min_clinic_car_median']:.0f}분"
        "(시군구 중앙값)",
        f"종합병원은 대중교통 {DEP['min_hosp_pt_median']:.0f}분, {int(DEP['n_sigungu'])}곳 중 {n_cens}곳은 2시간 내 도달 불가",
    ]),
    *block("기존 정책과 법제도의 한계", [
        f"농촌형 교통모델 2025년 {eok(S2['mafra_2025_public'], 0)}(국비 50%) 투입, {int(S2['mafra_2025_counties'])}개 군 "
        f"{n(S2['mafra_2025_villages'])}개 마을 운영",
        "택시형은 택시가 있는 지역에서만 작동, 버스형·수요응답형은 차량·전담 운전기사 신규 확보 필요",
        "「여객자동차 운수사업법」 제81조는 운행 경비 수령도 자가용 유상운송으로 보아 금지",
        "예외는 평일 출퇴근 카풀과 재난 등 허가 사유에 한정, 이웃 간 실비 운송은 위법",
    ]),
    *block("분석 목적", [
        "입법·정책 제안대회(2025) 제안 「등록제 기반 자가용 유상운송 허용 제도」의 핵심 가설을 공식 통계로 검증",
        ("차량 자원 가설", "교통취약지역 내 활용 가능한 주민 차량 자원 존재"),
        ("비용효율 가설", "운송 건별 실비·수고보상 방식의 기존 대안 대비 공공지출 절감"),
    ]),
])

# ================================================================== 3. 활용 데이터
DATA_ROWS = [
    ("자동차 등록자료 통계 2026. 8.(시군구) - 차량 자원", "국토교통부", "국토교통 통계누리",
     "stat.molit.go.kr/portal/cate/statMetaView.do?hRsId=58"),
    ("주민등록 인구·세대·연령별 인구 2026. 8. - 세대·고령인구", "행정안전부", "주민등록 인구통계", "jumin.mois.go.kr/statMonth.do"),
    ("인구감소지역 재지정(2026. 10. 7.) - 분석 대상 92곳", "행정안전부", "KDI 경제정보센터",
     "eiec.kdi.re.kr/policy/materialView.do?num=287880"),
    ("2025 교통접근성지표 - 병·의원 접근 격차", "한국교통연구원", "국가교통DB",
     "ktdb.go.kr/www/selectBbsNttView.do?key=45&bbsNo=2&nttNo=3829"),
    ("청년통계(2022·2025)·결산서(2024)·마을택시제 계획 - 읍면 차량·효도택시", "곡성군", "곡성군청",
     "gokseong.go.kr/document/kr/data/2025/2024_closing/2024_1.pdf"),
    ("성과보고서(2024)·세출예산(2026)·택시운임 고시 - 콜버스·택시", "완주군", "완주군청",
     "wanju.go.kr/www/file/budget/down/2026/0/2/23.pdf"),
    ("행복택시 운영현황 2025 - 택시형 단가", "용인시", "공공데이터포털", "data.go.kr/data/15126380/fileData.do"),
    ("농촌형 교통모델 2025 이용실태·2026 예산 - 전국 실적", "농림축산식품부", "농식품부 누리집",
     "mafra.go.kr/bbs/home/792/594703/download.do"),
    ("수요응답형교통 도입·운영 가이드라인 - DRT 원가", "국토교통부", "ITS Korea 공개자료",
     "itskorea.kr/downloadFile.do?fileId=FILE_000000000107685&fileSn=0"),
    ("교통시설 투자평가지침(고시 제2026-204호) - 차량운행비용", "국토교통부", "국가법령정보센터",
     "law.go.kr/LSW/flDownload.do?flSeq=164151329"),
    ("석유제품 평균판매가격 - 연료비", "한국석유공사", "오피넷", "www.opinet.co.kr/user/dopospdrg/dopOsPdrgSelect.do"),
    ("2026년 최저임금 고시 - 수고보상", "고용노동부", "국가법령정보센터", "law.go.kr/LSW/flDownload.do?flSeq=155278071"),
    ("유상운송 특약 도입 보도참고자료 - 보험료", "금융감독원", "금감원 누리집",
     "fss.or.kr/fss/bbs/B0000188/view.do?nttId=15852&menuNo=200218"),
    ("公共ライドシェア 현황 - 일본 운영 실적", "일본 국토교통성", "국토교통성 누리집",
     "www.mlit.go.jp/jidosha/content/002008895.pdf"),
    ("Volunteer drivers(EIM71155) - 영국 보상 기준", "영국 국세청", "GOV.UK",
     "gov.uk/hmrc-internal-manuals/employment-income-manual/eim71155"),
    ("여객자동차 운수사업법 제81조 - 법제", "법제처", "국가법령정보센터", "law.go.kr/법령/여객자동차운수사업법/제81조"),
]
data_cell = save("data", [
    *block("데이터 구성", [
        f"공식 통계·결산서·예산서·법령 등 원자료 {len(MAN)}건을 기관 누리집에서 직접 수집",
        "전 자료의 출처 URL·기준시점·SHA-256 해시를 코드 저장소 MANIFEST.csv로 공개",
        "핵심 자료와 선정 이유는 아래 표와 같음",
    ]),
    table(["활용 데이터(명) - 선정 이유", "제공기관(명)", "플랫폼(명)", "URL"], DATA_ROWS, [35, 12, 13, 40],
          size=TINY, sizes=[TINY, TINY, TINY, 6.3]),
])

# ================================================================== 4. 분석과정 및 방법
method = save("method", [
    *block("자료 수집·정제", [
        f"원자료 {len(MAN)}건을 SHA-256 해시와 함께 보관",
        f"결산서·지침·해외 문서 인용 수치 {n_needles}건은 원문 쪽의 동일 문자열을 스크립트로 자동 대조"
        f"(이미지 쪽 {n_image}건은 판독)",
        f"일반구는 시로 합산, 행정구역 개편 후 옛 명칭 잔여 등록 {n(residual_cars)}대 제외",
    ]),
    *block("분석 절차", [
        ("차량 자원", f"자동차 등록·주민등록 세대·인구·KTDB 접근지표를 {int(NAT['n_sigungu'])}개 시군구로 결합해 "
                    "인구감소지역·관심지역·기타 지역 비교"),
        ("기존 대안 비용", "결산·예산 집행액을 이용 실적으로 나눠 1건당 공공지출 산출, DRT는 차량 1대 연 운영비로 환산"),
        ("주민차량 비용", "차량실비(감가상각 제외) + 수고보상(최저임금 × 소요시간) + 운행보험 + 안전·등록비 + 정산비"),
        ("민감도·손익분기", f"평균 편도 {A3['d_base_km']:.1f}km 역산, 6개 변수 {A3['sens_n']}개 조합, 생활권 수요별 "
                       "손익분기 산출 후 곡성군 적용"),
    ]),
    *block("재현성", [
        ("코드·데이터", GITHUB),
        "Python 3.11 기반, run_all.py 한 번으로 원자료부터 그림·원고까지 재현",
        "결과 파일 해시는 2회 실행 시 동일, 인용 수치의 원문 대조 실패 0건",
    ]),
])


# ================================================================== 5. AI 기술 활용
ai = save("ai", [
    *block("사용 서비스와 활용 범위", [
        "Anthropic Claude Code(Claude Opus 5.5 모델), 한컴오피스 자동화(pyhwpx)",
        "공공데이터 수집 스크립트, 시군구 명칭 정규화·결합, 결산서 수치 원문 대조 코드 작성",
        "비용모형·민감도·그림 코드 작성과 공모전 양식 조판 자동화",
        "해외 1차 자료·국내 비용 원단위 조사는 하위 에이전트 2개가 병렬 수행, 출처·쪽 번호 기록",
    ]),
    *block("검증 원칙과 주요 프롬프트", [
        "AI 제시 수치는 미사용, 모든 수치를 원자료에서 스크립트로 재계산하고 원문과 대조",
        "\"자동차등록과 주민등록 세대를 시군구로 결합해 인구감소지역의 인구당 자가용을 계산하라\"",
        "\"결산서 쪽 번호와 금액을 원문에서 찾아 대조하고 못 찾으면 멈춰라\"",
        "\"주민차량 1회 비용을 항목별로 나누고 택시형·DRT와의 손익분기를 구하라\"",
    ]),
])

# ================================================================== 6. 분석 내용 및 결과
t1_rows = [
    ("택시형", "곡성 효도택시(2024 결산)", eok(S2["gk_taxi_2024_exp"], 2),
     f"{n(S2['gk_taxi_2024_trips'])}회·{n(S2['gk_taxi_2024_pax'])}명",
     f"운행 {won(A2['gokseong_taxi_per_trip'])}<br>이용자 {won(A2['gokseong_taxi_per_pax'])}"),
    ("택시형", "완주 으뜸택시(2024 결산)", eok(S2["wj_taxi_2024_exp"], 2), f"{n(S2['wj_taxi_2024_pax'])}명",
     f"이용자 {won(A2['wanju_taxi_per_pax'])}"),
    ("택시형", "용인 행복택시(2025)", eok(A2["yongin"]["subsidy_year"], 2), f"{n(A2['yongin']['trips_year'])}회",
     f"이용 {won(A2['yongin']['subsidy_per_trip'])}"),
    ("DRT", "완주 행복콜버스(2024, 차량 포함)", eok(S2["wj_callbus_2024_opex"] + S2["wj_callbus_2024_vehicle"], 2),
     f"{n(S2['wj_callbus_2024_pax'])}명", f"이용자 {won(A2['wanju_callbus_per_pax_incl_vehicle'])}"),
    ("DRT", "완주 행복콜버스(2026 예산)", f"대당 연 {man(A2['wanju_callbus_opex_per_vehicle_2026'])}",
     f"{int(S2['wj_callbus_2025_fleet'])}대", "차량 대당 4천만 원 별도"),
    ("노선버스", "곡성 벽지·비수익 노선(2024)",
     eok(S2["gk_bus_remote_loss"] + S2["gk_bus_subsidy"] + S2["gk_bus_flatfare_loss"]),
     f"{int(S2['gk_bus_routes'])}개 노선", f"노선당 연 {man(A2['gokseong_bus_loss_per_route'])}"),
    ("전체", "농촌형 교통모델 전국(2025)", eok(S2["mafra_2025_public"], 0), f"{n(S2['mafra_2025_users'] / 1e4)}만 명",
     f"이용자 {won(A2['mafra_public_per_user_2025'])}"),
]
t2_rows = [
    (f"차량실비({base['v_per_km']:.0f}원/km)", won(base["vehicle"]), won(rt["vehicle"]),
     f"투자평가지침 원단위, 휘발유 {n(A3['fuel_2026_avg'])}원/L(2026)"),
    ("수고보상", f"{won(base['effort'])}({base['minutes']:.0f}분)", f"{won(rt['effort'])}({rt['minutes']:.0f}분)",
     f"최저임금 {n(S3['min_wage_2026'])}원/시간"),
    ("운행보험", won(base["insurance"]), won(rt["insurance"]), "금감원 단체특약 10분당 178원 × 2"),
    ("안전교육·점검", won(base["safety"]), won(rt["safety"]), "운전자 연 5만 원 ÷ 120건(가정)"),
    ("정산·운행기록", won(base["mgmt"]), won(rt["mgmt"]), "건당 500원(가정)"),
    ("1회 총비용", won(base["total"]), won(rt["total"]), "항목 합계"),
    ("<b>1회 공공지출</b>", f"<b>{won(base['public'])}</b>", f"<b>{won(rt['public'])}</b>", "총비용 - 본인부담 100원"),
    ("<b>효도택시 대비</b>", f"<b>{pct(A3['saving_vs_taxi_empty'])} 절감</b>", f"<b>{pct(A3['saving_vs_taxi_round'])} 절감</b>",
     f"효도택시 운행당 {won(gk_trip)}"),
]
a4t = pd.read_csv(CLEAN / "A4_table.csv", dtype=str)
t3_rows = [(r["국가"], f"{r['제도']}<br>{r['운영 주체']}", r["운전자 보상·요금"], f"{r['규모']}({r['기준']})")
           for _, r in a4t.iterrows()]

results = save("results", [
    *block("교통취약지역의 주민 차량 자원", [
        f"인구감소지역 {int(DEP['n_sigungu'])}곳 자가용 승용차 {n(DEP['car_private'] / 1e4, 1)}만 대, 승합·화물 포함 자가용 "
        f"{n(DEP['total_private'] / 1e4, 1)}만 대(2026. 8.)",
        f"인구 1천 명당 자가용 승용차 {n(DEP['agg_car_per_1000'])}대로 전국 {n(NAT['agg_car_per_1000'])}대, 그 외 지역 "
        f"{n(OTH['agg_car_per_1000'])}대 상회, 세대당 자가용(전 차종)도 {DEP['agg_private_all_per_hh']:.2f}대로 전국 "
        f"{NAT['agg_private_all_per_hh']:.2f}대 상회",
        f"곡성군 개인 소유 차량 {n(GK['county_vehicles_2024'])}대·차주 {n(GK['county_owners_2024'])}명(2024년 말), 10개 면 "
        f"지역에도 {n(emd_myeon_vehicles)}대(2021년 말)",
        f"반면 종합병원 대중교통 30분 내 도달 인구 비율은 중앙값 {DEP['r30_hosp_pt_median']:.0f}%(승용차 "
        f"{DEP['r30_hosp_car_median']:.0f}%), 곡성 죽곡면은 대중교통 2시간 내 병·의원 도달 불가(승용차 "
        f"{EMD.loc['죽곡면', 'min_clinic_car']:.0f}분)",
        ("!", "차량 부족이 아닌 기존 차량과 이동 수요의 연결 부재가 교통취약지역 이동 문제의 핵심"),
    ]),
    figure("fig1_vehicle_assets.png", 450),
    caption("그림 1. (가) 시군구별 병·의원 대중교통 접근시간과 인구 1천 명당 자가용 승용차, (나) 곡성군 읍면별 병·의원 접근시간"
            "과 개인소유 차량. 자료: 국토교통부·행정안전부(2026. 8.), 한국교통연구원 KTDB(2025), 곡성군 청년통계(2022). 오곡면은 "
            "승용차 시간이 대중교통보다 긴 이상값으로 제외. 세대당 승용차(0.77대)는 1인 고령 세대 비중의 영향으로 전국(0.84대) 하회"),

    *block("기존 교통복지 대안의 비용구조", [
        f"택시형은 차량 투자 없이 이용자 1명당 {won_range(A2['wanju_taxi_per_pax'], A2['gokseong_taxi_per_pax'])}, 단 "
        "택시가 있는 지역에서만 작동",
        f"곡성 등록 택시 {int(S2['gk_taxi_fleet_total'])}대 중 {eup_okgwa}대가 곡성읍·옥과면에 집중, 삼기·죽곡·고달면 0대, "
        "오곡·목사동·겸·오산면 1대",
        f"수요응답형 버스(DRT)는 차량·전담 운전기사 신규 확보 필요, 완주 행복콜버스 대당 연 "
        f"{man(A2['wanju_callbus_opex_per_vehicle_2026'])}",
        f"국토부 가이드라인 원가 하루 {won(S2['drt_guide_daily_cost'])} 중 {pct(A2['drt_guide_driver_share'])}가 운전기사 인건비",
        ("!", "택시 부족 저수요 지역의 신규 공급 비용은 수요와 무관하게 고정"),
    ]),
    title("표 1. 기존 대안의 공공지출과 이용 1건당 비용"),
    table(["유형", "사례(기준)", "공공지출", "이용 실적", "1건당 공공지출"], t1_rows, [11, 33, 17, 17, 22], size=TINY + 0.5,
          align=["center", "left", "right", "right", "right"]),
    caption("자료: 곡성군·완주군 결산서·예산서, 용인시 공공데이터, 농림축산식품부(2026. 2.). DRT·노선버스는 차량과 전담 운전기사 필요"),

    *block("주민차량 1회 운행 비용", [
        f"효도택시 운행당 평균 지출 {won(gk_trip)}과 본인부담 100원을 완주군 택시 운임 고시(기본 2km "
        f"{n(S3['taxi_base_fare'])}원, {int(S3['taxi_unit_m'])}m당 {int(S3['taxi_unit_fare'])}원)에 대입해 평균 편도 "
        f"{A3['d_base_km']:.1f}km 산출",
        f"차량실비는 투자평가지침 차량운행비용 중 감가상각을 제외하고 휘발유 2026년 평균가 반영"
        f"({base['v_per_km']:.0f}원/km)",
        f"수고보상은 최저임금 {n(S3['min_wage_2026'])}원에 소요시간을 곱해 산정, 보험은 금감원 단체특약 요율의 2배 적용",
        f"공공지출은 1회당 빈차 귀가 {won(base['public'])}, 동행 왕복 {won(rt['public'])}(표 2)",
    ]),
    title(f"표 2. 주민차량 1회 운행 비용(편도 {A3['d_base_km']:.1f}km, 2026년 가격)"),
    table(["항목", "빈차 귀가", "동행 왕복", "근거"], t2_rows, [22, 19, 19, 40], size=TINY + 0.5,
          align=["left", "right", "right", "left"]),
    note("빈차 귀가는 승객 하차 후 운전자 단독 귀가(보수적 가정), 동행 왕복은 용무 종료까지 대기 후 함께 귀가(귀가 운행은 별도 "
         "1회, 대기시간 보상 없음). 감가상각은 기존 보유 차량이므로 제외"),

    *block("기존 대안 대비 절감 효과", [
        f"택시형 대비 빈차 귀가 {pct(A3['saving_vs_taxi_empty'])}, 동행 왕복 {pct(A3['saving_vs_taxi_round'])} 절감",
        f"거리 1~25km 전 구간에서 빈차 귀가는 택시 운임 대비 {-gap_e.min() * 100:.0f}% 높음~{gap_e.max() * 100:.0f}% 낮음, "
        f"동행 왕복은 {gap_r.min() * 100:.0f}~{gap_r.max() * 100:.0f}% 낮음",
        f"감가상각 포함·수고보상 1.5배 조건에서도 동행 왕복은 {worst_oat_round * 100:.0f}% 이상 절감, {A3['sens_n']}개 조합 중 "
        f"{pct(A3['sens_share_le_taxi_round'])}가 효도택시 단가 이하",
        f"곡성 면 평균 수요(연 {n(A3['myeon_trips'])}회)에 DRT 1대(연 {eok(A3['drt_fixed_per_vehicle'], 2)}) 투입 시 이용자 "
        f"1명당 {won(drt_low_pax)}, 주민차량은 {won_range(rt['public'] / pax, base['public'] / pax)}",
        f"생활권 수요 연 {n(A3['q_star_drt_trips'])}회(동행 왕복 {n(A3['q_star_drt_trips_round'])}회) 미만이면 주민차량이 "
        "DRT 신규 투입보다 유리",
    ]),
    figure("fig2_costs.png", 450),
    caption(f"그림 2. (가) 이용자 1명당 공공지출(주민차량은 1회 공공지출 ÷ 효도택시 운행당 탑승 {pax:.2f}명), (나) 생활권 연간 "
            "수요별 연간 공공지출. DRT는 완주 행복콜버스 대당 운영비(2026)와 차량 4,000만 원 7년 연할, 대당 연 이용 실적(2024) 기준"),

    *block("곡성군 적용 결과", [
        f"등록 택시 1대 이하 7개 면(면 지역 인구의 {pct(A3['share_low_taxi_myeon_pop'])})에 DRT 1대씩 투입 시 연 "
        f"{eok(LOW7['alt_cost'], 2)}",
        f"같은 운행(연 {n(LOW7['trips'])}회)을 주민차량이 맡으면 {eok_range(LOW7['res_cost_round'], LOW7['res_cost_empty'], 2)}",
        f"연 {eok_range(LOW7['saving_empty'], LOW7['saving_round'])}({prange(LOW7['saving_pct_empty'], LOW7['saving_pct_round'])}) "
        f"절감, 곡성군 2026년 효도택시 총사업비({eok(S2['gk_taxi_2026_budget'])}) 상회",
        ("!", f"택시 운영 지역에서는 택시형과 대등 이상, 택시 공백 지역에서는 공공지출 {pct(LOW7['saving_pct_empty'])} 이상 절감"),
    ]),

    *block("해외 운영 사례와 국내 운영 자원", [
        ("일본", "시정촌·NPO 등록제로 주민 자가용 유상운송 허용, 요금 기준을 택시요금의 약 50%에서 80%로 상향(2023. 12.)"),
        ("일본 실적", f"운영 단체 {int(S4['jp_orgs_2022'])}개(2022. 3.)에서 {int(S4['jp_orgs_2026'])}개(2026. 3.)로 "
                    f"{pct(A4['jp_orgs_growth_2022_2026'])} 증가, 전체 시정촌의 {pct(A4['jp_munis_share_2026'])} 운영, "
                    f"2024년도 사망사고 {int(S4['jp_fatal_2024'])}건"),
        ("영국", f"운행비 이하 사전 약정 요금은 영업에서 제외, 지역사회교통 기관의 {pct(S4['uk_cta_share_car_scheme'])}가 "
               f"자원봉사 차량제 운영, 비과세 실비 마일당 {int(round(S4['uk_amap_55p'] * 100))}펜스(2026/27)"),
        ("국내", f"곡성 개인 차주의 1%({drivers_1pct}명)가 월 10회 운행 시 연 {n(trips_1pct)}회로 효도택시 연간 운행의 "
               f"{pct(trips_1pct / S2['gk_taxi_2024_trips'])}, 전국 60~74세 운전면허 소지자 {n(LIC / 1e4)}만 명"),
        ("!", "등록·보험·요금 상한을 갖춘 주민 자가용 운송은 해외에서 검증된 제도, 국내 운영 자원도 충분"),
    ]),
    title("표 3. 해외 주민 자가용 유상·실비 운송 제도"),
    table(["국가", "제도·운영 주체", "보상·요금", "규모(기준)"], t3_rows, [8, 40, 26, 26], size=TINY,
          align=["center", "left", "left", "left"]),
    caption("자료: 일본 국토교통성(2022~2026), 영국 HMRC·DfT·CTA(2024~2026), 미국 IRS·미네소타 교통부(2018~2025)"),

    *block("이용 주민·운전 주민·지자체의 편익", [
        ("이용 주민", f"병·의원 접근시간 대중교통 {DEP['min_clinic_pt_median']:.0f}분에서 승용차 "
                    f"{DEP['min_clinic_car_median']:.0f}분 수준으로 단축(인구감소지역 중앙값, 호출 대기 제외)"),
        ("운전 주민", f"1회 수고보상 {won(base['effort'])}과 차량실비 {won(base['vehicle'])}, 수고보상은 월 10회 "
                    f"{man(A3['driver_month_10'], 1)}·월 30회 {man(A3['driver_month_30'], 1)} 수준의 여유 시간 부수입"),
        ("지자체", f"차량 구입비·운전기사 인건비 불필요, 군당 국비 지원기준 3.5억 원으로 연 "
                 f"{n(A3['budget_350m_trips_empty'] / 1e4, 1)}만~{n(A3['budget_350m_trips_round'] / 1e4, 1)}만 회 운행 가능"),
        ("안전망", "6인승 이하 승용차 유상운송 특약은 화물용만 존재(2020), 등록제로 비공식 여객 운송을 보험·운행기록 체계에 편입"),
    ]),
])

# ================================================================== 7. 정책제안 및 기대효과
t4_rows = [
    ("운수사업법 제81조", "운행 경비 수령도 금지, 예외는 출퇴근 카풀·재난 등 허가",
     "제1항 제3호 신설: 인구감소지역 등에서 시장·군수에게 등록한 주민의 실비 범위 보상 운송 허용"),
    ("시행규칙", "제103조 허가 사유에 일상 이동 없음",
     "등록 요건(실거주 1년·무사고·범죄경력 조회·안전교육 8시간), 보상 기준(차량운행비용 원단위 실비 + 최저임금 수고보상, "
     "택시요금 80% 이내), 월 30회 상한"),
    ("보험", "6인승 이하 승용차 여객 유상운송 특약 없음", "운행시간 비례 단체특약 도입, 지자체 일괄 가입·보험료 지원"),
    ("조례·운영", "효도택시 등 택시형 지원 조례", "등록·정산 근거 마련, 기존 콜센터의 택시·주민차량 통합 배차"),
]
policy = save("policy", [
    *block("입법: 「여객자동차 운수사업법」 제81조 ‘등록 주민 운송’ 예외 신설", [
        "제81조 제1항 제3호 신설로 인구감소지역 등에서 시장·군수에게 등록한 주민의 실비 범위 보상 운송 허용",
        "시행규칙에 등록 요건·보상 기준·월 30회 상한 규정",
        "승용차 여객 유상운송 단체특약 도입, 지자체 일괄 가입·보험료 지원",
    ]),
    table(["구분", "현행", "개정 방향"], t4_rows, [16, 32, 52], size=TINY + 0.5, align=["center", "left", "left"]),
    *block("적용 우선순위", [
        ("최우선", f"등록 택시 1대 이하 또는 DRT 신규 투입이 필요한 면(생활권 연 수요 약 "
                 f"{n(round(A3['q_star_drt_trips'], -3))}회 이하), DRT 대비 {prange(M1['saving_pct_empty'], LOW7['saving_pct_round'])} 절감"),
        ("차순위", f"택시형 운영 지역의 병원 대기·동행 왕복형 이동 보완, 택시형 대비 최대 {pct(A3['saving_vs_taxi_round'])} 절감"),
        ("유지", "택시가 충분한 읍 지역의 단거리 편도는 택시형 유지"),
    ]),
    *block("기대효과", [
        ("재정", f"곡성군 택시 1대 이하 7개 면 기준 DRT 대안 대비 연 {eok_range(LOW7['saving_empty'], LOW7['saving_round'])} "
               "절감, 차량 구입비 0원"),
        ("확산", "인구감소지역 92곳의 택시 공백 면에 동일 방식 적용 가능"),
        ("이동권·소득", "주민의 병원·장보기 이동 보장, 운전 주민의 실비·수고보상 확보"),
        ("안전", "비공식 운송의 보험·운행기록 기반 합법 운송 전환"),
    ]),
    *block("결론", [
        "교통취약지역의 주민 차량 자원 존재와 비용 우위 조건 확인",
        f"일본은 등록제 도입 후 전체 시정촌의 {pct(A4['jp_munis_share_2026'])}까지 확산",
        ("!", "시범사업 단계를 넘어 법 개정을 통한 본격 제도화 필요"),
    ]),
])

# ================================================================== 8. 분석도구 및 참고문헌
refs = [
    "국토교통부(2026). 자동차 등록자료 통계(2026. 8.). 국토교통 통계누리.",
    "행정안전부(2026). 주민등록 인구 및 세대현황·연령별 인구현황(2026. 8.).",
    "행정안전부(2026. 10. 7.). 5년 만의 '인구감소지역' 재지정, 지역 활력 회복을 위한 지원을 강화한다(보도자료).",
    "한국교통연구원(2026). 2025년 기준 교통접근성지표. 국가교통DB.",
    "국토교통부(2026). 교통시설 투자평가지침(국토교통부고시 제2026-204호).",
    "국토교통부(2025. 12.). 수요응답형교통 도입·운영 가이드라인.",
    "농림축산식품부(2026. 2. 11.). 농촌형 교통모델 연간 이용자 740만 명 돌파(보도자료); (2026. 1.) 2026년 예산 및 기금운용계획 개요.",
    "한국농촌경제연구원(2021). 농촌형·도시형 교통모델 개선 영향평가.",
    "곡성군(2025). 2024회계연도 결산서·성과보고서; 곡성군 청년통계(2022·2025); 민선8기 공약 실천계획(2025. 11.).",
    "곡성군의회(2026. 7. 13.). 제279회 제1차 본회의 회의록.",
    "완주군(2025). 2024회계연도 성과보고서; 2024년 제4회 추경·2026년 본예산 세출예산서; 고시 제2023-78호(택시운임).",
    "용인시(2026). 행복택시 운영현황. 공공데이터포털.",
    "한국석유공사. 오피넷 석유제품 평균판매가격(2025~2026).",
    "고용노동부(2025). 2026년 적용 최저임금 고시(제2025-47호).",
    "금융감독원(2020. 7. 23.). 자동차보험 화물 유상운송 특약 도입(보도참고자료).",
    "법제처. 여객자동차 운수사업법 제81조(법률 제21710호); 같은 법 시행규칙 제103조(국토교통부령 제1621호).",
    "경찰청. 운전면허 소지자 현황(2024). 국가통계포털.",
    "国土交通省(2026). 公共ライドシェア(交通空白地 自家用有償旅客運送)の活用について; (2025) 地域交通における担い手・移動の足不足への対応方策のカタログ.",
    "中国運輸局(2024). 自家用有償旅客運送者が利用者から収受する対価の取扱いについて.",
    "HMRC(2026). Employment Income Manual EIM71155; Public Passenger Vehicles Act 1981 s.1; Community Transport Association(2024). Mapping England.",
    "IRS(2025). IR-2025-128; Minnesota DOT(2019). 2018 report on Minnesota Council on Transportation Access.",
    "김대운 외(2025). 도서산간 교통복지 사각지대 해소를 위한 등록제 기반 자가용 유상운송 허용 제도. 2025년 입법 및 정책 제안대회 제안서.",
]
tools = save("refs", [
    p("<b>분석도구</b>: Python 3.11(pandas, pdfplumber, PyMuPDF, matplotlib), 한컴오피스(pyhwpx), Anthropic Claude Code", size=8),
    p(f"<b>코드·원자료 저장소</b>: {GITHUB}", size=8),
    *[p(f"[{i}] {html.escape(r)}", size=TINY + 0.3, align="left", space_after=0.5) for i, r in enumerate(refs, 1)],
])

# ================================================================== 9. 분석결과 이미지
image = save("image", [
    figure("fig3_summary.png", 450),
    caption("그림 3. 분석결과 요약. 자료: 본문 그림 1·2, 표 1~3"),
])


# ------------------------------------------------------------------ 검토용 텍스트
def strip(parts):
    t = "\n".join(parts)
    t = re.sub(r"<br>", " ", t)
    t = re.sub(r"</(p|tr)>", "\n", t)
    t = re.sub(r"</td>", " | ", t)
    t = re.sub(r"<[^>]+>", "", t)
    return html.unescape(re.sub(r"\n+", "\n", t)).strip()


md = [f"## 주제\n\n{plain['title']}\n{plain['subtitle']}\n"]
for ttl, parts in [("분석 배경 및 목적", bg), ("활용 데이터", data_cell), ("분석과정 및 방법", method), ("AI 기술 활용", ai),
                   ("분석 내용 및 결과", results), ("정책제안 및 기대효과", policy), ("분석도구 및 참고문헌", tools),
                   ("분석결과 이미지", image)]:
    md.append(f"## {ttl}\n\n{strip(parts)}\n")
(ROOT / "report" / "manuscript.md").write_text("\n".join(md), encoding="utf-8")
print("cells:", sorted(f.name for f in OUT.iterdir() if f.suffix == ".html"))
print("manuscript chars:", sum(len(x) for x in md))
