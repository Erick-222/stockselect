# A股选股系统

这是一个基于 Streamlit 的 A股选股系统，支持：
- 拉取沪深股票历史数据和财务数据
- 筛选条件：PE/PB、归母净利润增长率、营业收入增长率、价格区间、行业等
- Excel 导出

## 部署
1. 将仓库上传到 GitHub。
2. 登录 [Streamlit Cloud](https://share.streamlit.io)
3. 新建 App，选择 `stock_selector_app.py` 作为主文件。
4. 点击 Deploy 即可获得在线网址。

## 使用
- 点击 "🔄 更新数据库" 更新 Excel 数据
- 在侧边栏设置筛选条件
- 查看筛选结果并可导出 Excel