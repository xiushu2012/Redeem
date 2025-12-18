import pandas as pd
import time
import sys
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# ================= 配置区域 =================
if len(sys.argv) < 2:
    print("错误: 请提供输入文件路径作为参数")
    print("用法: python augment.py <输入文件路径>")
    sys.exit(1)

INPUT_FILE = sys.argv[1]
OUTPUT_FILE = INPUT_FILE.replace('in', 'au')

BOND_CODE_COL = '代码'  # Excel中存放转债代码的列名
BOND_NAME_COL = '名称'  # Excel中存放转债名称的列名
DELIST_REASON_COL = '退市原因' # 筛选列名
TARGET_REASON = '强赎'   # 筛选条件
# ===========================================

def get_bond_data(driver, bond_code, bond_name):
    """
    针对单个转债代码执行爬取逻辑
    """
    url = f"https://www.jisilu.cn/data/convert_bond_detail/{bond_code}"
    
    # === 构造正则表达式，顺序包含"提前"、"赎回"、bond_name、"公告"，且不包含"不提前" ===
    # 逻辑：整条标题中不能出现"不赎回"，并且按顺序匹配这四个关键词
    pattern_company_quotes = re.compile(
        rf"^(?!.*不提前).*提前.*赎回.*{re.escape(bond_name)}.*公告"
    )
    pattern_lawoffice_quotes = re.compile(r"提前.*赎回.*法律意见")
    
    print(f"正在处理: {url}->{bond_name}({bond_code})")
    print(
        "  -> 寻找目标: 标题按顺序包含'提前'、'赎回'、债券名称、'公告'（且不包含'不提前'）"
        "，或按顺序包含'提前'、'赎回'、'法律意见'的公告"
    )
    
    try:
        driver.get(url)
        time.sleep(3) # 等待页面加载

        # --- 步骤 1: 提取强赎时间 ---
        try:
            tab_annos = driver.find_element(By.ID, "lnk_annos")
            driver.execute_script("arguments[0].click();", tab_annos)
            time.sleep(1) 
        except Exception:
            pass

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        redemption_date_str = None
        redemption_price = None

        # 定位公告
        annos_div = soup.find('div', id='tbl_annos')
        matched_records = []  # 存储所有匹配的记录 (date_str, link_text, row)
        if annos_div:
            rows = annos_div.find_all('div', class_='grid-row')
            for row in rows:
                title_div = row.find('div', class_='grid-col-9')
                if title_div:
                    link_text = title_div.get_text(strip=True)
                    
                    # 对标题进行清洗：去掉空格、引号等，只保留用于比较的核心内容
                    cleaned_link_text = (
                        link_text.replace(" ", "")
                                 .replace(""", "")
                                 .replace(""", "")
                                 .replace('"', "")
                                 .replace("'", "")
                    )
                    
                    # 使用正则表达式进行匹配：匹配 pattern_company_quotes 或 pattern_lawoffice_quotes
                    if pattern_company_quotes.search(cleaned_link_text) or pattern_lawoffice_quotes.search(cleaned_link_text):
                        date_div = row.find('div', class_='grid-col-3')
                        if date_div:
                            date_str = date_div.get_text(strip=True)
                            matched_records.append((date_str, link_text, row))
                            print(f"  [匹配] 找到公告: {link_text}, 日期: {date_str}")
        
        # 找到最早的一条记录
        if matched_records:
            # 将日期字符串转换为 datetime 对象进行排序
            try:
                matched_records_with_dt = []
                for date_str, link_text, row in matched_records:
                    try:
                        date_dt = datetime.strptime(date_str, '%Y-%m-%d')
                        matched_records_with_dt.append((date_dt, date_str, link_text, row))
                    except ValueError:
                        continue  # 跳过无法解析的日期
                
                if matched_records_with_dt:
                    # 按日期排序，最早的在前
                    matched_records_with_dt.sort(key=lambda x: x[0])
                    earliest = matched_records_with_dt[0]
                    redemption_date_str = earliest[1]
                    print(f"  [成功] 选择最早的公告: {earliest[2]}")
                    print(f"  [成功] 提取日期: {redemption_date_str}")
            except Exception as e:
                print(f"  [错误] 日期排序时出错: {e}") 
        
        if not redemption_date_str:
            print(f"  [失败] 未在公告栏找到匹配的强赎公告")
            return None, None

        # --- 步骤 2: 提取强赎价格 (含模糊匹配逻辑) ---
        
        # 1. 将目标日期转换为 datetime 对象
        try:
            target_dt = datetime.strptime(redemption_date_str, '%Y-%m-%d')
        except ValueError:
            print(f"  [错误] 日期格式解析失败: {redemption_date_str}")
            return redemption_date_str, None

        date_cells = soup.find_all('td', attrs={'data-name': 'last_chg_dt'})
        
        target_row = None
        found_exact = False
        
        # 变量用于存储“最接近且小于目标日期”的候选行
        best_fallback_row = None
        best_fallback_dt = None

        for cell in date_cells:
            cell_text = cell.get_text(strip=True)
            try:
                cell_dt = datetime.strptime(cell_text, '%Y-%m-%d')
            except ValueError:
                continue # 跳过非日期格式的单元格

            # A. 精确匹配
            if cell_dt == target_dt:
                target_row = cell.parent
                found_exact = True
                break # 找到精确匹配，直接结束循环
            
            # B. 寻找备选：小于目标日期，且比当前找到的备选日期更大（更接近目标）
            if cell_dt < target_dt:
                if (best_fallback_dt is None) or (cell_dt > best_fallback_dt):
                    best_fallback_dt = cell_dt
                    best_fallback_row = cell.parent

        # 逻辑判断：如果没找到精确的，就用备选的
        if not found_exact:
            if best_fallback_row:
                target_row = best_fallback_row
                fallback_date_str = best_fallback_dt.strftime('%Y-%m-%d')
                print(f"  [提示] 未找到 {redemption_date_str}，已匹配最近前一交易日: {fallback_date_str}")
            else:
                print(f"  [警告] 未在下方历史行情表中找到日期 {redemption_date_str}，且未找到更早的日期")

        # 如果确定了行，提取价格
        if target_row:
            price_cell = target_row.find('td', attrs={'data-name': 'price'})
            if price_cell:
                redemption_price = price_cell.get_text(strip=True)
                print(f"  [成功] 提取价格: {redemption_price}")
            else:
                print("  [警告] 找到日期行，但未找到价格列")

        return redemption_date_str, redemption_price

    except Exception as e:
        print(f"  [错误] 发生异常: {e}")
        return None, None

