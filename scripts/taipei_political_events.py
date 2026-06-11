import numpy as np
import pandas as pd

from pipeline_common import read_stage, write_stage, data_path

EVENTS_FILE = data_path("taiwan_political_events") / "taiwan_political_events.xlsx"

YOUTH_MARKER = "成長經歷（非啟蒙年）"


def get_generation_label(age: int) -> str:
    if age >= 59:
        return "威權/解嚴世代"
    if age >= 47:
        return "民主轉型世代"
    if age >= 39:
        return "本土化世代"
    if age >= 28:
        return "公民運動世代"
    if age >= 20:
        return "社群網路/抗中保台世代"
    return "AI與短影音世代"


def main():
    personas = read_stage("v2")
    events_df = pd.read_excel(EVENTS_FILE)

    # 只保留數值型的 20歲時的2026現齡（排除「成長經歷」文字列）
    numeric_df = events_df[events_df["20歲時的2026現齡"] != YOUTH_MARKER].copy()
    numeric_df["20歲時的2026現齡"] = pd.to_numeric(numeric_df["20歲時的2026現齡"])

    ages_arr = numeric_df["20歲時的2026現齡"].values
    names_arr = numeric_df["事件名稱"].values

    def nearest_event(age: int) -> str:
        idx = np.argmin(np.abs(ages_arr - age))
        return names_arr[idx]

    personas["政治與歷史印記_世代"] = personas["年齡"].apply(lambda a: get_generation_label(int(a)))
    personas["政治與歷史印記_事件"] = personas["年齡"].apply(lambda a: nearest_event(int(a)))

    out = write_stage(personas, "politicalEvent")
    print(f"輸出完成：{out}")
    print(f"總行數：{len(personas)}，欄位數：{len(personas.columns)}")


if __name__ == "__main__":
    main()
