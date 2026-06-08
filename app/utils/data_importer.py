"""
CICCAS 数据导入处理系统
支持国家统计局数据自动导入、数据清洗、缺失值处理
"""

import pandas as pd
import numpy as np
import pymysql
from sqlalchemy import create_engine, text
import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """数据库配置"""
    def __init__(self):
        # 终极兼容：优先读取 DB_* 变量，其次读取 MYSQL_* 变量，最后进行 Docker 本地降级默认
        self.host = os.getenv('DB_HOST', os.getenv('MYSQL_HOST', 'mysql'))
        self.port = int(os.getenv('DB_PORT', os.getenv('MYSQL_PORT', '3306')))
        self.database = os.getenv('DB_NAME', os.getenv('MYSQL_DATABASE', 'cicdb'))
        self.user = os.getenv('DB_USER', os.getenv('MYSQL_USER', 'root'))
        self.password = os.getenv('DB_PASSWORD', os.getenv('MYSQL_PASSWORD', '123456'))

    def get_connection_string(self):
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def get_connection(self):
        return pymysql.connect(
            host=self.host, port=self.port,
            database=self.database,
            user=self.user, password=self.password,
            charset='utf8mb4'
        )


class DataImporter:
    """数据导入管理器"""

    def __init__(self):
        self.config = DatabaseConfig()
        self.engine = create_engine(self.config.get_connection_string())
        self.province_mapping = self._load_province_mapping()
        self.cpi_data = self._load_cpi_data()

    def _load_province_mapping(self) -> Dict[str, str]:
        """加载省份编码映射"""
        mapping = {
            '北京': '110000', '天津': '120000', '河北': '130000', '山西': '140000',
            '内蒙古': '150000', '辽宁': '210000', '吉林': '220000', '黑龙江': '230000',
            '上海': '310000', '江苏': '320000', '浙江': '330000', '安徽': '340000',
            '福建': '350000', '江西': '360000', '山东': '370000', '河南': '410000',
            '湖北': '420000', '湖南': '430000', '广东': '440000', '广西': '450000',
            '海南': '460000', '重庆': '500000', '四川': '510000', '贵州': '520000',
            '云南': '530000', '西藏': '540000', '陕西': '610000', '甘肃': '620000',
            '青海': '630000', '宁夏': '640000', '新疆': '650000'
        }
        return mapping

    def _load_cpi_data(self) -> Dict[int, float]:
        """加载CPI数据用于不变价转换"""
        try:
            query = "SELECT year, cumulative_cpi FROM cpi_conversion"
            df = pd.read_sql(query, self.engine)
            return dict(zip(df['year'], df['cumulative_cpi']))
        except Exception as e:
            logger.warning(f"加载CPI数据失败: {e}")
            return {}

    def log_import_start(self, import_type: str, file_name: str,
                         data_source: str, operator: str = 'system') -> str:
        """记录导入开始"""
        batch_id = hashlib.md5(
            f"{datetime.now()}{file_name}".encode()
        ).hexdigest()[:16]

        conn = self.config.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO data_import_log
                    (import_batch_id, import_type, file_name, data_source, operator,
                     processing_status, started_at)
                    VALUES (%s, %s, %s, %s, %s, '处理中', NOW())
                """
                cursor.execute(sql, (batch_id, import_type, file_name,
                                    data_source, operator))
                conn.commit()
        finally:
            conn.close()

        return batch_id

    def log_import_complete(self, batch_id: str, stats: Dict):
        """记录导入完成"""
        conn = self.config.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                    UPDATE data_import_log SET
                        records_total = %s,
                        records_success = %s,
                        records_failed = %s,
                        records_skipped = %s,
                        processing_status = %s,
                        processing_details = %s,
                        completed_at = NOW()
                    WHERE import_batch_id = %s
                """
                cursor.execute(sql, (
                    stats.get('total', 0),
                    stats.get('success', 0),
                    stats.get('failed', 0),
                    stats.get('skipped', 0),
                    stats.get('status', '已完成'),
                    json.dumps(stats.get('details', {}), ensure_ascii=False),
                    batch_id
                ))
                conn.commit()
        finally:
            conn.close()

    def detect_file_type(self, file_path: str) -> str:
        """检测文件类型"""
        ext = Path(file_path).suffix.lower()
        if ext in ['.xlsx', '.xls']:
            return 'excel'
        elif ext == '.csv':
            return 'csv'
        elif ext == '.json':
            return 'json'
        else:
            raise ValueError(f"不支持的文件类型: {ext}")

    def normalize_province_name(self, name: str) -> Optional[str]:
        """标准化省份名称"""
        if pd.isna(name):
            return None

        name = str(name).strip()

        # 去除"省"、"市"、"自治区"等后缀
        name = re.sub(r'(省|市|自治区|特别行政区)$', '', name)

        # 特殊处理
        name_map = {
            '内蒙': '内蒙古',
            '广西': '广西',
            '西藏': '西藏',
            '宁夏': '宁夏',
            '新疆': '新疆'
        }

        for short, full in name_map.items():
            if name.startswith(short):
                return full

        return name if name in self.province_mapping else None

    def convert_to_real_value(self, nominal_value: float, year: int) -> float:
        """将名义值转换为不变价（2010年基期）"""
        if pd.isna(nominal_value) or year not in self.cpi_data:
            return nominal_value
        return nominal_value / self.cpi_data[year] * 100

    def fill_missing_quarterly(self, df: pd.DataFrame,
                               province_col: str, year_col: str,
                               quarter_col: str, value_col: str) -> pd.DataFrame:
        """季度数据缺失值填充（同省份相邻3期均值法）"""
        df = df.sort_values([province_col, year_col, quarter_col])

        for province in df[province_col].unique():
            mask = df[province_col] == province
            province_data = df.loc[mask, value_col].copy()

            # 使用前后3期均值填充
            df.loc[mask, value_col] = province_data.fillna(
                province_data.rolling(window=3, min_periods=1, center=True).mean()
            )

        return df

    def fill_missing_annual(self, df: pd.DataFrame,
                           province_col: str, year_col: str,
                           value_col: str, region_col: str = None) -> pd.DataFrame:
        """年度数据缺失值填充（同区域同收入水平省份均值法）"""
        if region_col:
            # 按区域和年份计算均值填充
            df[value_col] = df.groupby([region_col, year_col])[value_col].transform(
                lambda x: x.fillna(x.mean())
            )

        # 仍未填充的，使用同省份插值
        df[value_col] = df.groupby(province_col)[value_col].transform(
            lambda x: x.interpolate(method='linear', limit_direction='both')
        )

        return df

    def validate_data(self, df: pd.DataFrame, data_type: str) -> Tuple[pd.DataFrame, List[str]]:
        """数据验证"""
        errors = []
        valid_df = df.copy()

        # 1. 检查省份编码
        invalid_provinces = valid_df[~valid_df['province_code'].isin(
            self.province_mapping.values()
        )]
        if len(invalid_provinces) > 0:
            errors.append(f"发现{len(invalid_provinces)}条无效省份编码")
            valid_df = valid_df[valid_df['province_code'].isin(
                self.province_mapping.values()
            )]

        # 2. 检查年份范围
        valid_df = valid_df[(valid_df['year'] >= 2010) & (valid_df['year'] <= 2025)]

        # 3. 检查负值（收入消费应为正）
        if data_type == 'income':
            negative = valid_df[valid_df['disposable_income'] < 0]
            if len(negative) > 0:
                errors.append(f"发现{len(negative)}条负收入数据，已标记")
                valid_df.loc[negative.index, 'data_status'] = '异常'

        # 4. 检查异常值（3倍标准差外）
        for col in ['disposable_income', 'consumption_expenditure']:
            if col in valid_df.columns:
                mean = valid_df[col].mean()
                std = valid_df[col].std()
                outliers = valid_df[abs(valid_df[col] - mean) > 3 * std]
                if len(outliers) > 0:
                    errors.append(f"{col}发现{len(outliers)}个异常值")

        return valid_df, errors


