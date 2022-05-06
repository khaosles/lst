#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Project ：olympic_winter_games
@File ：main.py
@IDE  ：PyCharm 
@Author ：yherguot
@Date ：2022/5/4 6:29 PM 
@Desc: 
"""

import os
import sys
import getopt

basedir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(basedir)

from fy3d4a import fy3fy4
from fy4a import fy4down
from lst import inversion_tempature


def main(args):
    """主程序"""
    # 解析参数
    try:
        options, arg = getopt.getopt(args, "o", ["opt="])
    except getopt.GetoptError as err:
        print(err)
        return -1
    opt = None
    for option, value in options:
        if option in ('-o', '--opt'):
            opt = value
    # 校验参数并处理
    if not opt:
        print('param error')
        return -1
    if opt == 'fy3fy4':
        fy3fy4.main(args)
    elif opt == 'fy4down':
        fy4down.main(args)
    elif opt == 'lst':
        inversion_tempature.main(args)
    else:
        print('input error')
        return -1


if __name__ == '__main__':
    main(sys.argv[1:])
