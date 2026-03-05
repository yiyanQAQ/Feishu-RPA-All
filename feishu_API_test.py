import json
import os
import time
from feishu_API_manager import FeishuAPIManager

# ==========================================
# 1. 测试配置区域 (请填入真实的测试数据)
# ==========================================
TEST_USER_ID = ""          # 您的 Open ID (如: ou_xxx)
TEST_CHAT_ID = ""          # 测试群聊 ID (如: oc_xxx)
TEST_BITABLE_APP_TOKEN = "" # 多维表格 App Token
TEST_BITABLE_TABLE_ID = ""  # 多维表格 Table ID
# ==========================================

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'app_config.json')
    if not os.path.exists(config_path):
        raise Exception(f"找不到配置文件: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_test():
    config = load_config()
    manager = FeishuAPIManager(config["APP_ID"], config["APP_SECRET"])
    
    print("开始飞书 API 综合测试...\n")

    # --- 1. 凭证测试 ---
    print("[测试 1/5] 凭证测试")
    try:
        token = manager.get_tenant_access_token()
        print(f"  √ get_tenant_access_token: 成功 (前 10 位: {token[:10]}...)")
        app_token = manager.get_app_access_token()
        print(f"  √ get_app_access_token: 成功 (前 10 位: {app_token[:10]}...)\n")
    except Exception as e:
        print(f"  × 凭证测试失败: {e}\n")

    # --- 2. 用户测试 ---
    if TEST_USER_ID:
        print("[测试 2/5] 用户测试")
        try:
            user_info = manager.get_user(TEST_USER_ID)
            # 根据 SDK 返回结构访问姓名
            name = getattr(getattr(user_info, 'user', None), 'name', '未知')
            print(f"  √ get_user: 成功 (姓名: {name})\n")
        except Exception as e:
            print(f"  × 用户测试失败: {e}\n")
    else:
        print("[测试 2/5] 用户测试: 跳过 (未提供 TEST_USER_ID)\n")

    # --- 3. 消息测试 ---
    if TEST_CHAT_ID:
        print("[测试 3/5] 消息测试")
        try:
            # 发送消息
            resp = manager.send_message(TEST_CHAT_ID, "API 自动化测试消息", "text", "chat_id")
            msg_id = getattr(resp, 'message_id', None)
            if not msg_id:
                raise Exception("未获取到 message_id")
            print(f"  √ send_message: 成功 (Msg ID: {msg_id})")
            
            # 编辑消息
            manager.update_message(msg_id, json.dumps({"text": "API 自动化测试消息 (已编辑)"}))
            print(f"  √ update_message: 成功")
            
            # 获取消息列表
            msgs = manager.list_messages(TEST_CHAT_ID, "chat", page_size=5)
            count = len(getattr(msgs, 'items', []))
            print(f"  √ list_messages: 成功 (获取到 {count} 条消息)")
            
            # 撤回消息
            manager.delete_message(msg_id)
            print(f"  √ delete_message: 成功\n")
        except Exception as e:
            print(f"  × 消息测试失败: {e}\n")
    else:
        print("[测试 3/5] 消息测试: 跳过 (未提供 TEST_CHAT_ID)\n")

    # --- 4. 群组测试 ---
    if TEST_CHAT_ID:
        print("[测试 4/5] 群组测试")
        try:
            chat_info = manager.get_chat_info(TEST_CHAT_ID)
            name = getattr(chat_info, 'name', '未命名')
            print(f"  √ get_chat_info: 成功 (群名: {name})")
            members = manager.get_chat_members(TEST_CHAT_ID, page_size=10)
            count = len(getattr(members, 'items', []))
            print(f"  √ get_chat_members: 成功 (获取到 {count} 个成员)\n")
        except Exception as e:
            print(f"  × 群组测试失败: {e}\n")
    else:
        print("[测试 4/5] 群组测试: 跳过 (未提供 TEST_CHAT_ID)\n")

    # --- 5. 多维表格测试 ---
    if TEST_BITABLE_APP_TOKEN and TEST_BITABLE_TABLE_ID:
        print("[测试 5/5] 多维表格测试")
        try:
            # 列表数据表
            tables = manager.list_bitable_tables(TEST_BITABLE_APP_TOKEN)
            count = len(getattr(tables, 'items', []))
            print(f"  √ list_bitable_tables: 成功 (App 下有 {count} 张表)")
            
            # 新增记录 (请确保表格有 '文字' 字段或修改字段名)
            # 注意：此处字段名需根据您的实际表格修改
            record_resp = manager.create_record(TEST_BITABLE_APP_TOKEN, TEST_BITABLE_TABLE_ID, {"文字": "测试数据"})
            record_id = getattr(getattr(record_resp, 'record', None), 'record_id', None)
            if not record_id:
                raise Exception("未获取到 record_id")
            print(f"  √ create_record: 成功 (Record ID: {record_id})")
            
            # 搜索记录
            manager.search_records(TEST_BITABLE_APP_TOKEN, TEST_BITABLE_TABLE_ID)
            print(f"  √ search_records: 成功")
            
            # 删除记录
            manager.delete_record(TEST_BITABLE_APP_TOKEN, TEST_BITABLE_TABLE_ID, record_id)
            print(f"  √ delete_record: 成功\n")
        except Exception as e:
            print(f"  × 多维表格测试失败 (请检查字段名): {e}\n")
    else:
        print("[测试 5/5] 多维表格测试: 跳过 (未提供 Token 或 ID)\n")

    print("=" * 40)
    print("测试流程执行完毕！")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"发生未预期的全局错误: {e}")
