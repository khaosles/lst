#!usr/bin/env python
# -*- coding: utf-8 -*-

'''
    @author: khaosles
    @date: 2022/3/28  12:23
'''

import os
import numpy as np
from tqdm import tqdm
from datetime import datetime
from scipy import optimize as op
from glob import glob
import warnings
import random
import getopt
import sys

from utils.utils import *

warnings.filterwarnings('ignore')
PI = np.pi
SLOPE = 1


class Sun(object):

    def __init__(self, ymd):
        self.getYMD(ymd)

    def getYMD(self, ymd):
        self.year = int(ymd[0:4])
        self.month = int(ymd[4:6])
        self.day = int(ymd[6:8])

    def rise(self, lon, lat):

        zenith = 90.83333333

        # 1. first calculate the day of the year
        N1 = np.floor(275 * self.month / 9)
        N2 = np.floor((self.month + 9) / 12)
        N3 = (1 + np.floor((self.year - 4 * np.floor(self.year / 4) + 2) / 3))
        dayOfYear = N1 - (N2 * N3) + self.day - 30

        localOffset = np.floor(-1 * lon * 24 / 360)

        # 2. convert the longitude to hour value and calculate an approximate time
        lngHour = lon / 15
        t = dayOfYear + ((6 - lngHour) / 24)
        # if you want sunset time:
        # t = dayOfYear + ((18 - lngHour) / 24)
        M = (0.9856 * t) - 3.289

        # 4. calculate the Sun's true
        # NOTE: L potentially needs to be adjusted into the range [0,360) by adding/subtracting 360
        L = M + (1.916 * np.sin(M * 3.1415926 / 180)) + (0.020 * np.sin(2 * M * 3.1415926 / 180)) + 282.634

        L = L - 360

        # 5
        # NOTE: RA potentially needs to be adjusted into the range [0,360) by adding/subtracting 360
        # a. calculate the Sun's right ascension
        # RA = np.atan(0.91764 * np.tan(L))
        RA = (180 / 3.1415926) * np.arctan(0.91764 * np.tan(L * 3.1415926 / 180))

        # b. right ascension value needs to be in the same quadrant as L
        Lquadrant = (np.floor(L / 90)) * 90
        RAquadrant = (np.floor(RA / 90)) * 90
        RA = RA + (Lquadrant - RAquadrant)

        # c. right ascension value needs to be converted into hours
        RA = RA / 15

        # 6. calculate the Sun's declination
        sinDec = 0.39782 * np.sin(L * 3.1415926 / 180)
        cosDec = np.cos(np.arcsin(sinDec))

        # 7
        # a. calculate the Sun's local hour angle
        cosH = (np.cos(zenith * 3.1415926 / 180) - (sinDec * np.sin(lat * 3.1415926 / 180))) / (
                cosDec * np.cos(lat * 3.1415926 / 180))

        if (cosH > 1) or (cosH < -1):
            sunriseT = 0
        else:
            # the sun never rises on this location (on the specified date)

            # b. finish calculating H and convert into hours
            H = 360 - 180 / np.pi * np.arccos(cosH)
            # if you want sunset time:
            # H = 180/3.1415926 * np.arccos(cosH)
            H = H / 15

            # 8. calculate local mean time of rising/setting
            T = H + RA - (0.06571 * t) - 6.622

            # 9. adjust back to UTC
            UT = T - lngHour
            # NOTE: UT potentially needs to be adjusted into the range [0,24) by adding/subtracting 24

            # 10. convert UT value to local time zone of latitude/longitude
            # sunriseT = UT - localOffset
            sunriseT = UT

        # # 日出
        # sunriseT = '%02d%02d%02d' % (
        #     int(sunriseT),
        #     int((sunriseT - int(sunriseT)) * 3600) // 60,
        #     (sunriseT - int(sunriseT)) * 3600 % 60)

        return (sunriseT + 24) % 24