class IncomeDataImporter(DataImporter):
    """收入数据导入器"""

    def import_from_excel(self, file_path: str, year: int,
                         data_source: str = '国家统计局') -> Dict:
        """从Excel导入收入数据"""
        batch_id = self.log_import_start('收入数据', file_path, data_source)

        try:
            # 读取Excel
            df = pd.read_excel(file_path)
            logger.info(f"读取到{len(df)}行数据")

            # 标准化列名
            column_mapping = {
                '省份': 'province_name',
                '人均可支配收入': 'disposable_income',
                '工资性收入': 'wage_income',
                '经营净收入': 'business_income',
                '财产净收入': 'property_income',
                '转移净收入': 'transfer_income',
                '收入增长率': 'income_growth_rate'
            }

            df = df.rename(columns=column_mapping)

            # 添加省份编码
            df['province_name'] = df['province_name'].apply(self.normalize_province_name)
            # 【核心 Bug 修复】：直接通过映射字典转换，不要进行不正确的反转
            df['province_code'] = df['province_name'].map(self.province_mapping)

            # 添加基础字段
            df['year'] = year
            df['data_type'] = '年度'
            df['data_source'] = data_source
            df['data_status'] = '原始'

            # 转换为不变价
            for col in ['disposable_income', 'wage_income', 'business_income',
                       'property_income', 'transfer_income']:
                if col in df.columns:
                    real_col = f'real_{col}'
                    df[real_col] = df[col].apply(
                        lambda x: self.convert_to_real_value(x, year)
                    )

            # 【核心 Bug 修复】：把计算出的 real_disposable_income 写入核心 real_income 字段
            if 'real_disposable_income' in df.columns:
                df['real_income'] = df['real_disposable_income']
            else:
                df['real_income'] = df['disposable_income']

            # 验证数据
            df, errors = self.validate_data(df, 'income')

            # 导入数据库
            if len(df) > 0:
                df.to_sql('income_data', self.engine, if_exists='append',
                         index=False, method='multi')

            stats = {
                'total': len(df),
                'success': len(df),
                'failed': 0,
                'skipped': 0,
                'status': '已完成',
                'details': {'validation_errors': errors}
            }

            self.log_import_complete(batch_id, stats)
            logger.info(f"收入数据导入完成: {stats}")

            return stats

        except Exception as e:
            logger.error(f"导入失败: {e}")
            self.log_import_complete(batch_id, {
                'status': '失败',
                'error': str(e)
            })
            raise


