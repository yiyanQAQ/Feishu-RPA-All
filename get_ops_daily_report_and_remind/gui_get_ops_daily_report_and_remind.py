import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import json
import os
import threading
import logging
import webbrowser
import argparse
import sys
import get_ops_daily_report_and_remind

# 配置文件路径
USER_HOME = os.path.expanduser("~")
CONFIG_FILE_NAME = "config_get_chat_history.json"
CONFIG_PATH = os.path.join(USER_HOME, CONFIG_FILE_NAME)

class TextHandler(logging.Handler):
    """
    日志处理器，将日志输出到Text控件
    """
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            try:
                self.text_widget.configure(state='normal')
                self.text_widget.insert(tk.END, msg + '\n')
                self.text_widget.configure(state='disabled')
                self.text_widget.see(tk.END)
            except Exception:
                pass

        self.text_widget.after(0, append)

class ConfigApp:
    def __init__(self, root):
        self.root = root
        self.root.title("飞书消息同步配置工具")
        self.root.geometry("800x600")

        self.config_data = {}
        self.rules_data = []

        self.load_config()

        self.create_widgets()

        self.setup_logging()

    def setup_logging(self):
        text_handler = TextHandler(self.log_text)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        text_handler.setFormatter(formatter)

        logger = logging.getLogger("get_chat_history")
        logger.addHandler(text_handler)
        logger.setLevel(logging.INFO)

    def load_config(self):
        """加载配置"""
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config_data = data.get("CONFIG", get_ops_daily_report_and_remind.DEFAULT_CONFIG)
                    self.rules_data = data.get("RULES", get_ops_daily_report_and_remind.DEFAULT_RULES)
            except Exception as e:
                messagebox.showerror("错误", f"加载配置文件失败: {e}")
                self.config_data = get_ops_daily_report_and_remind.DEFAULT_CONFIG
                self.rules_data = get_ops_daily_report_and_remind.DEFAULT_RULES
        else:
            self.config_data = get_ops_daily_report_and_remind.DEFAULT_CONFIG
            self.rules_data = get_ops_daily_report_and_remind.DEFAULT_RULES

    def save_config(self):
        """保存配置到文件"""
        self.update_data_from_ui()
        
        data = {
            "CONFIG": self.config_data,
            "RULES": self.rules_data
        }
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("成功", f"配置已保存至:\n{CONFIG_PATH}")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置文件失败: {e}")

    def create_widgets(self):
        paned_window = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # 上部配置区
        top_container = ttk.Frame(paned_window)
        paned_window.add(top_container, weight=1)

        # 顶部按钮区
        btn_frame = ttk.Frame(top_container, padding="5")
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="运行同步", command=self.run_sync).pack(side=tk.LEFT, padx=5)
        
        # 选项卡
        notebook = ttk.Notebook(top_container)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 基础配置
        self.config_frame = ttk.Frame(notebook, padding="10")
        notebook.add(self.config_frame, text="基础配置")
        self.create_config_tab()

        # 规则配置
        self.rules_frame = ttk.Frame(notebook, padding="10")
        notebook.add(self.rules_frame, text="规则配置")
        self.create_rules_tab()

        # 下部日志区
        log_frame = ttk.LabelFrame(paned_window, text="运行日志", padding="5")
        paned_window.add(log_frame, weight=1)
        
        self.log_text = ScrolledText(log_frame, state='disabled', height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def create_config_tab(self):
        # 配置Grid权重
        self.config_frame.columnconfigure(1, weight=1)

        # 字段映射
        self.config_label_map = {
            "APP_ID": "应用 ID (APP_ID)",
            "APP_SECRET": "应用密钥 (APP_SECRET)",
            "TZ_OFFSET": "时区偏移 (TZ_OFFSET)",
            "BITABLE_APP_TOKEN": "飞书多维表地址 (APP_TOKEN)",
            "BITABLE_TABLE_ID": "飞书多维表数据表地址 (TABLE_ID)"
        }
        
        # 使用Grid布局
        row = 0
        self.config_entries = {}
        
        # 根据映射显示标签
        for key, value in self.config_data.items():
            label_text = self.config_label_map.get(key, key)
            
            ttk.Label(self.config_frame, text=label_text).grid(row=row, column=0, sticky=tk.W, pady=5)
            entry = ttk.Entry(self.config_frame)
            entry.insert(0, str(value))
            entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
            self.config_entries[key] = entry
            row += 1

    def create_rules_tab(self):
        # 左侧规则列表，右侧详情编辑
        paned_window = ttk.PanedWindow(self.rules_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # 左侧列表
        list_frame = ttk.Frame(paned_window)
        paned_window.add(list_frame, weight=1)
        
        self.rules_listbox = tk.Listbox(list_frame)
        self.rules_listbox.pack(fill=tk.BOTH, expand=True)
        self.rules_listbox.bind('<<ListboxSelect>>', self.on_rule_select)
        
        # 填充列表
        self.refresh_rules_list()

        # 按钮区
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="添加规则", command=self.add_rule).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="删除规则", command=self.delete_rule).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 右侧详情
        self.detail_frame = ttk.Frame(paned_window, padding="10")
        paned_window.add(self.detail_frame, weight=3)
        
        # 配置Grid权重
        self.detail_frame.columnconfigure(1, weight=1)
        
        self.current_rule_entries = {}
        self.current_rule_index = -1
        
        # 规则字段映射
        self.rule_field_map = [
            ("name", "日志输出群聊备注"),
            ("chat_id", "群聊ID（非群名）"),
            ("regex", "正则规则"),
            ("deadline", "超时时间"),
            ("field_time", "发送时间字段"),
            ("field_status", "接龙/超时字段")
        ]
        
        row = 0
        for field_key, field_label in self.rule_field_map:
            # 标签
            ttk.Label(self.detail_frame, text=field_label).grid(row=row, column=0, sticky=tk.W, pady=5)
            
            # 输入框
            entry = ttk.Entry(self.detail_frame)
            entry.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
            self.current_rule_entries[field_key] = entry
            
            row += 1
            
            # 在chat_id下添加链接
            if field_key == "chat_id":
                link_text = "获取群聊ID: https://open.feishu.cn/api-explorer/cli_a9edd60855a35bd7?apiName=get&from=op_doc_tab"
                link_url = "https://open.feishu.cn/api-explorer/cli_a9edd60855a35bd7?apiName=get&from=op_doc_tab"
                
                link_label = tk.Label(self.detail_frame, text=link_text, fg="blue", cursor="hand2", justify=tk.LEFT)
                link_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=0)
                link_label.bind("<Button-1>", lambda e, url=link_url: webbrowser.open_new(url))
                row += 1

        ttk.Button(self.detail_frame, text="保存当前规则修改", command=self.save_current_rule).grid(row=row, column=1, sticky=tk.E, pady=10)

    def refresh_rules_list(self):
        self.rules_listbox.delete(0, tk.END)
        for rule in self.rules_data:
            self.rules_listbox.insert(tk.END, rule.get("name", "未命名规则"))

    def on_rule_select(self, event):
        selection = self.rules_listbox.curselection()
        if selection:
            index = selection[0]
            self.current_rule_index = index
            rule = self.rules_data[index]
            
            for field, entry in self.current_rule_entries.items():
                entry.delete(0, tk.END)
                entry.insert(0, str(rule.get(field, "")))

    def save_current_rule(self):
        if self.current_rule_index >= 0:
            rule = self.rules_data[self.current_rule_index]
            for field, entry in self.current_rule_entries.items():
                rule[field] = entry.get()
            
            # 刷新列表名称
            self.refresh_rules_list()
            self.rules_listbox.selection_set(self.current_rule_index)
            messagebox.showinfo("提示", "规则已更新 (记得点击顶部'保存配置'以写入文件)")

    def add_rule(self):
        new_rule = {
            "name": "新规则",
            "chat_id": "",
            "regex": "",
            "deadline": "09:00",
            "field_time": "",
            "field_status": ""
        }
        self.rules_data.append(new_rule)
        self.refresh_rules_list()
        self.rules_listbox.selection_set(tk.END)
        self.on_rule_select(None)

    def delete_rule(self):
        selection = self.rules_listbox.curselection()
        if selection:
            index = selection[0]
            del self.rules_data[index]
            self.refresh_rules_list()
            # 清空右侧
            for entry in self.current_rule_entries.values():
                entry.delete(0, tk.END)
            self.current_rule_index = -1

    def update_data_from_ui(self):
        # 更新Config数据
        for key, entry in self.config_entries.items():
            value = entry.get()
            # 转换数字类型
            if key == "TZ_OFFSET":
                try:
                    value = int(value)
                except:
                    pass
            self.config_data[key] = value

    def run_sync(self):
        # 保存配置
        self.save_config()
        
        # 清空日志区
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        
        # 在新线程中运行避免卡死
        def task():
            try:
                # 重新加载配置
                get_ops_daily_report_and_remind.load_config()
                get_ops_daily_report_and_remind.main()
                logging.getLogger("get_chat_history").info(">>> 同步任务执行完毕 <<<")
            except Exception as e:
                logging.getLogger("get_chat_history").error(f"执行失败: {e}")
                messagebox.showerror("错误", f"执行失败: {e}")

        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    # 命令行参数配置
    parser = argparse.ArgumentParser(description="飞书消息同步工具")
    parser.add_argument("--run-now", action="store_true", help="直接运行同步任务")
    args = parser.parse_args()

    if args.run_now:
        # 无头模式
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        print("正在以无头模式运行同步任务")
        try:
            get_ops_daily_report_and_remind.load_config()
            get_ops_daily_report_and_remind.main()
            print("任务完成。")
        except Exception as e:
            print(f"任务失败: {e}")
            sys.exit(1)
    else:
        # GUI模式
        root = tk.Tk()
        app = ConfigApp(root)
        root.mainloop()