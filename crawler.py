# -*- coding: utf-8 -*-
	
import pandas as pd
from selenium import webdriver
import time
import json
import datetime
import os

def get_browser(url):
    options = webdriver.ChromeOptions()
    #options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)


    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                          get: () => undefined
                        })
                      """
    })
    
    get_cookie(driver,url)
    set_cookie(driver)
    
    return driver



def set_cookie(driver):
	with open('cookies.json', 'r', encoding='utf-8') as f:
		listCookies = json.loads(f.read())

	for cookie in listCookies:
		driver.add_cookie(cookie)


def get_cookie(driver,url):
	driver.get(url)
	#这里可以手动登录 或者代码登录 
	time.sleep(50)
	dictCookies = driver.get_cookies()
	jsonCookies = json.dumps(dictCookies)
	print(jsonCookies)
	# 登录完成后，将cookie保存到本地文件
	with open('cookies.json', 'w') as f:
		f.write(jsonCookies)
	print("please check cookie in cookies.json")

def convert_float(rt1,rt2):
		ratio1 = float(rt1.strip('%'))
		ratio2 = float(rt2.strip('%'))
		return ratio1,ratio2


if __name__=='__main__':
			url = 'https://www.jisilu.cn/web/data/cb/delisted'
			browser = get_browser(url)
						
			browser.get(url)
			time.sleep(10)
			data = browser.page_source
			tables = pd.read_html(data,header=None)
			print(f"tables[0]:{tables[0]}")
			print(f"tables[1]:{tables[1]}")
			
			
			column1 = tables[1].columns.tolist()
			column0 = tables[0].columns.tolist()
			zipped = zip(column1, column0)
			#使用dict()函数将元组列表转换为字典
			dictionary = dict(zipped)
			print(f"column1:{column1},column0:{column0},dictionary:{dictionary}")
			jsl_df_raw = tables[1].rename(columns=dictionary)
			jsl_df = jsl_df_raw.rename(columns={'发行规模(亿元)': '发行规模', '回售规模(亿元)': '回售规模','剩余规模(亿元)': '剩余规模','存续年限(年)': '存续年限'})

			print(f"jsl_df:{jsl_df}")
			
			tnow = datetime.datetime.now()
			print("time is :" + tnow.strftime('%Y%m%d'))
			filein = tnow.strftime('%Y_%m_%d') + '_in.xlsx'
			getakpath =  "./%s" % (filein)
			jsl_df.replace('-','0',inplace=True)
			
			#修改名称
			
			#jsl_df.to_excel(getakpath,header=['代码','名称','最后交易价格', '正股代码','正股名称', '发行规模','回售规模','剩余规模', '发行日期','最后交易日', '到期日期','存续年限','退市原因'],index=False,sheet_name='jsl')
			jsl_df.to_excel(getakpath,index=False,sheet_name='jsl')
			print("data of path:" + getakpath)