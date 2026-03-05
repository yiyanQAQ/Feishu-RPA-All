import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import logging
import quick_reminder

class TextHandler(logging.Handler):
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

class QuickReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("紧急提醒工具")
        self.root.geometry("600x400")

        # 创建界面
        self.create_widgets()

        self.setup_logging()

    def setup_logging(self):
        text_handler = TextHandler(self.log_text)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        text_handler.setFormatter(formatter)

        logger = logging.getLogger("quick_reminder")
        logger.addHandler(text_handler)
        logger.setLevel(logging.INFO)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        msg_frame = ttk.LabelFrame(main_frame, text="提醒消息内容", padding="10")
        msg_frame.pack(fill=tk.X)
        
        self.msg_entry = ttk.Entry(msg_frame, width=80)
        self.msg_entry.insert(0, quick_reminder.DEFAULT_MESSAGE)
        self.msg_entry.pack(fill=tk.X, expand=True)

        btn_frame = ttk.Frame(main_frame, padding="10")
        btn_frame.pack(fill=tk.X)
        
        self.run_button = ttk.Button(btn_frame, text="发送提醒", command=self.run_task)
        self.run_button.pack()

        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_text = ScrolledText(log_frame, state='disabled', height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def run_task(self):
        self.run_button.config(state="disabled")

        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        
        # 获取消息内容
        message = self.msg_entry.get()

        def task():
            try:
                quick_reminder.run_reminder(custom_message=message)
                logging.getLogger("quick_reminder").info(">>> 任务执行完毕 <<<")
            except Exception as e:
                logging.getLogger("quick_reminder").error(f"执行失败: {e}")
                messagebox.showerror("错误", f"执行失败: {e}")
            finally:
                self.root.after(0, lambda: self.run_button.config(state="normal"))

        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = QuickReminderApp(root)
    root.mainloop()