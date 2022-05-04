1. fy3d fy4a 融合
python main.py (param)
--opt=fy3fy4
--fy3ddir=/Volumes/T7/winter/TestData/fy3d4a/fy3d           # fy3d文件夹目录
--fy4adir=/Volumes/T7/winter/TestData/fy3d4a/fy4a           # fy4a文件夹目录
--outdir=/Volumes/T7/winter/TestData/fy3d4a/outfir          # 输出文件夹目录
--ymd=20191030                                              # 文件日期


2. fy4降尺度
python main.py (param)
--opt=fy4down
--ims=/Volumes/T7/winter/TestData/fy4adown/ims/ims2021315_00UTC_4km_v1.3.asc.gz     # ims数据
--lstdir=/Volumes/T7/winter/TestData/fy4adown/lst                                   # fy4a lst文件夹目录
--lpwdir=/Volumes/T7/winter/TestData/fy4adown/tpw                                   # fy4a 水汽文件夹目录
--clmdir=/Volumes/T7/winter/TestData/fy4adown/clm                                   # fy4a 云掩膜目录
--geodir=/Volumes/T7/winter/TestData/fy4adown/l1                                    # fy4a geo文件目录
--l12kmdir=/Volumes/T7/winter/TestData/fy4adown/l1                                  # fy4a 1级数据2km 文件夹目录
--l14kmdir=/Volumes/T7/winter/TestData/fy4adown/l1                                  # fy4a 1级数据4km 文件夹目录
--outdir=/Volumes/T7/winter/TestData/fy4adown/outdir                                # 输出文件夹目录
--ymd=20211107                                                                      # 数据日期


3.温度反演
python main.py (param)
--opt=lst
--sensor=                   # 传感器(modis, fy4a, fy3d, landsat8, himawari8)
--l1file=                   # 一级数据(landsat8输入 .MTL.txt)
--geofile=                  # fy3d fy4a 需要geo文件
--clmfile=                  # fy3d fy4a 需要clm文件
--lpwfile=                  # 水汽文件
--outfile=                  # 输出文件
--ymd=                      # 数据日期