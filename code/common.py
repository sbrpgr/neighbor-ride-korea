"""공통 경로·명칭 정규화 유틸리티.

모든 스크립트는 이 파일 기준 상대경로만 사용한다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data_raw"
CLEAN = ROOT / "data_clean"
FIG = ROOT / "figures"
CLEAN.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

# 시도 명칭 정규화: 장문·구명칭 → 2026년 8월 자동차등록통계(국토부) 약칭
SIDO_SHORT = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천",
    "광주광역시": "전남광주", "대전광역시": "대전", "울산광역시": "울산",
    "세종특별자치시": "세종", "경기도": "경기", "강원특별자치도": "강원", "강원도": "강원",
    "충청북도": "충북", "충청남도": "충남", "전북특별자치도": "전북", "전라북도": "전북",
    "전라남도": "전남광주", "전남광주통합특별시": "전남광주", "경상북도": "경북",
    "경상남도": "경남", "제주특별자치도": "제주",
}


def sido_short(name: str) -> str:
    name = (name or "").strip()
    return SIDO_SHORT.get(name, name)


def to_num(x):
    """'1,234' / '>120.00' / 'N/A' / 숫자 → float (검열값은 상한 그대로, N/A는 NaN)."""
    import math
    if x is None:
        return math.nan
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(",", "")
    if s in ("", "-", "N/A"):
        return math.nan
    s = s.lstrip(">")
    try:
        return float(s)
    except ValueError:
        return math.nan


def save_json(obj, path: Path):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=float), encoding="utf-8")


def mois_region_split(label: str):
    """'전남광주통합특별시 곡성군 (1272000000)' → ('전남광주', '곡성군', '1272000000', depth)."""
    m = re.match(r"^(.*?)\s*\((\d{10})\)\s*$", label.strip())
    if not m:
        return None
    name, code = m.group(1).strip(), m.group(2)
    parts = name.split()
    sido = sido_short(parts[0])
    rest = parts[1:]
    return sido, " ".join(rest), code, len(rest)
