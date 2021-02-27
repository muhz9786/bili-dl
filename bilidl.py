import requests
from bs4 import BeautifulSoup
import os
import sys
import time
import re
import json
import prettytable as pt

HELP_DOC = '''
bili-dl: Bilibili video download toolkit. 
Version: 1.0 Beta | Author: Muhz
Option:
    -m: Download video and audio by id. 
        If input {vedio id}+{audio id}, like 80+280, they will be combined in a .mp4 file by ffmpeg.
    -i: Download video info into .txt file.
    -c: Download cover image of video.
    -o: Assign the output path and filename.
    -v: Set max rate to limit download speed.
Uasge:
    1. bili-dl {URL}            // Only look media list.
    2. bili-dl [options] {URL}
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

# cookie = ""

FFMPEG = "ffmpeg.exe"

def get(url):
    """
    Send a get request and init a new `Downloader` object.

    url: the url of video website, like `https://www.bilibili.com/video/BV114514`.

    Return:
    a new `Downloader` object
    """
    return Downloader(url)

def combine(input1, input2, output, ffmpeg=FFMPEG):
    """
    Combine video and audio uses ffmpeg.

    input1, input2: video and audio input.

    ffmpeg: path of ffmpeg.exe.
    """
    cmd = f'{FFMPEG} -i {input1} -i {input2} -c copy {output}'
    code = os.system(cmd)
    if code != 0:
        raise RuntimeError("ffmpeg run failed.")

class IdError(ValueError):
    pass

class Downloader:
    """
    The media downloader of Bilibili.
    """
    def __init__(self, url):
        #self.sess = requests.Session()
        #HEADER["cookie"] = cookie
        r = requests.get(url, headers=HEADER)
        soup = BeautifulSoup(r.text, "lxml")

        self.max_kbps = None
        self.download_path = "./"
        if not os.path.exists(self.download_path):
            os.mkdir(self.download_path)

        self.title = soup.find("h1")["title"]
        self.info = soup.find(class_="info").text
        self.cover = soup.find(attrs={"itemprop": "image"})["content"]
        self.playinfo = soup.find(text=re.compile("window.__playinfo__"))[20:]

        self.file_name = self.title
        self.video_list, self.audio_list = self.__get_media_list()

    def set_download_output(self, path):
        """
        Set output path and filename.
        """
        pass

    def set_download_speed(self, max_kbps):
        """
        Set max download speed.
        """
        pass

    def __get_media_list(self):
        """
        Return:
        video_list: a list of videos info.
        audio_list: a list of audios info.
        """
        data = self.playinfo
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
            if video["frame_rate"] == "16000/544":
                frame_rate = 30
            elif video["frame_rate"] == "16000/256":
                frame_rate = 60
            else:
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
        """
        Download video and audio with id.

        id: id of media in the list.
        """
        for media in self.video_list + self.audio_list:
            if media["id"] == id_:
                url_list = media["url_list"]
                break
        else:
            raise IdError("id not found.")
        
        url = url_list[0]
        # TODO: 限速
        with requests.get(url, stream=True, headers=HEADER) as r:
            with open(f'{self.download_path}/{self.file_name}_{id_}.m4s', "wb") as f:
                for chunk in r.iter_content(chunk_size=self.max_kbps):
                    if chunk:
                        f.write(chunk)
                        #time.sleep(sleep_time)

    def download_info(self):
        """
        Download video info into txt file.
        """
        with open(f'{self.download_path}/{self.file_name}_info.txt', "w", encoding="utf-8") as f:
            f.write(f'[title]\n{self.title}\n[info]\n{self.info}')
    
    def download_cover(self):
        """
        Download cover image of video.
        """
        r = requests.get(self.cover, headers=HEADER)
        with open(f'{self.download_path}/{self.file_name}_cover.png', "wb") as f:
            f.write(r.content)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(HELP_DOC)
    else:
        param_list = sys.argv[1:-1]
        url = sys.argv[-1]

        downloader = Downloader(url)

        param_dict = {
            "-m": downloader.download_media,
            "-i": downloader.download_info,
            "-c": downloader.download_cover,
            "-o": downloader.set_download_output,
            "-v": downloader.set_download_speed,
        }

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

        for index, keyword in enumerate(param_list):
            if keyword in param_dict.keys():
                param_dict[keyword]()
                # TODO: 参数传递，注意方法调用顺序（先-o -v）