class ConsumptionDataImporter(DataImporter):
    """消费数据导入器"""

    def import_from_excel(self, file_path: str, year: int,
                         data_source: str = '国家统计局') -> Dict:
        """从Excel导入消费数据"""
        batch_id = self.log_import_start('消费数据', file_path, data_source)

        try:
            df = pd.read_excel(file_path)

            # 标准化列名
            column_mapping = {
                '省份': 'province_name',
                '人均消费支出': 'consumption_expenditure',
                '食品烟酒': 'food_expenditure',
                '衣着': 'clothing_expenditure',
                '居住': 'housing_expenditure',
                '生活用品及服务': 'goods_expenditure',
                '交通通信': 'transport_expenditure',
                '教育文化娱乐': 'education_expenditure',
                '医疗保健': 'medical_expenditure',
                '其他用品及服务': 'other_expenditure'
            }

            df = df.rename(columns=column_mapping)

            # 省份编码转换
            df['province_name'] = df['province_name'].apply(self.normalize_province_name)
            # 【核心 Bug 修复】：直接映射省份编码，取消错误的反转
            df['province_code'] = df['province_name'].map(self.province_mapping)

            # 添加基础字段
            df['year'] = year
            df['data_type'] = '年度'
            df['data_source'] = data_source
            df['data_status'] = '原始'

            # 转换为不变价
            expenditure_cols = ['consumption_expenditure', 'food_expenditure',
                              'clothing_expenditure', 'housing_expenditure',
                              'goods_expenditure', 'transport_expenditure',
                              'education_expenditure', 'medical_expenditure',
                              'other_expenditure']

            for col in expenditure_cols:
                if col in df.columns:
                    real_col = f'real_{col}'
                    df[real_col] = df[col].apply(
                        lambda x: self.convert_to_real_value(x, year)
                    )

            # 【核心 Bug 修复】：把计算出的 real_consumption_expenditure 写入核心 real_consumption 字段
            if 'real_consumption_expenditure' in df.columns:
                df['real_consumption'] = df['real_consumption_expenditure']
            else:
                df['real_consumption'] = df['consumption_expenditure']

            # 验证数据
            df, errors = self.validate_data(df, 'consumption')

            # 导入数据库
            if len(df) > 0:
                df.to_sql('consumption_data', self.engine, if_exists='append',
                         index=False, method='multi')

            stats = {
                'total': len(df),
                'success': len(df),
                'errors': errors
            }

            self.log_import_complete(batch_id, {
                'total': len(df),
                'success': len(df),
                'status': '已完成',
                'details': {'validation_errors': errors}
            })

            return stats

        except Exception as e:
            logger.error(f"导入失败: {e}")
            self.log_import_complete(batch_id, {
                'status': '失败',
                'error': str(e)
            })
            raise


