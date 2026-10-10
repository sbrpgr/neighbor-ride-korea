"""행정안전부 2026.10.7. 보도자료 [참고]에서 인구감소지역(92)·관심지역(18) 명단을 추출한다.

PDF 표는 '2021년 지정 | 2026년 지정' 두 칸으로 되어 있어, 2026년 칸(x 좌표 기준)만 읽는다.
시도별 괄호 안 개수와 총계(92, 18)가 일치하는지 검증한다.
"""
import re
import sys

import pandas as pd
import pdfplumber

from common import CLEAN, RAW

PDF = RAW / "mois_depopulation" / "mois_depopulation_redesignation_20261007.pdf"

# (페이지 인덱스, 2026년 '구분' 칸 시작 x, 표 상단 y, 지역 유형, 기대 총계)
SPECS = [(3, 412, 200, "인구감소지역", 92), (4, 388, 145, "인구감소관심지역", 18)]


def parse_page(page, x_from, y_from):
    words = [w for w in page.extract_words() if w["x0"] >= x_from and w["top"] >= y_from]
    rows = {}
    for w in words:
        rows.setdefault(round(w["top"] / 4), []).append(w)
    entries, labels = [], []
    for key in sorted(rows):
        line = " ".join(w["text"] for w in sorted(rows[key], key=lambda w: w["x0"]))
        for m in re.finditer(r"([가-힣]+)\((\d+)\)", line):
            labels.append((key, m.group(1), int(m.group(2))))
        body = re.sub(r"[가-힣]+\(\d+\)", " ", line)
        body = body.replace("(종전동구)", "")
        for tok in re.split(r"[,\s]+", body):
            tok = tok.strip()
            if re.fullmatch(r"[가-힣]+(시|군|구)", tok):
                entries.append((key, tok))
    return entries, labels


def assign(entries, labels):
    """각 지명을 가장 가까운 시도 라벨에 배정하되, 라벨별 개수를 넘지 않도록 위에서부터 채운다."""
    out = []
    remaining = {i: n for i, (_, _, n) in enumerate(labels)}
    for key, name in entries:
        # 행 위치가 라벨 행 범위 안에 드는 첫 라벨: 위쪽 라벨부터 개수가 남은 곳
        cands = sorted(range(len(labels)), key=lambda i: abs(labels[i][0] - key))
        for i in cands:
            if remaining[i] > 0 and abs(labels[i][0] - key) <= 6:
                remaining[i] -= 1
                out.append((labels[i][1], name))
                break
        else:
            raise ValueError(f"배정 실패: {name} (row {key})")
    return out, remaining


def main():
    frames = []
    with pdfplumber.open(PDF) as pdf:
        for pidx, x_from, y_from, kind, expect in SPECS:
            entries, labels = parse_page(pdf.pages[pidx], x_from, y_from)
            pairs, remaining = assign(entries, labels)
            if any(v != 0 for v in remaining.values()):
                raise ValueError(f"{kind}: 시도별 개수 불일치 {remaining}")
            if len(pairs) != expect:
                raise ValueError(f"{kind}: {len(pairs)}곳 추출, 기대 {expect}곳")
            df = pd.DataFrame(pairs, columns=["sido", "sigungu"])
            df["type"] = kind
            frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out["sigungu"] = out["sigungu"].replace({"제물포구": "제물포구"})
    out.to_csv(CLEAN / "depopulation_areas_2026.csv", index=False, encoding="utf-8-sig")
    print(out.groupby(["type", "sido"]).size().to_string())
    print("total", out.groupby("type").size().to_dict())


if __name__ == "__main__":
    sys.exit(main())
