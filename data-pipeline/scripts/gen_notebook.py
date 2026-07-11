# -*- coding: utf-8 -*-
"""
Jupyter Notebook 生成脚本
生成包含完整技术指标分析流程的 Notebook
每个 Cell 独立可执行，含 Markdown 说明文字
"""
import argparse
import os
import sys

try:
    import nbformat
    from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell
except ImportError:
    print("请先安装 nbformat: pip install nbformat")
    sys.exit(1)


def md(text):
    return new_markdown_cell(text)

def code(text):
    return new_code_cell(text)


# ==================== 图表模板 ====================
# 用 .format() 而非 f-string 避免 dict {} 语法冲突

CHART_TEMPLATES = {
    'rsi': """# RSI 可视化
show = df.tail({show_days}).reset_index(drop=True)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5), gridspec_kw=dict(height_ratios=[2, 1]), sharex=True)
ax1.plot(show['trade_date'], show['close'], color='#d4380d', linewidth=1)
ax1.set_ylabel('收盘价（元）')
ax1.set_title('图{num}  RSI(14) 相对强弱指标分析', fontsize=10)
ax1.grid(True, alpha=0.3)

ax2.plot(show['trade_date'], show['rsi_14'], color='#1890ff', linewidth=1, label='RSI(14)')
ax2.axhline(y=70, color='#ff4d4f', linestyle='--', linewidth=0.8, label='超买(70)')
ax2.axhline(y=30, color='#52c41a', linestyle='--', linewidth=0.8, label='超卖(30)')
ax2.fill_between(show['trade_date'], 70, 100, alpha=0.06, color='#ff4d4f')
ax2.fill_between(show['trade_date'], 0, 30, alpha=0.06, color='#52c41a')
ax2.set_ylabel('RSI'); ax2.set_ylim(0, 100)
ax2.legend(loc='upper left', fontsize=7, ncol=3)
ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.tight_layout(); plt.show()""",

    'macd': """# MACD 可视化
show = df.tail({show_days}).reset_index(drop=True)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5), gridspec_kw=dict(height_ratios=[2, 1]), sharex=True)
ax1.plot(show['trade_date'], show['close'], color='#d4380d', linewidth=1, label='收盘价')
ax1.plot(show['trade_date'], show['dif'], color='#1890ff', linewidth=0.8, label='DIF')
ax1.plot(show['trade_date'], show['dea'], color='#faad14', linewidth=0.8, label='DEA')
ax1.set_ylabel('价格'); ax1.legend(loc='upper left', fontsize=7, ncol=3)
ax1.set_title('图{num}  MACD(12,26,9) 指标分析', fontsize=10)
ax1.grid(True, alpha=0.3)

colors = ['#ff4d4f' if v>=0 else '#52c41a' for v in show['macd_hist']]
ax2.bar(show['trade_date'], show['macd_hist'], color=colors, width=1, label='MACD柱')
ax2.axhline(y=0, color='#333', linewidth=0.5)
ax2.set_ylabel('MACD柱'); ax2.legend(loc='upper left', fontsize=7)
ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.tight_layout(); plt.show()""",

    'boll': """# 布林带可视化
show = df.tail({show_days}).reset_index(drop=True)

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(show['trade_date'], show['close'], color='#d4380d', linewidth=1, label='收盘价')
ax.plot(show['trade_date'], show['bb_mid'], color='#1890ff', linewidth=0.8, linestyle='--', label='中轨')
ax.plot(show['trade_date'], show['bb_upper'], color='#722ed1', linewidth=0.8, label='上轨')
ax.plot(show['trade_date'], show['bb_lower'], color='#52c41a', linewidth=0.8, label='下轨')
ax.fill_between(show['trade_date'], show['bb_upper'], show['bb_lower'], alpha=0.05, color='#722ed1')
ax.set_title('图{num}  布林带(20,2) 指标分析', fontsize=10)
ax.set_ylabel('价格（元）'); ax.legend(loc='upper left', fontsize=7, ncol=4)
ax.grid(True, alpha=0.3)
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.tight_layout(); plt.show()""",

    'atr': """# ATR 可视化
show = df.tail({show_days}).reset_index(drop=True)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5), gridspec_kw=dict(height_ratios=[2, 1]), sharex=True)
ax1.plot(show['trade_date'], show['close'], color='#d4380d', linewidth=1)
ax1.plot(show['trade_date'], show['stop_loss'], color='#faad14', linewidth=0.8, linestyle='--', label='止损线')
ax1.set_ylabel('价格（元）'); ax1.legend(loc='upper left', fontsize=7)
ax1.set_title('图{num}  ATR(14) 波动率与止损分析', fontsize=10)
ax1.grid(True, alpha=0.3)

ax2.plot(show['trade_date'], show['atr_14'], color='#1890ff', linewidth=1, label='ATR(14)')
ax2.set_ylabel('ATR'); ax2.legend(loc='upper left', fontsize=7)
ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.tight_layout(); plt.show()""",

    'kdj': """# KDJ 可视化
show = df.tail({show_days}).reset_index(drop=True)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5), gridspec_kw=dict(height_ratios=[2, 1.5]), sharex=True)
ax1.plot(show['trade_date'], show['close'], color='#d4380d', linewidth=1)
ax1.set_ylabel('收盘价（元）')
ax1.set_title('图{num}  KDJ(9,3,3) 随机指标分析', fontsize=10)
ax1.grid(True, alpha=0.3)

ax2.plot(show['trade_date'], show['k'], color='#1890ff', linewidth=1, label='K线')
ax2.plot(show['trade_date'], show['d'], color='#faad14', linewidth=1, label='D线')
ax2.plot(show['trade_date'], show['j'], color='#eb2f96', linewidth=0.8, linestyle='--', label='J线')
ax2.axhline(y=80, color='#ff4d4f', linestyle=':', linewidth=0.6)
ax2.axhline(y=20, color='#52c41a', linestyle=':', linewidth=0.6)
ax2.fill_between(show['trade_date'], 80, 100, alpha=0.05, color='#ff4d4f')
ax2.fill_between(show['trade_date'], 0, 20, alpha=0.05, color='#52c41a')
ax2.set_ylabel('KDJ值'); ax2.set_ylim(-10, 110)
ax2.legend(loc='upper left', fontsize=7, ncol=3)
ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.tight_layout(); plt.show()""",

    'cci': """# CCI 可视化
show = df.tail({show_days}).reset_index(drop=True)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5), gridspec_kw=dict(height_ratios=[2, 1]), sharex=True)
ax1.plot(show['trade_date'], show['close'], color='#d4380d', linewidth=1)
ax1.set_ylabel('收盘价（元）')
ax1.set_title('图{num}  CCI(14) 顺势指标分析', fontsize=10)
ax1.grid(True, alpha=0.3)

ax2.plot(show['trade_date'], show['cci_14'], color='#1890ff', linewidth=1, label='CCI(14)')
ax2.axhline(y=100, color='#ff4d4f', linestyle='--', linewidth=0.8, label='超买(100)')
ax2.axhline(y=-100, color='#52c41a', linestyle='--', linewidth=0.8, label='超卖(-100)')
ax2.set_ylabel('CCI'); ax2.legend(loc='upper left', fontsize=7, ncol=3)
ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.tight_layout(); plt.show()""",
}


