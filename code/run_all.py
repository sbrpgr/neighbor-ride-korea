"""전체 분석 재현: data_raw → data_clean → figures.

사용법:  python code/run_all.py
각 단계는 독립 프로세스로 실행하며, 하나라도 실패하면 즉시 멈춘다.
"""
import subprocess
import sys
import time
from pathlib import Path

CODE = Path(__file__).resolve().parent
STEPS = [
    "00_manifest.py",
    "01_parse_depopulation.py",
    "10_a1_vehicle_assets.py",
    "20_a2_alternative_costs.py",
    "30_a3_cost_model.py",
    "40_a4_cases.py",
    "51_fig1_vehicle_assets.py",
    "52_fig2_costs.py",
    "53_fig3_summary.py",
    "70_write_cells.py",
    "90_verify.py",
]


def main():
    for step in STEPS:
        t = time.time()
        print(f"== {step}", flush=True)
        r = subprocess.run([sys.executable, "-X", "utf8", str(CODE / step)], cwd=CODE.parent)
        if r.returncode != 0:
            sys.exit(f"실패: {step} (exit {r.returncode})")
        print(f"   {time.time() - t:.1f}s", flush=True)
    print("모든 단계 완료")


if __name__ == "__main__":
    main()
