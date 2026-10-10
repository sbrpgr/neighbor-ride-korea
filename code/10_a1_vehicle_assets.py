"""A1. 교통취약지역 차량 자원 존재 입증.

입력
- 국토교통부 「자동차 등록자료 통계」 2026.08 (시군구별 차종x용도)
- 행정안전부 주민등록 인구·세대 2026.08, 5세 연령별 인구 2026.08
- 행정안전부 인구감소지역 재지정(2026.10.7) 명단 (01_parse_depopulation.py 산출)
- 한국교통연구원 KTDB 2025 교통접근성지표 (평균접근시간, 접근가능인구비율)
- 곡성군 청년통계 2022(2021.12.31 읍면별 개인소유 차량), 2025(2024.12.31 군 전체)

출력
- data_clean/A1_sigungu.csv          시군구별 차량·세대·고령·접근성 통합표
- data_clean/A1_group_summary.csv    인구감소지역/관심지역/기타 집단 비교
- data_clean/A1_gokseong_emd.csv     곡성 읍면별 차량·접근성
- data_clean/A1_results.json         본문 인용 수치
"""
import re

import numpy as np
import pandas as pd
import pdfplumber

from common import CLEAN, RAW, mois_region_split, save_json, sido_short, to_num


# 행정구역 개편 후 옛 명칭에 남은 잔여 등록(인천 중·동·서구 2026.7. 개편, 군위군 2023.7. 대구 편입,
# 청원군 2014. 통합). 인구 자료에는 해당 시군구가 없으므로 집계에서 제외하고 규모를 기록한다.
RESIDUAL = {("인천", "중구"), ("인천", "동구"), ("인천", "서구"), ("경북", "군위군"), ("충북", "청원군")}


# ---------------------------------------------------------------- 1. 자동차 등록
def load_vehicles():
    path = RAW / "molit_vehicle" / "molit_vehicle_registration_202608.xlsx"
    raw = pd.read_excel(path, sheet_name="02.통계표_시군구", header=None, skiprows=4)
    cols = ["sido", "sigungu"]
    for kind in ["car", "van", "truck", "special", "total"]:
        cols += [f"{kind}_gov", f"{kind}_private", f"{kind}_commercial", f"{kind}_sum"]
    raw = raw.iloc[:, :22]
    raw.columns = cols
    raw["sido"] = raw["sido"].ffill()
    raw = raw[raw["sigungu"].notna() & (raw["sigungu"] != "계") & (raw["sido"] != "합계")].copy()
    raw["sido"] = raw["sido"].map(sido_short)
    for c in cols[2:]:
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    # 일반구(예: '용인시 기흥구')는 시 단위로 합산
    raw["sigungu"] = raw["sigungu"].astype(str).str.split().str[0]
    raw = raw.groupby(["sido", "sigungu"], as_index=False)[cols[2:]].sum()
    is_res = raw.apply(lambda r: (r.sido, r.sigungu) in RESIDUAL, axis=1)
    residual = raw[is_res][["sido", "sigungu", "car_private", "total_private"]]
    return raw[~is_res].reset_index(drop=True), residual


# ---------------------------------------------------------------- 2. 인구·세대
def load_population():
    hh = pd.read_csv(RAW / "mois_population" / "mois_household_population_sigungu_202608.csv", encoding="cp949")
    hh.columns = ["label", "pop", "households", "pop_per_hh", "male", "female", "sex_ratio"]
    age = pd.read_csv(RAW / "mois_population" / "mois_age5_sigungu_202608.csv", encoding="cp949")
    age_cols = [c for c in age.columns if re.search(r"_(6[5-9]|[7-9]\d)~\d+세$|100세 이상$", c)]
    assert len(age_cols) == 8, age_cols  # 65~69 ... 95~99, 100세 이상
    age["pop65"] = age[age_cols].map(to_num).sum(axis=1)
    age = age.rename(columns={age.columns[0]: "label"})[["label", "pop65"]]
    df = hh.merge(age, on="label", how="left")
    rows = []
    for _, r in df.iterrows():
        sp = mois_region_split(r["label"])
        if sp is None:
            continue
        sido, name, code, depth = sp
        if sido == "세종" and depth == 0:
            name, depth = "세종특별자치시", 1
        if depth != 1 or name.endswith("출장소"):
            continue
        rows.append({"sido": sido, "sigungu": name, "adm_code": code,
                     "pop": to_num(r["pop"]), "households": to_num(r["households"]),
                     "pop65": r["pop65"]})
    out = pd.DataFrame(rows)
    return out.groupby(["sido", "sigungu"], as_index=False).agg(
        adm_code=("adm_code", "first"), pop=("pop", "sum"), households=("households", "sum"), pop65=("pop65", "sum"))


