#!usr/bin/env python
# -*- coding: utf-8 -*-

'''
    @author: khaosles
    @date: 2022/3/22  16:44
'''

import h5py
import numpy as np
from numpy import deg2rad, rad2deg, arctan, arcsin, tan, sqrt, cos, sin
from netCDF4 import Dataset
import os
from configobj import ConfigObj
import gzip
from osgeo import gdal, osr

baseDir = os.path.dirname(os.path.realpath(__file__))
configFile = os.path.join(baseDir, '../conf/config.cfg')
config = ConfigObj(configFile)

# 待提取范围
xMin = float(config['RANGE']['X_MIN'])
xMax = float(config['RANGE']['X_MAX'])
yMin = float(config['RANGE']['Y_MIN'])
yMax = float(config['RANGE']['Y_MAX'])

ea = 6378.137  # 地球的半长轴[km]
eb = 6356.7523  # 地球的短半轴[km]
h = 42164  # 地心到卫星质心的距离[km]
lambdaD = deg2rad(104.7)  # 卫星星下点所在经度
# 列偏移
COFF = {
    500: 10991.5,
    1000: 5495.5,
    2000: 2747.5,
    4000: 1373.5
}
# 列比例因子
CFAC = {
    500: 81865099,
    1000: 40932549,
    2000: 20466274,
    4000: 10233137
}
LOFF = COFF  # 行偏移
LFAC = CFAC  # 行比例因子

# 无效值
nodata = np.nan


# 对于第一个参数为文件的函数判断文件是否存在
def isExists(func):
    def judge(*args, **kwargs):
        # 校验参数个数是否正确
        if len(args) < 1:
            print('Param error')
            return -1
        # 第一个参数为文件
        file = args[0]
        # 判断文件是否存在
        if not os.path.isfile(file):
            print('Input file not exist: %s' % file)
            return -1
        # 执行函数
        return func(*args, **kwargs)

    return judge


def saveImage(filename, data, res=0.02):
    '''保存影像'''

    filename = filename.replace('\\', os.sep).replace('/', os.sep)
    if os.sep in filename:
        filepath = os.path.dirname(filename)
        if not os.path.isdir(filepath):
            os.makedirs(filepath)

    # 影像大小
    (imgHeight, imgWidth) = data.shape

    # 建立
    ds = gdal.GetDriverByName('GTiff').Create(
        filename, imgWidth, imgHeight, 1, gdal.GDT_Float32, options=['TILED=YES', 'COMPRESS=LZW']
    )

    # 设置仿射参数
    ds.SetGeoTransform(
        [xMin, res, 0, yMax, 0, -res]
    )
    # 设置投影
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    ds.SetProjection(srs.ExportToWkt())

    # 写入数据
    ds.GetRasterBand(1).WriteArray(data[::-1])

    del ds


def saveImage3d(filename, data, res=0.01):
    '''保存影像'''

    filename = filename.replace('\\', os.sep).replace('/', os.sep)
    if os.sep in filename:
        filepath = os.path.dirname(filename)
        if not os.path.isdir(filepath):
            os.makedirs(filepath)

    # 影像大小
    (imgHeight, imgWidth) = data.shape

    # 建立
    ds = gdal.GetDriverByName('GTiff').Create(
        filename, imgWidth, imgHeight, 1, gdal.GDT_Float32, options=['TILED=YES', 'COMPRESS=LZW']
    )

    # 设置仿射参数
    ds.SetGeoTransform(
        [110, res, 0, 50, 0, -res]
    )
    # 设置投影
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    ds.SetProjection(srs.ExportToWkt())

    # 写入数据
    ds.GetRasterBand(1).WriteArray(data)

    del ds


