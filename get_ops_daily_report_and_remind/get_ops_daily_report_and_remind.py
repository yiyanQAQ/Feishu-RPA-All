import json
import logging
import re
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone, time
from typing import List, Dict, Any, Optional

import set_rpa_status_sync
from feishu_API_manager import FeishuAPIManager

# --- 默认配置 ---
DEFAULT_CONFIG = {
    "APP_ID": "cli_a9edd60855a35bd7",
    "APP_SECRET": "",
    "TZ_OFFSET": 8,
    "BITABLE_APP_TOKEN": "CmhSbOMbaapACXs4TbGcvSU3nVf",
    "BITABLE_TABLE_ID": "tbl4G3myGhXYooNn",
}

DEFAULT_RULES = [
    {
        "name": "组长通知群-早上好接龙",
        "chat_id": "oc_096fd9c5ecd898c4d63a77403af48515",
        "regex": r"已发.*早上好",
        "deadline": "08:41",
        "field_time": "早上好接龙时间",
        "field_status": "早上好是否接龙/超时"
    },
    {
        "name": "组长通知群-日报接龙",
        "chat_id": "oc_096fd9c5ecd898c4d63a77403af48515",
        "regex": r"已发.*日报",
        "deadline": "09:31",
        "field_time": "日报接龙时间",
        "field_status": "日报是否接龙/超时"
    },
    {
        "name": "所有运营专员群-早上好接龙",
        "chat_id": "oc_a491ce9eb59cc955e3c693d865a982c0",
        "regex": r"已发.*早上好.*",
        "deadline": "08:41",
        "field_time": "早上好接龙时间",
        "field_status": "早上好是否接龙/超时"
    }
]

# 配置文件路径
CONFIG_FILE_NAME = "config_get_chat_history.json"
USER_HOME = os.path.expanduser("~")
CONFIG_PATH = os.path.join(USER_HOME, CONFIG_FILE_NAME)

# 全局变量
CONFIG = {}
RULES = []

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    global CONFIG, RULES
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                CONFIG = data.get("CONFIG", DEFAULT_CONFIG)
                RULES = data.get("RULES", DEFAULT_RULES)
                logger.info(f"已加载配置文件: {CONFIG_PATH}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，将使用默认配置")
            CONFIG = DEFAULT_CONFIG
            RULES = DEFAULT_RULES
    else:
        logger.info(f"配置文件不存在，使用默认配置并创建文件: {CONFIG_PATH}")
        CONFIG = DEFAULT_CONFIG
        RULES = DEFAULT_RULES
        save_config()

def save_config():
    data = {
        "CONFIG": CONFIG,
        "RULES": RULES
    }
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"配置已保存至: {CONFIG_PATH}")
    except Exception as e:
        logger.error(f"保存配置文件失败: {e}")