# ---------------------------------------------------------------- 3. KTDB 접근성
FACIS = ["병·의원", "종합병원"]
KT_COLS = ["YEAR", "HDCD", "REGION", "HDCD_LEV", "FACI_CD", "TIME_ZONE", "MODE", "HDCD_SD_NM",
           "HDCD_SGG_NM", "HDCD_EMD_NM", "REGION_NM", "FACI_CA", "FACI_NM", "TIME_ZONE_NM", "MODE_NM"]


def load_ktdb():
    t = pd.read_excel(RAW / "ktdb" / "ktdb_avg_access_time_2025.xlsx", sheet_name="평균접근시간",
                      header=None, skiprows=6, usecols=range(16))
    t.columns = KT_COLS + ["minutes"]
    t = t[(t.FACI_NM.isin(FACIS)) & (t.TIME_ZONE == "2_T1214") & (t.REGION_NM == "전체")].copy()
    t["censored"] = t["minutes"].astype(str).str.startswith(">")
    t["minutes"] = t["minutes"].map(to_num)

    p = pd.read_excel(RAW / "ktdb" / "ktdb_access_pop_ratio_2025.xlsx", sheet_name=1,
                      header=None, skiprows=7, usecols=range(19))
    p.columns = KT_COLS + ["r15", "r30", "r45", "r60"]
    p = p[(p.FACI_NM.isin(FACIS)) & (p.TIME_ZONE == "2_T1214") & (p.REGION_NM == "전체")].copy()
    for c in ["r15", "r30", "r45", "r60"]:
        p[c] = p[c].map(to_num)
    return t, p


def ktdb_wide(t, p, level):
    t = t[t.HDCD_LEV == level].copy()
    p = p[p.HDCD_LEV == level].copy()
    mode = {"1_PC": "car", "2_PT": "pt"}
    fac = {"병·의원": "clinic", "종합병원": "hosp"}
    keys = ["HDCD_SD_NM", "HDCD_SGG_NM", "HDCD_EMD_NM"]
    t["col"] = "min_" + t.FACI_NM.map(fac) + "_" + t.MODE.map(mode)
    t["ccol"] = "cens_" + t.FACI_NM.map(fac) + "_" + t.MODE.map(mode)
    a = t.pivot_table(index=keys, columns="col", values="minutes", aggfunc="first")
    c = t.pivot_table(index=keys, columns="ccol", values="censored", aggfunc="first")
    p["col"] = "r30_" + p.FACI_NM.map(fac) + "_" + p.MODE.map(mode)
    b = p.pivot_table(index=keys, columns="col", values="r30", aggfunc="first")
    out = a.join(c).join(b).reset_index()
    out["sido"] = out.HDCD_SD_NM.map(sido_short)
    return out


# ---------------------------------------------------------------- 4. 곡성 읍면
EMDS = ["곡성읍", "오곡면", "삼기면", "석곡면", "목사동면", "죽곡면", "고달면", "옥과면", "입면", "겸면", "오산면"]


def gokseong_emd():
    with pdfplumber.open(RAW / "gokseong" / "gokseong_youth_stats_2022.pdf") as pdf:
        text = pdf.pages[193].extract_text()   # PDF 194쪽, 표 2_15
    num = r"\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)\s+([\d,]+)\s+([\d.]+)"
    rows = []
    for name in EMDS:
        m = re.search(rf"^{name}{num}", text, re.M)
        rows.append({"emd": name, "pop_2021": to_num(m.group(1)), "owners_2021": to_num(m.group(2)),
                     "owner_rate_pct": float(m.group(3)), "private_vehicles_2021": to_num(m.group(4))})
    tot = re.search(rf"^2021년{num}", text, re.M)
    age65 = re.search(rf"^65세 이상{num}", text, re.M)
    age50 = re.search(rf"^50~59세{num}", text, re.M)
    age60 = re.search(rf"^60세 이상{num}", text, re.M)
    return pd.DataFrame(rows), {
        "county_pop_2021": to_num(tot.group(1)), "county_owners_2021": to_num(tot.group(2)),
        "county_vehicles_2021": to_num(tot.group(4)),
        "owners_50s_2021": to_num(age50.group(2)), "vehicles_50s_2021": to_num(age50.group(4)),
        "owners_60plus_2021": to_num(age60.group(2)), "vehicles_60plus_2021": to_num(age60.group(4)),
        "owners_65plus_2021": to_num(age65.group(2)), "vehicles_65plus_2021": to_num(age65.group(4)),
    }


