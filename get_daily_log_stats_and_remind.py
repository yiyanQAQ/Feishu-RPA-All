import json
import logging
import traceback
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from feishu_API_manager import FeishuAPIManager
import set_rpa_status_sync

import os

# --- 配置区 ---
def load_app_config():
    config_path = os.path.join(os.path.dirname(__file__), 'app_config.json')
    if not os.path.exists(config_path):
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app_config.json')
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

app_config = load_app_config()

CONFIG = {
    "APP_ID": app_config["APP_ID"],
    "APP_SECRET": app_config["APP_SECRET"],
    "BITABLE_APP_TOKEN": "LQBKbFnCNa2Ze6sQwfscvJSonRe",
    "BITABLE_TABLE_ID": "tblom06hByATyJt9",
    "FIELD_STATUS": "提交情况",
    "FIELD_PERSON": "人员",
    "FIELD_DATE": "日期",
    "FIELD_DEPT": "部门",
    "REMINDER_CHAT_ID": "oc_aed11d5a664871bbaac3d3967c31a6c8",
    "START_DATE": "2026-02-01"
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DailyLogStatsReminder:
    def __init__(self):
        self.manager = FeishuAPIManager(CONFIG["APP_ID"], CONFIG["APP_SECRET"])
        self.start_ts = int(time.mktime(time.strptime(CONFIG["START_DATE"], "%Y-%m-%d"))) * 1000

    def fetch_all_data(self) -> List[Dict[str, Any]]:
        all_records = []
        page_token = None
        while True:
            try:
                resp_data = self.manager.search_records(
                    app_token=CONFIG["BITABLE_APP_TOKEN"],
                    table_id=CONFIG["BITABLE_TABLE_ID"],
                    page_size=500,
                    page_token=page_token
                )
                if resp_data and hasattr(resp_data, "items") and resp_data.items:
                    all_records.extend([item.fields for item in resp_data.items])
                if not resp_data or not getattr(resp_data, "has_more", False):
                    break
                page_token = resp_data.page_token
            except Exception as e:
                logger.error(f"数据抓取异常: {e}")
                break
        return all_records

    def recursive_extract_text(self, val: Any) -> str:
        """递归提取所有文本内容"""
        if val is None: return ""
        if isinstance(val, dict):
            if "value" in val: return self.recursive_extract_text(val["value"])
            if "text" in val: return str(val["text"])
            if "name" in val: return str(val["name"])
            return ""
        if isinstance(val, list):
            return "".join([self.recursive_extract_text(i) for i in val])
        return str(val).strip()

    def extract_user_info(self, field_value: Any):
        if isinstance(field_value, list) and len(field_value) > 0:
            p = field_value[0]
            return p.get("name", "未知"), p.get("id")
        elif isinstance(field_value, dict):
            return field_value.get("name", "未知"), field_value.get("id")
        return "未知", None

    def run(self):
        records = self.fetch_all_data()
        if not records: return

        person_stats = {} # {openid: {name, count, dates}}
        dept_stats = {}   # {dept: {total, unpaid}}
        total_unpaid = 0
        all_unpaid_user_ids = set()

        for fields in records:
            # 日期过滤
            raw_date = fields.get(CONFIG["FIELD_DATE"])
            if not isinstance(raw_date, int) or raw_date < self.start_ts:
                continue

            # 状态提取
            status = self.recursive_extract_text(fields.get(CONFIG["FIELD_STATUS"]))
            
            # 部门名称提取
            dept_raw = fields.get(CONFIG["FIELD_DEPT"])
            dept = self.recursive_extract_text(dept_raw) or "未归类部门"
            
            if dept not in dept_stats: dept_stats[dept] = {"total": 0, "unpaid": 0}
            dept_stats[dept]["total"] += 1

            if "未提交" in status:
                total_unpaid += 1
                dept_stats[dept]["unpaid"] += 1
                name, openid = self.extract_user_info(fields.get(CONFIG["FIELD_PERSON"]))
                date_str = datetime.fromtimestamp(raw_date / 1000).strftime('%m.%d')
                
                if openid:
                    all_unpaid_user_ids.add(openid)
                    if openid not in person_stats:
                        person_stats[openid] = {"name": name, "count": 0, "dates": []}
                    person_stats[openid]["count"] += 1
                    person_stats[openid]["dates"].append(date_str)

        if total_unpaid == 0:
            logger.info("指定时间段内无未提交记录。")
            return

        # 构造JSON卡片消息
        # 堆叠柱状图数据
        chart_values = []
        sorted_user_ids = sorted(person_stats.keys(), key=lambda uid: person_stats[uid]["count"], reverse=True)
        
        for uid in sorted_user_ids:
            info = person_stats[uid]
            for date_str in info["dates"]:
                chart_values.append({
                    "user": info["name"],
                    "date": date_str,
                    "val": 1
                })

        # 个人未交总占比饼图数据
        pie_values = []
        for uid, info in person_stats.items():
            pie_values.append({
                "user": info["name"],
                "count": info["count"]
            })

        # 部门占比Markdown横向图
        def get_bar(percent):
            filled = int(round(percent / 10))
            color = "🟥" if percent > 30 else "🟧" if percent > 10 else "🟩"
            return color * max(1, filled) + "⬜" * (10 - filled) if percent > 0 else "⬜" * 10

        dept_md = "**📊 部门未交占比：**\n"
        for d, s in sorted(dept_stats.items(), key=lambda x: x[1]['unpaid']/x[1]['total'], reverse=True):
            rate = (s["unpaid"] / s["total"]) * 100
            dept_md += f"{d}：{s['unpaid']}/{s['total']} ({rate:.1f}%)\n{get_bar(rate)}\n"

        # 集中@人员
        all_unpaid_user_ids = sorted(list(all_unpaid_user_ids))
        at_header = " ".join([f"<at id={uid}></at>" for uid in all_unpaid_user_ids if uid])

        # 组装卡片
        card = {
            "config": {"wide_screen_mode": True},
            "header": {"template": "red", "title": {"content": "🗓️ 周期性日志未提交统计", "tag": "plain_text"}},
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": f"{at_header}\n\n当前检测到 **{total_unpaid}** 条未提交记录："}},
                {"tag": "hr"},
                                {
                                    "tag": "div",
                                    "text": {"tag": "lark_md", "content": "**📉 个人未交频次分布**"}
                                },
                                                {
                                                    "tag": "chart",
                                                    "aspect_ratio": "4:3" if len(person_stats) > 15 else "16:9",
                                                    "chart_spec": {
                                                        "type": "bar",
                                                        "data": {"values": chart_values},
                                                        "xField": "user",
                                                        "yField": "val",
                                                        "seriesField": "date",
                                                        "stack": True,
                                                        "label": {"visible": False} # 段落太多时不显示数字
                                                    }
                                                },
                                                {"tag": "hr"},
                                                {
                                                    "tag": "div",
                                                    "text": {"tag": "lark_md", "content": "**📌 个人未交占比**"}
                                                },
                                                {
                                                    "tag": "chart",
                                                    "aspect_ratio": "16:9",
                                                    "chart_spec": {
                                                        "type": "pie",
                                                        "data": {"values": pie_values},
                                                        "categoryField": "user",
                                                        "valueField": "count",
                                                        "outerRadius": 0.8,
                                                        "innerRadius": 0.5,
                                                        "label": {"visible": True, "type": "outer"}
                                                    }
                                                },
                                                {"tag": "hr"},
                                
                {"tag": "div", "text": {"tag": "lark_md", "content": dept_md}},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": f"统计范围：2026-02-01 至 今日 | 生成时间：{datetime.now().strftime('%H:%M')}"}]}
            ]
        }

        try:
            self.manager.send_message(CONFIG["REMINDER_CHAT_ID"], json.dumps(card, ensure_ascii=False), "interactive", "chat_id")
            logger.info("综合统计卡片发送成功。")
        except Exception as e:
            logger.error(f"卡片发送失败: {e}")

def main():
    DailyLogStatsReminder().run()

try:
    if __name__ == "__main__": main()
    set_rpa_status_sync.main("每日日志 统计 & 提醒", 1, "神州")
except Exception as e:
    set_rpa_status_sync.main("每日日志 统计 & 提醒", 0, "神州", traceback.format_exc())
