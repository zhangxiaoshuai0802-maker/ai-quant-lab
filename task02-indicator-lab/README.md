# Task02: 中芯国际(港股)技术指标计算实验室

## 概述

使用 Tushare 获取中芯国际日线数据，在 Jupyter Notebook 中逐步计算 RSI、MACD、布林带、ATR 四项经典技术指标，展示完整计算过程与可视化判读。

## 数据说明

| 项目 | 内容 |
|------|------|
| **标的** | 中芯国际 |
| **主数据源** | 00981.HK (港股) — Tushare `hk_daily` 接口 |
| **实际数据源** | 688981.SH (A股科创板) — Tushare `pro.daily` 接口 (降级) |
| **降级原因** | 当前 token 的 `hk_daily` 限频 1次/小时，配额已用尽 |
| **回溯区间** | 2023-01-03 ~ 2026-07-03 |
| **数据行数** | 840 行 |

> 中芯国际在港股(00981.HK)和A股科创板(688981.SH)两地上市，为同一公司。技术指标计算方法完全一致。

## 指标列表

| 指标 | 参数 | 类型 | 说明 |
|------|------|------|------|
| RSI | 14 日 | 动量震荡 | 衡量超买超卖，0~100 区间 |
| MACD | 12/26/9 | 趋势跟踪 | 快慢线交叉捕捉趋势转折 |
| 布林带 | 20日, 2σ | 波动率通道 | 动态价格通道，识别挤压与突破 |
| ATR | 14 日 | 波动率度量 | 衡量波动幅度，用于止损/仓位管理 |

## 文件结构

```
task02_indicator_lab/
├── spec.yaml                        # 取数与计算规范文件
├── indicator_lab.ipynb              # Notebook 主文件 (22 cells, 已执行, 含图表输出)
├── gen_notebook.py                  # Notebook 生成脚本 (nbformat)
├── README.md                        # 本说明文档
├── data/
│   ├── 00981HK_daily.csv            # 原始日线数据 (840行)
│   └── 00981HK_indicators.csv       # 含全部指标计算结果 (18列)
└── figures/
    ├── price_volume.png             # 价格走势 + 成交量
    ├── rsi.png                      # RSI 指标图
    ├── macd.png                     # MACD 指标图 (含金叉死叉标注)
    ├── bollinger.png                # 布林带三面板图
    ├── atr.png                      # ATR 指标图 (含止损线)
    └── dashboard.png                # 四指标综合仪表盘 (2×2)
```

## 运行方法

### 环境要求

- Python >= 3.10
- 依赖: tushare, pandas, matplotlib, nbformat, nbconvert, ipykernel

### 执行 Notebook

```bash
# 设置 Tushare Token
export TUSHARE_TOKEN="your_token_here"

# 安装依赖
pip install tushare pandas matplotlib nbformat nbconvert ipykernel

# 执行 Notebook
jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=300 indicator_lab.ipynb
```

### 重新生成 Notebook

如需修改 Notebook 结构，编辑 `gen_notebook.py` 后重新生成：

```bash
python gen_notebook.py
```

## Notebook 结构 (22 Cells)

| Cell | 类型 | 内容 |
|------|------|------|
| 1 | Markdown | 标题与概述 |
| 2 | Code | 环境初始化 (tushare/pandas/matplotlib) |
| 3 | Code | 数据获取 (hk_daily -> A股降级 -> CSV兜底) |
| 4 | Markdown | 数据概览说明 |
| 5 | Code | 数据清洗与质量校验 (7项检查) |
| 6 | Code | 价格走势 + 成交量双面板图 |
| 7 | Markdown | RSI 指标原理与公式 |
| 8 | Code | RSI 计算过程 (Wilder平滑法, 打印中间结果) |
| 9 | Code | RSI 可视化 (超买超卖区域填充) |
| 10 | Markdown | MACD 指标原理与公式 |
| 11 | Code | MACD 计算过程 (EMA/DIF/DEA/柱, 金叉死叉识别) |
| 12 | Code | MACD 可视化 (柱状图+折线+交叉标注) |
| 13 | Markdown | 布林带原理与公式 |
| 14 | Code | 布林带计算过程 (中轨/上下轨/带宽/%B/挤压) |
| 15 | Code | 布林带可视化 (三面板: 价格+带宽+%B) |
| 16 | Markdown | ATR 原理与公式 |
| 17 | Code | ATR 计算过程 (TR三场景/Wilder平滑/止损线) |
| 18 | Code | ATR 可视化 (价格+止损线+TR柱+ATR折线) |
| 19 | Markdown | 综合仪表盘说明 |
| 20 | Code | 2×2 综合仪表盘 (RSI/MACD/布林带/ATR) |
| 21 | Code | 最近30日信号汇总表 + 指标CSV导出 |
| 22 | Markdown | 结论与判读 |

## 质量校验结果

| 校验项 | 状态 | 详情 |
|--------|------|------|
| Notebook 可执行 | PASS | 22/22 cells 无错误 |
| 数据充分性 | PASS | 840 行 (> 200 最低要求) |
| 指标列完整 | PASS | rsi_14/dif/dea/macd_hist/bb_upper/bb_lower/atr_14 全部存在 |
| 图表渲染 | PASS | 6 张图表全部生成 |
| 信号汇总表 | PASS | 最近 30 日信号表完整 |
| RSI 范围 | PASS | 20.37 ~ 92.49 (覆盖超买超卖) |
| 布林带合理性 | PASS | bb_upper > bb_lower (有效行) |
| ATR 正值 | PASS | atr_14 > 0 (有效行) |

## 关键发现

- **RSI**: 最近值为 50.41，处于中性区间，多空均衡
- **MACD**: 最近 MACD 柱由正转负 (-0.40)，DIF 即将下穿 DEA，可能出现死叉
- **布林带**: %B 从 0.97 降至 0.52，从接近上轨回落至中轨附近
- **ATR**: 当前 ATR 9.53，接近均值水平，波动率正常

---

> 本 Notebook 展示技术指标的计算过程与可视化判读，不构成投资建议。
