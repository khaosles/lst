#!usr/bin/env python
# -*- coding: utf-8 -*-

'''
    @author: khaosles
    @date: 2022/3/17  16:40
'''

from utils.utils import *
from utils.db import ParamQuery


def calcEpsilon(red, nir, MIN_E):
    '''计算地表比辐射率'''

    # 计算 ndvi
    ndvi = (nir - red) / (nir + red + 1e-10)

    # 缓存
    del nir, red

    # 裸土 ndvi
    NDVIMIN = .2
    # 纯植被 ndvi
    NDVIMAX = .5

    # 计算植被覆盖度
    vcf = np.where(
        ndvi > NDVIMAX, 1,
        np.where(
            ndvi < NDVIMIN, 0,
            (ndvi - NDVIMIN) / (NDVIMAX - NDVIMIN)
        )
    )
    vcf = vcf * vcf
    # 计算地表比辐射率
    epsilon = np.where(
        ndvi < NDVIMIN, MIN_E,
        np.where(
            ndvi > NDVIMAX, 0.99,
            0.99 * vcf + MIN_E * (1 - vcf)
        )
    )
    # 去除无效值
    epsilon[np.isnan(ndvi)] = np.nan

    # 返回
    return epsilon


def calcEpsilon_11(red, nir):
    '''计算地表比辐射率'''

    return calcEpsilon(red, nir, .9547)


def calcEpsilon_12(red, nir):
    '''计算地表比辐射率'''

    return calcEpsilon(red, nir, .9709)


def getFitParamAW(lpw, sza):
    '''查询拟合参数'''

    # 数据库地址
    dbfile = os.path.join(
        baseDir, '../resource', 'snow.db')
    # 查询拟合参数
    paramQuery = ParamQuery(dbfile)
    param = paramQuery.queryAW(lpw, sza)
    # 返回结果
    return param


def getFitParamAWT(lpw, sza, lst):
    '''查询拟合参数'''

    # 数据库地址
    dbfile = os.path.join(
        baseDir, '../resource', 'snow.db')
    # 查询拟合参数
    paramQuery = ParamQuery(dbfile)
    param = paramQuery.queryAWT(lpw, sza, lst)
    # 返回结果
    return param


def getSnowST(ims, b2, b3, b12, b13, geo, lpw):
    ''' 计算雪表温度 '''

    epsilon11 = calcEpsilon_11(b2, b3)
    epsilon12 = calcEpsilon_12(b2, b3)
    epsilon11[ims == 1] = .9632
    epsilon12[ims == 1] = .8990
    epsilon = (epsilon11 + epsilon12) / 2
    detalE = (epsilon11 - epsilon12) / 2

    lpw[np.isnan(lpw)] = np.nanmean(lpw)
    res = np.zeros_like(geo)
    for j in range(geo.shape[0]):
        for i in range(geo.shape[1]):
            # 非雪部分
            if ims[j, i] == 0:
                continue

            if all([~np.isnan(geo[j, i]), ~np.isnan(lpw[j, i])]):
                # 各个变量
                diff = (b12[j, i] - b13[j, i]) / 2
                summ = (b12[j, i] + b13[j, i]) / 2
                e1 = (1 - epsilon[j, i]) / epsilon[j, i]
                e2 = detalE[j, i] / epsilon[j, i] / epsilon[j, i]

                # 第一次获取拟合参数
                c, a1, a2, a3, b1, b2, b3 = getFitParamAW(lpw[j, i], geo[j, i])
                res[j, i] = c + a1 * summ + a2 * e1 * summ + a3 * summ * e2 + \
                            b1 * diff + b2 * e1 * diff + b3 * e2 * diff

                # 第二次获取拟合参数
                c, a1, a2, a3, b1, b2, b3 = getFitParamAWT(lpw[j, i], geo[j, i], res[j, i])
                res[j, i] = c + a1 * summ + a2 * e1 * summ + a3 * summ * e2 + \
                            b1 * diff + b2 * e1 * diff + b3 * e2 * diff

    return res