def main():
    # 1. 读取 Excel
    try:
        df = pd.read_excel(INPUT_FILE, dtype={BOND_CODE_COL: str})
        # 删除可能存在的索引列 'Unnamed: 0'
        if 'Unnamed: 0' in df.columns:
            df = df.drop(columns=['Unnamed: 0'])
            print("已删除多余列: 'Unnamed: 0'")
        print(f"成功读取文件，共 {len(df)} 行。")
    except FileNotFoundError:
        print(f"错误: 未找到文件 {INPUT_FILE}")
        return
    except KeyError:
        print(f"错误: 列名匹配失败，请检查Excel中是否包含 '{BOND_CODE_COL}' 和 '{BOND_NAME_COL}' 列。")
        return

    # 2. 初始化浏览器
    chrome_options = Options()
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    except Exception:
        print("尝试使用本地 chromedriver.exe...")
        try:
            driver = webdriver.Chrome(service=Service("./chromedriver.exe"), options=chrome_options)
        except Exception as e:
            print("错误: 无法启动浏览器，请确保已安装 chromedriver。")
            print(e)
            return

    # 初始化新列
    if '强赎时间' not in df.columns:
        df['强赎时间'] = None
    if '强赎价格' not in df.columns:
        df['强赎价格'] = None

    # 3. 遍历并处理
    try:
        for index, row in df.iterrows():
            if row[DELIST_REASON_COL] == TARGET_REASON:
                bond_code = str(row[BOND_CODE_COL]).strip()
                bond_name = str(row[BOND_NAME_COL]).strip()
                
                r_date, r_price = get_bond_data(driver, bond_code, bond_name)
                
                if r_date:
                    df.at[index, '强赎时间'] = r_date
                if r_price:
                    df.at[index, '强赎价格'] = r_price
                
                time.sleep(1)
            else:
                pass

    except KeyboardInterrupt:
        print("用户中断程序，正在保存已处理的数据...")
    finally:
        driver.quit()

    # 4. 保存结果：直接输出到 OUTPUT_FILE
    df.to_excel(OUTPUT_FILE, index=False, sheet_name='jsl')
    print(f"处理完成，结果已保存至输出文件: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()