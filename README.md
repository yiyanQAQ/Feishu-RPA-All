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
- `app_config.json`: **飞书应用凭据配置文件 (自行创建)**
- `feishu_API_manager.py`: **飞书 API 简化封装**
- `set_rpa_status_sync.py`: **RPA 运行状态数据库同步模块**
- `Daily_log_status_and_remind`: **每日日志统计与提醒**
- `Ops_daily_report_and_remind`: **运营日报同步与提醒**
- `Submission_status_and_remind`: **交表情况统计与提醒**
- `Quick_reminder`: **轻量级提醒工具**
- `RPA_status-broadcast-sync`: **RPA 状态广播**

### 配置凭据
使用 `app_config.json` 统一管理飞书自建APP凭据。请在项目根目录下创建该文件：
```json
{
    "APP_ID": "APP_ID",
    "APP_SECRET": "APP_SECRET"
}
```

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
- `app_config.json`: **Feishu Credentials Configuration (Create manually)**
- `feishu_API_manager.py`: **Feishu API Core Manager**
- `set_rpa_status_sync.py`: **RPA Status DB Sync Module**
- `Daily_log_status_and_remind.py`: **Daily Log Status & Reminder**
- `Ops_daily_report_and_remind`: **Ops Daily Report Sync & Reminder**
- `Submission_status_and_remind`: **Submission Status & Reminders**
- `Quick_reminder`: **Lightweight Reminder Tool**
- `RPA_status-broadcast-sync`: **RPA Status Broadcast**

### Configuration
Uses `app_config.json` to manage Feishu credentials. Please create this file in the project root:
```json
{
    "APP_ID": "APP_ID",
    "APP_SECRET": "APP_SECRET"
}
```

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
