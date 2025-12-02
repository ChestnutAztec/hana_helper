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
        # 东方财富新闻接口当前存在返回格式问题（JSONDecodeError），暂时标记为跳过
        "东方财富个股新闻": {
            "名称": "东方财富-个股新闻",
            "状态": "跳过",
            "错误": "官方接口返回格式异常，已临时跳过",
            "数据": [],
        },
        "东方财富最新资讯": {
            "名称": "东方财富-最新资讯",
            "状态": "跳过",
            "错误": "官方接口返回格式异常，已临时跳过",
            "数据": [],
        },
        "东方财富个股热度榜": fetch_if_exists("东方财富-个股热度榜", "stock_hot_rank_em"),
        # 概念热门接口在当前 AkShare 版本缺失
        "东方财富热门板块": {
            "名称": "东方财富-热门板块",
            "状态": "缺失",
            "错误": "akshare 无 stock_board_concept_name 接口",
            "数据": [],
        },
        "央视新闻": fetch_if_exists("央视新闻", "news_cctv"),
        # 百度财经类接口在云端经常 403 取不到 Cookie，改为跳过
        "百度财经": {
            "名称": "百度财经",
            "状态": "跳过",
            "错误": "云端获取百度 Cookie 403，已临时跳过",
            "数据": [],
        },
        "百度研报时效": {
            "名称": "百度研报时效",
            "状态": "跳过",
            "错误": "云端获取百度 Cookie 403，已临时跳过",
            "数据": [],
        },
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
