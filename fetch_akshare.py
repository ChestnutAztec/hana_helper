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


def safe_fetch(label: str, fn):
    """通用抓取与异常捕获，输出中文字段。"""
    try:
        df = fn()
        if df is None:
            return {"名称": label, "状态": "空", "数据": []}

        df = df.copy()
        df = df.apply(lambda col: col.map(_convert_value))

        return {
            "名称": label,
            "状态": "正常",
            "数据": df.to_dict(orient="records")[:50],
        }
    except Exception as e:
        return {
            "名称": label,
            "状态": "异常",
            "错误": str(e),
            "堆栈": traceback.format_exc(),
            "数据": [],
        }


def fetch_if_exists(label: str, attr: str, *args, **kwargs):
    """检查 akshare 是否有该接口；没有则标记缺失。"""
    if not hasattr(ak, attr):
        return {"名称": label, "状态": "缺失", "数据": [], "错误": f"akshare 无 {attr}"}
    return safe_fetch(label, lambda: getattr(ak, attr)(*args, **kwargs))


def main():
    print("Fetching AkShare A-share data...")

    results = {
        "财联社": fetch_if_exists("财联社-全球快讯", "stock_info_global_cls"),
        "东方财富个股新闻": fetch_if_exists("东方财富-个股新闻", "stock_news_em"),
        "东方财富最新资讯": fetch_if_exists("东方财富-最新资讯", "stock_news_em", symbol="最新资讯"),
        "东方财富个股热度榜": fetch_if_exists("东方财富-个股热度榜", "stock_hot_rank_em"),
        "东方财富热门板块": fetch_if_exists("东方财富-热门板块", "stock_board_concept_name"),
        "央视新闻": fetch_if_exists("央视新闻", "news_cctv"),
        "百度财经": fetch_if_exists("百度财经", "news_economic_baidu"),
        "百度研报时效": fetch_if_exists("百度研报时效", "news_report_time_baidu"),
        "财新要闻": fetch_if_exists("财新要闻", "stock_news_main_cx"),
    }

    output = {
        "更新时间": datetime.now(timezone.utc).isoformat(),
        "数据": results,
    }

    with open("akshare.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Saved to akshare.json")


if __name__ == "__main__":
    main()
