import bilidl
import json

URL = "https://www.bilibili.com/video/BV1FK4y1D7ja"

dl = bilidl.get(URL)

#with open("./list.json", "w") as f:
#    f.write(json.dumps(dl.video_list))

dl.download_media("102")

