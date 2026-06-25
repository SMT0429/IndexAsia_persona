#!/usr/bin/env python3
"""
persona_db.py — Persona 版本庫（SQLite）核心 library。

每次 pipeline 跑批 = 一筆不可變版本（runs 一列 + personas 3000 列），集中存進單檔
data/personas.db，取代「每跑一次吐一個時間戳 xlsx」的堆積。要 Excel 時再用
export_run.py 按需匯出。

設計重點（詳見 plan 與 method/field_dependency_map.md）：
  - 寬表：personas 25 欄逐欄對應最終交付 schema，df ↔ SQLite round-trip 無損。
  - 保留中文欄名（quoted identifier）：pandas to_sql/read_sql 原生處理，load_run 免轉換。
  - run 身分以 run_id（代理鍵）+ content_hash（資料 sha256）為準，不依賴檔名。
  - insert-only（無 update）+ content_hash UNIQUE → 版本不可變、冪等去重。
  - DB 出錯不靜默：呼叫端（finalize）應 fail-fast，因 DB 是唯一產出。

依賴：僅標準庫 sqlite3 + pandas（pipeline 既有），不需額外 pip install。
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd

from pipeline_common import DATA_DIR, DEFAULT_SEED, N_TOTAL, PROFILE, REPO_ROOT

# ── DB 路徑（PERSONA_DB_PATH 可覆寫，測試用暫存 DB）──────────────────────────
DB_PATH = Path(os.environ.get("PERSONA_DB_PATH", DATA_DIR / "personas.db"))

# ── 最終交付 25 欄（順序 = 單一事實來源；與 taipei_finalize 輸出逐欄對應）─────
FINAL_COLS = [
    "id", "居住地", "性別", "年齡", "年齡組", "教育程度", "職業", "婚姻狀況",
    "媒體習慣", "國家認同", "政黨傾向", "厭惡政黨", "政治與歷史印記_世代",
    "政治與歷史印記_事件", "產業別", "月收入區間", "族群", "分裂投票傾向",
    "社會價值觀_CO分數", "社會價值觀_ST分數", "社會價值觀_主類型",
    "社會價值觀_核心動機", "關注議題", "關注子議題", "房產持有狀態",
]
EXPECTED_COLS = len(FINAL_COLS)  # 25

# dtype 還原契約（load_run 用）；其餘 19 欄為字串。
INT_COLS = ["id", "年齡"]
FLOAT_COLS = ["國家認同", "分裂投票傾向", "社會價值觀_CO分數", "社會價值觀_ST分數"]

# crosswalk 欄（與 taipei_crosswalk.CROSSWALK_COLS 一致；全台 profile 才有）。
CROSSWALK_COLS = ["taiwan_id", "taipei_id", "行政區", "性別", "年齡"]

# 依 profile 分表：taipei 的人 → taipei_personas、taiwan 的人 → taiwan_personas。
# runs（版本目錄）維持共用，profile 欄指出該版本資料落在哪張表。
PERSONA_TABLES = {"taipei": "taipei_personas", "taiwan": "taiwan_personas"}


def _persona_table(profile: str) -> str:
    if profile not in PERSONA_TABLES:
        raise ValueError(f"未知 profile={profile!r}，可用：{list(PERSONA_TABLES)}")
    return PERSONA_TABLES[profile]


# ── DDL ───────────────────────────────────────────────────────────────────────
def _col_ddl() -> str:
    """persona 25 欄的 DDL 片段（中文欄名以雙引號包覆，依 dtype 給型別親和性）。"""
    parts = ['"id" INTEGER NOT NULL']
    for c in FINAL_COLS[1:]:
        if c in FLOAT_COLS:
            t = "REAL"
        elif c in INT_COLS:
            t = "INTEGER"
        else:
            t = "TEXT"
        parts.append(f'"{c}" {t}')
    return ",\n    ".join(parts)


def _persona_table_ddl(table: str) -> str:
    """單一 profile persona 表 + 其 run_id 索引。"""
    return f"""
