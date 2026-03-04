import json
import logging
import traceback
import time
from datetime import datetime, timedelta, timezone
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
    "BITABLE_APP_TOKEN": "OD1VbarIWasTz1sNnpdcszQfnuh",
    "BITABLE_TABLE_ID": "tblZJpyamcZqkH2p",
    "FIELD_STATUS": "未交", # 1代表未交
    "FIELD_PERSON": "交表人",
    "FIELD_DATE": "日期",
    "FIELD_TABLE_NAME": "表格名称",
    "REMINDER_CHAT_ID": "oc_aed11d5a664871bbaac3d3967c31a6c8",
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SubmissionStatusReminder:
    def __init__(self):
        self.manager = FeishuAPIManager(CONFIG["APP_ID"], CONFIG["APP_SECRET"])
        self.tz = timezone(timedelta(hours=8))
        # 统计起始时间
        now = datetime.now(self.tz)
        self.start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self.start_ts = int(self.start_dt.timestamp() * 1000)

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
        if isinstance(field_value, list) and len(field_value) > 0:
            p = field_value[0]
            return p.get("name", "未知"), p.get("id")
        elif isinstance(field_value, dict):
            return field_value.get("name", "未知"), field_value.get("id")
        return "未知", None

    def fetch_records(self) -> List[Dict[str, Any]]:
        all_records = []
        page_token = None
        logger.info(f"正在从 {self.start_dt.strftime('%Y-%m-%d')} 开始检索记录...")
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

        person_stats = {} # {openid: {name, count, details: {date: [tables]}}}
        total_unpaid = 0
        all_unpaid_user_ids = set()

        for fields in records:
            # 日期过滤
            raw_date = fields.get(CONFIG["FIELD_DATE"])
            if not isinstance(raw_date, int) or raw_date < self.start_ts:
                continue

            # 状态检查 (1未交)
            status = fields.get(CONFIG["FIELD_STATUS"])
            if status != 1:
                continue

            name, openid = self.extract_user_info(fields.get(CONFIG["FIELD_PERSON"]))
            
            # 如果没有openid，则使用姓名作为唯一标识，或者标记为未知
            user_key = openid if openid else f"name_{name}"
            
            total_unpaid += 1
            table_name = self.recursive_extract_text(fields.get(CONFIG["FIELD_TABLE_NAME"])) or "未知表格"
            date_str = datetime.fromtimestamp(raw_date / 1000, self.tz).strftime('%m.%d')

            if openid:
                all_unpaid_user_ids.add(openid)
            
            if user_key not in person_stats:
                person_stats[user_key] = {"name": name, "count": 0, "details": {}, "is_valid_user": bool(openid)}
            
            person_stats[user_key]["count"] += 1
            if date_str not in person_stats[user_key]["details"]:
                person_stats[user_key]["details"][date_str] = []
            person_stats[user_key]["details"][date_str].append(table_name)

        if total_unpaid == 0:
            logger.info("本月记录均已提交。")
            return

        # 构造JSON卡片消息
        # 堆叠柱状图数据
        chart_values = []
        pie_values = []
        sorted_uids = sorted(person_stats.keys(), key=lambda x: person_stats[x]["count"], reverse=True)
        
        for uid in sorted_uids:
            info = person_stats[uid]
            pie_values.append({"user": info["name"], "count": info["count"]})
            for d_str, tables in info["details"].items():
                for t_name in tables:
                    chart_values.append({
                        "user": info["name"],
                        "item": f"{d_str} {t_name}",
                        "val": 1
                    })

        # 构造Markdown格式统计数据
        detail_md = "**📝 未交表项明细：**\n"
        for user_key in sorted_uids:
            info = person_stats[user_key]
            
            if info.get("is_valid_user"):
                at_tag = f"<at id={user_key}></at>"
            else:
                at_tag = f"**{info['name']}** (未关联飞书ID)"
                
            items_list = []
            for d_str, tables in sorted(info["details"].items()):
                items_list.append(f"{d_str}({','.join(tables)})")
            detail_md += f"{at_tag} 共 **{info['count']}** 份: {' '.join(items_list)}\n"

        # 组装卡片
        at_header = " ".join([f"<at id={uid}></at>" for uid in sorted(list(all_unpaid_user_ids))])
        
        card = {
            "config": {"wide_screen_mode": True},
            "header": {"template": "orange", "title": {"content": "📊 本月交表情况追踪报告", "tag": "plain_text"}},
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": f"{at_header}\n\n当前检测到 **{total_unpaid}** 项表格尚未提交："}},
                {"tag": "hr"},
                {"tag": "div", "text": {"tag": "lark_md", "content": "**📉 个人未交频次分布**"}},
                {
                    "tag": "chart",
                    "aspect_ratio": "4:3" if len(person_stats) > 10 else "16:9",
                    "chart_spec": {
                        "type": "bar",
                        "data": {"values": chart_values},
                        "xField": "user",
                        "yField": "val",
                        "seriesField": "item",
                        "stack": True,
                        "label": {"visible": False}
                    }
                },
                {"tag": "hr"},
                {"tag": "div", "text": {"tag": "lark_md", "content": "**📌 个人交表延误权重分析**"}},
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
                {"tag": "div", "text": {"tag": "lark_md", "content": detail_md}},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": f"统计区间：{self.start_dt.strftime('%Y-%m-%d')} 至今 | 生成时间：{datetime.now().strftime('%H:%M')}"}]}
            ]
        }

        try:
            self.manager.send_message(CONFIG["REMINDER_CHAT_ID"], json.dumps(card, ensure_ascii=False), "interactive", "chat_id")
            logger.info("交表统计卡片发送成功。")
        except Exception as e:
            logger.error(f"卡片发送失败: {e}")

def main():
    SubmissionStatusReminder().run()

try:
    if __name__ == "__main__": main()
    set_rpa_status_sync.main("交表情况 统计 & 提醒", 1, "神州")
except Exception as e:
    set_rpa_status_sync.main("交表情况 统计 & 提醒", 0, "神州", traceback.format_exc())