class Doy(object):
    MONTH31 = [1, 3, 5, 7, 8, 10, 12]
    MONTH30 = [4, 6, 9, 11]
    MONTHFEB = 2

    def __init__(self, ymd):
        self.getYMD(ymd)

    def getYMD(self, ymd):
        self.year = int(ymd[0:4])
        self.month = int(ymd[4:6])
        self.day = int(ymd[6:8])

    def isLeapYear(self, year):
        '''
        判断当前年份是不是闰年，年份公元后，且不是过大年份
        :param year: 年份
        :return: True 闰年， False 平年
        '''
        if year % 4 == 0 and year % 100 != 0 or year % 400 == 0:
            return True
        return False

    def validateParam(self, year, month, day):
        '''
        参数校验
        :param year: 年份
        :param month: 月份
        :param day: 日期
        :return: error_msg 错误信息，没有为空
        '''
        error_msg = u''
        if not isinstance(year, int) or year < 1:
            error_msg = u'年份输入不符合要求'
        if not isinstance(month, int) or month < 1 or month > 12:
            error_msg = u'月份输入不符合要求'
        if not isinstance(day, int) or day < 1 \
                or (month in Doy.MONTH31 and day > 31) \
                or (month in Doy.MONTH30 and day > 30) \
                or (month == Doy.MONTHFEB and (day > 29 if self.isLeapYear(year) else day > 28)):
            error_msg = u'日期输入不符合要求'
        return error_msg

    def __call__(self):
        '''
        获取一个日期在这一年中的第几天
        :param year: 年份
        :param month: 月份
        :param day: 日期
        :return: 在这一年中的第几天
        '''
        # 参数校验
        error_msg = self.validateParam(self.year, self.month, self.day)
        if error_msg:
            return error_msg

        if self.month == 1:
            return self.day

        if self.month == 2:
            return self.day + 31

        daysOf31Num = 0
        daysOf30Num = 0
        # 31天月份数
        for days_of_31 in Doy.MONTH31:
            if days_of_31 < self.month:
                daysOf31Num += 1

        # 30天月份数
        for days_of_30 in Doy.MONTH30:
            if days_of_30 < self.month:
                daysOf30Num += 1

        return daysOf31Num * 31 + daysOf30Num * 30 + (29 if self.isLeapYear(self.year) else 28) + self.day