CREATE TABLE IF NOT EXISTS {table} (
    run_id INTEGER NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    {_col_ddl()},
    PRIMARY KEY (run_id, "id")
);
CREATE INDEX IF NOT EXISTS idx_{table}_run ON {table}(run_id);
"""


_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS runs (
    run_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    profile         TEXT    NOT NULL,
    seed            INTEGER NOT NULL,
    n_total         INTEGER NOT NULL,
    row_count       INTEGER NOT NULL,
    col_count       INTEGER NOT NULL,
    generated_at    TEXT    NOT NULL,
    source          TEXT    NOT NULL DEFAULT 'pipeline',
    git_commit      TEXT,
    git_short       TEXT,
    git_dirty       INTEGER NOT NULL DEFAULT 0,
    schema_hash     TEXT    NOT NULL,
    content_hash    TEXT    NOT NULL,
    label           TEXT,
    notes           TEXT,
    status          TEXT    NOT NULL DEFAULT 'active',
    ingested_at     TEXT    NOT NULL,
    UNIQUE (content_hash)
);
{_persona_table_ddl('taipei_personas')}
{_persona_table_ddl('taiwan_personas')}
CREATE TABLE IF NOT EXISTS crosswalks (
    run_id     INTEGER NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    taiwan_id  INTEGER NOT NULL,
    taipei_id  INTEGER NOT NULL,
    "行政區" TEXT,
    "性別" TEXT,
    "年齡" INTEGER,
    PRIMARY KEY (run_id, taiwan_id)
);

CREATE INDEX IF NOT EXISTS idx_runs_profile_time ON runs(profile, generated_at);
"""


def _migrate_legacy_personas(conn: sqlite3.Connection) -> None:
    """舊版單一 personas 表 → 依 profile 拆進 taipei_personas / taiwan_personas，再移除舊表。

    冪等：舊表不存在即 no-op（遷移後每次呼叫都直接返回）。
    """
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='personas'"
    ).fetchone()
    if not exists:
        return
    cols = ", ".join(f'"{c}"' for c in FINAL_COLS)
    sel = ", ".join(f'p."{c}"' for c in FINAL_COLS)
    for profile, table in PERSONA_TABLES.items():
        conn.execute(
            f"INSERT INTO {table} (run_id, {cols}) "
            f"SELECT p.run_id, {sel} FROM personas p "
            f"JOIN runs r ON r.run_id = p.run_id WHERE r.profile = ?",
            (profile,),
        )
    conn.execute("DROP TABLE personas")


# ── 連線 / 建表 ────────────────────────────────────────────────────────────────
def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    """開連線並啟用外鍵（SQLite 預設關），row_factory 設為 Row 方便取欄。"""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection | None = None, db_path: Path | str = DB_PATH) -> None:
    """建立 runs / taipei_personas / taiwan_personas / crosswalks 表與索引（全 IF NOT EXISTS，冪等）。

    同時自動把舊版單一 personas 表遷移成分表。
    """
    own = conn is None
    conn = conn or connect(db_path)
    try:
        conn.executescript(_SCHEMA)
        _migrate_legacy_personas(conn)
        conn.commit()
    finally:
        if own:
            conn.close()


# ── 溯源 / 雜湊 ────────────────────────────────────────────────────────────────
def _git_provenance(repo_root: Path = REPO_ROOT) -> dict:
    """回傳 {git_commit, git_short, git_dirty}；git 不存在或非 checkout 時降級為 NULL，不拋例外。"""
    def _git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True, text=True, check=True,
        ).stdout.strip()

    try:
        full = _git("rev-parse", "HEAD")
        short = _git("rev-parse", "--short", "HEAD")
        dirty = bool(_git("status", "--porcelain"))
        return {"git_commit": full, "git_short": short, "git_dirty": int(dirty)}
    except Exception:
        return {"git_commit": None, "git_short": None, "git_dirty": 0}


def _canonical(df: pd.DataFrame) -> pd.DataFrame:
    """正規化：欄序固定為 FINAL_COLS、列依 id 排序、float 統一四捨五入到 6 位，去除表示法噪音。"""
    out = df[FINAL_COLS].sort_values("id").reset_index(drop=True)
    for c in FLOAT_COLS:
        out[c] = out[c].astype(float).round(6)
    return out


def _content_hash(df: pd.DataFrame) -> str:
    """資料內容 sha256（與檔名/時間戳無關）→ 去重鍵。"""
    csv = _canonical(df).to_csv(index=False)
    return hashlib.sha256(csv.encode("utf-8")).hexdigest()


