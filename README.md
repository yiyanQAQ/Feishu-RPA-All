# Feishu RPA All

[中文](#中文) | [English](#english)

---

## 中文

### 简介
集成多种飞书自动化能力的RPA工具集

### 功能
- **多维表同步**: 自动从飞书群聊记录中提取关键词，同步至多维表
- **自动化提醒**: 针对未按时提交日报、接龙的人员发起精准的飞书群@提醒
- **状态监控**: 实时监控RPA流程执行状态，并将异常信息推送至飞书
- **可视化界面**: 提供多个 GUI 工具，方便快速发送提醒和查看运行日志

### 目录结构
- `feishu_API_manager.py`: **飞书 API 简化封装**
- `get_daily_log_stats_and_remind.py`: **每日日志统计与提醒**
- `get_ops_daily_report_and_remind.py`: **运营日报同步与提醒**
- `get_rpa_status_broadcast.py`: **RPA状态广播**
- `gui_quick_reminder.py`: **快速提醒GUI**
- `quick_reminder.py`: **轻量级提醒工具**
- `set_rpa_status_sync.py`: **数据库同步模块**

### 运行
1. **克隆**:
   ```bash
   git clone https://github.com/yiyanQAQ/feishu-rpa-all.git
   ```
2. **配置环境**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # 或 .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```
3. **启动**:
   根据需求运行对应的脚本，例如：
   ```bash
   python gui_quick_reminder.py
   ```

---

## English

### Introduction
A collection of RPA tools integrating various Feishu (Lark) automation capabilities

### Features
- **Bitable Sync**: Automatically extracts keywords from Feishu group chat history and syncs them to Bitable.
- **Automated Reminders**: Sends precise @ mentions in Feishu groups for members who missed daily reports or check-ins.
- **Status Monitoring**: Real-time monitoring of RPA execution status with error notifications pushed to Feishu.
- **GUI Tools**: Provides several visual tools for quick reminder sending and log viewing.

### Directory Structure
- `feishu_API_manager.py`: **Feishu API Core Manager**
- `get_daily_log_stats_and_remind.py`: **Daily Log Stats & Reminder**
- `get_ops_daily_report_and_remind.py`: **Ops Daily Report Sync & Reminder**
- `get_rpa_status_broadcast.py`: **RPA Status Broadcast**
- `gui_quick_reminder.py`: **Quick Reminder GUI**
- `quick_reminder.py`: **Lightweight Reminder Tool**
- `set_rpa_status_sync.py`: **DB Sync Module**

### Installation
1. **Clone**:
   ```bash
   git clone https://github.com/yiyanQAQ/feishu-rpa-all.git
   ```
2. **Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```
3. **Run**:
   Execute the desired script, for example:
   ```bash
   python gui_quick_reminder.py
   ```
