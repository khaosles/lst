#!usr/bin/env python
# -*- coding: utf-8 -*-

'''
    @author: khaosles
    @date: 2022/4/21  15:33
'''

from pyhdf.SD import SD, SDC
import numpy as np
import os
import time
import shutil
from osgeo import gdal

from pprint import pprint

from tempature.lst.lst import LST

baseDir = os.path.dirname(os.path.abspath(__file__))

os.environ['MRTDATADIR'] = os.path.join(baseDir, '../resource/HEG_Win/data')
os.environ['PGSHOME'] = os.path.join(baseDir, '../resource/HEG_Win/TOOLKIT_MTD')
os.environ['MRTBINDIR'] = os.path.join(baseDir, '../resource/HEG_Win/bin')

# 指定处理模块的可执行程序文件路径，此处采用swtif.exe，可以根据具体的处理问题设置
hegpath = os.path.join(baseDir, '../resource/HEG_Win/bin/swtif.exe')
template = os.path.join(baseDir, '../resource/template.prm')


class Modis(LST):

    def __init__(self, name):

        if not os.path.isfile(name):
            raise FileNotFoundError('FileNotFoundError: The input modis file not exist: %s' % name)
        if not os.path.isfile(template):
            raise FileNotFoundError('FileNotFoundError: The prm template not exist: %s' % template)
        # 临时文件夹
        self.tmp = os.path.join(baseDir, '%d' % time.time())
        if not os.path.isdir(self.tmp):
            os.makedirs(self.tmp)

        self.name = name
        # 各个波段
        self.RED = '1'
        self.NIR = '2'
        self.TIR1 = '31'
        self.TIR2 = '32'
        self.NODATA = np.nan
        self.RES = 0.01

        fp = open(template, 'r')
        self.prmSrc = fp.read()
        fp.close()

        # 打开hdf
        self.hdfobj = SD(name, SDC.READ)

        self.zenith = self.readData(1, 'SolarZenith')

        # 计算数据经纬度范围
        self.lonlat()

        # 热红外波段
        tir = self.getTir()
        # 红近红波段
        rednir = self.getOneTwo()

        super().__init__(rednir['Red'], rednir['Nir'], tir['Tir1'], tir['Tir2'])

    def __del__(self):
        try:
            # 关闭hdf
            self.hdfobj.end()
            # 删除临时文件
            if os.path.isdir(self.tmp):
                shutil.rmtree(self.tmp)
        except:
            pass

    def lonlat(self):
        lat = self.hdfobj.select('Latitude')[:]
        lon = self.hdfobj.select('Longitude')[:]
        self.minLon, self.maxLon = np.nanmin(lon), np.nanmax(lon)
        self.minLat, self.maxLat = np.nanmin(lat), np.nanmax(lat)

    def readData(self, bandId, bandName):

        # 输出
        outName = os.path.join(self.tmp, '%s_%s.tif' % (bandName, bandId))
        outPrm = os.path.join(self.tmp, '%s_%s_swath.prm' % (bandName, bandId))

        prm = self.prmSrc.format(
            infile=self.name,
            bandName=bandName,
            bandId=bandId,
            xRes=self.RES,
            yRes=self.RES,
            ULat=self.maxLat,
            LLon=self.minLon,
            LLat=self.minLat,
            RLon=self.maxLon,
            outName=outName
        )

        # 写入文件
        fo = open(outPrm, 'w', newline='\n')
        fo.writelines(prm)
        fo.close()
        cmd = '%s -P %s' % (hegpath, outPrm)
        os.system(cmd)

        # 判断是否处理成功
        if not os.path.isfile(outName):
            raise RuntimeError('RuntimeError: HEG deal failed.')

        ds = gdal.Open(outName)
        data = ds.ReadAsArray().astype(np.float16)
        self.tran = ds.GetGeoTransform()
        self.proj = ds.GetProjection()
        del ds

        return data

    def getTir(self):

        dsname = 'EV_1KM_Emissive'
        ds = self.hdfobj.select('EV_1KM_Emissive')
        # 有效值范围
        validRange = ds.attr(2).get()
        # 定标系数
        radiance_scales = ds.attr(5).get()
        # 定标偏移
        radiance_offsets = ds.attr(6).get()
        # 波段名称
        bandNames = ds.attr(4).get().split(',')

        idxTir1 = bandNames.index(self.TIR1)
        idxTir2 = bandNames.index(self.TIR2)

        # 读取两个热红外波段
        tir1 = self.readData(idxTir1 + 1, dsname)
        tir2 = self.readData(idxTir2 + 1, dsname)

        # 去除无效值
        tmp = np.logical_and(tir1 > validRange[0], tir1 < validRange[1])
        index = np.where(~tmp)
        tir1[index] = self.NODATA

        tmp = np.logical_and(tir2 > validRange[0], tir2 < validRange[1])
        index = np.where(~tmp)
        tir2[index] = self.NODATA

        # 定标
        tir1 = tir1 * radiance_scales[idxTir1] + radiance_offsets[idxTir1]
        tir2 = tir2 * radiance_scales[idxTir2] + radiance_offsets[idxTir2]

        info = {'Tir1': tir1, 'Tir2': tir2, }
        return info

    def getOneTwo(self):

        dsname = 'EV_250_Aggr1km_RefSB'
        # 读取数据
        ds = self.hdfobj.select(dsname)
        # 有效值范围
        validRange = ds.attr(2).get()
        # 定标系数
        radiance_scales = ds.attr(5).get()
        # 定标偏移
        radiance_offsets = ds.attr(6).get()
        # 波段名称
        bandNames = ds.attr(4).get().split(',')

        idxRed = bandNames.index(self.RED)
        idxNir = bandNames.index(self.NIR)

        # 读取两个热红外波段
        red = self.readData(idxRed + 1, dsname)
        nir = self.readData(idxNir + 1, dsname)

        # 去除无效值
        tmp = np.logical_and(red > validRange[0], red < validRange[1])
        index = np.where(~tmp)
        red[index] = self.NODATA

        tmp = np.logical_and(nir > validRange[0], nir < validRange[1])
        index = np.where(~tmp)
        nir[index] = self.NODATA

        # 定标
        red = red * radiance_scales[idxRed] + radiance_offsets[idxRed]
        nir = nir * radiance_scales[idxNir] + radiance_offsets[idxNir]

        info = {'Red': red, 'Nir': nir, }
        return info


if __name__ == '__main__':
    file = '/Volumes/T7/winter/TestData/LST/modis/MOD021KM.A2022001.0010.061.2022001133347.hdf'
    modis = Modis(file)