#!usr/bin/env python
# -*- coding: utf-8 -*-

'''
    @author: khaosles
    @date: 2022/4/21  10:15
'''

import os
import numpy as np
from osgeo import osr

from tempature.lst.lst import LST
from utils.utils import extractL1, extractCLM, extractGEO, xMin, yMax


class FY4A(LST):

    def __init__(self, l1File, clmFile):
        self.NODATA = np.nan  # 无效值

        # 校验文件
        if not all([os.path.isfile(file) for file in [l1File, clmFile]]):
            raise ImportError('FileNotFoundError: No such file or directory "{file}"'.format(file=l1File))

        # fenbianlv
        resL1 = self.getInfo(l1File)['Resolution']
        # 云掩膜
        clm = extractCLM(clmFile).repeat(4000 / resL1, 0).repeat(4000 / resL1, 1)
        # 读取波段数据
        red, nir, tir1, tir2 = list(map(lambda idx: extractL1(l1File, idx, resL1), [2, 3, 12, 13]))
        # 去除云数据
        for arr in [red, nir, tir1, tir2]:
            arr[np.isnan(clm)] = self.NODATA

        self.tran = [xMin, resL1 / 100 / 1000, 0, yMax, 0, -resL1 / 100 / 1000]
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        # 投影
        self.proj = srs.ExportToWkt()
        # geo
        self.extractGEO = extractGEO

        super().__init__(red, nir, tir1, tir2)

    def getInfo(self, file):

        # 根据文件路径获取文件名，并根据文件名获取各个字段信息，集成为字典
        info = file.split(os.sep)[-1].replace('-', '').split('_')
        temp = info[-1].split('.')
        del info[-1]
        info.append(temp[0])
        info.append(temp[1])  # 把文件名分割成字段列表

        if info[11] == '064KM':
            info[11] = 48  # 名字上写着64KM，实际上是48KM分辨率
        if 'K' in info[11]:
            info[11] = info[11].replace('K', '000')
        info[11] = int(info[11][:-1])  # 标准化分辨率参数

        info = {
            'Satellite_Name': info[0],  # 卫星名称
            'Sensor_Name': info[1],  # 仪器名称
            'Observation_Mode': info[2],  # 观测模式
            'Area': info[3],  # 数据区域类型
            'Sub_astral_Point': info[4],  # 星下点经纬度
            'Level': info[5],  # 数据级别
            'Product_Name': info[6],  # 数据名称
            'Band': info[7],  # 仪器通道名称
            'Project': info[8],  # 投影方式
            'Start_Time': info[9],  # 观测起始日期时间(UTC)
            'End_Time': info[10],  # 观测结束日期时间(UTC)
            'Resolution': info[11],  # 空间分辨率
            'Backup': info[12],  # 备用字段
            'Format': info[13]  # 数据格式
        }
        return info
