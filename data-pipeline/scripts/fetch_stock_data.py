#!/usr/bin/env python3
"""
按 stock-data-spec.yaml 规范从 Tushare 取数并分区落盘 + 质量校验 + 汇总报告。
用法:
  set TUSHARE_TOKEN=xxx   (或 export)
  python fetch_stock_data.py
"""
import os
import sys
import json
import time
from datetime import datetime

import tushare as ts
import pandas as pd

# -----------------------------------------------------------------------------
# 配置 (来自 spec)
# -----------------------------------------------------------------------------
TOKEN = os.getenv("TUSHARE_TOKEN", "")
START_DATE = "20200101"
END_DATE = datetime.now().strftime("%Y%m%d")
OUT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_data")
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".workbuddy", "state")

UNIVERSE = [
    {"name": "中芯国际", "ts_code": "688981.SH", "symbol": "688981", "exchange": "SSE", "sector": "半导体"},
    {"name": "比亚迪",   "ts_code": "002594.SZ", "symbol": "002594", "exchange": "SZSE", "sector": "新能源汽车"},
    {"name": "长江电力", "ts_code": "600900.SH", "symbol": "600900", "exchange": "SSE", "sector": "电力"},
]

# 数据集字段定义 (与 spec 对齐)
DAILY_FIELDS = ["ts_code", "trade_date", "open", "high", "low", "close", "pre_close",
                "change", "pct_chg", "vol", "amount"]
WEEKLY_FIELDS = ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"]
MONTHLY_FIELDS = ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"]
MONEYFLOW_FIELDS = ["ts_code", "trade_date", "buy_sm_amount", "sell_sm_amount", "buy_md_amount",
                    "sell_md_amount", "buy_lg_amount", "sell_lg_amount", "buy_elg_amount",
                    "sell_elg_amount", "net_mf_amount"]
BASIC_FIELDS = ["ts_code", "symbol", "name", "area", "industry", "fullname", "market",
                "exchange", "list_date", "is_hs"]
COMPANY_FIELDS = ["ts_code", "chairman", "manager", "secretary", "reg_capital", "setup_date",
                  "province", "city", "employees", "main_business", "business_scope", "website"]

