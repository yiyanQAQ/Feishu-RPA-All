import pymysql

class RPAStatusManager:
    def __init__(self):
        self.db_config = {
            'host': '',
            'user': '',
            'password': '',
            'database': 'RPA_State',
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }

    def sync_state(self, rpa_name, run_status, maintainer, error_log=None):
        if run_status == 1 and error_log:
            print("Note: 运行正常状态码为1时不能填写报错日志，已忽略该日志内容")
            error_log = None
        if run_status != 1 and not error_log:
            error_log = "Unknown error occurred."

        connection = pymysql.connect(**self.db_config)
        try:
            with connection.cursor() as cursor:
                sql = """
                      INSERT INTO RPA_State (rpa_name, run_status, error_log, maintainer)
                      VALUES (%s, %s, %s, %s) ON DUPLICATE KEY \
                      UPDATE \
                          run_status = \
                      VALUES (run_status), error_log = \
                      VALUES (error_log), maintainer = \
                      VALUES (maintainer), updated_at = CURRENT_TIMESTAMP \
                      """
                cursor.execute(sql, (rpa_name, run_status, error_log, maintainer))
            connection.commit()
            return True
        except Exception as e:
            print(f"Database Error: {e}")
            return False
        finally:
            connection.close()


def main(rpa_name, run_status, maintainer, error_log=None):
    RPAStatusManager().sync_state(rpa_name, run_status, maintainer, error_log)

# if __name__ == "__main__":
#     main("测试1",0,"火山","根据时间运行测试日志")