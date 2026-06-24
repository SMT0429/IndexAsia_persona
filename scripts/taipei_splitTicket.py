"""
分裂投票傾向（Split-ticket Voting Behavior）欄位生成腳本
讀入：taipei_personas_3000_group.xlsx（18欄）
輸出：taipei_personas_3000_splitTicket.xlsx（19欄）

方法論：見 method/split_ticket_methodology.md
依賴欄位：政黨傾向、國家認同、年齡組、媒體習慣、厭惡政黨、居住地
行政區校正：taipei_data_2020/ 中選會 2020 .xls
"""

import os
import pandas as pd

from pipeline_common import read_stage, write_stage, taipei_2020_path, PROFILE

PRES_FILE  = taipei_2020_path('總統-A05-4-候選人得票數一覽表-各投開票所(臺北市).xls')
PARTY_FILE = taipei_2020_path('不分區立委-A05-6-得票數一覽表(臺北市).xls')


# ── 行政區校正（King 1997）─────────────────────────────────────────

def _district_rows(xls_path: str) -> pd.DataFrame:
    """讀取中選會 .xls，取行政區合計列（排除總計）。"""
    df   = pd.read_excel(xls_path, header=None)
    data = df.iloc[5:]
    mask = data[0].notna() & data[1].isna() & data[2].isna()
    rows = data[mask].copy()
    rows = rows[~rows[0].str.strip().isin(['總　計', '總計'])]
    rows['district'] = rows[0].str.strip()
    return rows

def _to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(',', ''), errors='coerce')

def build_district_boost(pres_path: str, party_path: str) -> dict:
    """
    計算 2020 中選會各行政區拆票代理指標，標準化至 0–1。
    總統：col 5 = 蔡英文(DPP)，col 6 = 有效票
    不分區：col 16 = 民進黨，col 22 = 有效票
    """
    pres  = _district_rows(pres_path)
    party = _district_rows(party_path)

    pres['dpp_pres_rate']   = _to_num(pres[5])   / _to_num(pres[6])
    party['dpp_party_rate'] = _to_num(party[16])  / _to_num(party[22])

    merged = pres[['district', 'dpp_pres_rate']].merge(
        party[['district', 'dpp_party_rate']], on='district'
    )
    proxy = merged['dpp_pres_rate'] - merged['dpp_party_rate']
    norm  = (proxy - proxy.min()) / (proxy.max() - proxy.min())
    merged['boost'] = norm
    return dict(zip(merged['district'], merged['boost']))


def build_county_boost() -> dict:
    """全台版：以縣市為 key，從 election_pres/party CSV 算拆票 boost（同 King 1997 代理）。

    proxy(縣市) = 總統 DPP% − 不分區 DPP%，跨 22 縣市標準化至 0–1。
    """
    import region_profile as rp
    pres = rp.load_election_pres()['DPP']      # 縣市 → 總統 DPP 比例
    party = rp.load_election_party()['DPP']     # 縣市 → 不分區 DPP 比例
    proxy = (pres - party).dropna()
    norm = (proxy - proxy.min()) / (proxy.max() - proxy.min())
    return norm.to_dict()


# ── 賦值函數 ───────────────────────────────────────────────────────

def count_media_platforms(media_str) -> int:
    if pd.isna(media_str):
        return 0
    return len(str(media_str).split('、'))


def assign_split_ticket(row, boost_map: dict) -> float:
    """
    分裂投票傾向機率賦值（v1.2）
    回傳值：float 0.05–0.95
      Level 1 — 強否錨點 → 固定 0.10
      Level 2 — 信號加總 → prob = 0.5 + 0.10*(yes-no) + district_adj
    文獻依據見 split_ticket_methodology.md
    """
    party       = row['政黨傾向']
    identity    = row['國家認同']
    age_group   = row['年齡組']
    media       = row['媒體習慣']
    dislike     = row['厭惡政黨']
    district    = row['居住地']

    media_count = count_media_platforms(media)
    has_dislike = (
        pd.notna(dislike) and
        str(dislike).strip() not in ['不知道/沒意見', '無', '']
    )

    # ── Level 1：強否錨點 ─────────────────────────────────────────
    if party in ['民進黨', '國民黨'] and pd.notna(identity):
        if identity <= 3 or identity >= 8:
            return 0.10

    if age_group == '65歲以上' and str(party) not in ['無黨派', '不知道', 'nan', '']:
        return 0.10

    # ── Level 2：信號加總 → 連續機率 ─────────────────────────────
    yes_signals = 0
    no_signals  = 0

    if age_group in ['15–24歲', '25–34歲']:
        yes_signals += 1
    if pd.notna(identity) and 4 <= identity <= 7:
        yes_signals += 1
    if media_count >= 3:
        yes_signals += 1
    if has_dislike and str(dislike).strip() != str(party).strip():
        yes_signals += 1

    if age_group in ['55–64歲', '65歲以上']:
        no_signals += 1
    if pd.notna(media) and str(media).strip() == 'LINE':
        no_signals += 1
    if party in ['民進黨', '國民黨']:
        no_signals += 1
    if not has_dislike:
        no_signals += 1

    boost = boost_map.get(district, 0.5)
    district_adj = (boost - 0.5) * 0.10

    prob = 0.5 + 0.10 * (yes_signals - no_signals) + district_adj
    return round(max(0.05, min(0.95, prob)), 2)


# ── 主程式 ────────────────────────────────────────────────────────

def main():
    if PROFILE == 'taiwan':
        district_boost_map = build_county_boost()
        print('✅ 縣市拆票基準率已載入（2020 中選會，election_pres/party CSV）')
        print('   boost_map:', {k: round(v, 3) for k, v in sorted(district_boost_map.items())})
    elif os.path.exists(PRES_FILE) and os.path.exists(PARTY_FILE):
        district_boost_map = build_district_boost(PRES_FILE, PARTY_FILE)
        print('✅ 行政區拆票基準率已載入（2020 中選會資料）')
        print('   boost_map:', {k: round(v, 3) for k, v in sorted(district_boost_map.items())})
    else:
        district_boost_map = {}
        print('⚠️  中選會資料未找到，區域校正暫時停用')

    df = read_stage("group")
    df['分裂投票傾向'] = df.apply(
        lambda row: assign_split_ticket(row, district_boost_map), axis=1
    )

    print('\n── 分裂投票傾向機率分佈 ──')
    print(df['分裂投票傾向'].describe().round(3))
    bins   = [0, 0.25, 0.60, 1.0]
    labels = ['低 (0–0.25)', '中 (0.26–0.60)', '高 (0.61–1.0)']
    print(pd.cut(df['分裂投票傾向'], bins=bins, labels=labels).value_counts())

    print('\n── 各行政區平均拆票機率 ──')
    print(df.groupby('居住地')['分裂投票傾向'].mean().sort_values(ascending=False).round(3))

    out = write_stage(df, "splitTicket")
    print(f'\n✅ Done. 輸出至 {out}')


if __name__ == '__main__':
    main()