def latlon2linecolumn(lat, lon, resolution):
    '''
    经纬度转行列
    '''
    # Step1.检查地理经纬度
    # Step2.将地理经纬度的角度表示转化为弧度表示
    try:
        lat = lat - resolution / 100 / 1000 / 2
        lon = lon + resolution / 100 / 1000 / 2
        lat = deg2rad(lat)
        lon = deg2rad(lon)
        # Step3.将地理经纬度转化成地心经纬度
        eb2_ea2 = eb ** 2 / ea ** 2
        lambdaE = lon
        phiE = arctan(eb2_ea2 * tan(lat))
        # Step4.求Re
        cosPhiE = cos(phiE)
        re = eb / sqrt(1 - (1 - eb2_ea2) * cosPhiE ** 2)
        # Step5.求r1,r2,r3
        lambdaE_lambdaD = lambdaE - lambdaD
        r1 = h - re * cosPhiE * cos(lambdaE_lambdaD)
        r2 = -re * cosPhiE * sin(lambdaE_lambdaD)
        r3 = re * sin(phiE)
        # Step6.求rn,x,y
        rn = sqrt(r1 ** 2 + r2 ** 2 + r3 ** 2)
        x = rad2deg(arctan(-r2 / r1))
        y = rad2deg(arcsin(-r3 / rn))
        # Step7.求c,l
        column = COFF[resolution] + x * 2 ** -16 * CFAC[resolution]
        line = LOFF[resolution] + y * 2 ** -16 * LFAC[resolution]
    except Exception as e:
        print('经纬度行列号失败')
        return -1

    return np.rint(line).astype(np.uint16), np.rint(column).astype(np.uint16)


def extractData(data, xMin, xMax, yMin, yMax, res=4000):
    ''' 提取范围内数据 '''

    size = (res / 100 / 1000)

    # 行数
    row = int((xMax - xMin) / size + 0.5)
    # 列数
    column = int((yMax - yMin) / size + 0.5)

    xnew = np.linspace(xMin, xMax, row)  # 获取网格x
    ynew = np.linspace(yMin, yMax, column)  # 获取网格y
    xnew, ynew = np.meshgrid(xnew, ynew)  # 生成xy二维数组

    # 获取行列号
    fy_line, fy_column = latlon2linecolumn(ynew, xnew, res)
    # 提取数据
    data_grid = data[fy_line, fy_column]

    # 返回
    return data_grid


@isExists
def extractTime(filepath):
    return '%s_%s' % (os.path.basename(filepath).split('_')[9], os.path.basename(filepath).split('_')[10])


def extractST():
    ''' 读取研究区内的下垫面类型 '''
    size = 0.04
    # 行数
    lines = int((xMax - xMin) / size + 0.5)
    # 列数
    cols = int((yMax - yMin) / size + 0.5)

    # 下垫面文件
    lndFile = os.path.join(baseDir, '../resource', 'COMBINED_LULC4KM_CHN_FIVEKINDS_bjzjk_Prjed.img')

    if not os.path.isfile(lndFile):
        print('下垫面文件不存在')
        return -1

    # 工作空间
    ds = gdal.Open(lndFile)

    # 读取下垫面的参数
    lndMinX, xRes, _, lndMaxY, _, yRes = ds.GetGeoTransform()
    # 计算偏移
    xOffset = (xMin - lndMinX) / xRes
    yOffset = (yMax - lndMaxY) / yRes
    # 读取数据
    data = ds.ReadAsArray(xOffset, yOffset, lines, cols).astype(np.int8)
    del ds

    return data


