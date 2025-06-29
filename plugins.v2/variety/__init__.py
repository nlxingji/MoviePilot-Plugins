from typing import Any, List, Dict, Tuple
from xml.etree.ElementTree import Element, SubElement, tostring, parse
import xml.dom.minidom as minidom
import os

from playwright.sync_api import expect

from app.core.config import settings
from app.core.event import eventmanager, Event
from app.db.downloadhistory_oper import DownloadHistoryOper
from app.db.models.downloadhistory import DownloadFiles
from app.db.subscribe_oper import SubscribeOper
from app.db.transferhistory_oper import TransferHistoryOper
from app.helper.subscribe import SubscribeHelper
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.context import MediaInfo
from app.schemas.transfer import TransferInfo
from app.schemas.types import EventType, ChainEventType
from app.schemas import Notification, MediaType
from app.chain import ChainBase


import time

class EventHandler:
    def __init__(self):
        self.last_event_time = {}

    def is_recent(self, key, threshold=5):
        now = time.time()
        if key in self.last_event_time and now - self.last_event_time[key] < threshold:
            return True
        self.last_event_time[key] = now
        return False

handler = EventHandler()

class Variety(_PluginBase):
    # 插件名称
    plugin_name = "综艺刮削"
    # 插件描述
    plugin_desc = "综艺文件智能刮削"
    # 插件图标
    plugin_icon = "actor.png"
    # 插件版本
    plugin_version = "1.0.0"
    # 插件作者
    plugin_author = "nlxingji"
    # 作者主页
    author_url = "https://github.com/nlxingji"
    # 插件配置项ID前缀
    plugin_config_prefix = "variety_"
    # 加载顺序
    plugin_order = 15
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    openai = None
    _enabled = True
    _proxy = False
    _compatible = False
    _recognize = False
    _openai_url = None
    _openai_key = None
    _model = None
    # 存储多个API密钥
    _api_keys = []
    # 当前使用的密钥索引
    _current_key_index = 0
    # 密钥失效状态
    _key_status = {}
    # 是否发送通知
    _notify = False
    # 自定义提示词
    _customize_prompt = '接下来我会给你一个电影或电视剧的文件名，你需要识别文件名中的名称、版本、分段、年份、分瓣率、季集等信息，并按以下JSON格式返回：{"name":string,"version":string,"part":string,"year":string,"resolution":string,"season":number|null,"episode":number|null}，特别注意返回结果需要严格附合JSON格式，不需要有任何其它的字符。如果中文电影或电视剧的文件名中存在谐音字或字母替代的情况，请还原最有可能的结果。'

    def init_plugin(self, config: dict = None):
        self._enabled = True
        self.downloadHistoryOper = DownloadHistoryOper()
        self.transferHistoryOper = TransferHistoryOper()
        self.subscribe = SubscribeOper()
        self.chain = ChainBase()
        logger.info("插件已加载")
        # if config:
        #     self._enabled = config.get("enabled")
        #     self.downloadHistoryOper = DownloadHistoryOper()
        # self._proxy = config.get("proxy")
        # self._compatible = config.get("compatible")
        # self._recognize = config.get("recognize")
        # self._openai_url = config.get("openai_url")
        # self._openai_key = config.get("openai_key")
        # self._model = config.get("model")
        # self._notify = config.get("notify")
        # self._customize_prompt = config.get("customize_prompt")
        # 处理多个API密钥

    # def init_openai(self, api_key):
    #     """
    #     初始化OpenAI客户端
    #     """
    #     if self._openai_url and api_key:
    #         self.openai = OpenAi(api_key=api_key, api_url=self._openai_url,
    #                              proxy=settings.PROXY if self._proxy else None,
    #                              model=self._model, compatible=bool(self._compatible), customize_prompt=self._customize_prompt)
    #         logger.info(f"ChatGPT插件初始化API客户端成功")
    #         return True
    #     return False

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'proxy',
                                            'label': '使用代理服务器',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'compatible',
                                            'label': '兼容模式',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'recognize',
                                            'label': '辅助识别',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'notify',
                                            'label': '开启通知',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'openai_url',
                                            'label': 'OpenAI API Url',
                                            'placeholder': 'https://api.openai.com',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'openai_key',
                                            'label': 'API密钥 (多个密钥以逗号分隔)',
                                            'placeholder': 'sk-xxx,sk-yyy'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'model',
                                            'label': '自定义模型',
                                            'placeholder': 'gpt-3.5-turbo',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12},
                                'content': [
                                    {
                                        'component': 'VTextarea',
                                        'props': {
                                            'rows': 2,
                                            'auto-grow': True,
                                            'model': 'customize_prompt',
                                            'label': '辅助识别提示词',
                                            'hint': '在辅助识别时的给AI的提示词',
                                            'clearable': True,
                                            'persistent-hint': True,
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '开启插件后，消息交互时使用请[问帮你]开头，或者以？号结尾，或者超过10个汉字/单词，则会触发ChatGPT回复。'
                                                    '开启辅助识别后，内置识别功能无法正常识别种子/文件名称时，将使用ChatGTP进行AI辅助识别，可以提升动漫等非规范命名的识别成功率。'
                                                    '支持输入多个API密钥（以逗号分隔），在密钥调用失败时将自动切换到下一个可用密钥。'
                                                    '开启通知选项后，将在API密钥调用失败时发送系统通知。'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "proxy": False,
            "compatible": False,
            "recognize": False,
            "notify": False,
            "openai_url": "https://api.openai.com",
            "openai_key": "",
            "model": "gpt-3.5-turbo",
            "customize_prompt": '接下来我会给你一个电影或电视剧的文件名，你需要识别文件名中的名称、版本、分段、年份、分瓣率、季集等信息，并按以下JSON格式返回：{"name":string, '
                                '"version":string,"part":string,"year":string,"resolution":string,"season":number|null,"episode":number|null}，特别注意返回结果需要严格附合JSON格式，不需要有任何其它的字符。如果中文电影或电视剧的文件名中存在谐音字或字母替代的情况，请还原最有可能的结果。'
        }

    def get_page(self) -> List[dict]:
        pass

    def write_or_update_nfo(self, nfo_path, tmdbid, title, aired, season, episode):
        uniqueid = tmdbid + 2369150  # 自定义 ID
        time.sleep(10)
        # 如果文件存在，尝试读取并更新
        if os.path.exists(nfo_path):
            logger.info(f"已存在 NFO 文件：{nfo_path}，尝试更新...")
            try:
                tree = parse(nfo_path)
                root = tree.getroot()

                def update_or_create(tag, value, attrib=None):
                    elem = root.find(tag)
                    if elem is None:
                        elem = SubElement(root, tag, attrib or {})
                    if attrib:
                        elem.attrib.update(attrib)
                    elem.text = value

                update_or_create("uniqueid", str(uniqueid), {
                                 "type": "tmdb", "default": "true"})
                update_or_create("tmdbid", str(tmdbid))
                update_or_create("title", title)
                update_or_create("plot", f"<![CDATA[{title}]]>")
                update_or_create("outline", f"<![CDATA[{title}]]>")
                update_or_create("aired", aired[:10])
                update_or_create("year", str(aired.split("-")[0]))
                update_or_create("season", str(int(season.replace("S", ""))))
                update_or_create("episode", str(int(episode.replace("E", ""))))
                update_or_create("rating", "0")

                # 缩进保存
                rough_string = tostring(root, encoding="utf-8")
                reparsed = minidom.parseString(rough_string)
                xml_output = reparsed.toprettyxml(
                    indent="  ", encoding="utf-8").decode("utf-8")

                xml_output = xml_output.replace(
                    "&lt;![CDATA[", "<![CDATA[").replace("]]&gt;", "]]>")

                with open(nfo_path, "w", encoding="utf-8") as f:
                    f.write(xml_output)

                print(f"已更新 NFO 文件：{nfo_path}")
                return

            except Exception as e:
                print(f"更新失败，尝试重建：{nfo_path}，原因：{e}")

        # 不存在或更新失败则创建
        logger.info(f"不存在 NFO 文件：{nfo_path}，尝试创建...")
        root = Element("episodedetails")

        SubElement(root, "uniqueid", {
                   "type": "tmdb", "default": "true"}).text = str(uniqueid)
        SubElement(root, "tmdbid").text = str(tmdbid)
        SubElement(root, "title").text = title
        SubElement(root, "plot").text = f"<![CDATA[{title}]]>"
        SubElement(root, "outline").text = f"<![CDATA[{title}]]>"
        SubElement(root, "aired").text = aired[:10]
        SubElement(root, "year").text = str(aired.split("-")[0])
        SubElement(root, "season").text = str(int(season.replace("S", "")))
        SubElement(root, "episode").text = str(int(episode.replace("E", "")))
        SubElement(root, "rating").text = "0"

        rough_string = tostring(root, encoding="utf-8")
        reparsed = minidom.parseString(rough_string)
        xml_output = reparsed.toprettyxml(
            indent="  ", encoding="utf-8").decode("utf-8")

        xml_output = xml_output.replace(
            "&lt;![CDATA[", "<![CDATA[").replace("]]&gt;", "]]>")

        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write(xml_output)

        print(f"已创建 NFO 文件：{nfo_path}")

    @eventmanager.register(EventType.TransferComplete)
    def add_nfo(self, event: Event):
        if not self._enabled:
            return

        # {
        #     'fileitem': task.fileitem,
        #     'meta': task.meta,
        #     'mediainfo': task.mediainfo,
        #     'transferinfo': transferinfo,
        #     'downloader': task.downloader,
        #     'download_hash': task.download_hash,
        # }
        fileitem = event.event_data.get("fileitem")
        meta = event.event_data.get("meta")
        transferinfo: TransferInfo = event.event_data.get("transferinfo")
        mediainfo: MediaInfo = event.event_data.get("mediainfo")
        hash = event.event_data.get("download_hash")
        
        if handler.is_recent(f"add_nfo_{transferinfo.fileitem.path}"):
            logger.info(f"最近添加过NFO，跳过")
            return
        logger.info(transferinfo.fileitem.path)
        
        if mediainfo.category != "综艺":
            logger.info(f"识别到非综艺文件，不添加NFO")
            return
        
        
        if hash is None:
            logger.info(f"未识别到downlaod hash")
            DownloadFiles = self.downloadHistoryOper.get_files_by_fullpath(
                os.path.abspath(transferinfo.fileitem.path))
            for item in DownloadFiles:
                logger.info(item.fullpath)
                if item.fullpath == transferinfo.fileitem.path:
                    hash = item.download_hash
                    logger.info(f"获取到hash{hash}")
                    break
        else:
            logger.info(f"识别到downlaod hash")
        
        
        if hash is None:
            logger.info(f"最终未识别到downlaod hash")
            return
        
        downloadInfo = self.downloadHistoryOper.get_by_hash(hash)
        if downloadInfo.media_category == "综艺":
            transferHistory = self.transferHistoryOper.list_by_hash(hash)
            raw_title = downloadInfo.torrent_description.replace("｜", "|")
            logger.info(raw_title)
            # 再分割成列表
            title_parts = raw_title.split("|")
            for item in transferHistory:
                title = f"第{item.episodes.replace('E','')}集.{title_parts[-1]}"
                path = item.dest.replace("mkv", "nfo").replace("mp4", "nfo")
                try:
                    self.write_or_update_nfo(
                        path, item.tmdbid, title, item.date, item.seasons,  item.episodes)
                except Exception as e:
                    logger.info(f"Error:{e}")
                
                # os.remove(item.dest)
                # os.link(item.src,item.dest)
        
        logger.info("任务处理完成")

    @eventmanager.register(EventType.SubscribeAdded)
    @eventmanager.register(EventType.SubscribeModified)
    def modify_subscribe(self, event: Event):
        if not self._enabled:
            return
        id = event.event_data.get("subscribe_id")
        subscribe = self.subscribe.get(id)
        if handler.is_recent(f"modify_subscribe_{id}"):
            logger.info(f"最近修改过订阅，跳过")
            return
    
        logger.info(f"监测到订阅信息:{subscribe.name}")
        try:
            media_type = {mt.value: mt for mt in MediaType}.get(
                subscribe.type, MediaType.UNKNOWN)
            mediaInfo = self.chain.tmdb_info(subscribe.tmdbid, media_type)
            if (subscribe.media_category == "综艺" or mediaInfo['genres'][0]['id'] in [10764, 10767]) and subscribe.total_episode < 100:
                self.subscribe.update(id, {"media_category": "综艺", "sites": [
                                      11], "total_episode": 100, "manual_total_episode": 100, "keyword": ""})
                logger.info(f"订阅:{subscribe.name}已更新")
        except Exception as e:
            logger.info(f"Error: {e}")

    def stop_service(self):
        """
        退出插件
        """
        pass