# ==================== 计算代码模板 ====================

CALC_TEMPLATES = {
    'rsi': """# RSI(14) 计算
def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

df['rsi_14'] = calc_rsi(df['close'])
rsi_val = df['rsi_14'].iloc[-1]
print(f'最新 RSI(14): {rsi_val:.2f}')""",
    'macd': """# MACD(12,26,9) 计算
def calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = (dif - dea) * 2
    return dif, dea, hist

df['dif'], df['dea'], df['macd_hist'] = calc_macd(df['close'])
dif_val = df['dif'].iloc[-1]; dea_val = df['dea'].iloc[-1]; macd_val = df['macd_hist'].iloc[-1]
print(f'最新 DIF: {dif_val:.2f}, DEA: {dea_val:.2f}, MACD柱: {macd_val:.2f}')""",
    'boll': """# 布林带(20,2) 计算
def calc_boll(close, period=20, std_dev=2):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    width = (upper - lower) / mid
    pct_b = (close - lower) / (upper - lower)
    return mid, upper, lower, width, pct_b

df['bb_mid'], df['bb_upper'], df['bb_lower'], df['bb_width'], df['bb_pct_b'] = calc_boll(df['close'])
bb_u = df['bb_upper'].iloc[-1]; bb_m = df['bb_mid'].iloc[-1]; bb_l = df['bb_lower'].iloc[-1]
print(f'最新 上轨: {bb_u:.2f}, 中轨: {bb_m:.2f}, 下轨: {bb_l:.2f}')""",
    'atr': """# ATR(14) 计算
def calc_atr(high, low, close, period=14):
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return tr, atr

df['tr'], df['atr_14'] = calc_atr(df['high'], df['low'], df['close'])
df['stop_loss'] = df['close'] - 2 * df['atr_14']
atr_val = df['atr_14'].iloc[-1]; sl_val = df['stop_loss'].iloc[-1]
print(f'最新 ATR(14): {atr_val:.2f}, 止损价: {sl_val:.2f}')""",
    'kdj': """# KDJ(9,3,3) 计算
def calc_kdj(high, low, close, n=9, m1=3, m2=3):
    low_min = low.rolling(n, min_periods=1).min()
    high_max = high.rolling(n, min_periods=1).max()
    rsv = (close - low_min) / (high_max - low_min) * 100
    rsv = rsv.fillna(50)
    k = rsv.ewm(alpha=1/m1, adjust=False).mean()
    d = k.ewm(alpha=1/m2, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j

df['k'], df['d'], df['j'] = calc_kdj(df['high'], df['low'], df['close'])
k_val = df['k'].iloc[-1]; d_val = df['d'].iloc[-1]; j_val = df['j'].iloc[-1]
print(f'最新 K: {k_val:.2f}, D: {d_val:.2f}, J: {j_val:.2f}')""",
    'cci': """# CCI(14) 计算
def calc_cci(high, low, close, period=14):
    tp = (high + low + close) / 3
    ma = tp.rolling(period).mean()
    md = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - ma) / (0.015 * md)

df['cci_14'] = calc_cci(df['high'], df['low'], df['close'])
cci_val = df['cci_14'].iloc[-1]
print(f'最新 CCI(14): {cci_val:.2f}')""",
}


