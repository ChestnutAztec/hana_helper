#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import traceback
from datetime import date, datetime, time, timezone

import pandas as pd

import akshare as ak


def _convert_value(val):
    if val is pd.NaT:
        return None
    if isinstance(val, pd.Timestamp):
        return val.to_pydatetime().isoformat()
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, time):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    return val


def safe_fetch(name, fn):
    """获取接口并捕获异常，保证脚本不会崩"""
    try:
        df = fn()
        if df is None:
            return {"name": name, "status": "empty", "items": []}

        df = df.copy()
        # Use map over series to avoid applymap deprecation
        df = df.apply(lambda col: col.map(_convert_value))

        return {
            "name": name,
            "status": "ok",
            "items": df.to_dict(orient="records")[:50],
        }
    except Exception as e:
        return {
            "name": name,
            "status": "error",
            "error": str(e),
            "trace": traceback.format_exc(),
            "items": [],
        }


def main():
    print("Fetching AkShare A-share data...")

    results = {}

    results["eastmoney_news"] = safe_fetch("东方财富-财经要闻", lambda: ak.news_eastmoney())
    results["eastmoney_stock_news"] = safe_fetch("东方财富-个股新闻", lambda: ak.stock_news_em())
    results["ths_7x24"] = safe_fetch("同花顺-7x24快讯", lambda: ak.stock_news_7x24_ths())
    results["stcn_news"] = safe_fetch("证券时报-要闻", lambda: ak.stock_news_stcn())
    results["sse_news"] = safe_fetch("上海证券报-要闻", lambda: ak.stock_news_sh())
    results["szse_news"] = safe_fetch("深圳证券报-要闻", lambda: ak.stock_news_sz())
    results["cninfo_notices"] = safe_fetch("巨潮-公司公告", lambda: ak.stock_notice_with_filters_em(date=None))
    results["eastmoney_focus"] = safe_fetch("东方财富-大盘焦点", lambda: ak.stock_news_em(symbol="最新资讯"))
    results["cailianpress"] = safe_fetch("财联社-全球快讯", lambda: ak.stock_info_global_cls())

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }

    with open("akshare.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Saved to akshare.json")


if __name__ == "__main__":
    main()