@isExists
def fy4Rc(fy4_path, idx):
    '''
    radiometric calibration for FY 4
    '''

    nom = 'NOMChannelXX'
    cal = 'CALChannelXX'

    fy_4_dataset = h5py.File(fy4_path)

    # get nom name
    nomxx = nom.replace('XX', '{:02d}'.format(idx))
    # get cal name
    calxx = cal.replace('XX', '{:02d}'.format(idx))
    # get vaild range
    valid_range = fy_4_dataset[nomxx].attrs['valid_range']
    valid_range_cal = fy_4_dataset[calxx].attrs['valid_range']
    # nom
    nom_data = fy_4_dataset[nomxx][:]
    # cal
    cal_data = fy_4_dataset[calxx][:]

    # valid_range
    vaild_min = int(valid_range[0])
    valid_max = int(valid_range[1])

    # nom dataset to ndarray
    nom_data_array1 = np.copy(nom_data).astype(np.int32)
    # remove invalid value
    nom_array1 = np.where(nom_data_array1 <= valid_max, nom_data_array1, 0)
    nom_array = np.where(nom_data_array1 >= vaild_min, nom_array1, 0)

    # calibration value
    cal_dic = dict(enumerate(cal_data))
    k = np.array(list(cal_dic.keys()))
    v = np.array(list(cal_dic.values()))

    # replace value
    calibration_value = np.zeros(k.max() + 1, dtype=v.dtype)
    calibration_value[k] = v
    result = calibration_value[nom_array]

    # remove invalid value
    result1 = np.where(nom_data_array1 <= valid_max, result, nodata)
    rc = np.where(nom_data_array1 >= vaild_min, result1, nodata)

    vaild_min_cal = float(valid_range_cal[0])
    vaild_max_cal = float(valid_range_cal[1])

    rc[rc < vaild_min_cal] = nodata
    rc[rc > vaild_max_cal] = nodata

    # close
    fy_4_dataset.close()

    return rc  # radiative calibration of the idx band


@isExists
def fy4L2(l2File, xMin, xMax, yMin, yMax, key, res=4000):
    ''' 提取数据 '''

    # 打开数据
    nc_obj = Dataset(l2File)

    # 读取数据值
    value = nc_obj.variables[key][:]
    value[value > 900] = nodata
    # 关闭
    nc_obj.close()

    # 提取范围内数据
    data = extractData(value, xMin, xMax, yMin, yMax, res)

    # 返回结果
    return data.data


@isExists
def fy4L1(l1File, xMin, xMax, yMin, yMax, idx=7, res=2000):
    ''' 提取数据 '''

    # 读取数据，进行校正
    value = fy4Rc(l1File, idx)
    # 提取范围内数据
    data = extractData(value, xMin, xMax, yMin, yMax, res)

    # 返回结果
    return data


@isExists
def extractL1(l1File, idx, res=2000):
    '''读取一级数据'''
    data = fy4L1(l1File, xMin, xMax, yMin, yMax, idx, res)
    return data


@isExists
def extractCLM(clmFile):
    ''' 建立云掩膜 '''

    # 读取数据
    clmArr = fy4L2(clmFile, xMin - 0.04, xMax + 0.04, yMin - 0.04, yMax + 0.04, 'CLM').astype(np.int16)

    # 建立最后的云掩膜数组
    clm = np.full_like(clmArr, 1, dtype=np.int8)
    # 3*3 窗口遍历 获取云数据
    for y in range(0, clmArr.shape[0] - 2, 1):
        for x in range(0, clmArr.shape[1] - 2, 1):
            # 如果大于.8 则判断为晴空
            if np.sum(clmArr[y:y + 3, x:x + 3] == 3) / 9 >= .8:
                clm[y + 1, x + 1] = 0

    clm = clm[1:-1, 1:-1]

    return clm


@isExists
def extractLST(lstFile):
    '''提取lst文件'''

    # 提取范围内的lst
    lst = fy4L2(lstFile, xMin, xMax, yMin, yMax, 'LST', res=4000)
    return lst


@isExists
def extractLPW(lpwFile):
    '''提取tpw文件'''

    # 提取范围内的tpw
    tpw = fy4L2(lpwFile, xMin, xMax, yMin, yMax, 'TPW', res=4000)
    return tpw


@isExists
def extractGEO(geoFile):
    '''提取高度角文件'''

    # 提取范围内的天顶角
    geo = fy4L2(geoFile, xMin, xMax, yMin, yMax, 'NOMSunZenith', res=4000)
    # 转化为高度角
    geo = np.abs(90 - geo)
    return geo