# ==================== 解读模板 ====================

INTERP_MAP = {
    'rsi': "**解读要点：**\n- RSI > 70 为超买区，价格可能回调；RSI < 30 为超卖区，价格可能反弹\n- RSI = 50 为多空分界线\n- RSI 与价格背离时，是趋势反转的重要信号\n- 当前 RSI 值可从上方 Cell 输出中查看",
    'macd': "**解读要点：**\n- DIF 上穿 DEA 为金叉（买入信号），下穿为死叉（卖出信号）\n- 红色柱为多头动能，绿色柱为空头动能\n- MACD 柱由正转负提示短期调整\n- DIF 与价格的背离是趋势反转的早期信号",
    'boll': "**解读要点：**\n- 价格触及上轨可能超买，触及下轨可能超卖\n- 布林带收窄预示低波动，可能即将突破\n- 布林带张开预示波动增大，趋势加速\n- %B 指标量化价格在布林带中的相对位置",
    'atr': "**解读要点：**\n- ATR 衡量市场波动率，数值越大波动越剧烈\n- 止损线 = 收盘价 - 2×ATR，可作为动态止损参考\n- ATR 上升时建议加宽止损间距，下降时可收紧",
    'kdj': "**解读要点：**\n- K 线上穿 D 线且在 20 以下为低位金叉（强买信号）\n- K 线下穿 D 线且在 80 以上为高位死叉（强卖信号）\n- J 值 > 100 超买，J 值 < 0 超卖\n- KDJ 与 RSI 互补使用效果更好",
    'cci': "**解读要点：**\n- CCI > 100 为超买区，CCI < -100 为超卖区\n- CCI 在 ±100 之间为正常震荡区间\n- CCI 从超买/超卖区回归常区时可能是趋势转折信号",
}