class BitableService:
    def __init__(self, manager: FeishuAPIManager):
        self.manager = manager
        self.app_token = CONFIG["BITABLE_APP_TOKEN"]
        self.table_id = CONFIG["BITABLE_TABLE_ID"]

    def get_today_records_map(self, target_date_str: str) -> Dict[str, str]:
        """返回 {姓名: record_id}"""
        logger.info(f"正在获取多维表记录 (目标日期: {target_date_str})...")
        name_record_map = {}
        page_token = None
        
        while True:
            resp_data = self.manager.search_records(
                app_token=self.app_token,
                table_id=self.table_id,
                page_size=100,
                page_token=page_token,
                field_names=["姓名", "日期"]
            )
            
            if not resp_data or not resp_data.items:
                break

            for item in resp_data.items:
                fields = item.fields
                record_id = item.record_id
                raw_name = fields.get("姓名")
                record_date = fields.get("日期")
                
                name = self._extract_name(raw_name)
                if not name: continue
                
                if self._is_date_match(record_date, target_date_str):
                    name_record_map[name] = record_id

            if not resp_data.has_more:
                break
            page_token = resp_data.page_token
            
        logger.info(f"找到 {len(name_record_map)} 条匹配今天日期的记录")
        return name_record_map

    def get_today_full_records(self, target_date_str: str) -> List[Dict[str, Any]]:
        """获取今天的完整记录"""
        logger.info(f"正在获取多维表完整记录以检查空值...")
        records = []
        page_token = None
        
        while True:
            resp_data = self.manager.search_records(
                app_token=self.app_token,
                table_id=self.table_id,
                page_size=100,
                page_token=page_token,
                # 获取所有相关字段
                field_names=["姓名", "日期", "早上好接龙时间", "日报接龙时间"]
            )
            
            if not resp_data or not resp_data.items:
                break

            for item in resp_data.items:
                fields = item.fields
                record_date = fields.get("日期")
                
                if self._is_date_match(record_date, target_date_str):
                    # 提取纯文本姓名
                    fields["_parsed_name"] = self._extract_name(fields.get("姓名"))
                    records.append(fields)

            if not resp_data.has_more:
                break
            page_token = resp_data.page_token
            
        return records

    def _extract_name(self, raw_name):
        name = ""
        if isinstance(raw_name, list):
            if len(raw_name) > 0:
                first_item = raw_name[0]
                if isinstance(first_item, dict):
                    name = first_item.get("text") or first_item.get("name") or ""
                elif isinstance(first_item, str):
                    name = first_item
        elif isinstance(raw_name, str):
            name = raw_name
        return name

    def _is_date_match(self, record_date, target_date_str):
        if isinstance(record_date, int):
            dt = datetime.fromtimestamp(record_date / 1000, timezone(timedelta(hours=8)))
            return dt.strftime('%Y-%m-%d') == target_date_str
        elif isinstance(record_date, str):
            return record_date.startswith(target_date_str)
        return False

    def update_record_fields(self, record_id: str, fields: Dict[str, Any]):
        try:
            self.manager.update_record(self.app_token, self.table_id, record_id, fields)
            logger.info(f"记录 {record_id} 更新成功: {fields}")
        except Exception as e:
            logger.error(f"记录 {record_id} 更新失败: {e}")


class ChatHistoryService:
    def __init__(self, manager: FeishuAPIManager):
        self.manager = manager
        self.tz = timezone(timedelta(hours=CONFIG["TZ_OFFSET"]))

    def get_all_members_map(self, chat_id: str) -> Dict[str, str]:
        """返回 {open_id: name}"""
        logger.info(f"正在获取群 {chat_id} 成员列表...")
        id_map = {}
        page_token = None
        
        try:
            while True:
                resp_data = self.manager.get_chat_members(
                    chat_id=chat_id,
                    page_size=100,
                    page_token=page_token,
                )
                
                if not resp_data or not resp_data.items:
                    break

                for item in resp_data.items:
                    id_map[item.member_id] = item.name
                
                if not resp_data.has_more:
                    break
                page_token = resp_data.page_token
            logger.info(f"已获取 {len(id_map)} 位群成员信息")
        except Exception as e:
            logger.warning(f"获取群成员失败: {e}")
            
        return id_map

    def get_today_messages(self, chat_id: str) -> List[Any]:
        start_ts, end_ts = self._get_today_timestamp_range()
        logger.info(f"正在获取群 {chat_id} 今日消息...")
        all_messages = []
        page_token = None
        MAX_PAGES = 100

        for _ in range(MAX_PAGES):
            resp_data = self.manager.list_messages(
                container_id=chat_id,
                start_time=str(start_ts),
                end_time=str(end_ts),
                page_size=50,
                page_token=page_token
            )
            if not resp_data or not resp_data.items: break
            all_messages.extend(resp_data.items)
            if not resp_data.has_more: break
            if resp_data.page_token == page_token: break
            page_token = resp_data.page_token
        
        logger.info(f"成功获取 {len(all_messages)} 条消息")
        return all_messages

    def send_reminder(self, chat_id: str, text_content: str):
        """发送提醒消息"""
        try:
            self.manager.send_message(
                receive_id=chat_id,
                content=text_content,
                msg_type="text",
                receive_id_type="chat_id"
            )
            logger.info(f"已发送提醒消息到群 {chat_id}: {text_content}")
        except Exception as e:
            logger.error(f"发送提醒消息失败: {e}")

    def _get_today_timestamp_range(self):
        now = datetime.now(self.tz)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return int(start.timestamp()), int(end.timestamp())

    @staticmethod
    def parse_content(msg_type: str, content_json: str) -> str:
        try:
            data = json.loads(content_json)
        except json.JSONDecodeError:
            return ""
        texts = []
        if msg_type == 'text': return data.get('text', '')
        elif msg_type == 'post':
            if title := data.get('title'): texts.append(title)
            for line in data.get('content', []):
                for item in line:
                    if item.get('tag') == 'text': texts.append(item.get('text', ''))
        elif msg_type == 'interactive':
             elements = data.get('elements', [])
             stack = elements if isinstance(elements, list) else []
             while stack:
                 item = stack.pop(0)
                 if isinstance(item, list): stack = item + stack
                 elif isinstance(item, dict):
                     if item.get('tag') == 'text': texts.append(item.get('text', ''))
                     if 'elements' in item: stack = item['elements'] + stack
        return "".join(texts)