def test1():
    clmFile = r'H:\FY4A_DATA\L2\CLM\2021\20211107\FY4A-_AGRI--_N_DISK_1047E_L2-_CLM-_MULT_NOM_20211107060000_20211107061459_4000M_V0001.NC'
    geoFile = r'H:\FY4A_DATA\L1\2021\20211107\FY4A-_AGRI--_N_DISK_1047E_L1-_GEO-_MULT_NOM_20211107060000_20211107061459_4000M_V0001.HDF'
    l1File = r'H:\FY4A_DATA\L1\2021\20211107\FY4A-_AGRI--_N_DISK_1047E_L1-_FDI-_MULT_NOM_20211107060000_20211107061459_4000M_V0001.HDF'
    # lstFile = r'H:\FY4A_DATA\L2\LST\2021\20211107\FY4A-_AGRI--_N_DISK_1047E_L2-_LST-_MULT_NOM_20211107000000_20211107001459_4000M_V0001.NC'
    lpwFile = r'H:\FY4A_DATA\L2\LPW\2021\20211107\FY4A-_AGRI--_N_DISK_1047E_L2-_LPW-_MULT_NOM_20211107060000_20211107061459_4000M_V0001.NC'
    imsFile = r'H:\FY4A_DATA\IMS\NOM\2021\ims2021315_1km_v1.3.tif'

    ims = gdal.Open(imsFile).ReadAsArray()
    ims = np.where(ims == 4, 1, 0)
    ims = ims[0::4, 0::4] \
          + ims[0::4, 1::4] \
          + ims[0::4, 2::4] \
          + ims[0::4, 3::4] \
          + ims[1::4, 0::4] \
          + ims[1::4, 1::4] \
          + ims[1::4, 2::4] \
          + ims[1::4, 3::4] \
          + ims[2::4, 0::4] \
          + ims[2::4, 1::4] \
          + ims[2::4, 2::4] \
          + ims[2::4, 3::4] \
          + ims[3::4, 0::4] \
          + ims[3::4, 1::4] \
          + ims[3::4, 2::4] \
          + ims[3::4, 3::4]
    ims = np.where(ims > 8, 1, 0)
    clm = extractCLM(clmFile)
    # ims = np.full_like(clm, 1)
    geo = extractGEO(geoFile)
    lpw = extractLPW(lpwFile)
    b2 = extractL1(l1File, 2, 4000)
    b3 = extractL1(l1File, 3, 4000)
    b12 = extractL1(l1File, 12, 4000)
    b13 = extractL1(l1File, 13, 4000)
    b12[np.isnan(clm)] = np.nan
    saveImage(r'H:\Testdata\Output\test12.tif', b12, res=0.04)
    saveImage(r'H:\Testdata\Output\test12.tif', b12, res=0.04)
    saveImage(r'H:\Testdata\Output\ims.tif', ims, res=0.04)

    epsilon11 = calcEpsilon_11(b2, b3)
    epsilon12 = calcEpsilon_12(b2, b3)
    epsilon11[ims == 1] = .9632
    epsilon12[ims == 1] = .8990
    epsilon = (epsilon11 + epsilon12) / 2
    detalE = (epsilon11 - epsilon12) / 2
    sst = getSnowST(geo, lpw, b12, b13, epsilon, detalE, ims)
    sst[sst == 0] = np.nan
    sst[clm == 0] = np.nan
    print(sst)
    print(np.nanmax(sst))
    print(np.nanmin(sst))
    print(np.unique(sst))

    filename = r'H:\Testdata\Output\sst.tif'
    saveImage(filename, sst, res=0.04)


def main():
    # param = getFitParam(1, 10)
    # print(param)
    test1()


if __name__ == '__main__':
    # file = r'H:\FY4A_DATA\IMS\NOM\2021\ims2021315_1km_v1.3.asc'
    # out = r'H:\FY4A_DATA\IMS\NOM\2021\ims2021315_1km_v1.3.tif'
    # extractIMS(file, out)
    main()
