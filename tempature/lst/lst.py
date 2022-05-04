#!usr/bin/env python
# -*- coding: utf-8 -*-

'''
    @author: khaosles
    @date: 2022/4/20  16:00
'''

import os
import numpy as np
from abc import ABCMeta
from osgeo import gdal


class LST(metaclass=ABCMeta):

    def __init__(self, red, nir, tir1, tir2):
        self.red = red  # 红
        self.nir = nir  # 近红
        self.tir1 = tir1  # 热红外1
        self.tir2 = tir2  # 热红外2
        self.NODATA = np.nan  # 无效值
        self.L11 = 0.9547   # 11μm
        self.L12 = 0.9709   # 12μm

    @property
    def shape0(self):
        return self.red.shape[0]

    @property
    def shape1(self):
        return self.red.shape[1]

    @property
    def ndvi(self):
        # 计算ndvi
        return (self.nir - self.red) / (self.nir + self.red)

    @property
    def epsilon11(self):
        # 中心波长为11μm波段的比辐射率
        return self.calcEpsilon(self.L11)

    @property
    def epsilon12(self):
        # 中心波长为12μm波段的比辐射率
        return self.calcEpsilon(self.L12)

    @property
    def epsilonDif(self):
        return np.abs(self.epsilon12 - self.epsilon11)

    @property
    def epsilonAvg(self):
        return (self.epsilon12 + self.epsilon11) / 2

    def calcEpsilon(self, val):
        """计算地表比辐射率"""

        MIN_N = 0.2  # 裸土 ndvi
        MAX_N = 0.5  # 纯植被 ndvi
        ndvi = self.ndvi  # ndvi
        # 计算植被覆盖度
        vcf = np.where(ndvi > MAX_N, 1, np.where(ndvi < MIN_N, 0, (ndvi - MIN_N) / (MAX_N - MIN_N)))
        # 地表比辐射率
        epsilon = np.where(ndvi < MIN_N, val, np.where(ndvi > MAX_N, 0.99, 0.99 * vcf + val * (1 - vcf)))

        return epsilon

    def inversion(self, a, gamma1, alpha1, beta1, gamma2, alpha2, beta2):
        """计算lst"""

        # (Ti - Tj) / 2
        l11Sub12 = (self.tir1 - self.tir2) / 2
        # (Ti + Tj) / 2
        l11Add12 = (self.tir1 + self.tir2) / 2
        # (1 - epsilonAvg) / epsilonAvg
        oneSubEDivEAvg = (1 - self.epsilonAvg) / self.epsilonAvg
        # epsilonDif / epsilonAvg * epsilonAvg
        eDifDivEAvg = self.epsilonDif / np.square(self.epsilonAvg)

        lst = a + gamma1 * l11Add12 + alpha1 * oneSubEDivEAvg * l11Add12 + beta1 * eDifDivEAvg * l11Add12 + \
              gamma2 * l11Sub12 + alpha2 * oneSubEDivEAvg * l11Sub12 + beta2 * eDifDivEAvg * l11Sub12

        return lst

    def saveImage(self, filename, data, tran, proj):
        '''保存影像'''

        filename = filename.replace('\\', os.sep).replace('/', os.sep)
        if os.sep in filename:
            filepath = os.path.dirname(filename)
            if not os.path.isdir(filepath):
                os.makedirs(filepath)

        if os.path.splitext(filename)[1].lower() == '.tif':
            fmt = 'GTiff'
        else:
            fmt = 'ENVI'

        band, (imgHeight, imgWidth) = 1, data.shape

        # 建立
        ds = gdal.GetDriverByName(fmt).Create(
            filename, imgWidth, imgHeight, band, gdal.GDT_Float32, options=['TILED=YES', 'COMPRESS=LZW']
        )

        # 设置仿射参数
        ds.SetGeoTransform(tran)
        # 设置坐标
        ds.SetProjection(proj)

        # 写入数据
        ds.GetRasterBand(1).WriteArray(data)

        del ds