def check_and_send_reminders(chat_service: ChatHistoryService, bitable_service: BitableService, today_str: str):
    """检查空值并发送提醒"""
    logger.info("开始检查未接龙人员...")
    
    # 获取今天的所有记录
    records = bitable_service.get_today_full_records(today_str)
    if not records:
        logger.warning("今日无多维表记录，跳过提醒。")
        return

    # 分析群配置
    chat_configs = {}
    for rule in RULES:
        chat_id = rule.get("chat_id")
        if not chat_id: continue
        
        if chat_id not in chat_configs:
            chat_configs[chat_id] = {"check_morning": False, "check_daily": False}
            
        field_time = rule.get("field_time", "")
        if "早上好" in field_time:
            chat_configs[chat_id]["check_morning"] = True
        if "日报" in field_time:
            chat_configs[chat_id]["check_daily"] = True

    # 群成员映射
    chat_members_map = {}
    # 额外映射判断用户在哪些群
    user_chat_presence = {}
    
    for chat_id in chat_configs.keys():
        id_to_name = chat_service.get_all_members_map(chat_id)
        name_to_id = {name: uid for uid, name in id_to_name.items()}
        chat_members_map[chat_id] = name_to_id
        
        for name in name_to_id.keys():
            if name not in user_chat_presence:
                user_chat_presence[name] = []
            user_chat_presence[name].append(chat_id)

    # 筛选未接龙名单
    missing_status = {}
    for rec in records:
        name = rec.get("_parsed_name")
        if not name: continue
        
        morning_time = rec.get("早上好接龙时间")
        daily_time = rec.get("日报接龙时间")
        
        is_morning_missing = not morning_time
        is_daily_missing = not daily_time
        
        if is_morning_missing or is_daily_missing:
            missing_status[name] = {
                "morning": is_morning_missing,
                "daily": is_daily_missing
            }

    PRIORITY_CHAT_ID = RULES[2]["chat_id"]
    
    for chat_id, config in chat_configs.items():
        list_only_morning = []
        list_only_daily = []
        list_both = []
        
        current_chat_members = chat_members_map.get(chat_id, {})
        
        for name, status in missing_status.items():
            uid = current_chat_members.get(name)
            if not uid:
                continue

            if chat_id != PRIORITY_CHAT_ID:
                user_chats = user_chat_presence.get(name, [])
                if PRIORITY_CHAT_ID in user_chats:
                    continue
                
            at_text = f'<at user_id="{uid}"></at>'
            
            need_remind_morning = config["check_morning"] and status["morning"]
            need_remind_daily = config["check_daily"] and status["daily"]
            
            if need_remind_morning and need_remind_daily:
                list_both.append(at_text)
            elif need_remind_morning:
                list_only_morning.append(at_text)
            elif need_remind_daily:
                list_only_daily.append(at_text)
        
        # 发送消息
        if list_only_morning:
            msg = " ".join(list_only_morning) + " 早上好未接龙"
            chat_service.send_reminder(chat_id, msg)
            
        if list_only_daily:
            msg = " ".join(list_only_daily) + " 日报未接龙"
            chat_service.send_reminder(chat_id, msg)
            
        if list_both:
            msg = " ".join(list_both) + " 早上好未接龙 & 日报未接龙"
            chat_service.send_reminder(chat_id, msg)

    logger.info("提醒消息发送流程结束。")


