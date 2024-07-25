# -*- coding: utf-8 -*-



import akshare as ak
import numpy as np  
import pandas as pd  
import math
import datetime
import os
import matplotlib.pyplot as plt
import openpyxl
import re
from datetime import datetime, timedelta

if __name__=='__main__':

    from sys import argv
    filein = ""
    if len(argv) > 1:
        filein = argv[1]
    else:
        print("please run like 'python redeem.py [file]'")
        exit(1)

    quit_jsl_df = pd.read_excel(filein,'jsl')
    quit_jsl_df = quit_jsl_df[~quit_jsl_df['名称'].str.endswith('EB')]
    
    
    reason_jsl_count = quit_jsl_df['退市原因'].count()
    reason_redeem_count = quit_jsl_df['退市原因'].value_counts()['强赎']
    redeem_ratio = reason_redeem_count/reason_jsl_count
    print("============全局强赎统计============")
    print("强赎比例:%f,总数:%d,强赎个数:%d" % (redeem_ratio,reason_jsl_count,reason_redeem_count))
    
    
    
    quit_jsl_df['最后交易日'] = pd.to_datetime(quit_jsl_df['最后交易日'])
    two_years_ago = datetime.now() - timedelta(days=2*365)
    last_two_years_jsl_df = quit_jsl_df[quit_jsl_df['最后交易日'] >= two_years_ago]
    #print(last_two_years_jsl_df)
    last_two_reason_jsl_count = last_two_years_jsl_df['退市原因'].count()
    last_two_reason_redeem_count = last_two_years_jsl_df['退市原因'].value_counts()['强赎']
    last_two_redeem_ratio = last_two_reason_redeem_count/last_two_reason_jsl_count
    print("============近两年强赎统计==========")
    print("近两年强赎比例:%f,近两年总数:%d,近两年强赎个数:%d" % (last_two_redeem_ratio,last_two_reason_jsl_count,last_two_reason_redeem_count))
 

    last_two_fileout = filein.replace('in','last')
    with pd.ExcelWriter(last_two_fileout, engine='xlsxwriter') as writer:
        last_two_years_jsl_df.to_excel(writer, sheet_name='last')
        print("近两年已退市转债输出:" + last_two_fileout)
    
   
    
    print("======强赎条件下的存续年限分布======")
    redeem_jsl_df = quit_jsl_df[quit_jsl_df['退市原因'] == '强赎']
    print(redeem_jsl_df['存续年限'].describe(percentiles = [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,0.91,0.92,0.93,0.94,0.95,0.96,0.97,0.98,0.99]))

    redeem_jsl_df = quit_jsl_df[quit_jsl_df['退市原因'] != '强赎']
    print("======非强赎条件下的存续年限分布=====")
    print(redeem_jsl_df['存续年限'].describe(percentiles = [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]))
    

    redeem_small_jsl_df = quit_jsl_df[quit_jsl_df['发行规模'] <=5.0 ]
    print("=小于5亿的剩余转债最后交易价格限分布==")
    print(redeem_small_jsl_df['最后交易价格'].describe(percentiles = [0.2,0.4,0.5,0.6,0.8]))
    
    fileout = filein.replace('in','small')
    with pd.ExcelWriter(fileout, engine='xlsxwriter') as writer:
        redeem_small_jsl_df.to_excel(writer, sheet_name='small')
        print("已退市小规模转债输出:" + fileout)






