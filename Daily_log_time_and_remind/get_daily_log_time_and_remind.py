import json
import logging
import traceback
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

# 确保能引入同级或父级目录的模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from feishu_API_manager import FeishuAPIManager
    import set_rpa_status_sync
except ImportError:
    pass

# --- 配置区 ---
def load_app_config():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(base_dir, '../app_config.json'),
        os.path.join(base_dir, '../..', 'app_config.json'),
        os.path.join(os.getcwd(), '../app_config.json'),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("无法找到 app_config.json")

try:
    app_config = load_app_config()
except Exception:
    app_config = {"APP_ID": "", "APP_SECRET": ""}

CONFIG = {
    "APP_ID": app_config.get("APP_ID"),
    "APP_SECRET": app_config.get("APP_SECRET"),
    "BITABLE_APP_TOKEN": "VfltbrrzAazPq1sZwu3cM6Ognle",
    "BITABLE_TABLE_ID": "tblPOxRNIpCiLIXy",
    "FIELD_SUBMIT_STATUS": "是否当日提交", 
    "FIELD_PERSON": "人员",
    "FIELD_DATE": "日期",
    "REMINDER_CHAT_ID": "oc_aed11d5a664871bbaac3d3967c31a6c8",
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DailyLogTimeReminder:
    def __init__(self):
        self.manager = FeishuAPIManager(CONFIG["APP_ID"], CONFIG["APP_SECRET"])
        self.tz = timezone(timedelta(hours=8))
        now = datetime.now(self.tz)
        
        # 统计起始时间：本月1号
        self.month_start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self.month_start_ts = int(self.month_start_dt.timestamp() * 1000)
        
        # 昨天的时间区间
        self.yesterday_dt = now - timedelta(days=1)
        self.yesterday_str = self.yesterday_dt.strftime('%m.%d')
        self.yesterday_start_ts = int(self.yesterday_dt.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        self.yesterday_end_ts = int(self.yesterday_dt.replace(hour=23, minute=59, second=59, microsecond=999).timestamp() * 1000)

    def recursive_extract_text(self, val: Any) -> str:
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
        if not field_value: return "未知", None
        if isinstance(field_value, dict) and "value" in field_value:
            field_value = field_value["value"]
        if isinstance(field_value, list) and len(field_value) > 0:
            p = field_value[0]
            return p.get("name", "未知"), p.get("id")
        return "未知", None

    def fetch_records(self) -> List[Dict[str, Any]]:
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
                logger.error(f"抓取异常: {e}")
                break
        return all_records

    def run(self):
        records = self.fetch_records()
        if not records: return

        month_raw_items = []
        yesterday_raw_items = []
        month_counts = {}
        yesterday_counts = {}
        yesterday_details = {} 
        yesterday_at_uids = set()

        for fields in records:
            # 1. 日期处理
            raw_date_val = fields.get(CONFIG["FIELD_DATE"])
            if isinstance(raw_date_val, (int, float)):
                ts = int(raw_date_val)
            else:
                ts_str = self.recursive_extract_text(raw_date_val)
                try: ts = int(ts_str) if ts_str else 0
                except: ts = 0
            
            if ts < self.month_start_ts: continue

            # 2. 状态识别
            status_text = self.recursive_extract_text(fields.get(CONFIG["FIELD_SUBMIT_STATUS"]))
            if status_text != "非当天": continue

            name, openid = self.extract_user_info(fields.get(CONFIG["FIELD_PERSON"]))
            user_key = openid if openid else f"name_{name}"
            date_str = datetime.fromtimestamp(ts / 1000, self.tz).strftime('%m.%d')

            # 3. 统计全月
            month_counts[name] = month_counts.get(name, 0) + 1
            month_raw_items.append({"user": name, "item": f"[M] {date_str} 日志", "val": 1})

            # 4. 统计昨日
            if self.yesterday_start_ts <= ts <= self.yesterday_end_ts:
                yesterday_counts[name] = yesterday_counts.get(name, 0) + 1
                yesterday_raw_items.append({"user": name, "item": "日志", "val": 1})
                if openid: yesterday_at_uids.add(openid)
                if user_key not in yesterday_details:
                    yesterday_details[user_key] = {"name": name, "openid": openid, "count": 0}
                yesterday_details[user_key]["count"] += 1

        if not month_counts:
            logger.info("本月暂无日志未提交记录。")
            return

        # 5. 图表数据降序重排
        sorted_month_names = sorted(month_counts.keys(), key=lambda x: month_counts[x], reverse=True)
        month_chart_values = [item for name in sorted_month_names for item in month_raw_items if item["user"] == name]

        sorted_yesterday_names = sorted(yesterday_counts.keys(), key=lambda x: yesterday_counts[x], reverse=True)
        yesterday_chart_values = [item for name in sorted_yesterday_names for item in yesterday_raw_items if item["user"] == name]

        # 6. 构造昨日明细文字
        detail_md = f"**🚨 昨日 ({self.yesterday_str}) 日志超时人员明细：**\n"
        if not yesterday_details:
            detail_md += "昨日无超时数据\n"
        else:
            sorted_y_uids = sorted(yesterday_details.keys(), key=lambda x: yesterday_details[x]["count"], reverse=True)
            for uk in sorted_y_uids:
                info = yesterday_details[uk]
                at_tag = f"<at id={info['openid']}></at>" if info['openid'] else f"**{info['name']}**"
                detail_md += f"{at_tag} 日志超时\n"

        at_header = " ".join([f"<at id={uid}></at>" for uid in sorted(list(yesterday_at_uids))])

        # 7. 组装卡片
        card = {
            "config": {"wide_screen_mode": True},
            "header": {"template": "red", "title": {"content": "⏰ 日志超时行为推送", "tag": "plain_text"}},
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": f"{at_header}\n\n检测到昨日 ({self.yesterday_str}) 共有 **{len(yesterday_counts)}** 人超时提交日志。"}},
                {"tag": "hr"},
                {"tag": "div", "text": {"tag": "lark_md", "content": f"**📌 昨日 ({self.yesterday_str}) 个人超时详情**"}},
                {
                    "tag": "chart",
                    "aspect_ratio": "4:3",
                    "chart_spec": {
                        "type": "pie",
                        "data": {"values": yesterday_chart_values if yesterday_chart_values else [{"user": "全员已交", "val": 0}]},
                        "categoryField": "user",
                        "valueField": "val",
                        "outerRadius": 0.7,
                        "innerRadius": 0.4,
                        "label": {"visible": True, "type": "outer"}
                    }
                },
                {"tag": "hr"},
                {"tag": "div", "text": {"tag": "lark_md", "content": detail_md}},
                {"tag": "hr"},
                {"tag": "div", "text": {"tag": "lark_md", "content": "**📉 本月日志累计超时频次分布**"}},
                {
                    "tag": "chart",
                    "aspect_ratio": "4:3" if len(month_counts) > 10 else "16:9",
                    "chart_spec": {
                        "type": "bar",
                        "data": {"values": month_chart_values},
                        "xField": "user",
                        "yField": "val",
                        "seriesField": "item",
                        "stack": True,
                        "label": {"visible": False}
                    }
                },
                {"tag": "note", "elements": [{"tag": "plain_text", "content": f"统计区间：{self.month_start_dt.strftime('%Y-%m-%d')} 至今 | 昨日数据时间：{self.yesterday_str} | 生成时间：{datetime.now().strftime('%H:%M')}"}]}
            ]
        }

        try:
            self.manager.send_message(CONFIG["REMINDER_CHAT_ID"], json.dumps(card, ensure_ascii=False), "interactive", "chat_id")
            logger.info("统计卡片发送成功。")
        except Exception as e:
            logger.error(f"卡片发送失败: {e}")

def main():
    DailyLogTimeReminder().run()

if __name__ == "__main__":
    try:
        main()
        if hasattr(set_rpa_status_sync, 'main'):
            set_rpa_status_sync.main("日志超时 统计 & 提醒", 1, "神州")
    except Exception as e:
        if hasattr(set_rpa_status_sync, 'main'):
            set_rpa_status_sync.main("日志超时 统计 & 提醒", 0, "神州", traceback.format_exc())
        logger.error(traceback.format_exc())
