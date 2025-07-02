import requests
import datetime
import os
import shutil
from dateutil import parser

# Emby 服务器配置
EMBY_URL = "http://10.10.10.10:8096"
API_KEY = "b9be8894aa0140258969c20b4462285a"
DAYS_THRESHOLD = 180

HEADERS = {"X-Emby-Token": API_KEY}

# 排除剧集列表
EXCLUDE_SERIES = [
    "Running Man",
    "One Piece",
    "Your Lie in April"  # 示例，可按需添加
]

# 获取所有媒体
def get_items(item_type):
    url = f"{EMBY_URL}/emby/Items"
    params = {
        "IncludeItemTypes": item_type,
        "Recursive": True,
        "Fields": "Path,DateCreated,PremiereDate,LastPlayedDate",
        "api_key": API_KEY
    }
    resp = requests.get(url, params=params, headers=HEADERS)
    resp.raise_for_status()
    return resp.json().get("Items", [])

# 删除文件
def delete_file(path):
    try:
        os.remove(path)
        print(f"[Delete File] {path}")
    except Exception as e:
        print(f"Failed to delete file {path}: {e}")

# 删除文件夹
def delete_folder(path):
    try:
        shutil.rmtree(path)
        print(f"[Delete Folder] {path}")
    except Exception as e:
        print(f"Failed to delete folder {path}: {e}")

# 处理电影
def process_movies():
    movies = get_items("Movie")
    now = datetime.datetime.now(datetime.timezone.utc)
    for movie in movies:
        last_played = movie.get("LastPlayedDate")
        path = movie.get("Path")
        print(movie)
        if not path:
            continue

        try:
            if last_played:
                last_played_date = parser.isoparse(last_played)
            else:
                last_played_date = parser.isoparse(movie["DateCreated"])

            days_diff = (now - last_played_date).days
            if days_diff > DAYS_THRESHOLD:
                print(f"[Movie] {movie['Name']} not watched for {days_diff} days. Deleting...")
                delete_file(path)
        except Exception as e:
            print(f"Error processing movie {movie['Name']}: {e}")

# 处理电视剧
def process_series():
    series_list = get_items("Series")
    now = datetime.datetime.now(datetime.timezone.utc)
    for series in series_list:
        series_name = series["Name"]

        # 检查是否在排除列表中
        if series_name in EXCLUDE_SERIES:
            print(f"[Exclude] Skipping series '{series_name}' as it's in exclude list.")
            continue

        series_id = series["Id"]
        path = series.get("Path")
        if not path:
            continue

        try:
            # 获取剧集
            url = f"{EMBY_URL}/emby/Shows/{series_id}/Episodes"
            params = {"api_key": API_KEY}
            resp = requests.get(url, params=params, headers=HEADERS)
            resp.raise_for_status()
            episodes = resp.json().get("Items", [])

            if not episodes:
                continue

            delete_series = True
            for ep in episodes:
                print(ep)
                last_played = ep.get("LastPlayedDate")
                if last_played:
                    last_played_date = parser.isoparse(last_played)
                else:
                    last_played_date = parser.isoparse(ep["DateCreated"])

                days_diff = (now - last_played_date).days
                if days_diff <= DAYS_THRESHOLD:
                    delete_series = False
                    break

            if delete_series:
                print(f"[Series] {series_name} all episodes not watched for over {DAYS_THRESHOLD} days. Deleting...")
                delete_folder(path)
        except Exception as e:
            print(f"Error processing series {series_name}: {e}")

# 主函数
def main():
    process_movies()
    process_series()

if __name__ == "__main__":
    process_series()