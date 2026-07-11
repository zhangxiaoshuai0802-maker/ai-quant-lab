# -*- coding: utf-8 -*-
"""
量化技术指标计算核心脚本
支持: RSI, MACD, 布林带, ATR, KDJ, CCI
任务: diagnose | calc | charts
"""
import argparse
import json
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['font.sans-serif'] = ['SimSun']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.size'] = 9
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ==================== 指标计算函数 ====================

def calc_rsi(close, period=14):
    """RSI 相对强弱指标 (Wilder 平滑法)"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calc_macd(close, fast=12, slow=26, signal=9):
    """MACD 指数平滑异同移动平均线"""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = (dif - dea) * 2
    return dif, dea, hist


def calc_boll(close, period=20, std_dev=2):
    """布林带 Bollinger Bands"""
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    width = (upper - lower) / mid
    pct_b = (close - lower) / (upper - lower)
    return mid, upper, lower, width, pct_b


def calc_atr(high, low, close, period=14):
    """ATR 平均真实波幅"""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return tr, atr


def calc_kdj(high, low, close, n=9, m1=3, m2=3):
    """KDJ 随机指标"""
    low_min = low.rolling(n, min_periods=1).min()
    high_max = high.rolling(n, min_periods=1).max()
    rsv = (close - low_min) / (high_max - low_min) * 100
    rsv = rsv.fillna(50)
    k = rsv.ewm(alpha=1/m1, adjust=False).mean()
    d = k.ewm(alpha=1/m2, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


def calc_cci(high, low, close, period=14):
    """CCI 顺势指标"""
    tp = (high + low + close) / 3
    ma = tp.rolling(period).mean()
    md = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci = (tp - ma) / (0.015 * md)
    return cci


# ==================== 数据加载 ====================

def load_data(csv_path):
    """加载 CSV 股价数据"""
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    # 日期解析
    date_col = 'trade_date'
    if date_col not in df.columns:
        # 尝试其他常见名称
        for alt in ['date', 'Date', '交易日期']:
            if alt in df.columns:
                date_col = alt
                break
    # 多格式兼容解析
    raw = df[date_col].astype(str)
    # 优先尝试 YYYYMMDD (如 20260703)
    try:
        df[date_col] = pd.to_datetime(raw, format='%Y%m%d')
    except ValueError:
        try:
            df[date_col] = pd.to_datetime(raw, format='%Y-%m-%d')
        except ValueError:
            df[date_col] = pd.to_datetime(raw, format='mixed')
    df = df.sort_values(date_col).reset_index(drop=True)
    return df


# ==================== 诊断任务 ====================

def task_diagnose(df, output_dir):
    """数据诊断分析"""
    missing = df.isnull().sum()
    desc_cols = ['open', 'high', 'low', 'close', 'vol', 'pct_chg']
    # 兼容大小写
    actual_cols = []
    for c in desc_cols:
        if c in df.columns:
            actual_cols.append(c)
        elif c.upper() in df.columns:
            actual_cols.append(c.upper())
    desc = df[actual_cols].describe()

    result = {
        'total_rows': len(df),
        'date_start': str(df['trade_date'].min().date()),
        'date_end': str(df['trade_date'].max().date()),
        'missing_values': {col: int(missing[col]) for col in missing.index if missing[col] > 0},
        'desc_stats': {}
    }
    for col in actual_cols:
        s = df[col]
        result['desc_stats'][col.lower()] = {
            'count': int(s.count()),
            'mean': round(float(s.mean()), 4),
            'std': round(float(s.std()), 4),
            'min': round(float(s.min()), 4),
            '25%': round(float(s.quantile(0.25)), 4),
            '50%': round(float(s.median()), 4),
            '75%': round(float(s.quantile(0.75)), 4),
            'max': round(float(s.max()), 4),
        }

    out_path = os.path.join(output_dir, 'diag_stats.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"诊断结果已保存: {out_path}")
    print(f"  数据行数: {result['total_rows']}")
    print(f"  日期范围: {result['date_start']} ~ {result['date_end']}")
    print(f"  缺失值: {'无' if not result['missing_values'] else result['missing_values']}")
    return result


# ==================== 计算任务 ====================

def task_calc(df, indicators, params, output_dir):
    """计算技术指标"""
    close = df['close'] if 'close' in df.columns else df['CLOSE']
    high = df['high'] if 'high' in df.columns else df['HIGH']
    low = df['low'] if 'low' in df.columns else df['LOW']

    latest = {'latest_close': round(float(close.iloc[-1]), 2)}

    for ind in indicators:
        if ind == 'rsi':
            period = params.get('rsi_period', 14)
            df['rsi_14'] = calc_rsi(close, period)
            latest['latest_rsi'] = round(float(df['rsi_14'].iloc[-1]), 2)
        elif ind == 'macd':
            fast = params.get('macd_fast', 12)
            slow = params.get('macd_slow', 26)
            signal = params.get('macd_signal', 9)
            df['dif'], df['dea'], df['macd_hist'] = calc_macd(close, fast, slow, signal)
            latest['latest_dif'] = round(float(df['dif'].iloc[-1]), 2)
            latest['latest_dea'] = round(float(df['dea'].iloc[-1]), 2)
            latest['latest_macd'] = round(float(df['macd_hist'].iloc[-1]), 2)
        elif ind == 'boll':
            period = params.get('boll_period', 20)
            std_dev = params.get('boll_std', 2)
            df['bb_mid'], df['bb_upper'], df['bb_lower'], df['bb_width'], df['bb_pct_b'] = \
                calc_boll(close, period, std_dev)
            latest['latest_bb_upper'] = round(float(df['bb_upper'].iloc[-1]), 2)
            latest['latest_bb_mid'] = round(float(df['bb_mid'].iloc[-1]), 2)
            latest['latest_bb_lower'] = round(float(df['bb_lower'].iloc[-1]), 2)
        elif ind == 'atr':
            period = params.get('atr_period', 14)
            multiplier = params.get('atr_mult', 2)
            df['tr'], df['atr_14'] = calc_atr(high, low, close, period)
            df['stop_loss'] = close - multiplier * df['atr_14']
            latest['latest_atr'] = round(float(df['atr_14'].iloc[-1]), 2)
            latest['latest_stop_loss'] = round(float(df['stop_loss'].iloc[-1]), 2)
        elif ind == 'kdj':
            n = params.get('kdj_n', 9)
            df['k'], df['d'], df['j'] = calc_kdj(high, low, close, n)
            latest['latest_k'] = round(float(df['k'].iloc[-1]), 2)
            latest['latest_d'] = round(float(df['d'].iloc[-1]), 2)
            latest['latest_j'] = round(float(df['j'].iloc[-1]), 2)
        elif ind == 'cci':
            period = params.get('cci_period', 14)
            df['cci_14'] = calc_cci(high, low, close, period)
            latest['latest_cci'] = round(float(df['cci_14'].iloc[-1]), 2)

    # 保存 CSV
    csv_path = os.path.join(output_dir, 'indicators_data.csv')
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"指标数据已保存: {csv_path}")

    # 保存最新值 JSON
    json_path = os.path.join(output_dir, 'latest_indicators.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(latest, f, ensure_ascii=False, indent=2)
    print(f"最新指标值已保存: {json_path}")
    for k, v in latest.items():
        print(f"  {k}: {v}")

    return df, latest


# ==================== 图表任务 ====================

def task_charts(df, indicators, params, show_days, output_dir):
    """生成 PNG 图表"""
    close = df['close'] if 'close' in df.columns else df['CLOSE']
    date_col = 'trade_date'
    show = df.tail(show_days).reset_index(drop=True)

    chart_num = 1

    # 图1: 收盘价走势
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(show[date_col], show[close.name if close.name else 'close'], color='#d4380d', linewidth=1, label='收盘价')
    ax.fill_between(show[date_col], show[close.name if close.name else 'close'].min() * 0.95,
                    show[close.name if close.name else 'close'], alpha=0.08, color='#d4380d')
    ax.set_title(f'图{chart_num}  收盘价走势（近{show_days}个交易日）', fontsize=10)
    ax.set_xlabel('日期', fontsize=9)
    ax.set_ylabel('价格（元）', fontsize=9)
    ax.legend(loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'chart_price.png'), dpi=150, bbox_inches='tight')
    plt.close()
    chart_num += 1

    close_col = close.name if close.name else 'close'

    # 各指标图表
    for ind in indicators:
        if ind == 'rsi' and 'rsi_14' in show.columns:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 4.5),
                                            gridspec_kw={'height_ratios': [2, 1]}, sharex=True)
            ax1.plot(show[date_col], show[close_col], color='#d4380d', linewidth=1)
            ax1.set_ylabel('收盘价（元）', fontsize=9)
            ax1.set_title(f'图{chart_num}  RSI(14) 相对强弱指标分析', fontsize=10)
            ax1.grid(True, alpha=0.3)
            ax2.plot(show[date_col], show['rsi_14'], color='#1890ff', linewidth=1, label='RSI(14)')
            ax2.axhline(y=70, color='#ff4d4f', linestyle='--', linewidth=0.8, label='超买(70)')
            ax2.axhline(y=30, color='#52c41a', linestyle='--', linewidth=0.8, label='超卖(30)')
            ax2.axhline(y=50, color='#999', linestyle=':', linewidth=0.6)
            ax2.fill_between(show[date_col], 70, 100, alpha=0.06, color='#ff4d4f')
            ax2.fill_between(show[date_col], 0, 30, alpha=0.06, color='#52c41a')
            ax2.set_ylabel('RSI', fontsize=9)
            ax2.set_xlabel('日期', fontsize=9)
            ax2.set_ylim(0, 100)
            ax2.legend(loc='upper left', fontsize=7, ncol=3)
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'chart_rsi.png'), dpi=150, bbox_inches='tight')
            plt.close()
            chart_num += 1

        elif ind == 'macd' and 'dif' in show.columns:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 4.5),
                                            gridspec_kw={'height_ratios': [2, 1]}, sharex=True)
            ax1.plot(show[date_col], show[close_col], color='#d4380d', linewidth=1, label='收盘价')
            ax1.plot(show[date_col], show['dif'], color='#1890ff', linewidth=0.8, label='DIF')
            ax1.plot(show[date_col], show['dea'], color='#faad14', linewidth=0.8, label='DEA')
            ax1.set_ylabel('价格/DIF/DEA', fontsize=9)
            ax1.set_title(f'图{chart_num}  MACD(12,26,9) 指标分析', fontsize=10)
            ax1.legend(loc='upper left', fontsize=7, ncol=3)
            ax1.grid(True, alpha=0.3)
            colors_hist = ['#ff4d4f' if v >= 0 else '#52c41a' for v in show['macd_hist']]
            ax2.bar(show[date_col], show['macd_hist'], color=colors_hist, width=1, label='MACD柱')
            ax2.axhline(y=0, color='#333', linewidth=0.5)
            ax2.set_ylabel('MACD柱', fontsize=9)
            ax2.set_xlabel('日期', fontsize=9)
            ax2.legend(loc='upper left', fontsize=7)
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'chart_macd.png'), dpi=150, bbox_inches='tight')
            plt.close()
            chart_num += 1

        elif ind == 'boll' and 'bb_upper' in show.columns:
            fig, ax = plt.subplots(figsize=(8, 3.8))
            ax.plot(show[date_col], show[close_col], color='#d4380d', linewidth=1, label='收盘价')
            ax.plot(show[date_col], show['bb_mid'], color='#1890ff', linewidth=0.8, linestyle='--', label='中轨')
            ax.plot(show[date_col], show['bb_upper'], color='#722ed1', linewidth=0.8, label='上轨')
            ax.plot(show[date_col], show['bb_lower'], color='#52c41a', linewidth=0.8, label='下轨')
            ax.fill_between(show[date_col], show['bb_upper'], show['bb_lower'], alpha=0.05, color='#722ed1')
            ax.set_title(f'图{chart_num}  布林带(20,2) 指标分析', fontsize=10)
            ax.set_xlabel('日期', fontsize=9)
            ax.set_ylabel('价格（元）', fontsize=9)
            ax.legend(loc='upper left', fontsize=7, ncol=4)
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'chart_boll.png'), dpi=150, bbox_inches='tight')
            plt.close()
            chart_num += 1

        elif ind == 'atr' and 'atr_14' in show.columns:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 4),
                                            gridspec_kw={'height_ratios': [2, 1]}, sharex=True)
            ax1.plot(show[date_col], show[close_col], color='#d4380d', linewidth=1)
            ax1.plot(show[date_col], show['stop_loss'], color='#faad14', linewidth=0.8, linestyle='--', label='止损线')
            ax1.set_ylabel('价格（元）', fontsize=9)
            ax1.set_title(f'图{chart_num}  ATR(14) 波动率与止损分析', fontsize=10)
            ax1.legend(loc='upper left', fontsize=7)
            ax1.grid(True, alpha=0.3)
            ax2.plot(show[date_col], show['atr_14'], color='#1890ff', linewidth=1, label='ATR(14)')
            ax2.set_ylabel('ATR', fontsize=9)
            ax2.set_xlabel('日期', fontsize=9)
            ax2.legend(loc='upper left', fontsize=7)
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'chart_atr.png'), dpi=150, bbox_inches='tight')
            plt.close()
            chart_num += 1

        elif ind == 'kdj' and 'k' in show.columns:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 4.5),
                                            gridspec_kw={'height_ratios': [2, 1.5]}, sharex=True)
            ax1.plot(show[date_col], show[close_col], color='#d4380d', linewidth=1)
            ax1.set_ylabel('收盘价（元）', fontsize=9)
            ax1.set_title(f'图{chart_num}  KDJ(9,3,3) 随机指标分析', fontsize=10)
            ax1.grid(True, alpha=0.3)
            ax2.plot(show[date_col], show['k'], color='#1890ff', linewidth=1, label='K线')
            ax2.plot(show[date_col], show['d'], color='#faad14', linewidth=1, label='D线')
            ax2.plot(show[date_col], show['j'], color='#eb2f96', linewidth=0.8, linestyle='--', label='J线')
            ax2.axhline(y=80, color='#ff4d4f', linestyle=':', linewidth=0.6)
            ax2.axhline(y=20, color='#52c41a', linestyle=':', linewidth=0.6)
            ax2.fill_between(show[date_col], 80, 100, alpha=0.05, color='#ff4d4f')
            ax2.fill_between(show[date_col], 0, 20, alpha=0.05, color='#52c41a')
            ax2.set_ylabel('KDJ值', fontsize=9)
            ax2.set_xlabel('日期', fontsize=9)
            ax2.set_ylim(-10, 110)
            ax2.legend(loc='upper left', fontsize=7, ncol=3)
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'chart_kdj.png'), dpi=150, bbox_inches='tight')
            plt.close()
            chart_num += 1

        elif ind == 'cci' and 'cci_14' in show.columns:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 4.5),
                                            gridspec_kw={'height_ratios': [2, 1]}, sharex=True)
            ax1.plot(show[date_col], show[close_col], color='#d4380d', linewidth=1)
            ax1.set_ylabel('收盘价（元）', fontsize=9)
            ax1.set_title(f'图{chart_num}  CCI(14) 顺势指标分析', fontsize=10)
            ax1.grid(True, alpha=0.3)
            ax2.plot(show[date_col], show['cci_14'], color='#1890ff', linewidth=1, label='CCI(14)')
            ax2.axhline(y=100, color='#ff4d4f', linestyle='--', linewidth=0.8, label='超买(100)')
            ax2.axhline(y=-100, color='#52c41a', linestyle='--', linewidth=0.8, label='超卖(-100)')
            ax2.axhline(y=0, color='#999', linestyle=':', linewidth=0.6)
            ax2.set_ylabel('CCI', fontsize=9)
            ax2.set_xlabel('日期', fontsize=9)
            ax2.legend(loc='upper left', fontsize=7, ncol=3)
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'chart_cci.png'), dpi=150, bbox_inches='tight')
            plt.close()
            chart_num += 1

    print(f"图表已生成 {chart_num - 1} 张，保存在: {output_dir}")


# ==================== 主函数 ====================

def main():
    parser = argparse.ArgumentParser(description='量化技术指标计算工具')
    parser.add_argument('--input', required=True, help='输入 CSV 文件路径')
    parser.add_argument('--task', required=True, choices=['diagnose', 'calc', 'charts'],
                        help='任务类型: diagnose(诊断), calc(计算), charts(图表)')
    parser.add_argument('--indicators', default='rsi,macd,boll,atr,kdj',
                        help='指标列表，逗号分隔 (rsi,macd,boll,atr,kdj,cci)')
    parser.add_argument('--output-dir', default='.', help='输出目录')
    # 指标参数
    parser.add_argument('--rsi-period', type=int, default=14)
    parser.add_argument('--macd-fast', type=int, default=12)
    parser.add_argument('--macd-slow', type=int, default=26)
    parser.add_argument('--macd-signal', type=int, default=9)
    parser.add_argument('--boll-period', type=int, default=20)
    parser.add_argument('--boll-std', type=float, default=2)
    parser.add_argument('--atr-period', type=int, default=14)
    parser.add_argument('--atr-mult', type=float, default=2)
    parser.add_argument('--kdj-n', type=int, default=9)
    parser.add_argument('--cci-period', type=int, default=14)
    parser.add_argument('--show-days', type=int, default=250, help='图表展示天数')

    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    # 加载数据
    df = load_data(args.input)
    print(f"数据加载完成: {len(df)} 行, 日期范围 {df['trade_date'].min().date()} ~ {df['trade_date'].max().date()}")

    indicators = args.indicators.split(',')
    params = {
        'rsi_period': args.rsi_period,
        'macd_fast': args.macd_fast, 'macd_slow': args.macd_slow, 'macd_signal': args.macd_signal,
        'boll_period': args.boll_period, 'boll_std': args.boll_std,
        'atr_period': args.atr_period, 'atr_mult': args.atr_mult,
        'kdj_n': args.kdj_n,
        'cci_period': args.cci_period,
    }

    if args.task == 'diagnose':
        task_diagnose(df, args.output_dir)
    elif args.task == 'calc':
        task_calc(df, indicators, params, args.output_dir)
    elif args.task == 'charts':
        # charts 需要先 calc
        df, latest = task_calc(df, indicators, params, args.output_dir)
        task_charts(df, indicators, params, args.show_days, args.output_dir)


if __name__ == '__main__':
    main()
