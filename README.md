# AI Quant Lab

AI 驱动的量化投资研究实验室，基于 Tushare 数据，涵盖数据管道、技术指标分析、交互式工具等模块。

## 项目结构

```
ai-quant-lab/
├── data-pipeline/          # 数据获取与预处理管道
│   ├── scripts/            # 取数脚本（全量 / 增量）
│   └── spec/               # 取数规范文件
├── task02-indicator-lab/   # 技术指标分析 Notebook 实验室
│   ├── data/               # 计算后的指标数据
│   └── figures/            # 指标可视化图表
├── task03-indicator-tool/  # 交互式指标工具（HTML/ECharts）
└── requirements.txt        # Python 依赖
```

## 模块说明

### data-pipeline — 数据管道

- `fetch_stock_data.py`：全量取数脚本，支持日/周/月线，含限流退避与网络重试
- `fetch_incremental.py`：增量补数脚本，跳过已存在文件，65s 间隔避免限频
- `stock-data-spec.yaml`：取数规范 v1.1.0，定义字段、频率、输出格式

### task02-indicator-lab — 指标实验室

Jupyter Notebook（22 个 Cell），基于中芯国际港股数据计算并可视化四大技术指标：
- RSI（相对强弱指标）
- MACD（指数平滑异同移动平均线）
- 布林带（Bollinger Bands）
- ATR（平均真实波幅）

### task03-indicator-tool — 交互式指标工具

HTML 原型，基于 ECharts 5：
- 支持多股票切换
- 10 个可调参数滑块（四大指标各 2-3 个）
- 2×2 指标仪表盘 + 信号汇总表

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 Tushare Token

在 `data-pipeline/scripts/fetch_stock_data.py` 中填入你的 Tushare token：

```python
TUSHARE_TOKEN = "你的token"
```

或在环境变量中设置：

```bash
export TUSHARE_TOKEN="你的token"
```

### 运行全量取数

```bash
cd data-pipeline/scripts
python fetch_stock_data.py
```

### 运行增量补数

```bash
cd data-pipeline/scripts
python fetch_incremental.py
```

### 启动 Jupyter Notebook

```bash
cd task02-indicator-lab
jupyter notebook indicator_lab.ipynb
```

### 预览交互式工具

直接用浏览器打开 `task03-indicator-tool/prototype.html`。

## 技术指标说明

| 指标 | 用途 | 默认参数 |
|------|------|----------|
| RSI | 超买超卖判断 | 14 日 |
| MACD | 趋势转折 | 12/26/9 |
| 布林带 | 波动率与压力支撑 | 20 日 / 2σ |
| ATR | 真实波幅（风险管理） | 14 日 |

## 数据来源

[Tushare Pro](https://tushare.pro) — 免费注册获取 Token，部分高频接口需要一定积分。

## 许可证

MIT
