import requests
from bs4 import BeautifulSoup
import os
import sys
import re
import json
import prettytable as pt

HELP_DOC_CN = '''
bili-dl: bilibili视频下载工具
Version: 1.0 Beta | Author: Muhz
命令选项:
    -m: 下载指定id的视频或音频。
        如果输入 {视频id}+{音频id}, 如 80+280, 视频与音频会被自动合并为mp4文件。
    -i: 下载视频简介。
    -c: 下载视频封面。
    -o: 指定保存到的路径。
使用方法:
    1. bili-dl {URL或BV}             // 查看资源列表
    2. bili-dl [options] {URL或BV}
'''

HEADER = {
    "authority": "upos-sz-mirrorcoso1.bilivideo.com",
    "range": "bytes=0-",
    "referer": "https://www.bilibili.com/",
    "origin": "https://www.bilibili.com",
    "if-range": "2403be9af63370d0358a11e39adb93ef",
    "accept-encoding": "identity",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36 Edg/88.0.705.74",
}

# TODO: 登录功能
# cookie = ""

FFMPEG = "ffmpeg.exe"

def bv2url(bv):
    url = "https://www.bilibili.com/video/" + bv
    return url

def get(url):
    """Get a downloader for web page.

    Args:
        url: the url of video web page, like `https://www.bilibili.com/video/BV114514`.

    Returns:
        a new `Downloader` object.
    """
    return Downloader(url)

def combine(input1, input2, output, ffmpeg=None):
    """Combine video and audio uses ffmpeg.

    Args:
        input1, input2: video and audio file.
        output: output video file.
        ffmpeg: path of ffmpeg.exe.
    """
    if ffmpeg is None:
        ffmpeg = FFMPEG  # default
    cmd = f'{FFMPEG} -i {input1} -i {input2} -c copy {output}'
    code = os.system(cmd)
    if code != 0:  # commond execute failed.
        raise RuntimeError("ffmpeg run failed.")

class IdError(ValueError):
    ALARM = "未找到指定id的文件。"

