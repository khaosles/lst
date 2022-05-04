#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Project ：olympic_winter_games 
@File ：tpw.py
@IDE  ：PyCharm 
@Author ：yherguot
@Date ：2022/5/3 11:47 PM 
@Desc: 
"""

import os

import numpy as np
from configobj import ConfigObj
import xarray as xr
from datetime import datetime

baseDir = os.path.dirname(os.path.realpath(__file__))
configFile = os.path.join(baseDir, '../conf/config.cfg')
config = ConfigObj(configFile)

# 待提取范围
xMin = float(config['RANGE']['X_MIN'])
xMax = float(config['RANGE']['X_MAX'])
yMin = float(config['RANGE']['Y_MIN'])
yMax = float(config['RANGE']['Y_MAX'])
RES = 2.5

def readTPW(file, ymd):
    # 打开数据集
    dt = xr.open_dataset(file, engine='netcdf4')
    # 获取数据
    pr = dt.get('pr_wtr')
    # 数据经度
    lon = pr.lon
    # 数据纬度
    lat = pr.lat
    # 数据时间
    time = pr.time.data
    # 数据
    data = pr.data
    # 获取与输入最接近的时间
    time = list(map(lambda t: abs((datetime.strptime(str(t).split('.')[0], "%Y-%m-%dT%H:%M:%S") - datetime.strptime(ymd, "%Y%m%d")).days), time))
    idx = time.index(min(time))
    # 计算研究区范围
    xOffset = int((xMin - lon[0]) / RES)
    yOffset = int((lat[0] - yMax) / RES)
    rows = int((xMax - xMin) / RES + 0.5)
    cols = int((yMax - yMin) / RES + 0.5)
    # 提取并返回结果
    return np.nanmean(data[idx, yOffset:yOffset+cols, xOffset:xOffset+rows])


if __name__ == '__main__':
    file = r'/Volumes/T7/winter/LST_FITTING/pr_wtr.eatm.2021.nc'
    print(readTPW(file, '20210908'))
