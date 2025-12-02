# News Aggregator to GitHub Pages

抓取财联社、新浪财经、巨潮资讯、雪球新闻，合并为 `news.json`，通过 GitHub Actions 每 10 分钟自动更新，GitHub Pages 对外提供 JSON。

## 使用方式
1. Fork 本仓库。
2. 在仓库 Settings → Pages，将 Source 设为 `main` 分支根目录，保存后页面地址类似 `https://<username>.github.io/<repo>/news.json`。
3. （可选）在 Settings → Secrets and variables → Actions 新建 `XQ_TOKEN`，值为雪球 `xq_a_token`（未设置可能请求失败或被限流）。
4. 手动运行一次 Actions：`Actions → Fetch News → Run workflow`；之后每 10 分钟自动运行。
5. 直接访问 `https://<username>.github.io/<repo>/news.json` 获取最新 JSON。

## 本地运行
```bash
pip install akshare pysnowball feedparser pandas requests
export XQ_TOKEN="xq_a_token=xxxxx"  # 可选
python scripts/fetch_news.py
cat news.json
```

## 输出格式
`news.json` 为数组，每条包含：
```json
{
  "source": "财经来源",
  "title_zh": "标题",
  "link": "URL",
  "pubDate": "ISO8601 UTC 时间"
}
```

## 依赖
- Python 3.11+
- akshare, pysnowball, feedparser, pandas, requests

## Cloudflare Worker 示例
```javascript
export default {
  async fetch(request) {
    const url = "https://<username>.github.io/<repo>/news.json";
    const resp = await fetch(url, { cf: { cacheTtl: 300, cacheEverything: true } });
    return new Response(await resp.text(), {
      status: resp.status,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  },
};
```