class GOT01Fit(object):
    # 输出结果分辨率
    ORES = 0.01

    def __init__(self, fy4aList, fy3dList, ymd):
        self.getYMD(ymd)
        self.fy4aList = fy4aList
        self.fy3dList = fy3dList
        self.doy = Doy(ymd)()
        self.fit()

    def getYMD(self, ymd):
        if len(ymd) != 8:
            print('Import date error (yyyymmdd)')
        self.ymd = ymd
        self.year = int(ymd[0:4])
        self.month = int(ymd[4:6])
        self.day = int(ymd[6:8])

    def calcW(self, phi):
        '''半周期宽度'''

        # 计算一年的第几天
        delta = 23.45 * np.sin(np.deg2rad(360. / 365. * (284 + self.doy)))
        # 计算半周期宽度
        w = np.rad2deg(2. / 15. * np.arccos(-np.tan(np.deg2rad(phi)) * np.tan(np.deg2rad(delta))))

        # 返回w
        return w

    def getT0Range(self, timeList, dataList, sunRise):
        """获得T0的大致范围"""

        key = min(timeList, key=lambda k: abs(k - sunRise))
        index = timeList.index(key)

        return (dataList[index] - 5. - random.random() * 1, dataList[index] + 5.)

    def getTaRange(self, dataList):
        '''获取Ta的大致范围'''

        diff = np.nanmax(dataList) - np.nanmin(dataList)
        return (diff - 5 - random.random() * 1, diff + 5)

    def getTdiffRange(self, dataList):
        '''获取tdiff的大致范围'''
        diff = np.nanmax(dataList) - np.nanmin(dataList)
        return (diff / 6, diff / 3)

    def GOT01Fy4(self, t, t0, ta, tm, ts, tdif):
        ''' dtc模型 GOT01 '''

        # 衰减常数
        k = self.w / PI * (1 / np.tan(PI / self.w * (ts - tm)) - tdif / ta * 1 / np.sin(PI / self.w * (ts - tm)))

        # 白天
        tday = lambda t: t0 + ta * np.cos(PI / self.w * (t - tm))
        # 夜晚
        # tnight = lambda t: (t0 + tdif) + (ta * np.cos(PI / self.w * (ts - tm)) - tdif) * np.exp(-(t - ts) / k)
        tnight = lambda t: (t0 + tdif) + (ta * np.cos(PI / self.w * (ts - tm)) - tdif) * (k / (k + t - ts))

        # 分段函数
        return np.piecewise(t, [t < ts, t >= ts], [tday, tnight])

    def GOT01Fy3(self, t, t0, ta):
        ''' dtc模型 GOT01 '''

        # 衰减常数
        k = self.w / PI * (1 / np.tan(PI / self.w * (self.ts - self.tm)) - self.tdif / ta * 1 / np.sin(
            PI / self.w * (self.ts - self.tm)))

        # 白天
        tday = lambda t: t0 + ta * np.cos(PI / self.w * (t - self.tm))
        # 夜晚
        tnight = lambda t: (t0 + self.tdif) + (ta * np.cos(PI / self.w * (self.ts - self.tm)) - self.tdif) * (
                k / (k + t - self.ts))

        # 分段函数
        return np.piecewise(t, [t < self.ts, t >= self.ts], [tday, tnight])

    def GOT01(self, t):
        ''' dtc模型 GOT01 '''

        # `衰减常数`
        k = self.wArr / PI * (
                1 / np.tan(PI / self.wArr * (self.tsArr - self.tmArr)) - self.tdifArr / self.taArr * 1 / np.sin(
            PI / self.wArr * (self.tsArr - self.tmArr)))

        # 白天
        tday = lambda t: self.t0Arr + self.taArr * np.cos(PI / self.wArr * (t - self.tmArr))
        # 夜晚
        tnight = lambda t: (self.t0Arr + self.tdifArr) + (
                self.taArr * np.cos(PI / self.wArr * (self.tsArr - self.tmArr)) - self.tdifArr) * (
                                   k / (k + t - self.tsArr))

        # 分段函数
        return np.where(t < self.tsArr, tday(t), tnight(t))

    def fitFirst(self, X, y, sunRise, lat):
        '''第一次拟合计算参数'''

        try:
            # t0的范围
            t0Range = self.getT0Range(list(X), y, sunRise)
            # ta的范围
            taRange = self.getTaRange(y)
            # tdiff的范围
            tdiffRange = self.getTdiffRange(y)

            # 半周期半径
            self.w = self.calcW(lat)

            # 第一次拟合
            popt, pcov = op.curve_fit(self.GOT01Fy4, X, y, bounds=(
                [t0Range[0], taRange[0], 3.5, 8, tdiffRange[0]],
                [t0Range[1], taRange[1], 7, 9.5, tdiffRange[1]]))
            perr = np.sqrt(np.diag(pcov))
            if (perr > .2).all():
                return None
            # 参数复制
            self._t0, self._ta, self.tm, self.ts, self.tdif = popt

            return popt
        except Exception as err:
            print(err)
            return None

    def fitSecond(self, X, y, lat):
        '''第二次拟合计算参数'''

        try:
            # 半周期半径
            self.w = self.calcW(lat)
            # 第二次拟合
            popt, pcov = op.curve_fit(self.GOT01Fy3, X, y, bounds=(
                [self._t0 - 1 - 4 * random.random(), self._ta - 1 - 4 * random.random()],
                [self._t0 + 1 + 4 * random.random(), self._ta + 1 + 4 * random.random()]), )
            return popt
        except Exception as err:
            print(err)
            return None

    def fit(self):
        '''拟合入口'''

        # 读取文件夹中的lst数据
        lstList = sorted(glob(os.path.join(self.fy4aList, '*%s*.NC' % self.ymd)))
        # 用于保存读取后的数据
        lstDict = {}
        # 读取fy4a数据
        for lst_file in tqdm(lstList, desc='Reading'):
            # 提取数据
            data = extractLST(lst_file) * SLOPE
            # 读取时间
            time = os.path.basename(lst_file).split('_')[9]
            # 读取 时 分
            hh, mm = int(time[8:10]), int(time[10:12])
            # 添加到记录
            lstDict[hh + mm / 60] = data.data

        # 读取fy3d数据
        fy3dArr = extractFy3d(self.fy3dList, self.ymd) * SLOPE

        # 数据时间列表
        timeList = list(lstDict.keys())
        # timeList = (np.array(timeList) + 8) % 24
        # 数据转为ndarray
        data = np.array(list(lstDict.values()))

        del lstDict

        fillValue = -999
        # 建立数组保存参数
        taArr = np.full_like(fy3dArr[0], fillValue)
        t0Arr = np.full_like(fy3dArr[0], fillValue)
        tsArr = np.full_like(fy3dArr[0], fillValue)
        tmArr = np.full_like(fy3dArr[0], fillValue)
        tdifArr = np.full_like(fy3dArr[0], fillValue)
        wArr = np.full_like(fy3dArr[0], fillValue)

        # 实例化日出类
        sun = Sun(self.ymd)
        # 逐像元遍历数据
        for i in tqdm(range(data.shape[1]), desc='Fitting'):
            # 数据所属纬度
            lat = yMax - i * 0.04
            for j in range(data.shape[2]):
                # 该点数据
                y = data[:, i, j]
                # 数字据所属经度
                lon = xMin + j * 0.04

                # 去除数据中的nan
                tranDict = dict(zip(timeList, y))
                for key in timeList:
                    if np.isnan(tranDict[key]):
                        tranDict.pop(key)
                # 如果拟合数据量小于20 则放弃该点拟合
                if len(tranDict) < 20:
                    continue
                # 计算该点日出
                sunRise = sun.rise(lon, lat)

                # 第一次进行拟合
                popt = self.fitFirst(np.array(list(tranDict.keys())), np.array(list(tranDict.values())), sunRise, lat)
                # print('fit1', popt)
                if popt is None:
                    continue
                scale = int(0.04 / GOT01Fit.ORES)
                # 遍历3d数据
                for m in range(scale):
                    lat1 = yMax - (i * scale + m) * GOT01Fit.ORES
                    for n in range(scale):
                        # 提取该点数据
                        fy3dData = fy3dArr[:, i * scale + m, j * scale + n]
                        # 如果数据存在无效值， 则放弃拟合
                        if np.isnan(fy3dData).any():
                            continue
                        # 第二次拟合
                        popt = self.fitSecond(np.array([11, 19]), fy3dData, lat1)
                        if popt is None:
                            continue
                        t0Arr[i * scale + m, j * scale + n] = popt[0]
                        taArr[i * scale + m, j * scale + n] = popt[1]
                        tsArr[i * scale + m, j * scale + n] = self.ts
                        tmArr[i * scale + m, j * scale + n] = self.tm
                        tdifArr[i * scale + m, j * scale + n] = self.tdif
                        wArr[i * scale + m, j * scale + n] = self.w

        del data, fy3dArr

        t0Arr[t0Arr == fillValue] = nodata
        taArr[taArr == fillValue] = nodata
        tsArr[tsArr == fillValue] = nodata
        tmArr[tmArr == fillValue] = nodata
        wArr[wArr == fillValue] = nodata
        tdifArr[tdifArr == fillValue] = nodata

        # 属性赋值
        self.taArr = taArr
        self.t0Arr = t0Arr
        self.tsArr = tsArr
        self.tmArr = tmArr
        self.tdifArr = tdifArr
        self.wArr = wArr

    def predict(self, filename, t):
        '''预测数据'''
        # 输出路径
        outpath = os.path.dirname(filename)
        if not os.path.isdir(outpath):
            os.makedirs(outpath)
        tArr = np.full_like(self.tsArr, t)
        result = np.where(
            ~np.isnan(self.tsArr), self.GOT01(tArr), nodata) / SLOPE
        result[result > 350] = nodata

        # 保存结果
        saveImage(filename, result, res=GOT01Fit.ORES)