def _schema_hash(df: pd.DataFrame) -> str:
    """欄名 + dtype 的 sha256 → 偵測欄位漂移。"""
    sig = "\n".join(f"{c}:{df[c].dtype}" for c in df.columns)
    return hashlib.sha256(sig.encode("utf-8")).hexdigest()


# ── 寫入 ──────────────────────────────────────────────────────────────────────
def _validate(df: pd.DataFrame) -> None:
    missing = [c for c in FINAL_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"persona df 缺少欄位，無法入庫：{missing}")
    extra = [c for c in df.columns if c not in FINAL_COLS]
    if extra:
        raise ValueError(f"persona df 有非預期欄位（schema 漂移？）：{extra}")
    if len(df) != N_TOTAL:
        print(f"  ⚠ 列數 {len(df)} ≠ 期望 {N_TOTAL}（仍會入庫，請確認）")


def insert_run(
    df: pd.DataFrame,
    metadata: dict,
    *,
    crosswalk: pd.DataFrame | None = None,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str = DB_PATH,
    on_duplicate: str = "skip",
) -> int:
    """把一批 persona 寫成一個版本，回傳 run_id。

    metadata 需含 profile；其餘有預設：seed=DEFAULT_SEED、generated_at=now、
    source='pipeline'、label/notes=None。git 溯源由本函式內部補。
    content_hash 命中既有版本時：on_duplicate=='skip' 回傳既有 run_id；'error' 拋例外。
    單一 transaction：personas 寫入失敗則 runs 一併 rollback，不留孤兒。
    """
    if on_duplicate not in ("skip", "error"):
        raise ValueError(f"on_duplicate 須為 'skip'|'error'，得到 {on_duplicate!r}")
    _validate(df)

    own = conn is None
    conn = conn or connect(db_path)
    try:
        init_db(conn)

        c_hash = _content_hash(df)
        existing = conn.execute(
            "SELECT run_id FROM runs WHERE content_hash = ?", (c_hash,)
        ).fetchone()
        if existing:
            if on_duplicate == "error":
                raise ValueError(f"內容相同的版本已存在：run_id={existing['run_id']}")
            print(f"  ↳ 內容已存在，跳過（run_id={existing['run_id']}）")
            return int(existing["run_id"])

        now = datetime.now().isoformat(timespec="seconds")
        prov = _git_provenance()
        meta = {
            "profile": metadata["profile"],
            "seed": metadata.get("seed", DEFAULT_SEED),
            "n_total": metadata.get("n_total", N_TOTAL),
            "row_count": len(df),
            "col_count": len(df.columns),
            "generated_at": metadata.get("generated_at", now),
            "source": metadata.get("source", "pipeline"),
            "git_commit": prov["git_commit"],
            "git_short": prov["git_short"],
            "git_dirty": prov["git_dirty"],
            "schema_hash": _schema_hash(df),
            "content_hash": c_hash,
            "label": metadata.get("label"),
            "notes": metadata.get("notes"),
            "status": "active",
            "ingested_at": now,
        }

        with conn:  # transaction：例外即整批 rollback
            cols = ", ".join(meta.keys())
            placeholders = ", ".join(["?"] * len(meta))
            cur = conn.execute(
                f"INSERT INTO runs ({cols}) VALUES ({placeholders})",
                list(meta.values()),
            )
            run_id = int(cur.lastrowid)

            payload = df[FINAL_COLS].copy()
            payload.insert(0, "run_id", run_id)
            payload.to_sql(_persona_table(meta["profile"]), conn,
                           if_exists="append", index=False)

            if crosswalk is not None and len(crosswalk):
                cw = crosswalk[CROSSWALK_COLS].copy()
                cw.insert(0, "run_id", run_id)
                cw.to_sql("crosswalks", conn, if_exists="append", index=False)

        return run_id
    finally:
        if own:
            conn.close()


# ── 讀取 / 查詢 ────────────────────────────────────────────────────────────────
def list_runs(
    profile: str | None = None,
    *,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str = DB_PATH,
) -> pd.DataFrame:
    """回傳 runs 表（純 metadata，新→舊）；可選 profile 過濾。"""
    own = conn is None
    conn = conn or connect(db_path)
    try:
        init_db(conn)
        sql = "SELECT * FROM runs"
        params: list = []
        if profile:
            sql += " WHERE profile = ?"
            params.append(profile)
        sql += " ORDER BY generated_at DESC, run_id DESC"
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        if own:
            conn.close()