class DataProcessor:
    """数据处理器 - 计算衍生指标和耦合协调度"""

    def __init__(self):
        self.config = DatabaseConfig()
        self.engine = create_engine(self.config.get_connection_string())

    def calculate_engel_coefficient(self):
        """计算恩格尔系数"""
        query = """
            UPDATE consumption_data c
            JOIN income_data i ON c.province_code = i.province_code
                AND c.year = i.year AND c.data_type = i.data_type
            SET c.engel_coefficient = c.food_expenditure / c.consumption_expenditure
            WHERE c.consumption_expenditure > 0
        """
        with self.engine.connect() as conn:
            conn.execute(text(query))
            conn.commit()

    def calculate_coupling_degree(self, year: int, weight_income: float = 0.5,
                                  weight_consumption: float = 0.5):
        """计算指定年份的耦合协调度"""
        # 获取数据
        query = f"""
            SELECT
                i.province_code,
                i.year,
                i.real_income,
                c.real_consumption
            FROM income_data i
            JOIN consumption_data c ON i.province_code = c.province_code
                AND i.year = c.year AND i.data_type = c.data_type
            WHERE i.year = {year} AND i.data_type = '年度'
                AND i.real_income IS NOT NULL
                AND c.real_consumption IS NOT NULL
        """

        df = pd.read_sql(query, self.engine)

        if len(df) == 0:
            logger.warning(f"年份{year}无可用数据")
            return

        # 标准化
        max_income = df['real_income'].max()
        max_consumption = df['real_consumption'].max()

        df['u1'] = df['real_income'] / max_income
        df['u2'] = df['real_consumption'] / max_consumption

        # 计算耦合协调度
        df['coupling_c'] = (2 * np.sqrt(df['u1'] * df['u2']) / (df['u1'] + df['u2'])).fillna(0)
        df['comprehensive_t'] = weight_income * df['u1'] + weight_consumption * df['u2']
        df['coordination_d'] = np.sqrt(df['coupling_c'] * df['comprehensive_t'])

        # 保存结果
        results = df[['province_code', 'year', 'u1', 'u2', 'coupling_c',
                     'comprehensive_t', 'coordination_d']].copy()
        results.columns = ['province_code', 'year', 'income_system_u1',
                          'consumption_system_u2', 'coupling_degree_c',
                          'comprehensive_level_t', 'coordination_degree_d']
        results['weight_income'] = weight_income
        results['weight_consumption'] = weight_consumption

        # 【核心 Bug 修复】：根据 D 值得分区间计算协调划分等级，保存至数据库，用于前端大屏直接分类渲染
        def get_coordination_level(d: float) -> str:
            if d < 0.1: return '极度失调'
            elif d < 0.2: return '严重失调'
            elif d < 0.3: return '中度失调'
            elif d < 0.4: return '轻度失调'
            elif d < 0.5: return '濒临失调'
            elif d < 0.6: return '勉强协调'
            elif d < 0.7: return '初级协调'
            elif d < 0.8: return '中度协调'
            elif d < 0.9: return '良好协调'
            else: return '优质协调'

        results['coordination_level'] = results['coordination_degree_d'].apply(get_coordination_level)

        results.to_sql('coupling_results', self.engine, if_exists='append',
                      index=False, method='multi')

        logger.info(f"年份{year}耦合协调度计算完成，共{len(results)}条记录")

        return results

    def run_full_calculation(self, start_year: int = 2010, end_year: int = 2024):
        """运行全量计算"""
        logger.info(f"开始全量计算: {start_year}-{end_year}")

        for year in range(start_year, end_year + 1):
            try:
                self.calculate_coupling_degree(year)
            except Exception as e:
                logger.error(f"年份{year}计算失败: {e}")

        logger.info("全量计算完成")


# CLI命令行接口
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='CICCAS数据导入工具')
    parser.add_argument('command', choices=['import-income', 'import-consumption',
                                           'calculate', 'validate'])
    parser.add_argument('--file', '-f', help='数据文件路径')
    parser.add_argument('--year', '-y', type=int, help='数据年份')
    parser.add_argument('--source', '-s', default='国家统计局', help='数据来源')

    args = parser.parse_args()

    if args.command == 'import-income':
        importer = IncomeDataImporter()
        stats = importer.import_from_excel(args.file, args.year, args.source)
        print(json.dumps(stats, ensure_ascii=False, indent=2))

    elif args.command == 'import-consumption':
        importer = ConsumptionDataImporter()
        stats = importer.import_from_excel(args.file, args.year, args.source)
        print(json.dumps(stats, ensure_ascii=False, indent=2))

    elif args.command == 'calculate':
        processor = DataProcessor()
        processor.run_full_calculation()