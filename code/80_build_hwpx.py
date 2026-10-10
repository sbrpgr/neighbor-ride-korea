"""양식(붙임2-분석보고서최종.hwpx)에 원고를 조판해 HWPX·PDF를 만든다(한컴오피스 자동화).

1) report/cells/*.html 을 한글 문서로 변환하면서 글꼴(나눔바른고딕)·줄간격·표 폭을 맞춘다.
2) 양식 사본을 열어 본문 표의 각 칸(B1~B10) 안내 문구를 지우고 변환 문서를 끼워 넣는다.
3) 표 뒤의 '분석보고서 작성 시 유의사항' 안내 문단을 지운다.
4) report/분석보고서.hwpx 와 report/김대운_분석보고서.pdf 로 저장한다.
원본 양식 파일은 수정하지 않는다.
"""
import json
import shutil
import sys
from pathlib import Path

from pyhwpx import Hwp

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "report" / "template" / "붙임2-분석보고서최종_양식원본.hwpx"
CELLS = ROOT / "report" / "cells"
BUILD = ROOT / "report" / "build"
OUT_HWPX = ROOT / "report" / "분석보고서.hwpx"
OUT_PDF = ROOT / "report" / "김대운_분석보고서.pdf"
FONT = "나눔바른고딕"
CELL_WIDTH_MM = 121.5

# 본문 표 칸 주소 → 원고 조각
SLOTS = [("B1", "name"), ("B2", "title"), ("B3", "background"), ("B4", "data"), ("B5", "method"),
         ("B6", "ai"), ("B7", "results"), ("B8", "policy"), ("B9", "refs"), ("B10", "image")]


def plain_snippets():
    plain = json.loads((CELLS / "plain.json").read_text(encoding="utf-8"))
    head = '<html><head><meta charset="utf-8"></head><body>'
    (CELLS / "name.html").write_text(
        head + f'<p style="font-family:\'{FONT}\'; font-size:11pt;">{plain["name"]}</p></body></html>', encoding="utf-8")
    (CELLS / "title.html").write_text(
        head + f'<p style="font-family:\'{FONT}\'; font-size:12.5pt;"><b>{plain["title"]}</b></p>'
        f'<p style="font-family:\'{FONT}\'; font-size:10pt;">{plain["subtitle"]}</p></body></html>', encoding="utf-8")


# 개조식 기호별 왼쪽 여백과 내어쓰기(pt): 둘째 줄부터 기호 뒤 글자에 맞춘다.
HANG = {"○": (0, -11.5), "⇒": (0, -12.5), "- ": (9, -6.5), "* ": (9, -6)}


def hang_paragraphs(hwp):
    """본문(표 밖) 문단을 차례로 읽어 첫 글자 기호에 따라 여백·내어쓰기를 지정한다."""
    hwp.MoveDocBegin()
    seen = set()
    while True:
        pos = hwp.get_pos()
        if pos in seen:
            break
        seen.add(pos)
        hwp.HAction.Run("MoveParaBegin")
        hwp.HAction.Run("MoveSelParaEnd")
        text = (hwp.get_selected_text() or "").lstrip()
        hwp.HAction.Run("Cancel")
        for mark, (left, indent) in HANG.items():
            if text.startswith(mark):
                hwp.set_para(LeftMargin=left, Indentation=indent)
                break
        if not hwp.HAction.Run("MoveNextParaBegin"):
            break


def convert(hwp, name):
    src = CELLS / f"{name}.html"
    dst = BUILD / f"{name}.hwpx"
    if not hwp.open(str(src), format="HTML"):
        sys.exit(f"HTML 열기 실패: {src}")
    hwp.SelectAll()
    hwp.set_font(FaceName=FONT, Italic=False)
    hwp.set_para(LineSpacing=140)
    hwp.Cancel()
    hang_paragraphs(hwp)
    wfile = CELLS / f"{name}.tables.json"
    widths = json.loads(wfile.read_text(encoding="utf-8")) if wfile.exists() else []
    i = 0
    while hwp.get_into_nth_table(i):
        hwp.set_table_width(CELL_WIDTH_MM, as_="mm")
        if i < len(widths):
            hwp.get_into_nth_table(i)
            hwp.set_col_width(widths[i], as_="ratio")
        i += 1
    if i != len(widths):
        sys.exit(f"{name}: 표 개수 불일치(문서 {i}, 원고 {len(widths)})")
    hwp.MoveDocBegin()
    hwp.save_as(str(dst))
    return dst, i


