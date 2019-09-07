#!/usr/bin/env python3
# -*- coding:utf-8

# ######## 安装模块 ######
# pip install requests 使用手册：http://docs.python-requests.org/zh_CN/latest/user/quickstart.html
# pip install BeautifulSoup4 使用手册：https://www.crummy.com/software/BeautifulSoup/bs4/doc/index.zh.html
# pip install html5lib 安装解析器
# pip install PyExecJS 安装执行js类库 执行报错编码有问题
# pip install js2py 更换类库执行js
# 爬取前面的时候不要一次太多，爬取的时候出现过卡住没有报错不明所以

import requests
from bs4 import BeautifulSoup
import os
import js2py
import json
from multiprocessing import Pool


domain = 'http://www.dm5.com'
# 每页参数
args = {}


class Vol(object):

    def __init__(self, name, url):
        self.name = name
        self.url = url


def get_vols():
    # 爬取漫画全卷目录
    start_url = domain + '/manhua-fengyunquanji/'
    vols = []
    res = requests.get(start_url)
    # print(res.text)
    soup = BeautifulSoup(res.text, "html5lib")
    for li_tag in soup.find(id='detail-list-select-1').find_all('li'):
        url = domain + li_tag.a.get('href')
        name = vol_name(li_tag.a.get_text())
        vol = Vol(name, url)
        vols.append(vol)
        # print(vols)
    return vols


def vol_name(s):
    # 去除空格
    return s.rstrip().replace("                    ", "")


def get_imgs(urls, imgs, dirPath, n=1):
    print("开始爬取第%d卷图片URL开始。。。" % n)
    # 获取第n页参数
    print("params参数：", n)
    parse_var(urls[n-1])
    # ajax请求
    params = {"cid": args["DM5_CID"], "page": n, "key": "", "language": 1, "gtk": 6, "_cid": args["DM5_CID"], "_mid": args["DM5_MID"], "_dt": args["DM5_VIEWSIGN_DT"], "_sign": args["DM5_VIEWSIGN"]}
    print("params参数：", params)
    url = domain + args["DM5_CURL"] + "chapterfun.ashx"
    headers = {"Referer": args["DM5_CURL"]}
    res = requests.get(url, params=params, headers=headers)
    print(res.url)
    print("res:", res.text)
    # eval()函数解析返回
    img_urls = js2py.eval_js(res.text)
    print("eval函数解析后结果：", img_urls)
    for img_url in img_urls:
        img_name = "%03d" % n + ".jpg"
        path = dirPath + "/" + img_name
        img = {"name": img_name, "url": img_url, "referer": domain + args["DM5_CURL"], "path": path}
        imgs.append(img)
        n = n + 1
    # 判断返回图片url个数 len
    if len(imgs) == len(urls):
        return imgs
    else:
        # 递归查询
        return get_imgs(urls, imgs, dirPath, (len(imgs)+1))


def get_next_url(url, urls):
    res = requests.get(url)
    soup = BeautifulSoup(res.text, 'html5lib')
    tag = soup.select("#chapterpager .current + a", limit=1)
    if len(tag):
        next_url = domain + tag[0].get("href")
        urls.append(next_url)
        # print(next_url)
        return get_next_url(next_url, urls)
    else:
        return urls


def get_vol_urls(url):
    # 每卷所有页urls
    vol_urls = []
    # 获取首页 url
    vol_urls.append(url)
    get_next_url(url, vol_urls)
    return vol_urls


def parse_var(url):
    print("解析 %s 页面开始。。。" % url)
    res = requests.get(url)
    # print(res.text)
    soup = BeautifulSoup(res.text, 'html5lib')
    tags = soup.find_all("script")
    for tag in tags:
        content = tag.text
        if content.find("var DM5_CID") < 0:
            continue
        # 先去除var再按;分割
        vs = content.replace("var", "").split(";")
        for v in vs:
            if v.find("=") > 0:
                # print("v:", v)
                arg = v.split("=")
                args[arg[0].strip()] = arg[1].strip().replace("\"", "").replace("\'", "")
        print(args)
        print("解析%s页面结束。。。" % url)


def img_download(img):
    print('开始下载图片 %s 。。。' % img["name"])
    if not os.path.exists(img["path"]):
        fp = open(img["path"], "wb")
    headers = {"Referer": img["referer"]}
    res = requests.get(img["url"], headers=headers)
    fp.write(res.content)
    fp.close()
    print('图片 %s 下载完成' % img["name"])


def write_json(vols):
    if not os.path.exists("data"):
        os.mkdir("data")
    with open("data/fy.json", "w", encoding='utf-8') as f:
        json.dump(vols, f, ensure_ascii=False)


def test():
    parse_var("http://www.dm5.com/m25536/")
    params = {"cid": args["DM5_CID"], "page": 1, "key": "", "language": 1, "gtk": 6, "_cid": args["DM5_CID"], "_mid": args["DM5_MID"],
              "_dt": args["DM5_VIEWSIGN_DT"], "_sign": args["DM5_VIEWSIGN"]}
    print("params参数：", params)
    url = domain + "/m25536/" + "chapterfun.ashx"
    headers = {"Referer": "http://www.dm5.com/m25536/"}
    res = requests.get(url, params=params, headers=headers)
    print(res.encoding)
    print(res.url)
    print("res:", res.text)
    imgs = js2py.eval_js(res.text)
    print("eval函数解析后结果：", imgs)


def multiprocess_download():
    with open("data/fy.json", "r", encoding='utf-8') as f:
        vols = json.load(f)
    # 多进程下载图片
    pool = Pool(20)
    for vol in vols:
        dirname = "images/" + vol["volName"]
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        for img in vol["imgs"]:
            pool.apply_async(img_download, (img,))
    pool.close()
    pool.join()
    print("图片下载完成。。。")


def multiprocess_parse(v):
    try:
        imgs = []
        vol_urls = get_vol_urls(v.url)
        path = "images/" + v.name
        get_imgs(vol_urls, imgs, path, 1)
        vol = {"volName": v.name, "volUrl": v.url, "imgs": imgs}
    except Exception:
        print("%s解析出现问题: \n" % v.name, Exception)
        vol = {"volName": v.name, "volUrl": v.url, "imgs": []}
    return vol


if __name__ == '__main__':
    # test()
    print('开始爬取。。。')
    vols = get_vols()
    # 爬取指定数目卷(第0卷)
    vs = vols[650:]
    # print("vs:", vs)
    vols_json = []
    # 多进程解析
    pool = Pool(20)
    # 线程池返回线程对象
    res_p = []
    for v in vs:
        p = pool.apply_async(multiprocess_parse, (v, ))
        res_p.append(p)
    pool.close()
    pool.join()
    for res in res_p:
        # 获取结果
        vols_json.append(res.get())
    # 将爬取的链接写入json文件
    write_json(vols_json)
    print("爬取完成。。。")
    # 多线程下载图片
    # multiprocess_download()

