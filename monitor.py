import requests
import os
import json

# 1. 获取微信推送秘钥
SCT_KEY = os.environ.get("SCT_KEY", "")

# 2. 你的自选股票池 (sh代表上交所, sz代表深交所)
STOCKS = {
    'sh601899': '紫金矿业',
    'sh512880': '证券ETF国泰',
    'sh603888': '新华网'
}

def analyze_stock(symbol, name):
    # 调用新浪财经接口获取最新带有均线(MA5, MA10, MA20)的日K数据
    url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=5,10,20&datalen=1"
    
    try:
        res = requests.get(url, timeout=10)
        data = res.json()[0] # 提取今天的最新数据
        
        current_price = float(data['close'])
        # 获取接口自动算好的均价
        ma5 = float(data.get('ma_price5', current_price))
        ma10 = float(data.get('ma_price10', current_price))
        ma20 = float(data.get('ma_price20', current_price))
        
        # 整理均线字典
        mas = {'5日均线': ma5, '10日均线': ma10, '20日均线': ma20}
        
        # 筛选支撑位(在现价下方)和压力位(在现价上方)
        supports = {k: v for k, v in mas.items() if v < current_price}
        pressures = {k: v for k, v in mas.items() if v > current_price}
        
        # 计算做T买点（最靠近现价下方的均线支撑）
        if supports:
            # 找到数值最大的那条支撑线(离现价最近)
            buy_line_name = max(supports, key=supports.get)
            buy_price = supports[buy_line_name]
            buy_msg = f"{buy_line_name} ({buy_price:.3f}元)"
        else:
            # 如果跌破所有均线，默认用现价下浮2%作为左侧极限买点
            buy_price = current_price * 0.98
            buy_msg = f"所有均线跌破，参考下浮2% ({buy_price:.3f}元)"
            
        # 计算做T卖点（最靠近现价上方的均线压力）
        if pressures:
            # 找到数值最小的那条压力线(离现价最近)
            sell_line_name = min(pressures, key=pressures.get)
            sell_price = pressures[sell_line_name]
            sell_msg = f"{sell_line_name} ({sell_price:.3f}元)"
        else:
            # 如果突破所有均线，默认用现价上浮2%作为止盈卖点
            sell_price = current_price * 1.02
            sell_msg = f"强势突破均线，参考上浮2% ({sell_price:.3f}元)"

        # 组装单只股票的微信推送文本
        text = f"### 🔹 {name} ({symbol[2:]})\n\n"
        text += f"- **当前价格**: {current_price:.3f} 元\n"
        text += f"- **🟢 做T买点 (低吸)**: 建议在 **{buy_msg}** 附近挂单买入\n"
        text += f"- **🔴 做T卖点 (高抛)**: 建议在 **{sell_msg}** 附近挂单卖出\n"
        text += f"- *(今日指标参考: MA5={ma5:.3f}, MA10={ma10:.3f}, MA20={ma20:.3f})*\n\n"
        text += "---\n\n"
        return text
        
    except Exception as e:
        return f"### 🔹 {name} 自动分析失败，请检查代码或网络\n\n---\n\n"

def main():
    if not SCT_KEY:
        print("未获取到 SCT_KEY 密钥，无法推送到微信！")
        return
        
    report_content = "## 📉 均线动态做T自动化建议\n\n"
    
    # 遍历计算每一只股票
    for symbol, name in STOCKS.items():
        report_content += analyze_stock(symbol, name)
        
    # 发送到微信 (Server酱)
    send_url = f"https://sctapi.ftqq.com/{SCT_KEY}.send"
    data = {
        "title": "股票每日做T自动化建议",
        "desp": report_content
    }
    requests.post(send_url, data=data)
    print("推送任务执行完毕！")

if __name__ == "__main__":
    main()
