import json
import pymysql
import time
import os
from datetime import datetime
from feishu_API_manager import FeishuAPIManager
from set_rpa_status_sync import RPAStatusManager

# --- 配置 ---
FEISHU_CONFIG = {
    "APP_ID": "cli_a9edd60855a35bd7",
    "APP_SECRET": "",
    "CHAT_ID": "oc_d2395b6958036b69d94d9cf396e5b62c"
}

# 用于记录上次运行时间的文件
LAST_RUN_FILE = "last_run_time.txt"

class RPAMessageSender:
    def __init__(self):
        self.status_manager = RPAStatusManager()
        self.feishu_manager = FeishuAPIManager(FEISHU_CONFIG["APP_ID"], FEISHU_CONFIG["APP_SECRET"])
        self.member_map = {}  # 姓名->open_id

    def get_last_run_time(self):
        """从文件读取上次运行时间"""
        if os.path.exists(LAST_RUN_FILE):
            try:
                with open(LAST_RUN_FILE, "r") as f:
                    time_str = f.read().strip()
                    if time_str:
                        return time_str
            except Exception as e:
                print(f"读取上次运行时间失败: {e}")
        return None

    def save_current_run_time(self, current_time_str):
        """将本次运行时间写入文件"""
        try:
            with open(LAST_RUN_FILE, "w") as f:
                f.write(current_time_str)
        except Exception as e:
            print(f"保存运行时间失败: {e}")

    def fetch_group_members(self):
        """获取群成员姓名->open_id的映射"""
        print("正在获取群成员列表...")
        try:
            resp_data = self.feishu_manager.get_chat_members(FEISHU_CONFIG["CHAT_ID"])
            items = []
            if hasattr(resp_data, 'items') and resp_data.items:
                items = resp_data.items
            elif isinstance(resp_data, dict) and 'items' in resp_data:
                items = resp_data['items']

            for member in items:
                name = getattr(member, 'name', None) or member.get('name')
                member_id = getattr(member, 'member_id', None) or member.get('member_id')
                if name and member_id:
                    self.member_map[name] = member_id
            print(f"成功映射 {len(self.member_map)} 个群成员")
        except Exception as e:
            print(f"获取群成员失败: {e}")

    def get_rpa_states_incremental(self, last_time, current_time):
        """根据时间区间从数据库增量读取RPA状态数据"""
        connection = pymysql.connect(**self.status_manager.db_config)
        try:
            with connection.cursor() as cursor:
                if last_time:
                    # 获取上次运行到本次运行之间的数据
                    sql = """
                        SELECT rpa_name, run_status, error_log, maintainer, updated_at 
                        FROM RPA_State 
                        WHERE updated_at > %s AND updated_at <= %s
                    """
                    cursor.execute(sql, (last_time, current_time))
                    print(f"执行增量提取: {last_time} 至 {current_time}")
                else:
                    # 第一次运行获取本次运行时间之前的所有数据
                    sql = """
                        SELECT rpa_name, run_status, error_log, maintainer, updated_at 
                        FROM RPA_State 
                        WHERE updated_at <= %s
                    """
                    cursor.execute(sql, (current_time,))
                    print(f"执行首次提取: 获取 {current_time} 之前的所有数据")
                
                return cursor.fetchall()
        except Exception as e:
            print(f"读取数据库失败: {e}")
            return []
        finally:
            connection.close()

    def send_aggregated_message(self, title, records, need_at):
        """使用飞书JSON卡片发送聚合消息"""
        if not records:
            return

        status_map = {
            1: {"color": "green", "label": "✅ 运行成功"},
            0: {"color": "red", "label": "❌ 运行异常"},
            -1: {"color": "orange", "label": "⚠️ 状态未知"}
        }

        # 避免token消耗过多，根据maintainer分组发送
        grouped_records = {}
        for r in records:
            m = r['maintainer']
            if m not in grouped_records: grouped_records[m] = []
            grouped_records[m].append(r)

        for maintainer, m_records in grouped_records.items():
            # 准备@标签
            open_id = self.member_map.get(maintainer)
            at_content = f"<at id={open_id}></at>" if (need_at and open_id) else f"**负责人:** {maintainer}"

            elements = []
            for record in m_records:
                status_info = status_map.get(record['run_status'], status_map[-1])
                updated_at_str = record['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(record['updated_at'], datetime) else str(record['updated_at'])
                
                # 记录详情
                item_content = f"**RPA名称：** {record['rpa_name']}\n**更新时间：** {updated_at_str}\n**执行状态：** {status_info['label']}"
                if record['run_status'] != 1 and record['error_log']:
                    brief_log = record['error_log'][:200] + "..." if len(record['error_log']) > 200 else record['error_log']
                    item_content += f"\n**错误摘要：** {brief_log}"
                
                elements.append({
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": item_content}
                })
                elements.append({"tag": "hr"})

            # 去掉最后一个hr
            if elements: elements.pop()

            card_content = {
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": "blue" if not need_at else ("red" if m_records[0]['run_status']==0 else "orange"),
                    "title": {"content": f"{title} - {maintainer}", "tag": "plain_text"}
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": at_content}
                    },
                    {"tag": "hr"}
                ] + elements
            }

            try:
                self.feishu_manager.send_message(
                    receive_id=FEISHU_CONFIG["CHAT_ID"],
                    content=json.dumps(card_content, ensure_ascii=False),
                    msg_type="interactive",
                    receive_id_type="chat_id"
                )
                print(f"已发送 {maintainer} 的汇总卡片")
                time.sleep(0.5)
            except Exception as e:
                print(f"发送卡片失败: {e}")

    def run(self):
        # 获取时间区间
        last_time = self.get_last_run_time()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.fetch_group_members()
        
        # 增量提取
        records = self.get_rpa_states_incremental(last_time, current_time)
        
        if not records:
            print(f"区间 [{last_time} 至 {current_time}] 内无新数据更新")
            # 即使无新数据，也要更新运行时间，防止下次重复扫描历史数据
            self.save_current_run_time(current_time)
            return

        # 分类
        status_0 = [r for r in records if r['run_status'] == 0]
        status_neg1 = [r for r in records if r['run_status'] == -1]
        status_1 = [r for r in records if r['run_status'] == 1]

        # 发送
        if status_0:
            self.send_aggregated_message("RPA运行异常列表", status_0, need_at=True)
            time.sleep(1)
        if status_neg1:
            self.send_aggregated_message("RPA未知状态列表", status_neg1, need_at=True)
            time.sleep(1)
        if status_1:
            self.send_aggregated_message("RPA正常运行列表", status_1, need_at=False)

        # 任务成功后保存本次运行时间
        self.save_current_run_time(current_time)


try:
    if __name__ == "__main__":
        sender = RPAMessageSender()
        sender.run()
    set_rpa_status_sync.main("RPA运行状态推送", 1, "神州")
except Exception as e:
    full_error_msg = traceback.format_exc()
    set_rpa_status_sync.main("RPA运行状态推送", 0, "神州", full_error_msg)
