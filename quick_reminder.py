import tkinter as tk
from tkinter import messagebox
import json
from feishu_API_manager import FeishuAPIManager

# --- 基础配置 ---
APP_ID = "cli_a9edd60855a35bd7"
APP_SECRET = ""
CHAT_ID = "oc_f69094cda5ee5139924a926abc5816b2"


def send_remind():
    names_str = entry_names.get()
    msg_text = entry_msg.get()

    user_list = [n.strip() for n in names_str.replace("，", ",").split(",") if n.strip()]

    try:
        manager = FeishuAPIManager(APP_ID, APP_SECRET)
        name_to_id = {}
        resp = manager.get_chat_members(CHAT_ID, page_size=100)
        if resp and resp.items:
            for item in resp.items:
                name_to_id[item.name] = item.member_id

        at_tags = [f'<at user_id="{name_to_id[n]}"></at>' for n in user_list if n in name_to_id]

        if not at_tags:
            messagebox.showwarning("提示", "名单里的人一个都没找到")
            return

        full_body = " ".join(at_tags) + f" {msg_text}"
        manager.send_message(CHAT_ID, full_body, "text", "chat_id")

        status_label.config(text="状态: 发送成功！", fg="green")
    except Exception as e:
        messagebox.showerror("出错啦", str(e))


root = tk.Tk()
root.title("Feishu Simple Reminder")
root.geometry("400x250")

primary_color = "#927CD1"

tk.Label(root, text="？:").pack(pady=(15, 0))
entry_names = tk.Entry(root, width=40)
entry_names.insert(0, "火山, 青山, 雪山, 星辰, 神州")
entry_names.pack(pady=5)

tk.Label(root, text="？:").pack(pady=(10, 0))
entry_msg = tk.Entry(root, width=40)
entry_msg.insert(0, "？")
entry_msg.pack(pady=5)

btn = tk.Button(root, text="立即执行", command=send_remind, bg=primary_color, fg="white", width=15)
btn.pack(pady=20)

status_label = tk.Label(root, text="状态: 待命中", fg="gray")
status_label.pack()

root.mainloop()