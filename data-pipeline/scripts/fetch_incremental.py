#!/usr/bin/env python3
"""
增量补数: 只获取缺失的数据集, 每次调用间隔 65 秒(应对 1次/分钟 限频)。
"""
import os, sys, time, json
from datetime import datetime
import tushare as ts
import pandas as pd

TOKEN = os.getenv("TUSHARE_TOKEN", "")
START_DATE = "20200101"
END_DATE = datetime.now().strftime("%Y%m%d")
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_data")
PAUSE = 65  # 每次调用间隔 65 秒

UNIVERSE = [
    {"name": "中芯国际", "ts_code": "688981.SH"},
    {"name": "比亚迪",   "ts_code": "002594.SZ"},
    {"name": "长江电力", "ts_code": "600900.SH"},
]

WEEKLY_FIELDS = ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"]
MONTHLY_FIELDS = ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"]
COMPANY_FIELDS = ["ts_code", "chairman", "manager", "secretary", "reg_capital", "setup_date",
                  "province", "city", "employees", "main_business", "business_scope", "website"]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def save(df, dataset, ts_code, snapshot=False):
    if snapshot:
        d = os.path.join(BASE, dataset); os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"{dataset}_snapshot_{END_DATE}.csv")
    else:
        d = os.path.join(BASE, dataset, ts_code); os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"{ts_code}_{dataset}_{START_DATE}_{END_DATE}.csv")
    df.to_csv(p, index=False, encoding="utf-8-sig")
    return p

def exists(dataset, ts_code, snapshot=False):
    if snapshot:
        p = os.path.join(BASE, dataset, f"{dataset}_snapshot_{END_DATE}.csv")
    else:
        p = os.path.join(BASE, dataset, ts_code, f"{ts_code}_{dataset}_{START_DATE}_{END_DATE}.csv")
    return os.path.exists(p) and os.path.getsize(p) > 100

def call_with_wait(pro, api, fields, label, **kwargs):
    """单次调用, 自带重试与限频等待"""
    for attempt in range(4):
        try:
            df = getattr(pro, api)(**kwargs)
            if df is not None and not df.empty:
                cols = [c for c in fields if c in df.columns]
                return df[cols]
            return None
        except Exception as e:
            msg = str(e)
            if "权限" in msg:
                log(f"  ! {label}: 无权限")
                return "NO_PERM"
            if "频次" in msg or "frequency" in msg.lower():
                log(f"  ~ {label}: 限频, 等待 {PAUSE}s (attempt {attempt+1}/4)")
                time.sleep(PAUSE)
                continue
            if "Response ended" in msg or "timed out" in msg.lower():
                log(f"  ~ {label}: 网络中断, 15s 后重试 (attempt {attempt+1}/4)")
                time.sleep(15)
                continue
            log(f"  ! {label}: {msg[:80]}")
            return None
    return None

def main():
    if not TOKEN:
        log("错误: 未设置 TUSHARE_TOKEN"); sys.exit(1)
    pro = ts.pro_api(TOKEN)
    log("=== 增量补数开始 ===")
    results = []

    # 1. weekly 缺失项
    for s in UNIVERSE:
        if exists("weekly", s["ts_code"]):
            log(f"weekly {s['name']}: 已存在, 跳过")
            continue
        log(f"weekly {s['name']} ({s['ts_code']}) ...")
        df = call_with_wait(pro, "weekly", WEEKLY_FIELDS, f"weekly {s['ts_code']}",
                            ts_code=s["ts_code"], start_date=START_DATE, end_date=END_DATE)
        if df is not None and df != "NO_PERM":
            p = save(df, "weekly", s["ts_code"])
            log(f"  -> {len(df)} 行, {os.path.basename(p)}")
            results.append(("weekly", s["name"], s["ts_code"], len(df), True))
        else:
            results.append(("weekly", s["name"], s["ts_code"], 0, False))
        log(f"  等待 {PAUSE}s ..."); time.sleep(PAUSE)

    # 2. monthly 全部
    for s in UNIVERSE:
        if exists("monthly", s["ts_code"]):
            log(f"monthly {s['name']}: 已存在, 跳过")
            continue
        log(f"monthly {s['name']} ({s['ts_code']}) ...")
        df = call_with_wait(pro, "monthly", MONTHLY_FIELDS, f"monthly {s['ts_code']}",
                            ts_code=s["ts_code"], start_date=START_DATE, end_date=END_DATE)
        if df is not None and df != "NO_PERM":
            p = save(df, "monthly", s["ts_code"])
            log(f"  -> {len(df)} 行, {os.path.basename(p)}")
            results.append(("monthly", s["name"], s["ts_code"], len(df), True))
        else:
            results.append(("monthly", s["name"], s["ts_code"], 0, False))
        log(f"  等待 {PAUSE}s ..."); time.sleep(PAUSE)

    # 3. stock_company 按标的
    comp_frames = []
    for s in UNIVERSE:
        log(f"stock_company {s['name']} ({s['ts_code']}) ...")
        df = call_with_wait(pro, "stock_company", COMPANY_FIELDS, f"company {s['ts_code']}",
                            ts_code=s["ts_code"])
        if df is not None and df != "NO_PERM":
            comp_frames.append(df)
            log(f"  -> {len(df)} 行")
            results.append(("stock_company", s["name"], s["ts_code"], len(df), True))
        else:
            results.append(("stock_company", s["name"], s["ts_code"], 0, False))
        log(f"  等待 {PAUSE}s ..."); time.sleep(PAUSE)

    # 合并 stock_company 快照
    if comp_frames:
        comp_df = pd.concat(comp_frames, ignore_index=True)
        p = save(comp_df, "stock_company", "", snapshot=True)
        log(f"stock_company 合并: {len(comp_df)} 行 -> {os.path.basename(p)}")

    # 汇总
    log("\n=== 增量补数结果 ===")
    ok = sum(1 for r in results if r[4])
    fail = sum(1 for r in results if not r[4])
    log(f"成功 {ok} / 失败 {fail}")
    for ds, name, code, rows, ok in results:
        log(f"  {'OK ' if ok else 'FAIL'} {ds:14s} {name} ({code}): {rows} 行")

    # 保存结果 JSON
    rpath = os.path.join(BASE, f"_incremental_{END_DATE}.json")
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump([{"dataset":r[0],"name":r[1],"ts_code":r[2],"rows":r[3],"ok":r[4]} for r in results],
                  f, ensure_ascii=False, indent=2)
    log(f"结果: {rpath}")
    log("=== 完成 ===")

if __name__ == "__main__":
    main()
