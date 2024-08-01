# -*- coding: utf-8 -*-

import pandas as pd
import pymc3 as pm
import numpy as np
import arviz as az
import matplotlib.pyplot as plt
# 支持中文
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']

def fectch_data(filein):
    quit_jsl_df = pd.read_excel(filein,'jsl')
    quit_jsl_df = quit_jsl_df[~quit_jsl_df['名称'].str.endswith('EB')]
    
    df = quit_jsl_df[['存续年限','退市原因']]
    # 将退市原因编码成数字格式
    df['退市原因编码'] = df['退市原因'].apply(lambda x: 1 if x == "强赎" else 0)  # 强赎 = 1, 到期 = 0
    return df

if __name__ == '__main__':
    from sys import argv
    filein = ""
    if len(argv) > 1:
        filein = argv[1]
    else:
        print("please run like 'python redeem.py [file]'")
        exit(1)


    redeem_df = fectch_data(filein)
    
    
    years = redeem_df['存续年限'].values
    reasons = redeem_df['退市原因编码'].values

    # 使用 PyMC3 定义逻辑回归模型
    with pm.Model() as model:
        # 先验概率
        alpha = pm.Normal('alpha', mu=0, sigma=10)
        beta = pm.Normal('beta', mu=0, sigma=10)
    
        # 逻当我们使用逻辑回归模型时，背后的直觉是存续年限（years）和强赎的概率（p）之间可能存在某种线性关系。
        # 不过，由于概率 p 是0到1之间的值，我们需要通过某种方式将线性预测值映射到[0, 1]的区间。
        # Sigmoid函数（逻辑函数）正是用来实现这种映射的
        p = pm.Deterministic('p', pm.math.sigmoid(alpha + beta * years))
    
        #使用Bernoulli似然函数，这是因为退市原因是一个二分类变量：强赎（编码为1）和到期（编码为0）
        #果我们有基于某些解释变量（如存续年限）来预测一个事件会不会发生，那么Bernoulli分布是合适的选择
        likelihood = pm.Bernoulli('likelihood', p=p, observed=reasons)
        
        # 采样
        trace = pm.sample(2000, tune=1000, return_inferencedata=False)

    # 获取后验概率分布
    posterior_alpha = trace['alpha']
    posterior_beta = trace['beta']
  
    # 定义不同存续时间条件
    years_range = np.linspace(min(years), max(years), 72)
    
    # 计算不同存续时间条件下的强赎后验概率
    posterior_p = np.array([pm.math.sigmoid(posterior_alpha[i] + posterior_beta[i] * years_range).eval() for i in range(len(posterior_alpha))])
    print(f"length of posterior_p:{len(posterior_p)},length of posterior_alpha:{len(posterior_alpha)}")
    
    # 计算每个时间点上的中位数
    median_p = np.median(posterior_p, axis=0)

    # 绘制不同存续时间条件下的强赎后验概率分布
    plt.fill_between(years_range, np.percentile(posterior_p, 2.5, axis=0), np.percentile(posterior_p, 97.5, axis=0), alpha=0.5)
    plt.plot(years_range, median_p, label='后验概率中位数')
    plt.xlabel('存续年限')
    plt.ylabel('强赎后验概率')
    plt.legend()
    plt.title('不同存续时间条件下的强赎后验概率分布')
    plt.savefig("bayes.png")
    plt.show()

    # 打印退市原因为强赎的后验概率均值和95%后验概率区间
    posterior_hpd = az.hdi(posterior_p, hdi_prob=0.95)
    print(f"median_p个数:{len(median_p)},posterior_hpd个数:{len(posterior_hpd)}")
    
    [ print(f"{years_range[i]},{median_p[i]},{posterior_hpd[i]}") for i in range(len(years_range)) ]
   