IND_TITLE = {
    'rsi': 'RSI 相对强弱指标',
    'macd': 'MACD 指数平滑异同移动平均线',
    'boll': '布林带 Bollinger Bands',
    'atr': 'ATR 平均真实波幅',
    'kdj': 'KDJ 随机指标',
    'cci': 'CCI 顺势指标',
}


# ==================== Notebook 构建 ====================

def build_cells(stock_name, stock_code, indicators, show_days):
    cells = []

    # Cell 1: 标题
    cells.append(md(
        "# {0}({1}) 技术指标分析实验室\n\n"
        "本 Notebook 对 **{0}({1})** 的日线数据进行技术指标分析，"
        "涵盖数据诊断、{2} 个指标的计算与可视化。\n\n"
        "---".format(stock_name, stock_code, len(indicators))
    ))

    # Cell 2: 导入库
    cells.append(code(
        "import pandas as pd\n"
        "import numpy as np\n"
        "import matplotlib.pyplot as plt\n"
        "import matplotlib.dates as mdates\n\n"
        "# 中文字体配置\n"
        "plt.rcParams['font.sans-serif'] = ['SimSun']\n"
        "plt.rcParams['axes.unicode_minus'] = False\n"
        "plt.rcParams['font.size'] = 9\n\n"
        "print('库加载完成')"
    ))

    # Cell 3-5: 数据加载、诊断
    cells.append(md("## 1. 数据加载"))
    cells.append(code(
        "# 加载股价数据\n"
        "DATA_PATH = 'data.csv'  # 修改为实际数据路径\n"
        "df = pd.read_csv(DATA_PATH, encoding='utf-8-sig')\n"
        "df['trade_date'] = pd.to_datetime(df['trade_date'].astype(str), format='%Y%m%d')\n"
        "df = df.sort_values('trade_date').reset_index(drop=True)\n\n"
        "n_rows = len(df)\n"
        "date_start = df['trade_date'].min().date()\n"
        "date_end = df['trade_date'].max().date()\n"
        "print(f'数据加载完成: {n_rows} 行, 日期范围 {date_start} ~ {date_end}')"
    ))

    cells.append(md("## 2. 数据诊断分析\n\n### 2.1 缺失值检查"))
    cells.append(code(
        "# 缺失值统计\n"
        "missing = df.isnull().sum()\n"
        "has_missing = missing.sum() > 0\n"
        "print('缺失值统计:')\n"
        "if has_missing:\n"
        "    display(pd.DataFrame({'字段': missing.index, '缺失数': missing.values}))\n"
        "else:\n"
        "    print('无缺失值')"
    ))

    cells.append(md("### 2.2 描述性统计量"))
    cells.append(code(
        "# 核心字段描述性统计\n"
        "desc_cols = ['open', 'high', 'low', 'close', 'vol', 'pct_chg']\n"
        "desc = df[desc_cols].describe()\n"
        "display(desc.round(2))\n\n"
        "close_mean = df['close'].mean()\n"
        "close_std = df['close'].std()\n"
        "print(f'收盘价均值: {close_mean:.2f} 元, 标准差: {close_std:.2f} 元')"
    ))

    # Cell: 价格走势
    cells.append(md("### 2.3 收盘价走势"))
    cells.append(code(
        "# 绘制收盘价走势\n"
        "show = df.tail({0}).reset_index(drop=True)\n\n"
        "fig, ax = plt.subplots(figsize=(10, 4))\n"
        "ax.plot(show['trade_date'], show['close'], color='#d4380d', linewidth=1, label='收盘价')\n"
        "ax.fill_between(show['trade_date'], show['close'].min()*0.95, show['close'], alpha=0.08, color='#d4380d')\n"
        "ax.set_title('图1  收盘价走势（近{0}个交易日）', fontsize=10)\n"
        "ax.set_xlabel('日期')\n"
        "ax.set_ylabel('价格（元）')\n"
        "ax.legend(loc='upper left')\n"
        "ax.grid(True, alpha=0.3)\n"
        "ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))\n"
        "ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))\n"
        "plt.tight_layout()\n"
        "plt.show()".format(show_days)
    ))

    # === 各指标计算与可视化 ===
    indicator_num = 2

    for ind in indicators:
        title = IND_TITLE.get(ind, ind.upper())
        cells.append(md("## {0}. {1}".format(indicator_num + 1, title)))
        cells.append(code(CALC_TEMPLATES.get(ind, '')))

        cells.append(md("### {0} 可视化".format(title)))
        chart_tpl = CHART_TEMPLATES.get(ind, '')
        cells.append(code(chart_tpl.format(show_days=show_days, num=indicator_num)))

        cells.append(md(INTERP_MAP.get(ind, "**解读要点：** 查看上方图表和计算输出。")))
        indicator_num += 1

    # === 信号汇总 ===
    cells.append(md("## {0}. 综合信号汇总".format(indicator_num + 1)))
    cells.append(code(
        "# 综合信号汇总表 — 最近 10 个交易日\n"
        "signal_df = df.tail(10).copy()\n\n"
        "# 生成信号判断\n"
        "signals = {}\n"
        "if 'rsi_14' in signal_df.columns:\n"
        "    signals['RSI值'] = signal_df['rsi_14'].round(2)\n"
        "    signals['RSI信号'] = signal_df['rsi_14'].apply(\n"
        "        lambda x: '超买' if x > 70 else ('超卖' if x < 30 else '中性'))\n"
        "if 'macd_hist' in signal_df.columns:\n"
        "    signals['MACD柱'] = signal_df['macd_hist'].round(2)\n"
        "    signals['MACD信号'] = signal_df['macd_hist'].apply(\n"
        "        lambda x: '多头' if x > 0 else '空头')\n"
        "if 'bb_pct_b' in signal_df.columns:\n"
        "    signals['布林%B'] = signal_df['bb_pct_b'].round(2)\n"
        "    signals['布林信号'] = signal_df['bb_pct_b'].apply(\n"
        "        lambda x: '超买' if x > 1 else ('超卖' if x < 0 else '中性'))\n"
        "if 'atr_14' in signal_df.columns:\n"
        "    signals['ATR'] = signal_df['atr_14'].round(2)\n"
        "    signals['止损价'] = signal_df['stop_loss'].round(2)\n"
        "if 'k' in signal_df.columns:\n"
        "    signals['K'] = signal_df['k'].round(2)\n"
        "    signals['D'] = signal_df['d'].round(2)\n"
        "    signals['J'] = signal_df['j'].round(2)\n\n"
        "summary = pd.DataFrame(signals, index=signal_df['trade_date'].dt.strftime('%Y-%m-%d'))\n"
        "display(summary)"
    ))

    # === 结论 ===
    cells.append(md(
        "## {0}. 结论与展望\n\n"
        "本 Notebook 完成了 {1}({2}) 的技术指标分析，"
        "涵盖 {3} 个经典指标的计算与可视化。\n\n"
        "**下一步建议：**\n"
        "- 组合多个指标信号进行综合判断，避免单一指标误判\n"
        "- 对不同参数组合进行回测，验证信号有效性\n"
        "- 结合基本面分析，提升决策质量\n"
        "- 扩展到多股票横向对比分析".format(
            indicator_num + 2, stock_name, stock_code, len(indicators))
    ))

    return cells


# ==================== 主函数 ====================

def main():
    parser = argparse.ArgumentParser(description='量化技术指标 Notebook 生成工具')
    parser.add_argument('--input', required=True, help='输入 CSV 文件路径')
    parser.add_argument('--output', required=True, help='输出 .ipynb 文件路径')
    parser.add_argument('--stock-name', default='股票', help='股票名称')
    parser.add_argument('--stock-code', default='CODE', help='股票代码')
    parser.add_argument('--indicators', default='rsi,macd,boll,atr,kdj',
                        help='指标列表，逗号分隔')
    parser.add_argument('--show-days', type=int, default=250, help='图表展示天数')

    args = parser.parse_args()
    indicators = args.indicators.split(',')

    nb = new_notebook()
    nb.cells = build_cells(args.stock_name, args.stock_code, indicators, args.show_days)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)

    print("Notebook 已生成: " + args.output)
    print("  股票: " + args.stock_name + "(" + args.stock_code + ")")
    print("  指标: " + ', '.join(indicators))
    print("  Cell 数: " + str(len(nb.cells)))


if __name__ == '__main__':
    main()