class Downloader:
    """The media downloader for Bilibili.
    """
    def __init__(self, url):
        #self.sess = requests.Session()
        #HEADER["cookie"] = cookie
        r = requests.get(url, headers=HEADER)
        soup = BeautifulSoup(r.text, "lxml")

        self.max_kbps = None
        self.download_path = os.path.abspath("./")
        if not os.path.exists(self.download_path):
            os.mkdir(self.download_path)

        self.title = soup.find("h1")["title"]
        self.info = soup.find(class_="info").text
        self.cover = soup.find(attrs={"itemprop": "image"})["content"]
        self.__playinfo = soup.find(text=re.compile("window.__playinfo__"))[20:]

        self.file_name = self.title
        self.video_list, self.audio_list = self.__get_media_list()

    def set_output(self, path):
        """Set output path and filename.
        """
        self.download_path = path

    def __get_media_list(self):
        """Get video and audio resource list.

        Returns:  
            video_list: a list of videos info.  
            audio_list: a list of audios info.  
        """
        data = self.__playinfo
        list_dict = json.loads(data)["data"]["dash"]
        video_list = []
        audio_list = []

        best_index = 0
        best_quality = 0
        for index, video in enumerate(list_dict["video"]):
            base_url = video["base_url"]
            if re.match(".*-30*(.*).m4s", base_url) is not None:
                id_ = re.match(".*-30*(.*).m4s", base_url).group(1)
            else:
                id_ = video["id"]
            backup_url = video["backup_url"]
            bandwidth = video["bandwidth"]
            if bandwidth > best_quality:
                best_index = index
                best_quality = bandwidth
            codecs = video["codecs"]
            width = video["width"]
            height = video["height"]
            frame_rate = video["frame_rate"]

            video_list.append({
                "id": id_,
                "is_best": False,
                "url_list": [base_url] + backup_url,
                "bandwidth": bandwidth,
                "codecs": codecs,
                "width": width,
                "height": height,
                "fps": frame_rate,
            })
        video_list[best_index]["is_best"] = True

        best_index = 0
        best_quality = 0
        for index, audio in enumerate(list_dict["audio"]):
            base_url = audio["base_url"]
            if re.match(".*-30*(.*).m4s", base_url) is not None:
                id_ = re.match(".*-30*(.*).m4s", base_url).group(1)
            else:
                id_ = audio["id"]
            backup_url = audio["backup_url"]
            bandwidth = audio["bandwidth"]
            if bandwidth > best_quality:
                best_index = index
                best_quality = bandwidth
            codecs = audio["codecs"]
            rate = bandwidth

            audio_list.append({
                "id": id_,
                "is_best": False,
                "url_list": [base_url] + backup_url,
                "bandwidth": bandwidth,
                "codecs": codecs,
                "rate": rate,
            })
        audio_list[best_index]["is_best"] = True

        return video_list, audio_list

    def download_media(self, id_):
        """Download video and audio by id.

        Args:
            id_: id of media in the list.
        """
        index = id_.find("+")
        if index != -1:
            id_1 = id_[0:index]
            id_2 = id_[index+1:]
            print(id_1)
            print(id_2)
            self.download_media(id_1)
            self.download_media(id_2)
            input_1 = os.path.join(self.download_path, f'{self.file_name}_{id_1}.m4s')
            input_2 = os.path.join(self.download_path, f'{self.file_name}_{id_2}.m4s')
            output = os.path.join(self.download_path, f'{self.file_name}_{id_1}+{id_2}.mp4')
            combine(input_1, input_2, output)
            return
        
        for media in self.video_list + self.audio_list:
            if media["id"] == id_:
                url_list = media["url_list"]
                break
        else:
            raise IdError("id was not found.")
        
        url = url_list[0]

        with requests.get(url, stream=True, headers=HEADER) as r:
            with open(os.path.join(self.download_path, f'{self.file_name}_{id_}.m4s'), "wb") as f:
                for chunk in r.iter_content(chunk_size=self.max_kbps):
                    if chunk:
                        f.write(chunk)

    def download_info(self):
        """Download video info into txt file.
        """
        with open(os.path.join(self.download_path, f'{self.file_name}_info.txt'), "w", encoding="utf-8") as f:
            f.write(f'[title]\n{self.title}\n[info]\n{self.info}')
    
    def download_cover(self):
        """Download cover image of video.
        """
        r = requests.get(self.cover, headers=HEADER)
        with open(os.path.join(self.download_path, f'{self.file_name}_cover.png'), "wb") as f:
            f.write(r.content)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        doc = HELP_DOC_CN
        print(doc)
    else:
        param_list = sys.argv[1:-1]
        if re.match("BV.*", sys.argv[-1]):
            url = bv2url(sys.argv[-1])

        try:
            downloader = get(url)
        except:
            print("获取视频信息失败")

        param_dict = {
            "-o": [downloader.set_output, None],
            "-m": [downloader.download_media, None],
            "-i": [downloader.download_info, None],
            "-c": [downloader.download_cover, None],
        }

        if len(sys.argv) == 2:
            # print media info.
            table = pt.PrettyTable()
            table.field_names = ["id", "type", "quality", "code", ]
            for video in downloader.video_list:
                quality = f'{video["height"]}, {video["fps"]}'
                flag = "(best)" if video["is_best"] else ""
                table.add_row([video["id"] + flag, "video", quality, video["codecs"]])
            for audio in downloader.audio_list:
                quality = audio["bandwidth"]
                flag = "(best)" if audio["is_best"] else ""
                table.add_row([audio["id"] + flag, "audio", quality, audio["codecs"]])
            print(table)

        else :
            # download
            for index, option in enumerate(param_list):
                if option in param_dict.keys():
                    if option == "-m":
                        try:
                            param_dict[option][1] = param_list[index + 1]
                        except:
                            print("请指定id")
                    else:
                        param_dict[option][1] = 1

            for method, param in param_dict.values():
                if param is not None:
                    try:
                        method()
                    except TypeError:
                        try:
                            method(param)
                        except IdError as e:
                            print(e.ALARM)