def main(args):
    '''主程序'''
    try:
        # 解析参数
        try:
            options, args = getopt.getopt(args, "", ["fy3ddir=", "fy4adir=", "outdir=", "ymd="])
        except getopt.GetoptError as err:
            print(err)
            return -1
        fy3d_dir, fy4d_dir, out_dir, ymd = None, None, None, None
        for option, value in options:
            if option == "--fy3ddir":
                fy3d_dir = value
            elif option == "--fy4adir":
                fy4d_dir = value
            elif option == "--outdir":
                out_dir = value
            elif option == "--ymd":
                ymd = value

        # 校验参数
        if not all([fy3d_dir, fy4d_dir, out_dir, ymd]):
            print("param error")
            return -1
        if not all([os.path.isdir(dir) for dir in [fy3d_dir, fy4d_dir]]):
            print("input dir error")
            return -1
        if len(ymd) != 8:
            print("input ymd error")
            return -1
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)

        # 拟合
        got01 = GOT01Fit(fy4d_dir, fy3d_dir, ymd)
        # 预测
        for i in range(24):
            outname = os.path.join(out_dir, 'FY3D_LST_%s%02d0000_1000M.tif' % (ymd, i))
            got01.predict(outname, i)

    except Exception as err:
        print("Running error", str(err))
        return -1


if __name__ == '__main__':
    startTime = datetime.now()
    main(sys.argv[1:])
    endTime = datetime.now()
    print('StartTime: ' + startTime.strftime('%Y-%m-%d %H:%M:%S'))
    print('EndTime: ' + endTime.strftime('%Y-%m-%d %H:%M:%S'))
    print('ElapsedTime: ' + str((endTime - startTime).seconds))
    print('Success')
