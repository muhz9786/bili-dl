import bilidl

URL = "https://www.bilibili.com/video/BV1FK4y1D7ja"
#URL = "https://www.bilibili.com/video/BV1Nz4y1C7Ta"

dl = bilidl.get(URL)

dl.download_media("80")
