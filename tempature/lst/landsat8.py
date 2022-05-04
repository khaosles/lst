#!usr/bin/env python
# -*- coding: utf-8 -*-

'''
    @author: khaosles
    @date: 2022/4/21  10:39
'''

import re
import os
import numpy as np
from osgeo import gdal

from tempature.lst.lst import LST


class Landsat8(LST):

    def __init__(self, mltFile):

        if not os.path.isfile(mltFile):
            raise FileNotFoundError('FileNotFoundError: No such file or directory "{file}"'.format(file=mltFile))
        if '_MTL.txt' != mltFile[-8:]:
            raise NameError('NameError: The file can only "_MTL.txt"')
        # 解析元数据
        self.info = self.parseInfo(mltFile)
        # 辐射定标
        red, nir, tir1, tir2 = list(map(
            lambda idx: self.radiance(*np.array([self.info['fileList'], self.info['mult'], self.info['add']])[:, idx]), range(0, 4)))

        super().__init__(red, nir, tir1, tir2)

    @property
    def zenith(self):
        return self.info['zenith']

    def parseInfo(self, mltFile):
        """读取元数据的参数"""

        try:
            filePath = os.path.dirname(mltFile)
            # 元数据名称
            file = open(mltFile, 'r')
            # 获取元数据
            metadata = " ".join(file.readlines())
            # 关闭元数据
            file.close()
            # 波段信息
            bandList = [4, 5, 10, 11]

            # 定标系数
            mult = list(map(lambda id:
                # 增益系数
                float(''.join(re.findall('RADIANCE_MULT_BAND_{id}.+'.format(id=id), metadata)[0]).split("=")[1]), bandList))
            add = list(map(lambda id:
                # 偏移系数
                float(''.join(re.findall('RADIANCE_ADD_BAND_{id}.+'.format(id=id), metadata)[0]).split("=")[1]), bandList))
            # 文件名称
            fileNameList = list(map(lambda id:
                # 偏移系数
                (''.join(re.findall('FILE_NAME_BAND_{id}.+'.format(id=id), metadata)[0]).split("=")[1]).replace('"',
                                                                                '').replace("'", '').strip(), bandList))
            # 影像绝对路径
            fileAbsPathList = list(map(lambda filename: os.path.join(filePath, filename), fileNameList))

            # 高度角
            zenith = float(''.join(re.findall('SUN_ELEVATION.+', metadata)).split("=")[1])

            # 读取信息
            info = {
                'mult': mult,
                'add': add,
                'fileList': fileAbsPathList,
                'zenith': zenith
            }
        except Exception as err:
            raise Exception('ParseMetadataError: Can not parse the metadata "{err}""'.format(err=err))

        return info

    def radiance(self, file, mult, add):
        """辐射定标"""
        if not os.path.isfile(file):
            raise FileNotFoundError('FileNotFoundError: No such file or directory "{file}"'.format(file=file))
        # 打开
        ds = gdal.Open(file)
        if ds is None:
            raise IOError('IOError: Can not open the file "{file}"'.format(file=file))
        # 读取数据
        data = ds.ReadAsArray()
        del ds

        # 辐射定标
        data = data * float(mult) + float(add)
        # 返回结果
        return data