def load_run(
    run_id: int,
    *,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str = DB_PATH,
) -> pd.DataFrame:
    """取某版本的 25 欄 persona 表（依 id 排序、還原 dtype，與原交付檔 byte-faithful）。

    依該版本的 profile 自動從 taipei_personas / taiwan_personas 取資料。
    """
    own = conn is None
    conn = conn or connect(db_path)
    try:
        prow = conn.execute(
            "SELECT profile FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if prow is None:
            raise ValueError(f"run_id={run_id} 不存在")
        table = _persona_table(prow["profile"])
        cols = ", ".join(f'"{c}"' for c in FINAL_COLS)
        df = pd.read_sql_query(
            f'SELECT {cols} FROM {table} WHERE run_id = ? ORDER BY "id"',
            conn, params=[run_id],
        )
        if df.empty:
            raise ValueError(f"run_id={run_id} 無資料（{table}）")
        for c in INT_COLS:
            df[c] = df[c].astype("int64")
        for c in FLOAT_COLS:
            df[c] = df[c].astype("float64")
        return df
    finally:
        if own:
            conn.close()


def load_crosswalk(
    run_id: int,
    *,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str = DB_PATH,
) -> pd.DataFrame:
    """取某 taiwan 版本的對照表；無則回傳空 DataFrame（欄位齊全）。"""
    own = conn is None
    conn = conn or connect(db_path)
    try:
        cols = ", ".join(f'"{c}"' for c in CROSSWALK_COLS)
        df = pd.read_sql_query(
            f"SELECT {cols} FROM crosswalks WHERE run_id = ? ORDER BY taiwan_id",
            conn, params=[run_id],
        )
        return df
    finally:
        if own:
            conn.close()


def latest_run(
    profile: str = PROFILE,
    *,
    conn: sqlite3.Connection | None = None,
    db_path: Path | str = DB_PATH,
) -> int | None:
    """某 profile 最新 active 版本的 run_id（依 generated_at）；無則 None。"""
    runs = list_runs(profile, conn=conn, db_path=db_path)
    runs = runs[runs["status"] == "active"]
    if runs.empty:
        return None
    return int(runs.iloc[0]["run_id"])


def compare_runs(
    run_id_a: int,
    run_id_b: int,
    *,
    db_path: Path | str = DB_PATH,
) -> dict:
    """比較兩版本：metadata 並排 + identical（content_hash 相等）+ 數值欄統計差 + 類別欄分布差。"""
    conn = connect(db_path)
    try:
        meta = {}
        for tag, rid in (("a", run_id_a), ("b", run_id_b)):
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (rid,)).fetchone()
            if row is None:
                raise ValueError(f"run_id={rid} 不存在")
            meta[tag] = dict(row)
        da = load_run(run_id_a, conn=conn)
        db = load_run(run_id_b, conn=conn)
    finally:
        conn.close()

    identical = meta["a"]["content_hash"] == meta["b"]["content_hash"]

    numeric_drift = {}
    for c in FLOAT_COLS + ["年齡"]:
        sa, sb = da[c], db[c]
        numeric_drift[c] = {
            "mean_a": round(float(sa.mean()), 4), "mean_b": round(float(sb.mean()), 4),
            "mean_delta": round(float(sb.mean() - sa.mean()), 4),
            "std_delta": round(float(sb.std() - sa.std()), 4),
            "min_delta": round(float(sb.min() - sa.min()), 4),
            "max_delta": round(float(sb.max() - sa.max()), 4),
        }

    categorical_shift = {}
    cat_cols = [c for c in FINAL_COLS if c not in FLOAT_COLS + INT_COLS]
    for c in cat_cols:
        va = da[c].value_counts()
        vb = db[c].value_counts()
        keys = sorted(set(va.index) | set(vb.index))
        deltas = {k: int(vb.get(k, 0) - va.get(k, 0)) for k in keys}
        deltas = {k: v for k, v in deltas.items() if v != 0}
        if deltas:
            categorical_shift[c] = deltas

    return {
        "meta": meta,
        "identical": identical,
        "numeric_drift": numeric_drift,
        "categorical_shift": categorical_shift,
    }


if __name__ == "__main__":
    # 簡易自我檢查：建表 + 印 runs。
    init_db()
    print(f"✓ DB ready：{DB_PATH}")
    print(list_runs().to_string(index=False) if len(list_runs()) else "（尚無版本）")
