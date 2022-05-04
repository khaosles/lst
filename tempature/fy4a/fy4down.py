#!usr/bin/env python
# -*- coding: utf-8 -*-

'''
    @author: khaosles
    @date: 2022/4/11  16:56
'''

import os
import glob
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import getopt
import sys

from fy4a.SCT import getSnowST
from utils.utils import *
from fy4a.IMS import extractIMS


def fit(lstArr, l14KmArr, lnd):
    '''拟合'''

    # 保存模型参数
    modelList = list()
    # 获取下垫面类型
    lndList = np.unique(lnd)
    # 根据下垫面类型处理数据
    for lc in lndList:
        # 训练数据集y
        tempLst = list()
        # 训练数据集x
        trmpL1 = list()
        # 获取数据索引
        for i in range(len(lstArr)):
            tempLst.extend(list(lstArr[i][lnd == lc]))
            trmpL1.extend(list(l14KmArr[i][lnd == lc]))
        # 训练数据集y
        trainLst = list()
        # 训练数据集x
        trainL1 = list()
        # 去除无效值
        for idx, (ts_d, l1_d) in enumerate(zip(tempLst, trmpL1)):
            if np.isnan(ts_d) or np.isnan(l1_d):
                pass
            else:
                trainLst.append(ts_d)
                trainL1.append([l1_d])
        # sklearn  LinearRegression 最小二乘法拟合
        regr = LinearRegression()
        # 根据数据进行训练
        regr.fit(trainL1, trainLst)
        modelList.append(regr)

    # 返回不同下垫面类型的拟合参数
    return modelList


def predict(model, data):
    '''预测'''

    # 元数据行列号
    line, col = data.shape
    # nan 转化为 0
    data = np.nan_to_num(data)
    # 二维转成1维
    predictData = data.flatten()
    predictData = np.array(list(map(lambda v: [v], predictData)))
    # 预测
    result = model.predict(predictData)

    # 返回结果并改回原数据
    return result.reshape(line, col)


