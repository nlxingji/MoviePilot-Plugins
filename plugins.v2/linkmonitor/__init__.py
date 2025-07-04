from typing import Optional, List

from app.plugins import _PluginBase
from app.db.transferhistory_oper import TransferHistoryOper
from datetime import datetime, timedelta

transferhistory_oper = TransferHistoryOper()

transferhistory_oper.list_by_date()


class LinkMonitor(_PluginBase):
    # 插件名称
    plugin_name = "目录监控"
    # 插件描述
    plugin_desc = "监控目录文件变化，自动转移链接。"
    # 插件图标
    plugin_icon = "Linkease_A.png"
    # 插件版本
    plugin_version = "3.0.0"
    # 插件作者
    plugin_author = "nlxingji"
    # 作者主页
    author_url = "https://github.com/nlxingji"
    # 插件配置项ID前缀
    plugin_config_prefix = "linkmonitor_"
    # 加载顺序
    plugin_order = 4
    # 可使用的用户级别
    auth_level = 1

    def init_plugin(self, config: dict = None):
        self.transferhis = TransferHistoryOper()


    def sync_file(self):
        start = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        transfer_history = self.transferhis.list_by_date(start)
        transfer_history_list = [item.src for item in transfer_history]




    def get_page(self) -> Optional[List[dict]]:
        pass


    def get_state(self) -> bool:
        return True


    def stop_plugin(self):
        pass