@isExists
def fy3dL2(file):
    '''读取fy3d mersi lst 数据'''

    # 打开
    h5Obj = h5py.File(file)

    def readData(h5Obj, key):
        # 读取数据
        lstDS = h5Obj[key]
        # 数据偏移
        slope = lstDS.attrs['Slope']
        Intercept = lstDS.attrs['Intercept']
        FillValue = lstDS.attrs['FillValue']
        # 实际数据值
        lst = lstDS[:] * slope + Intercept
        # 去除无效值
        lst[lst == FillValue] = nodata
        return lst

    # 白天数据
    dLst = readData(h5Obj, 'MERSI_1Km_LST_D')
    # 夜晚数据
    nLst = readData(h5Obj, 'MERSI_1Km_LST_N')

    # 获取数据的四至
    maxLon = h5Obj.attrs['Right-Bottom X'][0]
    minLon = h5Obj.attrs['Left-Top X'][0]
    minLat = h5Obj. attrs['Right-Bottom Y'][0]
    maxLat = h5Obj.attrs['Left-Top Y'][0]

    # 获取数据分辨率
    cellsX = h5Obj.attrs['Resolution X'][0]
    cellsY = h5Obj.attrs['Resolution Y'][0]

    # 关闭数据集
    h5Obj.close()

    # 返回字典
    content = {
        'day': dLst,
        'night': nLst,
        'extent': [minLon, maxLon, minLat, maxLat],
        'cells': [cellsX, cellsY],
    }
    return content


@isExists
def un_gz(file_name):
    # 获取文件的名称，去掉后缀名
    f_name = file_name.replace(".gz", "")
    # 开始解压
    g_file = gzip.GzipFile(file_name)
    # 读取解压后的文件，并写入去掉后缀名的同名文件（即得到解压后的文件）
    open(f_name, "wb+").write(g_file.read())
    g_file.close()
    return f_name


def extractFy3d(fy3dPath, ymd):
    '''读取风云3D数据'''

    # 3d mersi lst 数据名称
    fy3dMersi = 'FY3D_MERSI_%s_L2_LST_MLT_GLL_%s_POAD_1000M_MS.HDF'

    # 30
    file_30B0 = os.path.join(fy3dPath, fy3dMersi % ('30B0', ymd))
    if not os.path.isfile(file_30B0):
        print('Inputfile not exists: %s' % file_30B0)
        return -1
    # 40
    file_40B0 = os.path.join(fy3dPath, fy3dMersi % ('40B0', ymd))
    if not os.path.isfile(file_40B0):
        print('Inputfile not exists: %s' % file_40B0)
        return -1

    # 读取数据
    fy3d30Dict = fy3dL2(file_30B0)
    fy3d40Dict = fy3dL2(file_40B0)

    # 合并数据
    allDayLst = np.vstack((fy3d40Dict['day'], fy3d30Dict['day']))
    allnightLst = np.vstack((fy3d40Dict['night'], fy3d30Dict['night']))

    # 合并后数组四至
    extent = [
        min(fy3d30Dict['extent'][0], fy3d40Dict['extent'][0]),  # min lon
        max(fy3d30Dict['extent'][1], fy3d40Dict['extent'][1]),  # max lon
        min(fy3d30Dict['extent'][2], fy3d40Dict['extent'][2]),  # min lat
        max(fy3d30Dict['extent'][3], fy3d40Dict['extent'][3]),  # max lat
    ]

    # 数据分辨率
    cells = fy3d30Dict['cells']

    # 列数
    width = int((xMax - xMin) / cells[0] + 0.5)
    # 行数
    height = int((yMax - yMin) / cells[1] + 0.5)

    # 数据偏移
    offsetX = int((xMin - extent[0] - cells[0] / 2) / cells[0])
    offsetY = int((extent[3] - yMax - cells[1] / 2) / cells[1])

    # 提取数据
    dayLst = allDayLst[offsetY: offsetY + height, offsetX: offsetX + width]
    nigLst = allnightLst[offsetY: offsetY + height, offsetX: offsetX + width]

    return np.array([dayLst[::-1], nigLst[::-1]])