def fy4DownloadScaling(imsZip, lstPath, clmPath, lpwPath, geoPath, l12KmPath, l14KmPath, outPath, ymd):
    '''降尺度'''

    # 0、校验数据
    # 校验ims
    if not os.path.isfile(imsZip):
        print('ims文件不存在 %s' % imsZip)
        return -1

    # 读取lst文件列表
    lstFileList = glob.glob(os.path.join(lstPath, '*LST*%s0[0-9]*.NC' % ymd))
    lstFileList.extend(glob.glob(os.path.join(lstPath, '*LST*%s1[0-2]*.NC' % ymd)))
    # 读取clm文件列表
    clmFileList = glob.glob(os.path.join(clmPath, '*CLM*%s0[0-9]*.NC' % ymd))
    clmFileList.extend(glob.glob(os.path.join(clmPath, '*CLM*%s1[0-2]*.NC' % ymd)))
    # 读取lpw文件列表
    lpwFileList = glob.glob(os.path.join(lpwPath, '*LPW*%s0[0-9]*.NC' % ymd))
    lpwFileList.extend(glob.glob(os.path.join(lpwPath, '*LPW*%s1[0-2]*.NC' % ymd)))
    # 读取l1文件列表
    l14KmFileList = glob.glob(os.path.join(l14KmPath, '*L1*FDI*%s0[0-9]*4000M*.HDF' % ymd))
    l14KmFileList.extend(glob.glob(os.path.join(l14KmPath, '*L1*FDI*%s1[0-2]*4000M*.HDF' % ymd)))
    l12KmFileList = glob.glob(os.path.join(l12KmPath, '*L1*FDI*%s0[0-9]*2000M*.HDF' % ymd))
    l12KmFileList.extend(glob.glob(os.path.join(l12KmPath, '*L1*FDI*%s1[0-2]*2000M*.HDF' % ymd)))
    # 读取geo文件列表
    geoFileList = glob.glob(os.path.join(geoPath, '*L1*GEO*%s0[0-9]*4000M*.HDF' % ymd))
    geoFileList.extend(glob.glob(os.path.join(geoPath, '*L1*GEO*%s1[0-2]*4000M*.HDF' % ymd)))

    # # 校验文件个数是否相同
    if not (len(lstFileList) == len(clmFileList) == len(lpwFileList) ==
            len(l14KmFileList) == len(l12KmFileList) == len(geoFileList)):
        print('输入文件个数不一致')
        return -1

    # 输出文件夹不存在则创建
    if not os.path.isdir(outPath):
        os.makedirs(outPath)

    # 1、读取ims数据，并提取研究区内的数据
    ims = extractIMS(imsZip)
    if not isinstance(ims, np.ndarray):
        print('读取ims数据失败 %s' % imsZip)
        return -1
    imsArr = np.where(ims == 4, 1, 0)

    # 2、读取 lst clm l1，下垫面类型数据
    lstArr = np.array(list(map(extractLST, lstFileList)))  # lst列表
    clmArr = np.array(list(map(extractCLM, clmFileList)))  # 云列表
    timeList = list(map(extractTime, lstFileList))  # 数据时间 utc
    l12KmList = list(map(lambda file: extractL1(file, 7, 2000), l12KmFileList))  # 2km一级数据列表

    # 下垫面数据
    lnd = extractST()
    # 去云
    l12KmArr = np.array(l12KmList)
    l14KmArr = (l12KmArr[:, 0::2, 0::2] +
                l12KmArr[:, 1::2, 1::2] +
                l12KmArr[:, 0::2, 1::2] +
                l12KmArr[:, 1::2, 0::2]) / 4
    l14KmArr[clmArr == 1] = nodata
    lstArr[clmArr == 1] = nodata

    # 3、判断是否有雪，如果有雪，则读取 lpw geo 数据
    # 是否有雪标志
    isSnow = bool(np.sum(imsArr))
    if isSnow:
        lpwList = list(map(extractLPW, lpwFileList))  # 水蒸气列表
        geoList = list(map(extractGEO, geoFileList))  # 天顶角列表
        b2List = list(map(lambda file: extractL1(file, 2, 4000), l14KmFileList))  # 4km 2波段一级数据列表
        b3List = list(map(lambda file: extractL1(file, 3, 4000), l14KmFileList))  # 4km 3波段一级数据列表
        b12List = list(map(lambda file: extractL1(file, 12, 4000), l14KmFileList))  # 4km 12波段一级数据列表
        b13List = list(map(lambda file: extractL1(file, 13, 4000), l14KmFileList))  # 4km 13波段一级数据列表

        snowList = list()
        # 4、如果研究区内有雪，进行雪表温度反演，在下垫面数据中有雪的地方替换为雪， 在lst数据中把雪盖部分替换反演的雪表温度，否则跳过
        for idx, (b2, b3, b12, b13, geo, lpw) in enumerate(zip(b2List, b3List, b12List, b13List, geoList, lpwList)):
            # 反演雪表温度
            snowSTArr = getSnowST(imsArr, b2, b3, b12, b13, geo, lpw)
            snowSTArr[imsArr == 0] = nodata
            snowList.append(snowSTArr)

        snowArr = np.array(snowList)
        # 替换数据
        # lst
        lstArr = np.where(np.isnan(snowArr), lstArr, snowArr)
        # 下垫面
        lnd[imsArr == 1] = 6

        # 删除缓存
        del b2List, b3List, b12List, b13List, geoList, lpwList, snowList, snowArr

    # 5、根据不同下垫面类型对lst进行拟合
    # 下垫面采样2km
    lnd2km = lnd.repeat(2, 0).repeat(2, 1)
    # 根据极值温度计算拟合系数
    models = fit(lstArr, l14KmArr, lnd)

    # 获取下垫面类型
    lndList = np.unique(lnd)

    # 6、根据l1数据进行降尺度
    for i, (t, l1Arr) in enumerate(zip(timeList, l12KmList)):
        # 世界时影像起止时间
        sTime, eTime = t.split('_')
        # 转化为北京时
        sTimeBJ = datetime.strptime(sTime, '%Y%m%d%H%M%S') + timedelta(hours=8)
        eTimeBJ = datetime.strptime(eTime, '%Y%m%d%H%M%S') + timedelta(hours=8)

        # 建立输出
        result = np.zeros_like(l1Arr)
        for idx, lc in enumerate(lndList):
            # 预测
            result = np.where(
                lnd2km == lc, predict(models[idx], l1Arr), result)

        # 7、根据能量守恒按照权重对降尺度结果进行分配
        # 对结果进行升尺度
        resultUp = (result[0::2, 0::2] +
                    result[1::2, 1::2] +
                    result[0::2, 1::2] +
                    result[1::2, 0::2]) / 4

        # 计算温度差值 并处理成2km
        differenceValue = (resultUp - lstArr[i]).repeat(2, 0).repeat(2, 1)

        # 把升尺度的拟合温度插值成2km
        resultUp = resultUp.repeat(2, 0).repeat(2, 1)

        # 根据权值重新分配温度
        result = result - differenceValue * result / resultUp

        # 去云
        result[np.isnan(lstArr[i].repeat(2, 0).repeat(2, 1))] = nodata

        # 影像名称
        filename = os.path.join(outPath, 'FY4A_AGRI_LST_NOM_%s_%s_2000M.tif' % (
            sTimeBJ.strftime("%Y%m%d%H%M%S"), eTimeBJ.strftime("%Y%m%d%H%M%S")))
        if not os.path.isdir(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        # 保存
        saveImage(filename, result)



def main(args):
    """主程序"""
    # try:
    # 解析参数
    try:
        options, args = getopt.getopt(args, "", ["ims=", "lstdir=", "clmdir=", "lpwdir=", "geodir=", "l12kmdir=", "l14kmdir=", "outdir=", "ymd="])
    except getopt.GetoptError as err:
        print(err)
        return -1
    ims, lst_dir, clm_dir, lpw_dir, geo_dir, l12km_dir, l14km_dir, out_dir, ymd = [None] * 9
    for option, value in options:
        if option == "--ims":
            ims = value
        elif option == "--lstdir":
            lst_dir = value
        elif option == "--clmdir":
            clm_dir = value
        elif option == "--geodir":
            geo_dir = value
        elif option == "--lpwdir":
            lpw_dir = value
        elif option == "--l12kmdir":
            l12km_dir = value
        elif option == "--l14kmdir":
            l14km_dir = value
        elif option == "--outdir":
            out_dir = value
        elif option == "--ymd":
            ymd = value

    # 校验参数
    # 检验参数完整性
    if not all([ims, lst_dir, clm_dir, lpw_dir, geo_dir, l12km_dir, l14km_dir, out_dir, ymd]):
        print("get param error")
        return -1
    # 校验ims数据是否存在
    if not os.path.isfile(ims):
        print("ims file not exist")
        return -1
    # 校验输入文件夹是否存在
    if not all([os.path.isdir(dir) for dir in [lst_dir, clm_dir, lpw_dir, geo_dir, l12km_dir, l14km_dir]]):
        print("param error")
        return -1
    # 如果输入文件夹不存在，则进行创建
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    # 降尺度
    fy4DownloadScaling(ims, lst_dir, clm_dir, lpw_dir, geo_dir, l12km_dir, l14km_dir, out_dir, ymd)
    # except Exception as err:
    #     print("down error", str(err))
    #     return -1


if __name__ == '__main__':
    startTime = datetime.now()
    main(sys.argv[1:])
    endTime = datetime.now()
    print('StartTime: ' + startTime.strftime('%Y-%m-%d %H:%M:%S'))
    print('EndTime: ' + endTime.strftime('%Y-%m-%d %H:%M:%S'))
    print('ElapsedTime: ' + str((endTime - startTime).seconds))
    print('Success')