def clear_cell(hwp, addr):
    hwp.get_into_nth_table(1)
    if not hwp.goto_addr(addr):
        sys.exit(f"칸 이동 실패: {addr}")
    hwp.HAction.Run("MoveListBegin")
    hwp.HAction.Run("MoveSelListEnd")
    hwp.HAction.Run("Delete")
    hwp.HAction.Run("Cancel")
    return hwp.get_cell_addr()


def strip_guide_xml(src, dst):
    """양식 사본에서 본문 표 뒤의 '분석보고서 작성 시 유의사항' 문단들을 XML 수준에서 잘라낸다.

    한컴 자동화의 선택·삭제가 이 문단에 적용되지 않아(편집 보호) 사본의 section0.xml을 직접 편집한다.
    잘라낸 구간에 표·그림이 없는지 확인하고, mimetype을 첫 항목·무압축으로 다시 묶는다.
    """
    import re
    import zipfile
    with zipfile.ZipFile(src) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist()]
    out = []
    removed = ""
    for info, data in items:
        if info.filename == "Contents/section0.xml":
            xml = data.decode("utf-8")
            k = xml.index("분석보고서 작성 시 유의사항")
            p0 = xml.rfind("<hp:p ", 0, k)
            p_end = xml.rindex("</hs:sec>")
            removed = xml[p0:p_end]
            if "<hp:tbl" in removed or "<hp:pic" in removed or "<hp:secPr" in removed:
                sys.exit("안내 문단 구간에 표·그림·구역정보가 섞여 있음")
            xml = xml[:p0] + xml[p_end:]
            data = xml.encode("utf-8")
        out.append((info, data))
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in sorted(out, key=lambda x: x[0].filename != "mimetype"):
            if info.filename == "mimetype":
                z.writestr(info, data, compress_type=zipfile.ZIP_STORED)
            else:
                z.writestr(info, data)
    return len(re.findall(r"<hp:p ", removed))


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    plain_snippets()
    work = BUILD / "template_copy.hwpx"
    n_removed = strip_guide_xml(TEMPLATE, work)
    print("guide paragraphs removed from copy:", n_removed)
    hwp = Hwp(visible=False)
    try:
        converted = {}
        for _, name in SLOTS:
            converted[name] = convert(hwp, name)
            print("converted", name, "tables:", converted[name][1])
        hwp.open(str(work))
        for addr, name in SLOTS:
            got = clear_cell(hwp, addr)
            ok = hwp.insert_file(str(converted[name][0]), keep_section=0, keep_charshape=1, keep_parashape=1,
                                 keep_style=0)
            print("filled", addr, name, got, ok)
            if not ok:
                sys.exit(f"끼워넣기 실패: {addr}")
        # 끼워 넣은 표는 한글이 열 너비를 다시 맞추므로, 최종 문서에서 문서 순서대로 다시 지정한다.
        nested = []
        for _, name in SLOTS:
            wfile = CELLS / f"{name}.tables.json"
            if wfile.exists():
                nested += json.loads(wfile.read_text(encoding="utf-8"))
        for k, widths in enumerate(nested, start=2):   # 0: 표지 표, 1: 본문 양식 표
            if not hwp.get_into_nth_table(k):
                sys.exit(f"중첩 표 {k} 없음")
            hwp.set_table_width(CELL_WIDTH_MM - 1.0, as_="mm")
            hwp.get_into_nth_table(k)
            hwp.set_col_width(widths, as_="ratio")
        print("nested tables resized:", len(nested))
        hwp.MoveDocBegin()
        hwp.save_as(str(OUT_HWPX))
        hwp.save_as(str(OUT_PDF), format="PDF")
        print("pages", hwp.PageCount)
    finally:
        try:
            hwp.quit()
        except Exception as e:  # 저장 후 종료 단계의 COM 예외는 결과에 영향 없음
            print('quit warning:', e)
    print("saved", OUT_HWPX, OUT_PDF)


if __name__ == "__main__":
    main()
