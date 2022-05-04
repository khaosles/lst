#!usr/bin/env python
# -*- coding: utf-8 -*-

'''
    @author: khaosles
    @date: 2022/3/23  15:23
'''

import sqlite3


class ParamQuery(object):
    '''查询雪表温度反演参数'''

    def __init__(self, dbname):
        self.conn = self.__connect(dbname)

    def __del__(self):
        self.close()

    def __connect(self, dbname):
        '''连接数据库'''

        conn = sqlite3.connect(dbname)
        if conn is None:
            raise ConnectionError('参数数据库连接失败')
        return conn

    def close(self):
        '''关闭'''
        try:
            if self.conn is not None:
                self.conn.close()
        except:
            pass

    def query(self, sql):
        '''根据天顶角和水汽查询参数'''

        # 建立游标
        cursor = self.conn.cursor()
        try:
            # 查询参数
            result = cursor.execute(sql)
            # 提交结果
            self.conn.commit()

            result = list(result)

            # 返回
            return result[0]
        except Exception as err:
            print(err)
            return []
        finally:
            try:
                cursor.close()
            except:
                pass

    def queryAW(self, lpw, sza, sensor='FY4A', AT=3.0, AE=1.0):
        '''根据天顶角和水汽查询参数'''

        sql ='''
            SELECT
                "C", "A1", "A2", "A3", "B1", "B2", "B3"  
            FROM
                "%s_AW" 
            WHERE
                "SENSOR"='%s' AND "AT"=%s AND "AE"=%s AND
                ABS( %s - "TPW_MID" ) = ( SELECT MIN( ABS(%s - "TPW_MID") ) FROM "%s_AW" ) 
                AND ABS( %s - "SZA_MID" ) = ( SELECT MIN( ABS(%s - "SZA_MID") ) FROM "%s_AW" );
            ''' % (sensor, sensor, AT, AE, lpw, lpw, sensor, sza, sza, sensor)

        result = self.query(sql)
        return result

    def queryAWT(self, lpw, sza, lst, sensor='FY4A', AT=3.0, AE=1.0):
        '''根据天顶角和水汽查询参数'''

        sql ='''
            SELECT
                "C", "A1", "A2", "A3", "B1", "B2", "B3"  
            FROM
                "%s_AWT" 
            WHERE
                "SENSOR"='%s' AND "AT"=%s AND "AE"=%s AND
                ABS( %s - "TPW_MID" ) = ( SELECT MIN( ABS(%s - "TPW_MID") ) FROM "%s_AWT" ) 
                AND ABS( %s - "SZA_MID" ) = ( SELECT MIN( ABS(%s - "SZA_MID") ) FROM "%s_AWT" )
                AND ABS( %s - "LST_MID" ) = ( SELECT MIN( ABS(%s - "LST_MID") ) FROM "%s_AWT" );
            ''' % (sensor, sensor, AT, AE, lpw, lpw, sensor, sza, sza, sensor, lst, lst, sensor)

        result = self.query(sql)
        return result

