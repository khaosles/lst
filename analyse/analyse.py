#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Project ：olympic_winter_games 
@File ：analyse.py
@IDE  ：PyCharm 
@Author ：yherguot
@Date ：2022/5/4 10:08 PM 
@Desc: 
"""

import os
import glob
import imageio

import numpy as np
from osgeo import gdal
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import matplotlib as mpl
basedir = os.path.dirname(os.path.abspath(__file__))
shp = os.path.join(basedir, 'resource/vector/CHINA_市_region')

def readdata(file):
    ds = gdal.Open(file)
    data = ds.ReadAsArray()
    xMin, xRes, _, yMax, _, yRes = ds.GetGeoTransform()

    xMax = xMin + xRes * data.shape[1]
    yMin = yMax + yRes * data.shape[0]

    del ds
    return data, (xMin, xMax, yMin, yMax)


def main(dir):
    timeList = list()
    meanList = list()
    stdList = list()
    dataList = list()
    ymd = 0
    (xMin, xMax, yMin, yMax) = [0] * 4
    # data
    for file in sorted(glob.glob(os.path.join(dir, '*.tif'))):
        ymd = os.path.basename(file).split('_')[-2][0:8]
        # timeList.append(int(os.path.basename(file).split('_')[-2][8:10]))
        timeList.append(os.path.basename(file).split('_')[-2][8:10])
        data, (xMin, xMax, yMin, yMax) = readdata(file)
        meanList.append(np.nanmean(data))
        stdList.append(np.nanstd(data))
        dataList.append(data)

    # +++++++++++++++++++++++++++++++++++++++
    # =============gif======================
    for data, time in zip(dataList, timeList):
        colormap = plt.get_cmap("jet")
        norm = mpl.colors.Normalize(250, 320)
        map = Basemap(llcrnrlon=xMin, llcrnrlat=yMin, urcrnrlon=xMax, urcrnrlat=yMax)
        map.imshow(data[::-1], cmap=colormap, norm=norm)
        plt.colorbar(fraction=0.05, pad=0.05)
        parallels = np.arange(int(yMin), int(yMax) + 1, .5)
        map.drawparallels(parallels, labels=[True, False, False, False], dashes=[1, 400])  #
        map.readshapefile(shp, 'v', default_encoding='gbk')
        meridians = np.arange(int(xMin), int(xMax) + 1, .5)  # 经线
        map.drawmeridians(meridians, labels=[False, False, False, True], dashes=[1, 400])
        plt.title('%s-%s' % (ymd, time))
        plt.savefig(os.path.join(basedir, 'tmp', '%s.png' % time))
        plt.show()
        plt.close()

    # +++++++++++++++++++++++++++++++++++++++
    # =============mean======================
    # plt.plot(timeList, meanList, label='Mean')
    # plt.title(ymd)
    # plt.legend()
    # plt.xlabel('Hour')
    # plt.ylabel('LST(K)')
    # plt.show()
    # +++++++++++++++++++++++++++++++++++++++
    # =============std======================
    # plt.plot(timeList, stdList, label='Std')
    # plt.title(ymd)
    # plt.legend()
    # plt.xlabel('Hour')
    # plt.ylabel('LST(K)')
    # plt.show()


def imgs2gif(dir, saveName, duration=None, loop=0, fps=None):
    """
    生成动态图片 格式为 gif
    :param imgPaths: 一系列图片路径
    :param saveName: 保存gif的名字
    :param duration: gif每帧间隔， 单位 秒
    :param fps: 帧率
    :param loop: 播放次数（在不同的播放器上有所区别）， 0代表循环播放
    :return:
    """
    imgPaths = sorted(glob.glob(os.path.join(dir, '*.png')))
    if fps:
        duration = 1 / fps
    images = [imageio.imread(str(img_path)) for img_path in imgPaths]
    imageio.mimsave(saveName, images, "gif", duration=duration, loop=loop)


if __name__ == '__main__':
    dir = '/Volumes/T7/winter/TestData/fy3d4a/outfir'
    main(dir)
    imgs2gif(os.path.join(basedir, 'tmp'), os.path.join(basedir, 'tmp', '20191030.gif'), duration=0.5)