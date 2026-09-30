import requests
import os

# 1. 获取微信推送秘钥
SCT_KEY = os.environ.get("SCT_KEY", "")

# 2. 标的配置池（可为每一只股票/ETF单独设定做T比例）
# buy_ratio: 跌破均线/做T买入的下浮比例 (例如 0.005 代表 0.5%, 0.012 代表 1.2%)
# sell_ratio: 突破均线/做T卖出的上浮比例
STOCKS = {
    'sh512880': {
        'name': '证券ETF国泰', 
        'buy_ratio': 0.005,   # ETF波动小，设为 0.5% (可按需调整为 0.003~0.008)
        'sell_ratio': 0.005
    },
    'sh601899': {
        'name': '紫金矿业', 
        'buy_ratio': 0.012,   # 个股波动较大，设为 1.2%
        'sell_ratio': 0.012
    },
    'sh603888': {
        'name': '新华网', 
        'buy_ratio': 0.015,   # 1.5%
        'sell_ratio': 0.015
    }
}

def analyze_stock(symbol, config):
    name = config['name']
    buy_ratio = config['buy_ratio']
    sell_ratio = config['sell_ratio']

    # 调用新浪财经接口获取最新带有均线(MA5, MA10, MA20)的数据
    url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=5,10,20&datalen=1"
    
    try:
        res = requests.get(url, timeout=10)
        data = res.json()[0]
        
        current_price = float(data['close'])
        ma5 = float(data.get('ma_price5', current_price))
        ma10 = float(data.get('ma_price10', current_price))
        ma20 = float(data.get('ma_price20', current_price))
        
        mas = {'5日均线': ma5, '10日均线': ma10, '20日均线': ma20}
        
        supports = {k: v for k, v in mas.items() if v < current_price}
        pressures = {k: v for k, v in mas.items() if v > current_price}
        
        # 计算做T买点
        if supports:
            buy_line_name = max(supports, key=supports.get)
            buy_price = supports[buy_line_name]
            buy_msg = f"{buy_line_name} ({buy_price:.3f}元)"
        else:
            # 跌破所有均线时，使用该标的专属的下浮网格
            buy_price = current_price * (1 - buy_ratio)
            buy_msg = f"均线下方，参考下浮{buy_ratio*100:.1f}% ({buy_price:.3f}元)"
            
        # 计算做T卖点
        if pressures:
            sell_line_name = min(pressures, key=pressures.get)
            sell_price = pressures[sell_line_name]
            sell_msg = f"{sell_line_name} ({sell_price:.3f}元)"
        else:
            # 突破所有均线时，使用该标的专属的上浮网格
            sell_price = current_price * (1 + sell_ratio)
            sell_msg = f"均线上方，参考上浮{sell_ratio*100:.1f}% ({sell_price:.3f}元)"

        # 组装微信推送文本
        text = f"### 🔹 {name} ({symbol[2:]})\n\n"
        text += f"- **当前价格**: {current_price:.3f} 元\n"
        text += f"- **🟢 做T买点 (低吸)**: 建议在 **{buy_msg}** 附近挂单买入\n"
        text += f"- **🔴 做T卖点 (高抛)**: 建议在 **{sell_msg}** 附近挂单卖出\n"
        text += f"- *(参考指标: MA5={ma5:.3f}, MA10={ma10:.3f}, MA20={ma20:.3f})*\n\n"
        text += "---\n\n"
        return text
        
    except Exception as e:
        return f"### 🔹 {name} 数据获取失败\n\n---\n\n"

def main():
    if not SCT_KEY:
        print("未获取到 SCT_KEY 密钥！")
        return
        
    report_content = "## 📉 动态做T自动化建议 (分标的定制版)\n\n"
    
    for symbol, config in STOCKS.items():
        report_content += analyze_stock(symbol, config)
        
    send_url = f"https://sctapi.ftqq.com/{SCT_KEY}.send"
    data = {
        "title": "股票每日做T自动化建议",
        "desp": report_content
    }
    requests.post(send_url, data=data)
    print("推送任务执行完毕！")

if __name__ == "__main__":
    main()
