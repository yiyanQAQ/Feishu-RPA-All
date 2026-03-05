import json
from typing import Any, Dict, List, Optional
import lark_oapi as lark
from lark_oapi.api.auth.v3 import *
from lark_oapi.api.contact.v3 import *
from lark_oapi.api.im.v1 import *
from lark_oapi.api.im.v2 import *
from lark_oapi.api.bitable.v1 import *

class FeishuAPIManager:
    def __init__(self, app_id: str, app_secret: str, log_level: lark.LogLevel = lark.LogLevel.INFO):
        self.app_id = app_id
        self.app_secret = app_secret
        self.client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .enable_set_token(True) \
            .log_level(log_level) \
            .build()
        self.logger = lark.logger

    def _get_option(self, user_access_token: Optional[str] = None) -> Optional[lark.RequestOption]:
        if user_access_token:
            return lark.RequestOption.builder().user_access_token(user_access_token).build()
        return None

    def _handle_response(self, response: Any, action_name: str) -> Any:
        if not response.success():
            raw_content = response.raw.content.decode('utf-8') if response.raw else ""
            try:
                raw_json = json.dumps(json.loads(raw_content), indent=4, ensure_ascii=False)
            except:
                raw_json = raw_content
            error_msg = (f"{action_name} failed, code: {response.code}, "
                         f"msg: {response.msg}, log_id: {response.get_log_id()}\n"
                         f"Raw Resp: {raw_json}")
            self.logger.error(error_msg)
            raise Exception(f"Feishu API Error: {error_msg}")
        
        # 某些删除接口成功后返回结果可能没有 data 属性
        return getattr(response, 'data', {})

    # --- 凭证 (Auth) ---

    def get_tenant_access_token(self) -> str:
        """自建应用获取 tenant_access_token"""
        resp = self.client.auth.v3.tenant_access_token.internal(
            lark.InternalTenantAccessTokenRequest.builder() \
            .request_body(InternalTenantAccessTokenRequestBody.builder() \
                .app_id(self.app_id) \
                .app_secret(self.app_secret) \
                .build()) \
            .build()
        )
        if not resp.success():
            raise Exception(f"Failed to get tenant token: {resp.msg}")
        return resp.data.tenant_access_token

    def get_app_access_token(self) -> str:
        """自建应用获取 app_access_token"""
        resp = self.client.auth.v3.app_access_token.internal(
            InternalAppAccessTokenRequest.builder() \
            .request_body(InternalAppAccessTokenRequestBody.builder() \
                .app_id(self.app_id) \
                .app_secret(self.app_secret) \
                .build()) \
            .build()
        )
        if not resp.success():
            raise Exception(f"Failed to get app token: {resp.msg}")
        return resp.data.app_access_token

    # --- 用户 (Contact) ---

    def get_user(self, user_id: str, user_id_type: str = "open_id", department_id_type: str = "open_department_id", user_access_token: Optional[str] = None) -> Any:
        """获取单个用户信息"""
        request = GetUserRequest.builder() \
            .user_id(user_id) \
            .user_id_type(user_id_type) \
            .department_id_type(department_id_type) \
            .build()
        response = self.client.contact.v3.user.get(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "get_user")

    def batch_get_users(self, user_ids: List[str], user_id_type: str = "open_id", user_access_token: Optional[str] = None) -> Any:
        """批量获取用户信息"""
        request = BatchUserRequest.builder() \
            .user_ids(user_ids) \
            .user_id_type(user_id_type) \
            .build()
        response = self.client.contact.v3.user.batch(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "batch_get_users")

    def find_users_by_department(self, department_id: str, user_id_type: str = "open_id", page_size: int = 10, user_access_token: Optional[str] = None) -> Any:
        """获取部门直属用户列表"""
        request = FindByDepartmentUserRequest.builder() \
            .department_id(department_id) \
            .user_id_type(user_id_type) \
            .page_size(page_size) \
            .build()
        response = self.client.contact.v3.user.find_by_department(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "find_users_by_department")

    # --- 消息 (IM) ---

    def list_messages(self, container_id: str, container_id_type: str = "chat", start_time: Optional[str] = None, end_time: Optional[str] = None, sort_type: str = "ByCreateTimeAsc", page_size: int = 20, page_token: Optional[str] = None, user_access_token: Optional[str] = None) -> Any:
        """获取会话历史消息"""
        request_builder = ListMessageRequest.builder() \
            .container_id_type(container_id_type) \
            .container_id(container_id) \
            .sort_type(sort_type) \
            .page_size(page_size)
        if start_time: request_builder.start_time(start_time)
        if end_time: request_builder.end_time(end_time)
        if page_token: request_builder.page_token(page_token)
        response = self.client.im.v1.message.list(request_builder.build(), option=self._get_option(user_access_token))
        return self._handle_response(response, "list_messages")

    def send_message(self, receive_id: str, content: str, msg_type: str = "text", receive_id_type: str = "open_id", uuid: Optional[str] = None, user_access_token: Optional[str] = None) -> Any:
        """发送消息"""
        if msg_type == "text" and not content.strip().startswith("{"):
            content_json = json.dumps({"text": content})
        else:
            content_json = content
        body_builder = CreateMessageRequestBody.builder() \
            .receive_id(receive_id) \
            .msg_type(msg_type) \
            .content(content_json)
        if uuid: body_builder.uuid(uuid)
        request = CreateMessageRequest.builder() \
            .receive_id_type(receive_id_type) \
            .request_body(body_builder.build()) \
            .build()
        response = self.client.im.v1.message.create(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "send_message")

    def delete_message(self, message_id: str, user_access_token: Optional[str] = None) -> Any:
        """撤回消息"""
        request = DeleteMessageRequest.builder().message_id(message_id).build()
        response = self.client.im.v1.message.delete(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "delete_message")

    def reply_message(self, message_id: str, content: str, msg_type: str = "text", reply_in_thread: bool = True, uuid: Optional[str] = None, user_access_token: Optional[str] = None) -> Any:
        """回复消息"""
        body = ReplyMessageRequestBody.builder() \
            .content(content) \
            .msg_type(msg_type) \
            .reply_in_thread(reply_in_thread)
        if uuid: body.uuid(uuid)
        request = ReplyMessageRequest.builder() \
            .message_id(message_id) \
            .request_body(body.build()) \
            .build()
        response = self.client.im.v1.message.reply(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "reply_message")

    def update_message(self, message_id: str, content: str, msg_type: str = "text", user_access_token: Optional[str] = None) -> Any:
        """编辑消息"""
        request = UpdateMessageRequest.builder() \
            .message_id(message_id) \
            .request_body(UpdateMessageRequestBody.builder().msg_type(msg_type).content(content).build()) \
            .build()
        response = self.client.im.v1.message.update(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "update_message")

    def forward_message(self, message_id: str, receive_id: str, receive_id_type: str = "open_id", user_access_token: Optional[str] = None) -> Any:
        """转发消息"""
        request = ForwardMessageRequest.builder() \
            .message_id(message_id) \
            .receive_id_type(receive_id_type) \
            .request_body(ForwardMessageRequestBody.builder().receive_id(receive_id).build()) \
            .build()
        response = self.client.im.v1.message.forward(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "forward_message")

    def merge_forward_message(self, receive_id: str, message_id_list: List[str], receive_id_type: str = "chat_id", user_access_token: Optional[str] = None) -> Any:
        """合并转发消息"""
        request = MergeForwardMessageRequest.builder() \
            .receive_id_type(receive_id_type) \
            .request_body(MergeForwardMessageRequestBody.builder() \
                .receive_id(receive_id) \
                .message_id_list(message_id_list) \
                .build()) \
            .build()
        response = self.client.im.v1.message.merge_forward(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "merge_forward_message")

    def forward_thread(self, thread_id: str, receive_id: str, receive_id_type: str = "chat_id", user_access_token: Optional[str] = None) -> Any:
        """转发话题"""
        request = ForwardThreadRequest.builder() \
            .thread_id(thread_id) \
            .receive_id_type(receive_id_type) \
            .request_body(ForwardThreadRequestBody.builder().receive_id(receive_id).build()) \
            .build()
        response = self.client.im.v1.thread.forward(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "forward_thread")

    def push_follow_up_message(self, message_id: str, follow_ups: List[FollowUp], user_access_token: Optional[str] = None) -> Any:
        """添加跟随气泡"""
        request = PushFollowUpMessageRequest.builder() \
            .message_id(message_id) \
            .request_body(PushFollowUpMessageRequestBody.builder().follow_ups(follow_ups).build()) \
            .build()
        response = self.client.im.v1.message.push_follow_up(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "push_follow_up_message")

    def get_message_read_users(self, message_id: str, user_id_type: str = "open_id", user_access_token: Optional[str] = None) -> Any:
        """查询消息已读信息"""
        request = ReadUsersMessageRequest.builder().message_id(message_id).user_id_type(user_id_type).build()
        response = self.client.im.v1.message.read_users(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "get_message_read_users")

    def get_message_resource(self, message_id: str, file_key: str, type: str = "image", user_access_token: Optional[str] = None):
        """获取消息中的资源文件"""
        request = GetMessageResourceRequest.builder().message_id(message_id).file_key(file_key).type(type).build()
        response = self.client.im.v1.message_resource.get(request, option=self._get_option(user_access_token))
        if not response.success():
            self._handle_response(response, "get_message_resource")
        return response

    def get_message_content(self, message_id: str, user_access_token: Optional[str] = None) -> Any:
        """获取指定消息的内容"""
        request = GetMessageRequest.builder().message_id(message_id).build()
        response = self.client.im.v1.message.get(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "get_message_content")

    def get_batch_message_read_user(self, batch_message_id: str, user_access_token: Optional[str] = None) -> Any:
        """查询批量消息推送和阅读人数"""
        request = ReadUserBatchMessageRequest.builder().batch_message_id(batch_message_id).build()
        response = self.client.im.v1.batch_message.read_user(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "get_batch_message_read_user")

    def get_batch_message_progress(self, batch_message_id: str, user_access_token: Optional[str] = None) -> Any:
        """查询批量消息整体进度"""
        request = GetProgressBatchMessageRequest.builder().batch_message_id(batch_message_id).build()
        response = self.client.im.v1.batch_message.get_progress(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "get_batch_message_progress")

    def delete_batch_message(self, batch_message_id: str, user_access_token: Optional[str] = None) -> Any:
        """批量撤回消息"""
        request = DeleteBatchMessageRequest.builder().batch_message_id(batch_message_id).build()
        response = self.client.im.v1.batch_message.delete(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "delete_batch_message")

    def upload_image(self, image_type: str, image_file: Any, user_access_token: Optional[str] = None) -> Any:
        """上传图片"""
        request = CreateImageRequest.builder() \
            .request_body(CreateImageRequestBody.builder().image_type(image_type).image(image_file).build()) \
            .build()
        response = self.client.im.v1.image.create(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "upload_image")

    def download_image(self, image_key: str, user_access_token: Optional[str] = None):
        """下载图片"""
        request = GetImageRequest.builder().image_key(image_key).build()
        response = self.client.im.v1.image.get(request, option=self._get_option(user_access_token))
        if not response.success():
            self._handle_response(response, "download_image")
        return response

    def upload_file(self, file_type: str, file_name: str, file: Any, duration: Optional[int] = None, user_access_token: Optional[str] = None) -> Any:
        """上传文件"""
        body = CreateFileRequestBody.builder().file_type(file_type).file_name(file_name).file(file)
        if duration: body.duration(duration)
        request = CreateFileRequest.builder().request_body(body.build()).build()
        response = self.client.im.v1.file.create(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "upload_file")

    def download_file(self, file_key: str, user_access_token: Optional[str] = None):
        """下载文件"""
        request = GetFileRequest.builder().file_key(file_key).build()
        response = self.client.im.v1.file.get(request, option=self._get_option(user_access_token))
        if not response.success():
            self._handle_response(response, "download_file")
        return response

    def urgent_app_message(self, message_id: str, user_id_list: List[str], user_id_type: str = "open_id", user_access_token: Optional[str] = None) -> Any:
        """发送应用内加急"""
        request = UrgentAppMessageRequest.builder() \
            .message_id(message_id) \
            .user_id_type(user_id_type) \
            .request_body(UrgentReceivers.builder().user_id_list(user_id_list).build()) \
            .build()
        response = self.client.im.v1.message.urgent_app(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "urgent_app_message")

    def patch_message(self, message_id: str, content: str, user_access_token: Optional[str] = None) -> Any:
        """更新已发送的消息卡片"""
        request = PatchMessageRequest.builder() \
            .message_id(message_id) \
            .request_body(PatchMessageRequestBody.builder().content(content).build()) \
            .build()
        response = self.client.im.v1.message.patch(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "patch_message")

    def batch_update_url_preview(self, preview_tokens: List[str], open_ids: List[str], user_access_token: Optional[str] = None) -> Any:
        """更新 URL 预览"""
        request = BatchUpdateUrlPreviewRequest.builder() \
            .request_body(BatchUpdateUrlPreviewRequestBody.builder() \
                .preview_tokens(preview_tokens) \
                .open_ids(open_ids) \
                .build()) \
            .build()
        response = self.client.im.v2.url_preview.batch_update(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "batch_update_url_preview")

    # --- 群组 (IM Chat) ---

    def get_chat_info(self, chat_id: str, user_access_token: Optional[str] = None) -> Any:
        """获取群信息"""
        request = GetChatRequest.builder().chat_id(chat_id).build()
        response = self.client.im.v1.chat.get(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "get_chat_info")

    def update_chat_top_notice(self, chat_id: str, chat_top_notice: List[ChatTopNotice], user_access_token: Optional[str] = None) -> Any:
        """更新群置顶"""
        request = PutTopNoticeChatTopNoticeRequest.builder() \
            .chat_id(chat_id) \
            .request_body(PutTopNoticeChatTopNoticeRequestBody.builder().chat_top_notice(chat_top_notice).build()) \
            .build()
        response = self.client.im.v1.chat_top_notice.put_top_notice(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "update_chat_top_notice")

    def delete_chat_top_notice(self, chat_id: str, user_access_token: Optional[str] = None) -> Any:
        """撤销群置顶"""
        request = DeleteTopNoticeChatTopNoticeRequest.builder().chat_id(chat_id).build()
        response = self.client.im.v1.chat_top_notice.delete_top_notice(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "delete_chat_top_notice")

    def get_chat_link(self, chat_id: str, validity_period: str = "week", user_access_token: Optional[str] = None) -> Any:
        """获取群分享链接"""
        request = LinkChatRequest.builder() \
            .chat_id(chat_id) \
            .request_body(LinkChatRequestBody.builder().validity_period(validity_period).build()) \
            .build()
        response = self.client.im.v1.chat.link(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "get_chat_link")

    def get_chat_members(self, chat_id: str, member_id_type: str = "open_id", page_size: int = 20, page_token: Optional[str] = None, user_access_token: Optional[str] = None) -> Any:
        """获取群成员列表"""
        request_builder = GetChatMembersRequest.builder().chat_id(chat_id).member_id_type(member_id_type).page_size(page_size)
        if page_token: request_builder.page_token(page_token)
        response = self.client.im.v1.chat_members.get(request_builder.build(), option=self._get_option(user_access_token))
        return self._handle_response(response, "get_chat_members")

    def add_chat_members(self, chat_id: str, id_list: List[str], member_id_type: str = "open_id", user_access_token: Optional[str] = None) -> Any:
        """将用户或机器人拉入群聊"""
        request = CreateChatMembersRequest.builder() \
            .chat_id(chat_id) \
            .member_id_type(member_id_type) \
            .request_body(CreateChatMembersRequestBody.builder().id_list(id_list).build()) \
            .build()
        response = self.client.im.v1.chat_members.create(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "add_chat_members")

    def is_member_in_chat(self, chat_id: str, member_id: str, member_id_type: str = "open_id", user_access_token: Optional[str] = None) -> Any:
        """判断用户或机器人是否在群里"""
        request = IsInChatChatMembersRequest.builder().chat_id(chat_id).member_id(member_id).member_id_type(member_id_type).build()
        response = self.client.im.v1.chat_members.is_in_chat(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "is_member_in_chat")

    # --- 多维表格 (Bitable) ---

    def get_bitable_app(self, app_token: str, user_access_token: Optional[str] = None) -> Any:
        """获取多维表格元数据"""
        request = GetAppRequest.builder().app_token(app_token).build()
        response = self.client.bitable.v1.app.get(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "get_bitable_app")

    def list_bitable_tables(self, app_token: str, page_size: int = 20, page_token: Optional[str] = None, user_access_token: Optional[str] = None) -> Any:
        """列出数据表"""
        request_builder = ListAppTableRequest.builder().app_token(app_token).page_size(page_size)
        if page_token: request_builder.page_token(page_token)
        response = self.client.bitable.v1.app_table.list(request_builder.build(), option=self._get_option(user_access_token))
        return self._handle_response(response, "list_bitable_tables")

    def create_record(self, app_token: str, table_id: str, fields: Dict[str, Any], user_access_token: Optional[str] = None) -> Any:
        """新增记录"""
        request = CreateAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(AppTableRecord.builder().fields(fields).build()) \
            .build()
        response = self.client.bitable.v1.app_table_record.create(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "create_record")

    def update_record(self, app_token: str, table_id: str, record_id: str, fields: Dict[str, Any], user_access_token: Optional[str] = None) -> Any:
        """更新记录"""
        request = UpdateAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .record_id(record_id) \
            .request_body(AppTableRecord.builder().fields(fields).build()) \
            .build()
        response = self.client.bitable.v1.app_table_record.update(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "update_record")

    def search_records(self, app_token: str, table_id: str, view_id: Optional[str] = None, field_names: Optional[List[str]] = None, sort_list: Optional[List[Sort]] = None, filter_info: Optional[Dict] = None, page_size: int = 20, page_token: Optional[str] = None, user_access_token: Optional[str] = None) -> Any:
        """查询记录"""
        body_builder = SearchAppTableRecordRequestBody.builder()
        if view_id: body_builder.view_id(view_id)
        if field_names: body_builder.field_names(field_names)
        if sort_list: body_builder.sort(sort_list)
        if filter_info: body_builder.filter(filter_info)
        body_builder.automatic_fields(True)
        request_builder = SearchAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .page_size(page_size) \
            .request_body(body_builder.build())
        if page_token: request_builder.page_token(page_token)
        response = self.client.bitable.v1.app_table_record.search(request_builder.build(), option=self._get_option(user_access_token))
        return self._handle_response(response, "search_records")

    def delete_record(self, app_token: str, table_id: str, record_id: str, user_access_token: Optional[str] = None) -> Any:
        """删除记录"""
        request = DeleteAppTableRecordRequest.builder().app_token(app_token).table_id(table_id).record_id(record_id).build()
        response = self.client.bitable.v1.app_table_record.delete(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "delete_record")

    def batch_create_records(self, app_token: str, table_id: str, records_fields: List[Dict[str, Any]], user_access_token: Optional[str] = None) -> Any:
        """新增多条记录"""
        app_table_records = [AppTableRecord.builder().fields(fs).build() for fs in records_fields]
        request = BatchCreateAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(BatchCreateAppTableRecordRequestBody.builder().records(app_table_records).build()) \
            .build()
        response = self.client.bitable.v1.app_table_record.batch_create(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "batch_create_records")

    def batch_update_records(self, app_token: str, table_id: str, records_data: List[Dict[str, Any]], user_access_token: Optional[str] = None) -> Any:
        """更新多条记录"""
        app_table_records = []
        for item in records_data:
            rec = AppTableRecord.builder().record_id(item.get("record_id")).fields(item.get("fields")).build()
            app_table_records.append(rec)
        request = BatchUpdateAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(BatchUpdateAppTableRecordRequestBody.builder().records(app_table_records).build()) \
            .build()
        response = self.client.bitable.v1.app_table_record.batch_update(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "batch_update_records")

    def batch_get_records(self, app_token: str, table_id: str, record_ids: List[str], user_id_type: str = "open_id", with_shared_url: bool = True, automatic_fields: bool = True, user_access_token: Optional[str] = None) -> Any:
        """批量获取记录"""
        request = BatchGetAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(BatchGetAppTableRecordRequestBody.builder() \
                .record_ids(record_ids) \
                .user_id_type(user_id_type) \
                .with_shared_url(with_shared_url) \
                .automatic_fields(automatic_fields) \
                .build()) \
            .build()
        response = self.client.bitable.v1.app_table_record.batch_get(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "batch_get_records")

    def batch_delete_records(self, app_token: str, table_id: str, record_ids: List[str], user_access_token: Optional[str] = None) -> Any:
        """删除多条记录"""
        request = BatchDeleteAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(BatchDeleteAppTableRecordRequestBody.builder().records(record_ids).build()) \
            .build()
        response = self.client.bitable.v1.app_table_record.batch_delete(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "batch_delete_records")

    def list_bitable_fields(self, app_token: str, table_id: str, page_size: int = 20, page_token: Optional[str] = None, user_access_token: Optional[str] = None) -> Any:
        """列出字段"""
        request_builder = ListAppTableFieldRequest.builder().app_token(app_token).table_id(table_id).page_size(page_size)
        if page_token: request_builder.page_token(page_token)
        response = self.client.bitable.v1.app_table_field.list(request_builder.build(), option=self._get_option(user_access_token))
        return self._handle_response(response, "list_bitable_fields")

    def list_bitable_workflows(self, app_token: str, table_id: str, user_access_token: Optional[str] = None) -> Any:
        """列出自动化流程"""
        request = ListAppWorkflowRequest.builder().app_token(app_token).table_id(table_id).build()
        response = self.client.bitable.v1.app_workflow.list(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "list_bitable_workflows")

    def update_bitable_workflow(self, app_token: str, table_id: str, workflow_id: str, status: str = "Enable", user_access_token: Optional[str] = None) -> Any:
        """更新自动化流程状态"""
        request = UpdateAppWorkflowRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .workflow_id(workflow_id) \
            .request_body(UpdateAppWorkflowRequestBody.builder().status(status).build()) \
            .build()
        response = self.client.bitable.v1.app_workflow.update(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "update_bitable_workflow")
