import logging
import traceback
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from feishu_API_manager import FeishuAPIManager
import set_rpa_status_sync

# --- 配置区域 ---
CONFIG = {
    "APP_ID": "cli_a9edd60855a35bd7",
    "APP_SECRET": "",
    "TZ_OFFSET": 8,
    
    # 多维表配置
    "BITABLE_APP_TOKEN": "OD1VbarIWasTz1sNnpdcszQfnuh",
    "BITABLE_TABLE_ID": "tblZJpyamcZqkH2p",
    
    # 提醒群ID
    "CHAT_ID": "oc_aed11d5a664871bbaac3d3967c31a6c8",
    
    # 字段名称配置
    "FIELD_DATE": "日期",
    "FIELD_STATUS": "未交",
    "FIELD_TABLE_NAME": "表格名称",
    "FIELD_PERSON": "交表人"
}

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LogChecker:
    def __init__(self):
        self.manager = FeishuAPIManager(CONFIG["APP_ID"], CONFIG["APP_SECRET"])
        self.tz = timezone(timedelta(hours=CONFIG["TZ_OFFSET"]))

    def get_records_in_range(self) -> List[Dict[str, Any]]:
        """获取本月（1号到今天）的所有记录"""
        now = datetime.now(self.tz)
        start_dt = now.replace(day=1).date() # 本月第一天
        end_dt = now.date()                  # 今天
        
        logger.info(f"正在获取本月 ({start_dt} 到 {end_dt}) 之间的记录...")
        
        target_records = []
        page_token = None
        
        # 需获取的字段列表
        field_names = [
            CONFIG["FIELD_DATE"], 
            CONFIG["FIELD_STATUS"], 
            CONFIG["FIELD_TABLE_NAME"], 
            CONFIG["FIELD_PERSON"]
        ]
        
        while True:
            try:
                resp_data = self.manager.search_records(
                    app_token=CONFIG["BITABLE_APP_TOKEN"],
                    table_id=CONFIG["BITABLE_TABLE_ID"],
                    page_size=100,
                    page_token=page_token,
                    field_names=field_names
                )
                
                if not resp_data or not resp_data.items:
                    break
                
                for item in resp_data.items:
                    fields = item.fields
                    record_date_val = fields.get(CONFIG["FIELD_DATE"])
                    
                    # 解析记录日期
                    record_dt = None
                    if isinstance(record_date_val, int):
                        record_dt = datetime.fromtimestamp(record_date_val / 1000, self.tz).date()
                    elif isinstance(record_date_val, str):
                        try:
                            # 解析常见日期格式
                            for fmt in ["%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d"]:
                                try:
                                    record_dt = datetime.strptime(record_date_val, fmt).date()
                                    break
                                except ValueError:
                                    continue
                        except ValueError:
                            pass

                    if record_dt and start_dt <= record_dt <= end_dt:
                        target_records.append(item)

                if not resp_data.has_more:
                    break
                page_token = resp_data.page_token
            except Exception as e:
                logger.error(f"获取记录失败: {e}")
                break
                
        logger.info(f"共找到 {len(target_records)} 条本月的记录")
        return target_records

    def extract_user_id(self, person_field):
        """从人员字段提取Open ID"""
        if isinstance(person_field, list) and len(person_field) > 0:
            p = person_field[0]
            if isinstance(p, dict):
                return p.get("id")
        return None

    def extract_text(self, field_value):
        """从多维表字段中提取纯文本"""
        if isinstance(field_value, list):
            texts = []
            for item in field_value:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        texts.append(text)
                elif isinstance(item, str):
                    texts.append(item)
            return "".join(texts) # 或者用逗号连接，视情况而定
        elif isinstance(field_value, str):
            return field_value
        return str(field_value) if field_value is not None else ""

    def run(self):
        records = self.get_records_in_range()
        if not records:
            logger.info("没有找到本月的记录。")
            return

        # 统计未提交情况
        missing_items = {}

        for item in records:
            fields = item.fields
            status = fields.get(CONFIG["FIELD_STATUS"])
            
            # 检查未交字段是否为1
            if status == 1:
                user_id = self.extract_user_id(fields.get(CONFIG["FIELD_PERSON"]))
                if user_id:
                    date_val = fields.get(CONFIG["FIELD_DATE"])

                    raw_table_name = fields.get(CONFIG["FIELD_TABLE_NAME"])
                    table_name = self.extract_text(raw_table_name)

                    date_str = ""
                    if isinstance(date_val, int):
                        date_str = datetime.fromtimestamp(date_val / 1000, self.tz).strftime('%Y.%m.%d')
                    elif isinstance(date_val, str):
                        date_str = date_val
                    
                    item_str = f"{date_str}{table_name}"
                    
                    if user_id not in missing_items:
                        missing_items[user_id] = []
                    missing_items[user_id].append(item_str)

        # 发送提醒
        if not missing_items:
            logger.info("本月所有记录均已提交，无需提醒。")
            return

        logger.info("开始发送提醒...")
        chat_id = CONFIG["CHAT_ID"]
        
        for user_id, items in missing_items.items():
            items.sort()
            
            at_tag = f'<at user_id="{user_id}"></at>'
            
            if len(items) > 1:
                # 多个未交
                items_str = "，\n".join(items)
                msg = f"{at_tag}\n{items_str}\n\n多表未交，请及时提交 or 找IT核对"
            else:
                # 单个未交
                msg = f"{at_tag}\n{items[0]}\n\n未交，请及时提交 or 找IT核对"
            
            try:
                self.manager.send_message(
                    receive_id=chat_id,
                    content=msg,
                    msg_type="text",
                    receive_id_type="chat_id"
                )
                logger.info(f"已发送提醒给用户 {user_id}: {items}")
            except Exception as e:
                logger.error(f"发送失败: {e}")

        logger.info("任务完成。")
try:
    if __name__ == "__main__":
        main_checker = LogChecker()
        main_checker.run()
    set_rpa_status_sync.main("交表情况 统计 & 提醒", 1, "神州")
except Exception as e:
    full_error_msg = traceback.format_exc()
    set_rpa_status_sync.main("交表情况 统计 & 提醒", 0, "神州", full_error_msg)