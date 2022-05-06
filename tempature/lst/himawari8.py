#!usr/bin/env python
# -*- coding: utf-8 -*-

'''
    @author: khaosles
    @date: 2022/4/22  10:34
'''

import re
import os
import numpy as np
from osgeo import gdal, osr
import netCDF4 as nc
import xarray as xr
from configobj import ConfigObj

baseDir = os.path.dirname(os.path.abspath(__file__))
cfgFile = os.path.join(baseDir, '../conf', 'config.cfg')
cfg = ConfigObj(cfgFile)
os.environ['PATH'] += baseDir

from tempature.lst.lst import LST


class Himawari8(LST):

    def __init__(self, name):

        if not os.path.isfile(name):
            raise FileNotFoundError()

        # 读取数据分辨率
        if os.path.basename(name).split('.')[-2] == '06001_06001':
            self.RES = 0.02
        elif os.path.basename(name).split('.')[-2] == '02401_02401':
            self.RES = 0.05
        else:
            raise ImportError()

        self.RED = 3
        self.NIR = 4
        self.TIR1 = 14
        self.TIR2 = 15
        self.SOZ = 'SOZ'
        self.NODATA = np.nan

        self.minLon = float(cfg['RANGE']['X_MIN'])
        self.minLat = float(cfg['RANGE']['Y_MIN'])
        self.maxLon = float(cfg['RANGE']['X_MAX'])
        self.maxLat = float(cfg['RANGE']['Y_MAX'])

        self.obj = xr.open_dataset(name, engine='netcdf4')
        red = self.readB34(self.RED)  # 红
        nir = self.readB34(self.NIR)  # 近红
        tir1 = self.readB(self.TIR1)  # 热红1
        tir2 = self.readB(self.TIR2)  # 热红2
        soz = self.readB(self.SOZ)  # 太阳天顶角

        red = red / np.cos(soz)  # 校正红
        nir = nir / np.cos(soz)  # 校正近红

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        # 投影
        self.proj = srs.ExportToWkt()
        # 仿射参数
        self.tran = [self.minLon, self.RES, 0, self.maxLat, 0, -self.RES]

        self.zenith = soz

        super().__init__(red, nir, tir1, tir2)

    def readB(self, idx):

        if idx == 'SOZ':
            bandName = idx
        else:
            bandName = 'tbb_%02d' % idx
        ds = self.obj.get(bandName)
        # 经纬度
        lat = ds.latitude.data
        lon = ds.longitude.data
        lon, lat = np.meshgrid(lon, lat)
        # 有效值范围
        valid_min = ds.valid_min
        valid_max = ds.valid_max
        data = ds.data.astype(np.float16)

        # 去除无效值
        tmp = np.logical_or(data < valid_min, data > valid_max)
        index = np.where(tmp)
        data[index] = self.NODATA

        tmp = np.logical_and(lon >= self.minLon, lon < self.maxLon)
        tmp = np.logical_and(tmp, lat >= self.minLat)
        tmp = np.logical_and(tmp, lat < self.maxLat)
        index = np.where(tmp)
        row, column = self.build()
        data = data[index]
        data = data.reshape(column, row)

        return data

    def readB34(self, idx):

        bandName = 'albedo_%02d' % idx
        ds = self.obj.get(bandName)

        # 经纬度
        lat = ds.latitude.data
        lon = ds.longitude.data
        lon, lat = np.meshgrid(lon, lat)
        # 有效值范围
        valid_min = ds.valid_min
        valid_max = ds.valid_max
        correction_factor = ds.correction_factor
        correction_offset = ds.correction_offset
        data = ds.data.astype(np.float16)

        # 去除无效值
        tmp = np.logical_or(data < valid_min, data > valid_max)
        index = np.where(tmp)
        data[index] = self.NODATA

        tmp = np.logical_and(lon >= self.minLon, lon < self.maxLon)
        tmp = np.logical_and(tmp, lat >= self.minLat)
        tmp = np.logical_and(tmp, lat < self.maxLat)
        index = np.where(tmp)
        row, column = self.build()

        data = data[index]
        data = data.reshape(column, row)
        # 数据校正
        data = data * correction_factor + correction_offset

        return data

    def build(self):
        # 行数
        row = int((self.maxLon - self.minLon) / self.RES + 0.5)
        # 列数
        column = int((self.maxLat - self.minLat) / self.RES + 0.5)
        return row, column