RATE_LIMIT_PAUSE = 0.3   # 普通请求间隔
RATE_LIMIT_WAIT = 62     # 触发"频次超限"后退避秒数
MAX_RETRIES = 3          # 网络错误重试次数


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def save_csv(df, dataset, ts_code, is_snapshot=False):
    """按 spec 的 output.naming 规范落盘"""
    if is_snapshot:
        out_dir = os.path.join(OUT_ROOT, dataset)
        os.makedirs(out_dir, exist_ok=True)
        fname = f"{dataset}_snapshot_{END_DATE}.csv"
        path = os.path.join(out_dir, fname)
    else:
        out_dir = os.path.join(OUT_ROOT, dataset, ts_code)
        os.makedirs(out_dir, exist_ok=True)
        fname = f"{ts_code}_{dataset}_{START_DATE}_{END_DATE}.csv"
        path = os.path.join(out_dir, fname)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def safe_fetch(pro, api_name, fields, **kwargs):
    """调用 API 并按 fields 过滤列；处理限流退避与网络重试；无权限返回 None"""
    for attempt in range(MAX_RETRIES):
        try:
            df = getattr(pro, api_name)(**kwargs)
            if df is not None and not df.empty:
                cols = [c for c in fields if c in df.columns]
                time.sleep(RATE_LIMIT_PAUSE)
                return df[cols]
            time.sleep(RATE_LIMIT_PAUSE)
            return None
        except Exception as e:
            msg = str(e)
            # 无权限 -> 直接放弃，不重试
            if "访问权限" in msg or "权限" in msg:
                log(f"  ! {api_name} 无权限: {msg[:60]}")
                return "NO_PERM"
            # 频次超限 -> 等待 62 秒后重试
            if "频次" in msg or "frequency" in msg.lower():
                log(f"  ~ {api_name} 限流，等待 {RATE_LIMIT_WAIT}s 后重试 (attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(RATE_LIMIT_WAIT)
                continue
            # 网络中断 -> 短暂等待后重试
            if "Response ended prematurely" in msg or "timed out" in msg.lower() or "Connection" in msg:
                log(f"  ~ {api_name} 网络中断，{10}s 后重试 (attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(10)
                continue
            log(f"  ! {api_name} 失败: {msg[:80]}")
            return None
    log(f"  ! {api_name} 重试 {MAX_RETRIES} 次仍失败")
    return None


def fetch_ohlc(pro, api_name, dataset, fields):
    """行情类: daily/weekly/monthly, 按标的循环; weekly/monthly 限 1次/分钟需间隔"""
    results = []
    is_low_freq = dataset in ("weekly", "monthly")
    for i, s in enumerate(UNIVERSE):
        if i > 0 and is_low_freq:
            log(f"  ({dataset} 限 1次/分钟, 等待 {RATE_LIMIT_WAIT}s ...)")
            time.sleep(RATE_LIMIT_WAIT)
        log(f"  {dataset}: {s['name']} ({s['ts_code']}) ...")
        df = safe_fetch(pro, api_name, fields,
                        ts_code=s["ts_code"], start_date=START_DATE, end_date=END_DATE)
        if df is not None and df != "NO_PERM":
            path = save_csv(df, dataset, s["ts_code"])
            log(f"    -> {len(df)} 行, {path}")
            results.append({"name": s["name"], "ts_code": s["ts_code"],
                            "dataset": dataset, "rows": len(df), "path": path,
                            "date_min": df["trade_date"].min() if "trade_date" in df else "",
                            "date_max": df["trade_date"].max() if "trade_date" in df else ""})
        elif df == "NO_PERM":
            log(f"    -> 无权限, 跳过")
            results.append({"name": s["name"], "ts_code": s["ts_code"],
                            "dataset": dataset, "rows": 0, "path": "", "note": "无权限"})
        else:
            log(f"    -> 无数据")
            results.append({"name": s["name"], "ts_code": s["ts_code"],
                            "dataset": dataset, "rows": 0, "path": ""})
    return results


def fetch_moneyflow(pro):
    results = []
    for s in UNIVERSE:
        log(f"  moneyflow: {s['name']} ({s['ts_code']}) ...")
        df = safe_fetch(pro, "moneyflow", MONEYFLOW_FIELDS,
                        ts_code=s["ts_code"], start_date=START_DATE, end_date=END_DATE)
        if df is not None and df != "NO_PERM":
            path = save_csv(df, "moneyflow", s["ts_code"])
            log(f"    -> {len(df)} 行, {path}")
            results.append({"name": s["name"], "ts_code": s["ts_code"],
                            "dataset": "moneyflow", "rows": len(df), "path": path})
        elif df == "NO_PERM":
            log(f"    -> 无权限, 跳过 (moneyflow 需更高积分)")
            results.append({"name": s["name"], "ts_code": s["ts_code"],
                            "dataset": "moneyflow", "rows": 0, "path": "", "note": "无权限"})
        else:
            log(f"    -> 无数据")
            results.append({"name": s["name"], "ts_code": s["ts_code"],
                            "dataset": "moneyflow", "rows": 0, "path": ""})
    return results


def fetch_snapshots(pro):
    """stock_basic + stock_company 快照"""
    results = []
    # stock_basic
    log("  stock_basic: 全市场快照 ...")
    df = safe_fetch(pro, "stock_basic", BASIC_FIELDS, list_status="L")
    if df is not None:
        path = save_csv(df, "stock_basic", "", is_snapshot=True)
        log(f"    -> {len(df)} 行, {path}")
        # 校验三只标的命中
        hits = df[df["ts_code"].isin([s["ts_code"] for s in UNIVERSE])]
        log(f"    标的校验: 命中 {len(hits)}/3")
        for _, r in hits.iterrows():
            log(f"      {r['ts_code']} {r['name']} | {r['industry']} | 上市 {r['list_date']}")
        results.append({"dataset": "stock_basic", "rows": len(df), "path": path})
    else:
        results.append({"dataset": "stock_basic", "rows": 0, "path": ""})

    # stock_company: 按标的逐个取(避免全市场大报文中断)
    log("  stock_company: 按标的取 ...")
    comp_frames = []
    for s in UNIVERSE:
        log(f"    {s['name']} ({s['ts_code']}) ...")
        df = safe_fetch(pro, "stock_company", COMPANY_FIELDS, ts_code=s["ts_code"])
        if df is not None and df != "NO_PERM":
            comp_frames.append(df)
            log(f"      -> {len(df)} 行")
        time.sleep(RATE_LIMIT_PAUSE)
    if comp_frames:
        comp_df = pd.concat(comp_frames, ignore_index=True)
        path = save_csv(comp_df, "stock_company", "", is_snapshot=True)
        log(f"    合计 {len(comp_df)} 行, {path}")
        results.append({"dataset": "stock_company", "rows": len(comp_df), "path": path})
    else:
        results.append({"dataset": "stock_company", "rows": 0, "path": ""})
    return results


# -----------------------------------------------------------------------------
# 质量校验
# -----------------------------------------------------------------------------
def quality_check(all_results):
    log("\n=== 质量校验 ===")
    report = []
    for r in all_results:
        if r.get("rows", 0) == 0 or not r.get("path"):
            report.append({"check": "row_count", "ts_code": r.get("ts_code"),
                           "dataset": r["dataset"], "status": "FAIL", "detail": "0 行"})
            continue
        df = pd.read_csv(r["path"], encoding="utf-8-sig")
        ts_code = r.get("ts_code", "")
        # 1 行数
        report.append({"check": "row_count", "ts_code": ts_code, "dataset": r["dataset"],
                       "status": "PASS" if len(df) > 0 else "FAIL", "detail": f"{len(df)} 行"})
        # 2 去重
        if "trade_date" in df.columns and ts_code:
            dup = df.duplicated(subset=["ts_code", "trade_date"]).sum()
            report.append({"check": "no_duplicate", "ts_code": ts_code, "dataset": r["dataset"],
                           "status": "PASS" if dup == 0 else "FAIL", "detail": f"{dup} 重复"})
        # 3 价格合理性 (daily/weekly/monthly)
        if r["dataset"] in ("daily", "weekly", "monthly") and all(c in df.columns for c in ["open","high","low","close"]):
            ok = ((df[["open","high","low","close"]] > 0).all().all()
                  and (df["high"] >= df["low"]).all()
                  and (df["high"] >= df["close"]).all()
                  and (df["close"] >= df["low"]).all())
            report.append({"check": "price_sanity", "ts_code": ts_code, "dataset": r["dataset"],
                           "status": "PASS" if ok else "FAIL", "detail": "OHLC 区间合理" if ok else "异常"})
        # 4 空值
        if r["dataset"] in ("daily","weekly","monthly") and "close" in df.columns:
            nulls = df[["open","close","vol"]].isnull().sum().sum() if "vol" in df.columns else df[["open","close"]].isnull().sum().sum()
            report.append({"check": "null_check", "ts_code": ts_code, "dataset": r["dataset"],
                           "status": "PASS" if nulls == 0 else "WARN", "detail": f"{nulls} 空值"})

    passed = sum(1 for x in report if x["status"] == "PASS")
    failed = sum(1 for x in report if x["status"] == "FAIL")
    warned = sum(1 for x in report if x["status"] == "WARN")
    log(f"  通过 {passed} / 失败 {failed} / 警告 {warned}")
    return report, passed, failed, warned


def write_summary(all_results, qc_report, passed, failed, warned):
    md = []
    md.append(f"# Tushare 取数汇总报告\n")
    md.append(f"- 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    md.append(f"- 回溯区间: {START_DATE} ~ {END_DATE}\n")
    md.append(f"- 标的: {', '.join(s['name']+'('+s['ts_code']+')' for s in UNIVERSE)}\n\n")
    md.append("## 取数结果\n")
    md.append("| 数据集 | 标的 | 行数 | 时间范围 | 文件 |\n")
    md.append("|--------|------|------|----------|------|\n")
    for r in all_results:
        rng = ""
        if r.get("date_min") and r.get("date_max"):
            rng = f"{r['date_min']}~{r['date_max']}"
        md.append(f"| {r['dataset']} | {r.get('name','')} {r.get('ts_code','')} | {r['rows']} | {rng} | {os.path.basename(r.get('path',''))} |\n")
    md.append(f"\n## 质量校验\n")
    md.append(f"- 通过: {passed} / 失败: {failed} / 警告: {warned}\n\n")
    md.append("| 校验项 | 数据集 | 标的 | 状态 | 详情 |\n")
    md.append("|--------|--------|------|------|------|\n")
    for q in qc_report:
        md.append(f"| {q['check']} | {q['dataset']} | {q.get('ts_code','')} | {q['status']} | {q['detail']} |\n")
    md.append(f"\n## 输出目录结构\n")
    md.append("```\noutputs/stock_data/\n")
    md.append("├── daily/{ts_code}/{ts_code}_daily_*.csv\n")
    md.append("├── weekly/{ts_code}/{ts_code}_weekly_*.csv\n")
    md.append("├── monthly/{ts_code}/{ts_code}_monthly_*.csv\n")
    md.append("├── moneyflow/{ts_code}/{ts_code}_moneyflow_*.csv\n")
    md.append("├── stock_basic/stock_basic_snapshot_*.csv\n")
    md.append("└── stock_company/stock_company_snapshot_*.csv\n```\n")
    path = os.path.join(OUT_ROOT, f"_summary_{END_DATE}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(md))
    # 质量报告 JSON
    qpath = os.path.join(OUT_ROOT, f"_quality_report_{END_DATE}.json")
    with open(qpath, "w", encoding="utf-8") as f:
        json.dump({"date": END_DATE, "passed": passed, "failed": failed, "warned": warned,
                   "checks": qc_report}, f, ensure_ascii=False, indent=2)
    log(f"\n汇总报告: {path}")
    log(f"质量报告: {qpath}")
    return path


def main():
    if not TOKEN:
        log("错误: 未设置 TUSHARE_TOKEN 环境变量")
        sys.exit(1)
    log(f"=== Tushare 取数开始 | {START_DATE} ~ {END_DATE} ===")
    log(f"标的: {[s['name'] for s in UNIVERSE]}")
    # 直接传 token，避免 set_token 写文件到 home
    pro = ts.pro_api(TOKEN)

    # 1. 标的校验 + 基础快照
    log("\n--- 步骤1: 基础信息快照 & 标的校验 ---")
    snap_results = fetch_snapshots(pro)

    # 2. 日线
    log("\n--- 步骤2: 日线行情 ---")
    daily_results = fetch_ohlc(pro, "daily", "daily", DAILY_FIELDS)

    # 3. 周线
    log("\n--- 步骤3: 周线行情 ---")
    weekly_results = fetch_ohlc(pro, "weekly", "weekly", WEEKLY_FIELDS)

    # 4. 月线
    log("\n--- 步骤4: 月线行情 ---")
    monthly_results = fetch_ohlc(pro, "monthly", "monthly", MONTHLY_FIELDS)

    # 5. 资金流向
    log("\n--- 步骤5: 资金流向 ---")
    mf_results = fetch_moneyflow(pro)

    all_results = snap_results + daily_results + weekly_results + monthly_results + mf_results

    # 6. 质量校验
    qc_report, passed, failed, warned = quality_check(all_results)

    # 7. 汇总报告
    log("\n--- 步骤6: 生成汇总报告 ---")
    write_summary(all_results, qc_report, passed, failed, warned)
    log("\n=== 全部完成 ===")


if __name__ == "__main__":
    main()
