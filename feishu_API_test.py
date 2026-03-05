import json
import os
import time
from feishu_API_manager import FeishuAPIManager

# ==========================================
# 1. 测试配置区域 (请填入真实的测试数据)
# ==========================================
TEST_USER_ID = "ou_d019d4c273cfe5d18d5a91b99da4b0e6"          # 您的 Open ID
TEST_CHAT_ID = "oc_f69094cda5ee5139924a926abc5816b2"          # 测试群聊 ID
TEST_BITABLE_APP_TOKEN = "" # 多维表格 App Token
TEST_BITABLE_TABLE_ID = ""  # 多维表格 Table ID
# ==========================================

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'app_config.json')
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
            print(f"  √ get_user: 成功 (姓名: {user_info.user.name})")
            print(f"  √ batch_get_users: 已准备 (需真实 User ID 列表)\n")
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
            msg_id = resp.message_id
            print(f"  √ send_message: 成功 (Msg ID: {msg_id})")
            
            # 编辑消息
            manager.update_message(msg_id, json.dumps({"text": "API 自动化测试消息 (已编辑)"}))
            print(f"  √ update_message: 成功")
            
            # 获取消息列表
            msgs = manager.list_messages(TEST_CHAT_ID, "chat", page_size=5)
            print(f"  √ list_messages: 成功 (获取到 {len(msgs.items)} 条消息)")
            
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
            print(f"  √ get_chat_info: 成功 (群名: {chat_info.name})")
            members = manager.get_chat_members(TEST_CHAT_ID, page_size=10)
            print(f"  √ get_chat_members: 成功 (获取到 {len(members.items)} 个成员)\n")
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
            print(f"  √ list_bitable_tables: 成功 (App 下有 {len(tables.items)} 张表)")
            
            # 新增记录 (请确保表格有 '文字' 字段或修改字段名)
            record_resp = manager.create_record(TEST_BITABLE_APP_TOKEN, TEST_BITABLE_TABLE_ID, {"文字": "测试数据"})
            record_id = record_resp.record.record_id
            print(f"  √ create_record: 成功 (Record ID: {record_id})")
            
            # 搜索记录
            search_resp = manager.search_records(TEST_BITABLE_APP_TOKEN, TEST_BITABLE_TABLE_ID)
            print(f"  √ search_records: 成功")
            
            # 删除记录
            manager.delete_record(TEST_BITABLE_APP_TOKEN, TEST_BITABLE_TABLE_ID, record_id)
            print(f"  √ delete_record: 成功\n")
        except Exception as e:
            print(f"  × 多维表格测试失败 (可能是字段名对不上): {e}\n")
    else:
        print("[测试 5/5] 多维表格测试: 跳过 (未提供 Token 或 ID)\n")

    print("=" * 40)
    print("测试流程执行完毕！")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"发生未预期的全局错误: {e}")
