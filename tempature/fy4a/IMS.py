#!usr/bin/env python
# -*- coding: utf-8 -*-

'''
    @author: khaosles
    @date: 2022/4/11  17:45
'''

from utils.utils import *


@isExists
def extractIMS(imsFile):
    '''提取ims文件'''

    imsFile = un_gz(imsFile)

    # 提取范围内的ims
    def y2i(y, maxLat=54.0, res=0.04):  # y 转行号
        if isinstance(y, (list, tuple)):
            y = np.array(y)
        return np.floor(((maxLat - res / 2.0) - y) / res).astype(int)

    def x2j(x, minLon=97.0, res=0.04):  # x 转列号
        if isinstance(x, (list, tuple)):
            x = np.array(x)
        return np.floor((x - (minLon + res / 2.0)) / res).astype(int)

    def fill_points_2d(box, invalidValue=0):
        '''
        #2维矩阵补点
        '''
        # 用上方的点补点
        condition = box == invalidValue
        condition[1:, :] = condition[1:, :] * np.logical_not(condition)[:-1, :]
        condition[0, :] = False
        index = np.where(condition)
        box[index[0], index[1]] = box[index[0] - 1, index[1]]

        # 用右方的点补点
        condition = box == invalidValue
        condition[:, :-1] = condition[:, :-1] * np.logical_not(condition)[:, 1:]
        condition[:, -1] = False
        index = np.where(condition)
        box[index[0], index[1]] = box[index[0], index[1] + 1]

        # 用下方的点补点
        condition = box == invalidValue
        condition[:-1, :] = condition[:-1, :] * np.logical_not(condition)[1:, :]
        condition[-1, :] = False
        index = np.where(condition)
        box[index[0], index[1]] = box[index[0] + 1, index[1]]

        # 用左方的点补点
        condition = box == invalidValue
        condition[:, 1:] = condition[:, 1:] * np.logical_not(condition)[:, :-1]
        condition[:, 0] = False
        index = np.where(condition)
        box[index[0], index[1]] = box[index[0], index[1] - 1]

    # 分辨率
    resolution = 0.04

    # 行数
    width = int((xMax - xMin) / 0.04 + 0.5)
    # 列数
    height = int((yMax - yMin) / 0.04 + 0.5)

    # 经纬度查找表文件
    lon_filename = os.path.join(baseDir, '../resource', 'geolocation', 'longitude.raw')
    lat_filename = os.path.join(baseDir, '../resource', 'geolocation', 'latitude.raw')
    grid_size = 6144

    with open(lat_filename, "r") as f:
        lat_array = np.fromfile(f, dtype=np.float32)
        latitude = lat_array.reshape(grid_size, grid_size)

    with open(lon_filename, "r") as f:
        lon_array = np.fromfile(f, dtype=np.float32)
        longitude = lon_array.reshape(grid_size, grid_size)

    H5Row, H5Col = longitude.shape
    iih5 = np.array([list(range(H5Row))] * H5Col).T.reshape((-1))  # hdf5的行1d序列
    jjh5 = np.array([list(range(H5Col))] * H5Row).reshape((-1))  # hdf5的列1d序列

    # 投影 lons,lats -> i,j
    lons = np.array(longitude).reshape((-1))  # 转成1维，因为proj只接收1维参数
    lats = np.array(latitude).reshape((-1))
    ii = y2i(lats, yMax, resolution)
    jj = x2j(lons, xMin, resolution)

    # 判断在网格里
    condition = np.logical_and(ii >= 0, ii < height)
    condition = np.logical_and(condition, jj >= 0)
    condition = np.logical_and(condition, jj < width)
    index = np.where(condition)
    ii = ii[index]
    jj = jj[index]
    if len(ii) == 0:
        print("Not Pass Ragion!\n")
        return -1

    iih5 = iih5[index]
    jjh5 = jjh5[index]

    # # 打开文件
    fp = open(imsFile, 'r')
    orderLines = fp.readlines()[30:]
    fp.close()

    # 获取数据
    ascii_grid = np.array(list(map(lambda line: [int(val) for val in line[:-1]], orderLines)))[:, ::-1]

    # 数据
    tmp3d = np.zeros((1, int(height), int(width)), dtype='f4')
    tmp3d[0, ii, jj] = ascii_grid[iih5, jjh5]

    # 对tmp3d 补点1次
    for n in range(1):
        fill_points_2d(tmp3d[0], 0)

    # 读取数据
    imsData = tmp3d[0]
    imsData = np.array(imsData, dtype='int16')

    return imsData



