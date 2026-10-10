"""D6 검증: 결과 재현 해시, 원문 대조 결과, 원고의 금지 표현, 양식 필수 항목, PDF 분량, 데이터 URL 접속.

사용법: python code/90_verify.py [--urls]
  --urls  활용 데이터 표의 URL에 실제로 접속해 응답 코드를 기록한다(네트워크 필요).
출력: report/verification.md, report/verification_hashes.json
"""
import hashlib
import json
import re
import sys
import urllib.request

import pandas as pd

from common import CLEAN, FIG, RAW, ROOT

REPORT = ROOT / "report"
FORBIDDEN = ["시범사업을 검토할 필요", "추가 연구가 필요", "11,103", "698만", "7,900만", "3,800만", "10~15%", "5%p",
             "수백억", "40~60분", "20~30분"]
REQUIRED = ["이름/팀명", "주제", "분석 배경", "활용", "분석과정", "AI 기술", "분석 내용", "정책제안", "분석도구", "분석결과"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    lines, fails = ["# 검증 기록", ""], []

    # 1) 결과 파일 해시(재실행 시 비교)
    files = sorted([*CLEAN.glob("*.csv"), *CLEAN.glob("*.json")])
    hashes = {f.name: sha(f) for f in files}
    prev_path = REPORT / "verification_hashes.json"
    if prev_path.exists():
        prev = json.loads(prev_path.read_text(encoding="utf-8"))
        changed = [k for k in hashes if prev.get(k) != hashes[k]]
        lines.append(f"- 결과 파일 {len(hashes)}개 해시: 직전 실행 대비 변경 {len(changed)}개 {changed[:5]}")
    else:
        lines.append(f"- 결과 파일 {len(hashes)}개 해시 최초 기록")
    prev_path.write_text(json.dumps(hashes, indent=1), encoding="utf-8")

    # 2) 원문 대조
    for name in ["A2_source_values.csv", "A3_sources.csv", "A4_overseas_values.csv"]:
        d = pd.read_csv(CLEAN / name)
        bad = d[~d.verified.isin(["ok", "image"])]
        lines.append(f"- {name}: {len(d)}건 중 원문 일치 {int((d.verified == 'ok').sum())}건, 이미지 판독 "
                     f"{int((d.verified == 'image').sum())}건, 실패 {len(bad)}건")
        if len(bad):
            fails.append(f"{name} 원문 대조 실패 {list(bad.id)}")

    # 3) 원자료 목록
    man = pd.read_csv(RAW / "MANIFEST.csv")
    missing_url = man[man.url.isna() | (man.url == "")]
    lines.append(f"- 원자료 {len(man)}건(해시 기록), URL 누락 {len(missing_url)}건")
    if len(missing_url):
        fails.append("MANIFEST URL 누락")

    # 4) 원고 금지 표현
    text = (REPORT / "manuscript.md").read_text(encoding="utf-8")
    hits = [w for w in FORBIDDEN if w in text]
    lines.append(f"- 금지 표현(원제안의 미검증 수치·원론적 결론) 검색: {hits if hits else '0건'}")
    if hits:
        fails.append(f"금지 표현 {hits}")

    # 4-2) 개조식 명사형 종결: 표·참고문헌·리드문 외 본문 줄이 '~다'로 끝나면 실패
    body = [ln.strip() for ln in text.splitlines()
            if ln.strip() and not ln.startswith("#") and "|" not in ln and not ln.lstrip().startswith("[")
            and not ln.strip().endswith("하고자 함.")]
    narrative = [ln for ln in body if re.search(r"다[.\"]?$", ln)]
    lines.append(f"- 서술형 종결(~다) 줄: {len(narrative)}건 / 본문 {len(body)}줄")
    if narrative:
        fails.append(f"서술형 종결 {narrative[:3]}")

    # 4-3) 글머리 피라미드: 모든 ○ 소제목 아래 - 내용 3~5개, - 는 번호·숫자로 시작하지 않음, 다른 글머리 기호 없음
    struct_bad, cur, kids = [], None, 0
    for ln in text.splitlines() + ["○ END"]:
        t = ln.strip()
        if t.startswith("○") or t.startswith("##"):
            if cur and not 3 <= kids <= 5:
                struct_bad.append(f"{cur[:20]}({kids}개)")
            cur, kids = (t if t.startswith("○") else None), 0
        elif t.startswith("- ") and cur is not None:
            kids += 1
            if re.match(r"^- [0-9①-⑩]", t):
                struct_bad.append(f"번호 시작: {t[:20]}")
        elif cur is not None and kids:
            if not 3 <= kids <= 5:
                struct_bad.append(f"{cur[:20]}({kids}개)")
            cur = None
    other = [t for t in (l.strip() for l in text.splitlines()) if t and t[0] in "□⇒*①②③④⑤"]
    n_topics = sum(1 for l in text.splitlines() if l.strip().startswith("○ ") and l.strip() != "○ END")
    lines.append(f"- 글머리 구조: 소제목 {n_topics}개, 내용 3~5개 위반 {len(struct_bad)}건, 기타 기호 {len(other)}건")
    if struct_bad or other:
        fails.append(f"글머리 구조 위반 {struct_bad[:3]} {other[:3]}")

    # 5) PDF 필수 항목·분량·그림
    pdf = REPORT / "김대운_분석보고서.pdf"
    if pdf.exists():
        import pdfplumber
        with pdfplumber.open(pdf) as d:
            pages = [(pg.extract_text() or "") for pg in d.pages]
            n_img = sum(len(pg.images) for pg in d.pages)
        full = re.sub(r"\s+", "", "".join(pages))
        miss = [r for r in REQUIRED if re.sub(r"\s+", "", r) not in full]
        ref_page = next((i + 1 for i, t in enumerate(pages) if "[1] 국토교통부" in t), None)
        lines.append(f"- PDF {len(pages)}쪽, 참고문헌 시작 {ref_page}쪽, 삽입 그림 {n_img}개, 필수 항목 누락 {miss or '없음'}")
        if miss:
            fails.append(f"필수 항목 누락 {miss}")
        if "유의사항" in full:
            fails.append("양식 안내문(유의사항) 잔존")
        guide = [g for g in ["※ 데이터 분석의 핵심", "※ 분석 배경(현황", "※ 정책제안 및 기대효과"] if g.replace(" ", "") in full]
        if guide:
            fails.append(f"양식 안내 문구 잔존 {guide}")
    else:
        fails.append("PDF 없음")

    # 6) 그림 파일
    figs = sorted(f.name for f in FIG.glob("*.png"))
    lines.append(f"- 그림 파일: {figs}")

    # 7) URL 접속(선택)
    if "--urls" in sys.argv:
        import importlib.util
        spec = importlib.util.spec_from_file_location("cells", ROOT / "code" / "70_write_cells.py")
        src = (ROOT / "code" / "70_write_cells.py").read_text(encoding="utf-8")
        block = src[src.index("DATA_ROWS = ["):src.index("data_cell = save(")]
        urls = re.findall(r'"((?:www\.)?(?:[a-z0-9-]+\.)+(?:kr|jp|uk|go\.kr|com)(?:/[^"]*)?)"\)', block)
        gh = re.search(r'GITHUB = "([^"]+)"', src).group(1)
        urls = [gh.replace("https://", "")] + urls
        res = []
        for u in urls:
            url = "https://" + u
            try:
                req = urllib.request.Request(urllib.parse.quote(url, safe=":/?&=%#"), method="GET",
                                             headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    code = r.status
            except Exception as e:
                code = getattr(e, "code", type(e).__name__)
            res.append((url, code))
        ok = sum(1 for _, c in res if c == 200)
        lines.append(f"- 활용 데이터 URL {len(res)}개 접속: 200 응답 {ok}개")
        for u, c in res:
            lines.append(f"  - {c} {u}")

    lines += ["", f"## 판정: {'통과' if not fails else '실패'}"] + [f"- {f}" for f in fails]
    (REPORT / "verification.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    if fails:
        sys.exit(1)


if __name__ == "__main__":
    import urllib.parse  # noqa: F401
    main()
