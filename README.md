# Feishu RPA All

[中文](#中文) | [English](#english)

---

## 中文

### 简介

集成多种飞书自动化能力的RPA工具集

### 目录结构

- `app_config.json`: **飞书应用凭据配置文件 (自行创建)**
- `feishu_API_manager.py`: **飞书 API 简化封装**
- `set_rpa_status_sync.py`: **RPA 运行状态数据库同步模块**
- `Daily_log_status_and_remind/`: **每日日志统计与提醒**
- `Ops_daily_report_and_remind/`: **运营日报同步与提醒**
- `Quick_reminder/`: **轻量级提醒工具**
- `RPA_status-broadcast-sync/`: **RPA 状态广播**
- `Submission_status_and_remind/`: **交表情况统计与提醒**

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

### Directory Structure

- `app_config.json`: **Feishu Credentials Configuration (Create manually)**
- `feishu_API_manager.py`: **Feishu API Core Manager**
- `set_rpa_status_sync.py`: **RPA Status DB Sync Module**
- `Daily_log_status_and_remind/`: **Daily Log Status & Reminder**
- `Ops_daily_report_and_remind/`: **Ops Daily Report Sync & Reminder**
- `Quick_reminder/`: **Lightweight Reminder Tool**
- `RPA_status-broadcast-sync/`: **RPA Status Broadcast**
- `Submission_status_and_remind/`: **Submission Status & Reminders**

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

