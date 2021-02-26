import requests
from bs4 import BeautifulSoup
import os
import sys
import time
import re
import json

HEADER = {
    "authority": "upos-sz-mirrorcoso1.bilivideo.com",
    "range": "bytes=0-",
    "referer": "https://www.bilibili.com/",
    "origin": "https://www.bilibili.com",
    "if-range": "2403be9af63370d0358a11e39adb93ef",
    "accept-encoding": "identity",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36 Edg/88.0.705.74",
}
cookie = "_uuid=15F39D72-278A-752B-C188-01AC2FAEC51D12422infoc; buvid3=C2C61D20-6DD4-413D-B354-A9C9C017D6B3184997infoc; buvid_fp=C2C61D20-6DD4-413D-B354-A9C9C017D6B3184997infoc; SESSDATA=ba2c89ca%2C1629568877%2Cf9a68%2A21; bili_jct=7f3532b9c9dccd54d264d5f4d95afd55; DedeUserID=6670765; DedeUserID__ckMd5=216ed540b0210a77; sid=6fzaup96; LIVE_BUVID=AUTO8816140171651705; CURRENT_FNVAL=80; blackside_state=1; rpdid=|(um|l||JJ)~0J'uYuR|ku|RR; fingerprint=d8db56ee518e8fbd444e1edd760400d1; buvid_fp_plain=C2C61D20-6DD4-413D-B354-A9C9C017D6B3184997infoc; dy_spec_agreed=1; CURRENT_QUALITY=112; finger=-166317360; bp_video_offset_6670765=496015959025095618; bsource=search_bing; PVID=14; bp_t_offset_6670765=496189256659689793"
#INTRO_API = "https://api.bilibili.com/x/web-interface/archive/desc?bvid="

def get(url):
    return Downloader(url)

class IdError(ValueError):
    pass

class Downloader:
    def __init__(self, url):
        #self.sess = requests.Session()
        HEADER["cookie"] = cookie
        r = requests.get(url, headers=HEADER)
        soup = BeautifulSoup(r.text, "lxml")
        self.max_rate = None
        self.info = soup.find(class_="info").text
        self.image = soup.find(attrs={"itemprop": "image"})["content"]
        self.playinfo = soup.find(text=re.compile("window.__playinfo__"))[20:]
        self.video_list, self.audio_list = self.get_media_list()

    def get_media_list(self):
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
        for media in self.video_list + self.audio_list:
            if media["id"] == id_:
                url_list = media["url_list"]
                break
        else:
            raise IdError("id not found.")
        
        url = url_list[0]
        with requests.get(url, stream=True, headers=HEADER) as r:
            with open("./video.mp4", "wb") as f:
                for chunk in r.iter_content(chunk_size=self.max_rate):
                    if chunk:
                        f.write(chunk)
                        #time.sleep(sleep_time)