def main():
    load_config()
    manager = FeishuAPIManager(CONFIG["APP_ID"], CONFIG["APP_SECRET"])
    chat_service = ChatHistoryService(manager)
    bitable_service = BitableService(manager)
    
    today_str = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
    today_records = bitable_service.get_today_records_map(today_str)
    
    if not today_records:
        logger.warning("多维表中没有找到今天的记录，无法进行同步。")
        return

    # --- 同步逻辑 ---
    chat_rules_map = {}
    for rule in RULES:
        chat_id = rule["chat_id"]
        if chat_id not in chat_rules_map:
            chat_rules_map[chat_id] = []
        chat_rules_map[chat_id].append(rule)

    total_updated = 0
    
    for chat_id, rules in chat_rules_map.items():
        member_map = chat_service.get_all_members_map(chat_id)
        raw_messages = chat_service.get_today_messages(chat_id)
        
        if not raw_messages:
            continue
            
        logger.info(f"开始处理群 {chat_id} 的 {len(rules)} 条规则...")
        
        for msg in raw_messages:
            content_text = chat_service.parse_content(msg.msg_type, msg.body.content)
            sender_id = msg.sender.id if msg.sender else ""
            sender_name = member_map.get(sender_id, f"未知ID({sender_id})")
            
            is_debug_target = "已发" in content_text
            if is_debug_target:
                logger.info(f"--- 正在分析消息: [{sender_name}] {content_text[:30]}... ---")

            for rule in rules:
                regex = re.compile(rule["regex"], re.IGNORECASE)
                
                if regex.search(content_text):
                    if is_debug_target:
                        logger.info(f"  >>> 命中规则: {rule['name']}")

                    record_id = today_records.get(sender_name)
                    if not record_id:
                        logger.warning(f"  [匹配成功但未找到人] 用户[{sender_name}] 规则[{rule['name']}]")
                        continue
                    
                    msg_dt = datetime.fromtimestamp(int(msg.create_time) / 1000, timezone(timedelta(hours=8)))
                    msg_time_str = msg_dt.strftime('%H:%M:%S')
                    msg_time = msg_dt.time()
                    deadline = datetime.strptime(rule["deadline"], "%H:%M").time()
                    is_late = msg_time > deadline
                    
                    status = "超时" if is_late else "是"
                    
                    fields = {
                        rule["field_time"]: msg_time_str,
                        rule["field_status"]: status
                    }
                    
                    bitable_service.update_record_fields(record_id, fields)
                    total_updated += 1
                else:
                    if is_debug_target:
                        logger.info(f"  (未命中规则: {rule['name']})")

    logger.info(f"同步任务完成，共更新 {total_updated} 条记录。")
    
    # --- 提醒逻辑 ---
    check_and_send_reminders(chat_service, bitable_service, today_str)

try:
    if __name__ == "__main__":
        main()
    set_rpa_status_sync.main("交表情况 统计 & 提醒", 1, "神州")
except Exception as e:
    full_error_msg = traceback.format_exc()
    set_rpa_status_sync.main("交表情况 统计 & 提醒", 0, "神州", full_error_msg)