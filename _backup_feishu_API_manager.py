import json

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *
from lark_oapi.api.im.v1 import *


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

    def _handle_response(self, response: Any, action_name: str) -> Dict[str, Any]:

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

        return response.data

    def get_tenant_access_token(self) -> str:

        resp = self.client.auth.tenant_access_token.internal(
            lark.InternalTenantAccessTokenRequest.builder()
            .app_id(self.app_id)
            .app_secret(self.app_secret)
            .build()
        )

        if not resp.success():
            raise Exception(f"Failed to get tenant token: {resp.msg}")

        return resp.data.tenant_access_token

    def create_record(self, app_token: str, table_id: str, fields: Dict[str, Any],
                      user_access_token: Optional[str] = None) -> Dict[str, Any]:
        request = CreateAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(AppTableRecord.builder().fields(fields).build()) \
            .build()

        response = self.client.bitable.v1.app_table_record.create(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "create_record")

    def update_record(self, app_token: str, table_id: str, record_id: str, fields: Dict[str, Any],
                      user_access_token: Optional[str] = None) -> Dict[str, Any]:
        request = UpdateAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .record_id(record_id) \
            .request_body(AppTableRecord.builder().fields(fields).build()) \
            .build()

        response = self.client.bitable.v1.app_table_record.update(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "update_record")

    def delete_record(self, app_token: str, table_id: str, record_id: str, user_access_token: Optional[str] = None) -> \
            Dict[str, Any]:
        request = DeleteAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .record_id(record_id) \
            .build()

        response = self.client.bitable.v1.app_table_record.delete(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "delete_record")

    def search_records(self,
                       app_token: str,
                       table_id: str,
                       view_id: Optional[str] = None,
                       field_names: Optional[List[str]] = None,
                       sort_list: Optional[List[Sort]] = None,
                       filter_info: Optional[Dict] = None,
                       page_size: int = 20,
                       page_token: Optional[str] = None,
                       user_access_token: Optional[str] = None) -> Dict[str, Any]:

        body_builder = SearchAppTableRecordRequestBody.builder()
        if view_id:
            body_builder.view_id(view_id)
        if field_names:
            body_builder.field_names(field_names)
        if sort_list:
            body_builder.sort(sort_list)
        if filter_info:
            body_builder.filter(filter_info)

        body_builder.automatic_fields(True)

        request_builder = SearchAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .page_size(page_size) \
            .request_body(body_builder.build())

        if page_token:
            request_builder.page_token(page_token)

        response = self.client.bitable.v1.app_table_record.search(request_builder.build(),
                                                                  option=self._get_option(user_access_token))
        return self._handle_response(response, "search_records")

    def batch_create_records(self, app_token: str, table_id: str, records_fields: List[Dict[str, Any]],
                             user_access_token: Optional[str] = None) -> Dict[str, Any]:

        app_table_records = [AppTableRecord.builder().fields(fs).build() for fs in records_fields]

        request = BatchCreateAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(BatchCreateAppTableRecordRequestBody.builder().records(app_table_records).build()) \
            .build()

        response = self.client.bitable.v1.app_table_record.batch_create(request,
                                                                        option=self._get_option(user_access_token))
        return self._handle_response(response, "batch_create_records")

    def batch_update_records(self, app_token: str, table_id: str, records_data: List[Dict[str, Any]],
                             user_access_token: Optional[str] = None) -> Dict[str, Any]:

        app_table_records = []
        for item in records_data:
            rec = AppTableRecord.builder() \
                .record_id(item.get("record_id")) \
                .fields(item.get("fields")) \
                .build()
            app_table_records.append(rec)

        request = BatchUpdateAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(BatchUpdateAppTableRecordRequestBody.builder().records(app_table_records).build()) \
            .build()

        response = self.client.bitable.v1.app_table_record.batch_update(request,
                                                                        option=self._get_option(user_access_token))
        return self._handle_response(response, "batch_update_records")

    def batch_delete_records(self, app_token: str, table_id: str, record_ids: List[str],
                             user_access_token: Optional[str] = None) -> Dict[str, Any]:

        request = BatchDeleteAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(BatchDeleteAppTableRecordRequestBody.builder().records(record_ids).build()) \
            .build()

        response = self.client.bitable.v1.app_table_record.batch_delete(request,
                                                                        option=self._get_option(user_access_token))
        return self._handle_response(response, "batch_delete_records")

    def batch_get_records(self,
                          app_token: str,
                          table_id: str,
                          record_ids: List[str],
                          user_id_type: str = "open_id",
                          with_shared_url: bool = True,
                          automatic_fields: bool = True,
                          user_access_token: Optional[str] = None) -> Dict[str, Any]:

        request = BatchGetAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(BatchGetAppTableRecordRequestBody.builder()
                          .record_ids(record_ids)
                          .user_id_type(user_id_type)
                          .with_shared_url(with_shared_url)
                          .automatic_fields(automatic_fields)
                          .build()) \
            .build()

        response = self.client.bitable.v1.app_table_record.batch_get(request,
                                                                     option=self._get_option(user_access_token))
        return self._handle_response(response, "batch_get_records")

    def send_message(self,
                     receive_id: str,
                     content: str,
                     msg_type: str = "text",
                     receive_id_type: str = "open_id",
                     uuid: Optional[str] = None,
                     user_access_token: Optional[str] = None) -> Dict[str, Any]:

        if msg_type == "text" and not content.strip().startswith("{"):
            content_json = json.dumps({"text": content})
        else:
            content_json = content

        body_builder = CreateMessageRequestBody.builder() \
            .receive_id(receive_id) \
            .msg_type(msg_type) \
            .content(content_json)

        if uuid:
            body_builder.uuid(uuid)

        request = CreateMessageRequest.builder() \
            .receive_id_type(receive_id_type) \
            .request_body(body_builder.build()) \
            .build()

        response = self.client.im.v1.message.create(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "send_message")

    def get_chat_info(self, chat_id: str, user_access_token: Optional[str] = None) -> Dict[str, Any]:
        request = GetChatRequest.builder() \
            .chat_id(chat_id) \
            .build()

        response = self.client.im.v1.chat.get(request, option=self._get_option(user_access_token))
        return self._handle_response(response, "get_chat_info")

    def get_chat_members(self,
                         chat_id: str,
                         member_id_type: str = "open_id",
                         page_size: int = 20,
                         page_token: Optional[str] = None,
                         user_access_token: Optional[str] = None) -> Dict[str, Any]:

        request_builder = GetChatMembersRequest.builder() \
            .chat_id(chat_id) \
            .member_id_type(member_id_type) \
            .page_size(page_size)

        if page_token:
            request_builder.page_token(page_token)

        response = self.client.im.v1.chat_members.get(request_builder.build(),
                                                      option=self._get_option(user_access_token))
        return self._handle_response(response, "get_chat_members")

    def list_messages(self,
                      container_id: str,
                      container_id_type: str = "chat",
                      start_time: Optional[str] = None,
                      end_time: Optional[str] = None,
                      sort_type: str = "ByCreateTimeAsc",
                      page_size: int = 20,
                      page_token: Optional[str] = None,
                      user_access_token: Optional[str] = None) -> Dict[str, Any]:

        request_builder = ListMessageRequest.builder() \
            .container_id_type(container_id_type) \
            .container_id(container_id) \
            .sort_type(sort_type) \
            .page_size(page_size)

        if start_time:
            request_builder.start_time(start_time)
        if end_time:
            request_builder.end_time(end_time)
        if page_token:
            request_builder.page_token(page_token)

        response = self.client.im.v1.message.list(request_builder.build(), option=self._get_option(user_access_token))
        return self._handle_response(response, "list_messages")


# 使用示例

# if __name__ == "__main__":
#     APP_ID = "app_id"
#     APP_SECRET = "app_secret"
#
#     # 示例 ID
#     APP_TOKEN = "bascnxxxxxxxxxx"
#     TABLE_ID = "tblxxxxxxxxxxxxx"
#     CHAT_ID = "oc_xxxxxxxxxxxxxx"
#     OPEN_ID = "ou_xxxxxxxxxxxxxx"
#
#     manager = FeishuAPIManager(APP_ID, APP_SECRET, log_level=lark.LogLevel.DEBUG)
#
#     try:
#         print("\n>>> Sending Message...")
#
#         manager.send_message(OPEN_ID, "你好，这是测试消息", receive_id_type="open_id")
#
#         manager.send_message(
#             receive_id=OPEN_ID,
#             content='{"text":"test content with uuid"}',
#             msg_type="text",
#             receive_id_type="open_id",
#             uuid="a0d69e20-1dd1-458b-k525-dfeca4015204"
#         )
#
#     except Exception as e:
#         print(f"An error occurred: {e}")
