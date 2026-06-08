#!/usr/bin/env python3
"""
CICCAS 数据批量导入脚本
支持从国家统计局Excel文件批量导入2010-2024年数据
"""

import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.append('/app')
from utils.data_importer import IncomeDataImporter, ConsumptionDataImporter, DataProcessor

def prepare_sample_data():
    """生成示例数据（用于测试）"""
    provinces = ['北京', '上海', '天津', '重庆', '河北', '山西', '辽宁', '吉林',
                 '黑龙江', '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南',
                 '湖北', '湖南', '广东', '广西', '海南', '四川', '贵州', '云南',
                 '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆', '内蒙古']

    # 【修改点】：将 sample 改为 raw，适配真实目录结构
    os.makedirs('/app/data/raw', exist_ok=True)

    # 生成2010-2024年收入数据
    for year in range(2010, 2025):
        data = []
        base_income = 20000 + (year - 2010) * 2500  # 逐年增长

        for i, prov in enumerate(provinces):
            # 不同地区基线不同
            region_factor = 1.0 if i < 15 else 0.75
            income = base_income * region_factor * (0.8 + np.random.random() * 0.4)

            data.append({
                '省份': prov,
                '人均可支配收入': round(income, 2),
                '工资性收入': round(income * 0.65, 2),
                '经营净收入': round(income * 0.12, 2),
                '财产净收入': round(income * 0.08, 2),
                '转移净收入': round(income * 0.15, 2),
                '收入增长率': round(5 + np.random.random() * 5, 2)
            })

        df = pd.DataFrame(data)
        # 【修改点】：将 sample 改为 raw
        df.to_excel(f'/app/data/raw/income_{year}.xlsx', index=False)
        print(f"已生成: /app/data/raw/income_{year}.xlsx")

    # 生成消费数据
    for year in range(2010, 2025):
        data = []
        base_consumption = 15000 + (year - 2010) * 1500

        for i, prov in enumerate(provinces):
            region_factor = 1.0 if i < 15 else 0.72
            consumption = base_consumption * region_factor * (0.8 + np.random.random() * 0.4)

            data.append({
                '省份': prov,
                '人均消费支出': round(consumption, 2),
                '食品烟酒': round(consumption * 0.30, 2),
                '衣着': round(consumption * 0.07, 2),
                '居住': round(consumption * 0.22, 2),
                '生活用品及服务': round(consumption * 0.06, 2),
                '交通通信': round(consumption * 0.13, 2),
                '教育文化娱乐': round(consumption * 0.11, 2),
                '医疗保健': round(consumption * 0.09, 2),
                '其他用品及服务': round(consumption * 0.02, 2)
            })

        df = pd.DataFrame(data)
        # 【修改点】：将 sample 改为 raw
        df.to_excel(f'/app/data/raw/consumption_{year}.xlsx', index=False)
        print(f"已生成: /app/data/raw/consumption_{year}.xlsx")

def batch_import_data():
    """批量导入数据"""
    income_importer = IncomeDataImporter()
    consumption_importer = ConsumptionDataImporter()

    print("开始导入收入数据...")
    for year in range(2010, 2025):
        # 【修改点】：将 sample 改为 raw
        file_path = f'/app/data/raw/income_{year}.xlsx'
        if os.path.exists(file_path):
            try:
                stats = income_importer.import_from_excel(file_path, year, '国家统计局')
                print(f"  {year}年: {stats}")
            except Exception as e:
                print(f"  {year}年导入失败: {e}")

    print("\n开始导入消费数据...")
    for year in range(2010, 2025):
        # 【修改点】：将 sample 改为 raw
        file_path = f'/app/data/raw/consumption_{year}.xlsx'
        if os.path.exists(file_path):
            try:
                stats = consumption_importer.import_from_excel(file_path, year, '国家统计局')
                print(f"  {year}年: {stats}")
            except Exception as e:
                print(f"  {year}年导入失败: {e}")

def calculate_all_coupling():
    """计算所有年份的耦合协调度"""
    processor = DataProcessor()
    print("\n开始计算耦合协调度...")
    processor.run_full_calculation(2010, 2024)
    print("计算完成!")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='CICCAS数据导入工具')
    parser.add_argument('action', choices=['generate', 'import', 'calculate', 'all'])

    args = parser.parse_args()

    if args.action == 'generate':
        prepare_sample_data()
    elif args.action == 'import':
        batch_import_data()
    elif args.action == 'calculate':
        calculate_all_coupling()
    elif args.action == 'all':
        prepare_sample_data()
        batch_import_data()
        calculate_all_coupling()