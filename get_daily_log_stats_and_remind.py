import json
import logging
import re
import traceback
from typing import List, Dict, Any, Optional
from feishu_API_manager import FeishuAPIManager
import set_rpa_status_sync

# --- 配置区 ---
CONFIG = {
    "APP_ID": "cli_a9edd60855a35bd7",
    "APP_SECRET": "",

    # 多维表配置
    "BITABLE_APP_TOKEN": "LQBKbFnCNa2Ze6sQwfscvJSonRe",
    "BITABLE_TABLE_ID": "tbluLeSFKLy4wt64",

    # 提醒配置
    "REMINDER_CHAT_ID": "oc_aed11d5a664871bbaac3d3967c31a6c8",
    "TARGET_FIELD": "昨日-每日汇报",
    "MESSAGE": "昨日日志未提交 or 未审核，请及时补交 or 催审。"
}

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WorkElementReminder:
    def __init__(self):
        self.manager = FeishuAPIManager(CONFIG["APP_ID"], CONFIG["APP_SECRET"])
        self.app_token = CONFIG["BITABLE_APP_TOKEN"]
        self.table_id = CONFIG["BITABLE_TABLE_ID"]

    def get_first_record(self) -> Optional[Dict[str, Any]]:
        """获取多维表中的第一条记录"""
        logger.info("正在获取多维表的第一条记录...")
        
        TARGET_FIELD = CONFIG["TARGET_FIELD"]
        
        try:
            # 只获取第一页，甚至可以只获取 1 条
            resp_data = self.manager.search_records(
                app_token=self.app_token,
                table_id=self.table_id,
                page_size=1, 
                field_names=[TARGET_FIELD]
            )
            
            if resp_data and resp_data.items:
                item = resp_data.items[0]
                logger.info(f"获取到记录: {item.record_id}")
                return item.fields
            else:
                logger.warning("多维表中没有记录。")
                return None

        except Exception as e:
            logger.error(f"获取多维表记录失败: {e}")
            return None

    def extract_user_ids(self, field_value: Any) -> List[str]:
        """从字段值中提取Open ID"""
        logger.info(f"原始字段值类型: {type(field_value)}")
        # logger.info(f"原始字段值内容: {field_value}")
        
        user_ids = []

        if isinstance(field_value, dict):
            value_list = field_value.get("value")
            if isinstance(value_list, list):
                for item in value_list:
                    if isinstance(item, dict):
                        uid = item.get("id")
                        if uid: user_ids.append(uid)

        elif isinstance(field_value, list):
            for item in field_value:
                if isinstance(item, dict):
                    uid = item.get("id")
                    if uid: user_ids.append(uid)
        
        logger.info(f"提取到的用户 ID 数量: {len(user_ids)}")
        return user_ids

    def run(self):
        fields = self.get_first_record()
        if not fields:
            return

        target_field_value = fields.get(CONFIG["TARGET_FIELD"])
        if not target_field_value:
            logger.info(f"字段 '{CONFIG['TARGET_FIELD']}' 为空，无需提醒。")
            return
            
        user_ids_to_remind = self.extract_user_ids(target_field_value)
        
        if not user_ids_to_remind:
            logger.warning("未提取到任何有效用户 ID。")
            return

        at_tags = []
        for uid in user_ids_to_remind:
            at_tags.append(f'<at user_id="{uid}"></at>')
        
        full_message = " ".join(at_tags) + f" {CONFIG['MESSAGE']}"

        chat_id = CONFIG["REMINDER_CHAT_ID"]
        try:
            self.manager.send_message(
                receive_id=chat_id,
                content=full_message,
                msg_type="text",
                receive_id_type="chat_id"
            )
            logger.info("提醒消息发送成功！")
        except Exception as e:
            logger.error(f"发送失败: {e}")


def main():
    reminder = WorkElementReminder()
    reminder.run()

try:
    if __name__ == "__main__":
        main()
    set_rpa_status_sync.main("交表情况 统计 & 提醒", 1, "神州")
except Exception as e:
    full_error_msg = traceback.format_exc()
    set_rpa_status_sync.main("交表情况 统计 & 提醒", 0, "神州", full_error_msg)