def gokseong_2024():
    with pdfplumber.open(RAW / "gokseong" / "gokseong_youth_stats_2025.pdf") as pdf:
        text = pdf.pages[79].extract_text()   # PDF 80쪽, 표 2-12
    tot = re.search(r"곡성군 전체\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)\s+([\d,]+)\s+([\d.]+)", text)
    return {"county_pop_2024": to_num(tot.group(1)), "county_owners_2024": to_num(tot.group(2)),
            "county_vehicles_2024": to_num(tot.group(4))}


# ---------------------------------------------------------------- 5. 통합·집단 비교
def q(s, x):
    s = s.dropna()
    return float(s.quantile(x)) if len(s) else np.nan


def main():
    veh, residual = load_vehicles()
    pop = load_population()
    dep = pd.read_csv(CLEAN / "depopulation_areas_2026.csv")

    df = pop.merge(veh, on=["sido", "sigungu"], how="outer", indicator=True)
    unmatched = df[df["_merge"] != "both"][["sido", "sigungu", "_merge"]]
    df = df[df["_merge"] == "both"].drop(columns="_merge")

    df = df.merge(dep.rename(columns={"type": "area_type"}), on=["sido", "sigungu"], how="left")
    miss_dep = dep.merge(df[["sido", "sigungu"]], on=["sido", "sigungu"], how="left", indicator=True)
    miss_dep = miss_dep[miss_dep["_merge"] == "left_only"]
    df["area_type"] = df["area_type"].fillna("기타 지역")
    df["is_gun"] = df["sigungu"].str.endswith("군")

    df["car_per_hh"] = df["car_private"] / df["households"]
    df["car_per_1000"] = df["car_private"] / df["pop"] * 1000
    df["private_all_per_hh"] = df["total_private"] / df["households"]
    df["pop65_share"] = df["pop65"] / df["pop"]
    df["car_per_65"] = df["car_private"] / df["pop65"]

    t, p = load_ktdb()
    kt = ktdb_wide(t, p, 2)
    kt = kt.rename(columns={"HDCD_SGG_NM": "sigungu"}).drop(columns=["HDCD_SD_NM", "HDCD_EMD_NM"])
    df = df.merge(kt, on=["sido", "sigungu"], how="left")
    df["gap_clinic_min"] = df["min_clinic_pt"] - df["min_clinic_car"]
    df["gap_hosp_min"] = df["min_hosp_pt"] - df["min_hosp_car"]
    df.to_csv(CLEAN / "A1_sigungu.csv", index=False, encoding="utf-8-sig")

    metrics = ["car_per_hh", "private_all_per_hh", "car_per_1000", "pop65_share",
               "min_clinic_car", "min_clinic_pt", "min_hosp_car", "min_hosp_pt",
               "r30_hosp_car", "r30_hosp_pt", "r30_clinic_car", "r30_clinic_pt"]
    rows = []
    groups = [("인구감소지역", df.area_type == "인구감소지역"),
              ("인구감소관심지역", df.area_type == "인구감소관심지역"),
              ("기타 지역", df.area_type == "기타 지역"),
              ("전국", df.area_type.notna()),
              ("군 지역", df.is_gun)]
    for name, mask in groups:
        g = df[mask]
        r = {"group": name, "n_sigungu": int(len(g)),
             "households": g.households.sum(), "pop": g["pop"].sum(), "car_private": g.car_private.sum(),
             "total_private": g.total_private.sum(), "pop65": g.pop65.sum(),
             "agg_car_per_hh": g.car_private.sum() / g.households.sum(),
             "agg_private_all_per_hh": g.total_private.sum() / g.households.sum(),
             "agg_car_per_1000": g.car_private.sum() / g["pop"].sum() * 1000,
             "agg_pop65_share": g.pop65.sum() / g["pop"].sum(),
             "share_hosp_pt_censored": g["cens_hosp_pt"].astype(float).mean()}
        for col in metrics:
            r[f"{col}_median"], r[f"{col}_q1"], r[f"{col}_q3"] = q(g[col], .5), q(g[col], .25), q(g[col], .75)
        rows.append(r)
    summ = pd.DataFrame(rows)
    summ.to_csv(CLEAN / "A1_group_summary.csv", index=False, encoding="utf-8-sig")
    S = summ.set_index("group")

    # 곡성 읍면
    emd, cnt = gokseong_emd()
    c24 = gokseong_2024()
    kt_emd = ktdb_wide(t, p, 4)
    kt_emd = kt_emd[kt_emd.HDCD_SGG_NM == "곡성군"].rename(columns={"HDCD_EMD_NM": "emd"})
    emd = emd.merge(kt_emd.drop(columns=["HDCD_SD_NM", "HDCD_SGG_NM", "sido"]), on="emd", how="left")
    emd["vehicles_per_100pop"] = emd.private_vehicles_2021 / emd.pop_2021 * 100
    emd.to_csv(CLEAN / "A1_gokseong_emd.csv", index=False, encoding="utf-8-sig")

    gk = df[(df.sido == "전남광주") & (df.sigungu == "곡성군")].iloc[0]
    dp = df[df.area_type == "인구감소지역"]
    keep = ["n_sigungu", "households", "pop", "pop65", "car_private", "total_private", "agg_car_per_hh",
            "car_per_hh_median", "car_per_hh_q1", "car_per_hh_q3", "agg_private_all_per_hh",
            "private_all_per_hh_median", "agg_car_per_1000", "agg_pop65_share",
            "min_clinic_car_median", "min_clinic_pt_median", "min_hosp_car_median", "min_hosp_pt_median",
            "r30_clinic_car_median", "r30_clinic_pt_median", "r30_hosp_car_median", "r30_hosp_pt_median",
            "share_hosp_pt_censored"]
    res = {
        "base_month": "2026-08",
        "n_matched_sigungu": int(len(df)),
        "unmatched_rows": unmatched.to_dict("records"),
        "residual_old_name_rows_excluded": residual.to_dict("records"),
        "depop_not_matched": miss_dep[["sido", "sigungu", "type"]].to_dict("records"),
        "groups": {g: {k: S.loc[g, k] for k in keep} for g in ["인구감소지역", "인구감소관심지역", "기타 지역", "전국", "군 지역"]},
        "depop_share_above_national_median": float((dp.car_per_hh > S.loc["전국", "car_per_hh_median"]).mean()),
        "depop_n_above_national_median": int((dp.car_per_hh > S.loc["전국", "car_per_hh_median"]).sum()),
        "depop_min_car_per_hh": {"sigungu": dp.loc[dp.car_per_hh.idxmin(), "sigungu"], "value": dp.car_per_hh.min()},
        "gokseong": {"households": gk.households, "pop": gk["pop"], "pop65": gk.pop65,
                     "car_private": gk.car_private, "total_private": gk.total_private,
                     "car_per_hh": gk.car_per_hh, "private_all_per_hh": gk.private_all_per_hh,
                     "min_clinic_car": gk.min_clinic_car, "min_clinic_pt": gk.min_clinic_pt,
                     "min_hosp_car": gk.min_hosp_car, "min_hosp_pt": gk.min_hosp_pt,
                     "r30_clinic_car": gk.r30_clinic_car, "r30_clinic_pt": gk.r30_clinic_pt,
                     "r30_hosp_car": gk.r30_hosp_car, "r30_hosp_pt": gk.r30_hosp_pt,
                     **cnt, **c24},
    }
    save_json(res, CLEAN / "A1_results.json")
    show = ["group", "n_sigungu", "agg_car_per_hh", "car_per_hh_median", "agg_private_all_per_hh",
            "agg_pop65_share", "min_clinic_pt_median", "min_hosp_car_median", "min_hosp_pt_median",
            "r30_hosp_car_median", "r30_hosp_pt_median", "share_hosp_pt_censored"]
    print(summ[show].round(3).to_string())
    print("unmatched:\n", unmatched.to_string())
    print("depop not matched:\n", miss_dep.to_string())
    print(emd.round(2).to_string())


if __name__ == "__main__":
    main()
