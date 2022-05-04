import h5py as h5
import os
import numpy as np
import time
import shutil
from osgeo import gdal, osr

from tempature.lst.lst import LST

baseDir = os.path.dirname(os.path.abspath(__file__))


class FY3D(LST):

    def __init__(self, name, geofile, clmfile):

        self.RED = 3
        self.NIR = 4
        self.TIR1 = 24
        self.TIR2 = 25
        self.NODATA = np.nan

        # 临时文件
        self.tmp = os.path.join(baseDir, '%d' % time.time())
        if not os.path.isdir(self.tmp):
            os.makedirs(self.tmp)
        # 文件分辨率
        if name.split('_')[-2] == '1000M':
            self.res = 0.01
        elif name.split('_')[-2] == '0250M':
            self.res = 0.0025
        # 文件名称
        self.name = name
        # geo文件名称
        self.geofile = geofile
        # 云
        self.clmfile = clmfile
        if not os.path.isfile(name) or not os.path.isfile(geofile) or not os.path.isfile(clmfile):
            raise FileNotFoundError('FileNotFoundError: The input file not exist.')

        # 以h5格式打开文件
        self.obj = h5.File(name)
        # 以gdal打开文件
        self.dataset = gdal.Open(self.name)
        # 云
        mask = self.clm()
        # 热红外波段
        tir1, tir2 = self.geolocation(7)
        # 红波段
        red, nir = self.geolocation(8)
        # 天顶角
        self.zenith = self.soz()
        # 去除云
        for arr in [red, nir, tir1, tir2]:
            arr[mask != 0] = self.NODATA

        super().__init__(red, nir, tir1, tir2)

    def __del__(self):
        try:
            if os.path.isdir(self.tmp):
                shutil.rmtree(self.tmp)
            if self.dataset is not None:
                del self.dataset
        except:
            pass

    def geolocation(self, idx):

        # 打开文件
        vrtPath = os.path.join(self.tmp, 'vrt_%s.vrt' % idx)
        subDataset = self.dataset.GetSubDatasets()[idx][0]  # B25
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        self.createVRT(vrtPath, subDataset)

        # 校正
        ds = gdal.Warp('', vrtPath,
                       format='MEM', geoloc=True, dstSRS=srs,
                       resampleAlg=gdal.GRIORA_Bilinear, xRes=self.res, yRes=self.res)
        # 读取数据
        data = ds.ReadAsArray()
        if idx == 7:
            arr1, arr2 = data[0], data[1]
        else:
            arr1, arr2 = data[-2], data[-1]
        # 读取文件投影放射参数
        self.tran = ds.GetGeoTransform()
        self.proj = ds.GetProjection()

        del ds
        # 返回
        return arr1, arr2

    def soz(self):
        # vrt 路径
        vrtPath = os.path.join(self.tmp, 'soz.vrt')
        # 打开geo文件
        ds = gdal.Open(self.geofile)
        # 读取子文件
        subDataset = ds.GetSubDatasets()[8][0]
        # 建立输出坐标
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        #
        self.createVRT(vrtPath, subDataset)
        # 校正
        ds = gdal.Warp('', vrtPath,
                       format='MEM', geoloc=True, dstSRS=srs,
                       resampleAlg=gdal.GRIORA_Bilinear, xRes=self.res, yRes=self.res)
        # 读取数据
        data = ds.ReadAsArray()
        del ds
        return data

    def clm(self):
        # 打开geo文件
        ds = gdal.Open(self.clmfile)
        # 读取子文件
        subDataset = ds.GetSubDatasets()
        vrtPath = os.path.join(self.tmp, 'clm.vrt')
        self.createVRT(vrtPath, subDataset[0][0])
        # 建立输出坐标
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        # 校正
        ds = gdal.Warp('', vrtPath,
                       format='MEM', geoloc=True, dstSRS=srs,
                       resampleAlg=gdal.GRIORA_Bilinear, xRes=self.res, yRes=self.res)
        # 读取数据
        data = ds.ReadAsArray()
        del ds
        return data

    def createVRT(self, vrtPath, subDataset):
        """构建vrt"""
        gdal.Translate(vrtPath,
                       subDataset,
                       format='vrt')
        # 构建vrt
        lines = []
        with open(vrtPath, 'r') as f:
            for line in f:
                lines.append(line)
        lines.insert(1, '<Metadata domain="GEOLOCATION">\n')
        lines.insert(2, ' <MDI key="LINE_OFFSET">1</MDI>\n')
        lines.insert(3, ' <MDI key="LINE_STEP">1</MDI>\n')
        lines.insert(4, ' <MDI key="PIXEL_OFFSET">1</MDI>\n')
        lines.insert(5, ' <MDI key="PIXEL_STEP">1</MDI>\n')
        lines.insert(6, ' <MDI key="SRS">EPSG:4326</MDI>\n')
        lines.insert(7, ' <MDI key="X_BAND">1</MDI>')
        lines.insert(8, ' <MDI key="X_DATASET">HDF5:"{}"://Geolocation/Longitude</MDI>\n'.format(self.geofile))
        lines.insert(9, ' <MDI key="Y_BAND">1</MDI>\n')
        lines.insert(10, ' <MDI key="Y_DATASET">HDF5:"{}"://Geolocation/Latitude</MDI>\n'.format(self.geofile))
        lines.insert(11, '</Metadata>\n')
        with open(vrtPath, 'w') as f:
            for line in lines:
                f.writelines(line)

