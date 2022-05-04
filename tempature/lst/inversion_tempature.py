#!usr/bin/env python
# -*- coding: utf-8 -*-

'''
    @author: khaosles
    @date: 2022/4/21  15:35
'''

import os
import getopt
import sys
import numpy as np

baseDir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(baseDir))

from tempature.lst.lst import LST
from tempature.utils.db import ParamQuery
from tempature.lst.fy3d import FY3D
from tempature.lst.fy4a import FY4A
from tempature.lst.modis import Modis
from tempature.lst.landsat8 import Landsat8
from tempature.lst.himawari8 import Himawari8
from tempature.lst.tpw import readTPW

dbpath = os.path.join(baseDir, '../resource', 'snow.db')
if not os.path.isfile(dbpath):
    print("Param database not exist.")
    sys.exit(1)
db = ParamQuery(dbpath)


def calcLst(lstObj: LST, lpw, sza, sensor, AT=3.0, AE=1.0):
    # 拟合参数
    paramArr = np.zeros((7, lstObj.shape0, lstObj.shape1))
    # 第1次模拟
    for yy in range(lstObj.shape0):
        for xx in range(lstObj.shape1):
            if isinstance(sza, np.ndarray):
                # 第1次模拟参数
                paramArr[:, yy, xx] = db.queryAW(lpw, sza[yy, xx], sensor, AT, AE)
            else:
                paramArr[:, yy, xx] = db.queryAW(lpw, sza, sensor, AT, AE)
    lst = lstObj.inversion(*paramArr)
    # 第2次模拟
    for yy in range(lstObj.shape0):
        for xx in range(lstObj.shape1):
            # 第2次模拟参数
            if isinstance(sza, np.ndarray):
                paramArr[:, yy, xx] = db.queryAWT(lpw, sza[yy, xx], lst[yy, xx], sensor, AT, AE)
            else:
                paramArr[:, yy, xx] = db.queryAWT(lpw, sza, lst[yy, xx], sensor, AT, AE)
    lstArr = lstObj.inversion(*paramArr)

    return lstArr


def main(args):
    """主程序"""

    # 解析参数
    try:
        options, args = getopt.getopt(args, "",
              ["l1file=", "geofile=", "clmfile=", "lpwfile=", "sensor=", "ymd=", "outfile="])
    except getopt.GetoptError as err:
        print(err)
        return -1
    # 初始化参数
    l1file, geofile, clmfile, sensor, lpwfile, ymd, outfile = [None] * 7
    for option, value in options:
        if option == "--l1file":
            l1file = value
        elif option == "--geofile":
            geofile = value
        elif option == "--clmfile":
            clmfile = value
        elif option == "--lpwfile":
            lpwfile = value
        elif option == "--sensor":
            sensor = value
        elif option == "--ymd":
            ymd = value
        elif option == "--outfile":
            outfile = value

    # 校验参数
    if not all([l1file, sensor, lpwfile, ymd, outfile]):
        print('param error')
        return -1
    # 校验输入文件
    if not all([os.path.isfile(file) for file in [l1file, lpwfile]]):
        print('FileNotFound')
        return -1
    # 校验传感器
    if sensor in ['fy4a', 'fy3d']:
        if not all([os.path.isfile(file) for file in [geofile, clmfile]]):
            print('FileNotFound')
            return -1
    elif sensor in ['modis', 'fy4a', 'fy3d', 'landsat8', 'himawari8']:
        pass
    else:
        print('sensor error')
        return -1
    # 日期
    if len(ymd) != 8:
        print('date error')
        return -1
    # 输出文件
    outpath = os.path.join(outfile)
    if not os.path.isdir(outpath):
        os.makedirs(outpath)
    try:
        # 实例化对象
        if sensor == 'modis':
            lst = Modis(l1file)
            zenith = lst.zenith
        elif sensor == 'fy4a':
            lst = FY4A(l1file, clmfile)
            zenith = lst.extractGEO(geofile)
        elif sensor == 'fy3d':
            lst = FY3D(l1file, geofile, clmfile)
            zenith = lst.zenith
        elif sensor == 'landsat8':
            lst = Landsat8(l1file)
            zenith = lst.zenith
        elif sensor == 'himawari8':
            lst = Himawari8(l1file)
            zenith = lst.zenith
        else:
            return -1

        # 水汽
        tpw = readTPW(lpwfile, ymd)
        # 反演lst
        lstArr = calcLst(lst, tpw, zenith, sensor.upper(), AT=3.0, AE=1.0)
        # 保存
        lst.saveImage(outfile, lstArr, lst.tran, lst.proj)
    except Exception as err:
        print(err)
        return -1


if __name__ == '__main__':
    """
    l1file = '/Volumes/T7/FY4A_DATA/L1/2021/20211107/FY4A-_AGRI--_N_DISK_1047E_L1-_FDI-_MULT_NOM_20211107000000_20211107001459_4000M_V0001.HDF'
    geofile = r'/Volumes/T7/FY4A_DATA/L1/2021/20211107/FY4A-_AGRI--_N_DISK_1047E_L1-_GEO-_MULT_NOM_20211107234500_20211107235959_4000M_V0001.HDF'
    clmfile = '/Volumes/T7/FY4A_DATA/L2/CLM/2021/20211107/FY4A-_AGRI--_N_DISK_1047E_L2-_CLM-_MULT_NOM_20211107000000_20211107001459_4000M_V0001.NC'
    sensor = 'fy4a'
    ymd = '20211107'
    tpwfile = '/Volumes/T7/winter/LST_FITTING/pr_wtr.eatm.2021.nc'
    outfile = ''
    """

    main(sys.argv[1:])
