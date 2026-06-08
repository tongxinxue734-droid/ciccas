"""
CICCAS 数据库操作模块
封装所有数据库操作，提供统一接口
"""

import pandas as pd
import numpy as np
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import os
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""

    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', '3306'))
        self.database = os.getenv('DB_NAME', 'ciccas_db')
        self.user = os.getenv('DB_USER', 'ciccas_admin')
        self.password = os.getenv('DB_PASSWORD', 'CICCAS_Admin_2024')

        self.connection_string = (
            f"mysql+pymysql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )
        self.engine = create_engine(
            self.connection_string,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600
        )

    def get_connection(self):
        """获取原始数据库连接"""
        return pymysql.connect(
            host=self.host, port=self.port,
            database=self.database,
            user=self.user, password=self.password,
            charset='utf8mb4'
        )

    @contextmanager
    def session(self):
        """会话上下文管理器"""
        Session = sessionmaker(bind=self.engine)
        session = Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    # ==========================================
    # 基础查询方法
    # ==========================================

    def execute_query(self, sql: str, params: Dict = None) -> pd.DataFrame:
        """执行SQL查询"""
        try:
            return pd.read_sql(sql, self.engine, params=params)
        except Exception as e:
            logger.error(f"查询执行失败: {e}, SQL: {sql}")
            raise

    def execute_update(self, sql: str, params: Dict = None) -> int:
        """执行更新操作"""
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            conn.commit()
            return result.rowcount

    # ==========================================
    # 省份相关查询
    # ==========================================

    def get_provinces(self, region: Optional[str] = None) -> pd.DataFrame:
        """获取省份列表"""
        if region:
            sql = "SELECT * FROM provinces WHERE region_type = %(region)s"
            return self.execute_query(sql, {'region': region})
        return self.execute_query("SELECT * FROM provinces ORDER BY province_code")

    def get_regions(self) -> List[str]:
        """获取区域类型列表"""
        df = self.execute_query("SELECT DISTINCT region_type FROM provinces")
        return df['region_type'].tolist()

    def get_province_by_name(self, name: str) -> Optional[Dict]:
        """根据名称获取省份信息"""
        sql = "SELECT * FROM provinces WHERE province_name = %(name)s"
        df = self.execute_query(sql, {'name': name})
        return df.iloc[0].to_dict() if len(df) > 0 else None

    # ==========================================
    # 收入数据查询
    # ==========================================

    def get_income_data(self, year: Optional[int] = None,
                       province_code: Optional[str] = None,
                       region: Optional[str] = None,
                       data_type: str = '年度') -> pd.DataFrame:
        """获取收入数据"""
        conditions = ["i.data_type = %(data_type)s"]
        params = {'data_type': data_type}

        if year:
            conditions.append("i.year = %(year)s")
            params['year'] = year
        if province_code:
            conditions.append("i.province_code = %(province_code)s")
            params['province_code'] = province_code
        if region:
            conditions.append("p.region_type = %(region)s")
            params['region'] = region

        sql = f"""
            SELECT i.*, p.province_name, p.region_type
            FROM income_data i
            JOIN provinces p ON i.province_code = p.province_code
            WHERE {' AND '.join(conditions)}
            ORDER BY i.year, p.province_code
        """
        return self.execute_query(sql, params)

    def get_income_trend(self, province_codes: List[str],
                        start_year: int = 2010,
                        end_year: int = 2024) -> pd.DataFrame:
        """获取收入趋势数据"""
        placeholders = ', '.join([f"'{code}'" for code in province_codes])
        sql = f"""
            SELECT i.*, p.province_name, p.region_type
            FROM income_data i
            JOIN provinces p ON i.province_code = p.province_code
            WHERE i.province_code IN ({placeholders})
            AND i.year BETWEEN %(start_year)s AND %(end_year)s
            AND i.data_type = '年度'
            ORDER BY i.year, p.province_code
        """
        return self.execute_query(sql, {
            'start_year': start_year,
            'end_year': end_year
        })

    # ==========================================
    # 消费数据查询
    # ==========================================

    def get_consumption_data(self, year: Optional[int] = None,
                            province_code: Optional[str] = None,
                            region: Optional[str] = None,
                            data_type: str = '年度') -> pd.DataFrame:
        """获取消费数据"""
        conditions = ["c.data_type = %(data_type)s"]
        params = {'data_type': data_type}

        if year:
            conditions.append("c.year = %(year)s")
            params['year'] = year
        if province_code:
            conditions.append("c.province_code = %(province_code)s")
            params['province_code'] = province_code
        if region:
            conditions.append("p.region_type = %(region)s")
            params['region'] = region

        sql = f"""
            SELECT c.*, p.province_name, p.region_type
            FROM consumption_data c
            JOIN provinces p ON c.province_code = p.province_code
            WHERE {' AND '.join(conditions)}
            ORDER BY c.year, p.province_code
        """
        return self.execute_query(sql, params)

    def get_consumption_structure(self, year: int,
                                  province_code: Optional[str] = None) -> pd.DataFrame:
        """获取消费结构数据"""
        if province_code:
            sql = """
                SELECT province_code, year,
                       food_expenditure, clothing_expenditure, housing_expenditure,
                       goods_expenditure, transport_expenditure, education_expenditure,
                       medical_expenditure, other_expenditure
                FROM consumption_data
                WHERE year = %(year)s AND province_code = %(province_code)s
                AND data_type = '年度'
            """
            return self.execute_query(sql, {'year': year, 'province_code': province_code})

        sql = """
            SELECT p.region_type, c.year,
                   AVG(c.food_expenditure) as food,
                   AVG(c.clothing_expenditure) as clothing,
                   AVG(c.housing_expenditure) as housing,
                   AVG(c.goods_expenditure) as goods,
                   AVG(c.transport_expenditure) as transport,
                   AVG(c.education_expenditure) as education,
                   AVG(c.medical_expenditure) as medical,
                   AVG(c.other_expenditure) as other
            FROM consumption_data c
            JOIN provinces p ON c.province_code = p.province_code
            WHERE c.year = %(year)s AND c.data_type = '年度'
            GROUP BY p.region_type, c.year
        """
        return self.execute_query(sql, {'year': year})

    # ==========================================
    # 耦合协调度查询
    # ==========================================

    def get_coupling_results(self, year: Optional[int] = None,
                            province_code: Optional[str] = None,
                            region: Optional[str] = None) -> pd.DataFrame:
        """获取耦合协调度结果"""
        conditions = ["1=1"]
        params = {}

        if year:
            conditions.append("cr.year = %(year)s")
            params['year'] = year
        if province_code:
            conditions.append("cr.province_code = %(province_code)s")
            params['province_code'] = province_code
        if region:
            conditions.append("p.region_type = %(region)s")
            params['region'] = region

        sql = f"""
            SELECT cr.*, p.province_name, p.region_type,
                   i.disposable_income, c.consumption_expenditure
            FROM coupling_results cr
            JOIN provinces p ON cr.province_code = p.province_code
            LEFT JOIN income_data i ON cr.province_code = i.province_code
                AND cr.year = i.year AND i.data_type = '年度'
            LEFT JOIN consumption_data c ON cr.province_code = c.province_code
                AND cr.year = c.year AND c.data_type = '年度'
            WHERE {' AND '.join(conditions)}
            ORDER BY cr.coordination_degree_d DESC
        """
        return self.execute_query(sql, params)

    def get_coupling_trend(self, province_codes: List[str],
                          start_year: int = 2010,
                          end_year: int = 2024) -> pd.DataFrame:
        """获取耦合协调度趋势"""
        placeholders = ', '.join([f"'{code}'" for code in province_codes])
        sql = f"""
            SELECT cr.*, p.province_name, p.region_type
            FROM coupling_results cr
            JOIN provinces p ON cr.province_code = p.province_code
            WHERE cr.province_code IN ({placeholders})
            AND cr.year BETWEEN %(start_year)s AND %(end_year)s
            ORDER BY cr.year, cr.province_code
        """
        return self.execute_query(sql, {
            'start_year': start_year,
            'end_year': end_year
        })

    def get_region_coupling_avg(self, year: int) -> pd.DataFrame:
        """获取区域平均耦合协调度"""
        sql = """
            SELECT p.region_type,
                   AVG(cr.coupling_degree_c) as avg_coupling,
                   AVG(cr.coordination_degree_d) as avg_coordination,
                   MIN(cr.coordination_degree_d) as min_coordination,
                   MAX(cr.coordination_degree_d) as max_coordination,
                   COUNT(*) as province_count
            FROM coupling_results cr
            JOIN provinces p ON cr.province_code = p.province_code
            WHERE cr.year = %(year)s
            GROUP BY p.region_type
        """
        return self.execute_query(sql, {'year': year})

    def get_coordination_distribution(self, year: int) -> pd.DataFrame:
        """获取协调等级分布"""
        sql = """
            SELECT coordination_level,
                   COUNT(*) as province_count,
                   AVG(coordination_degree_d) as avg_d
            FROM coupling_results cr
            WHERE year = %(year)s
            GROUP BY coordination_level
            ORDER BY avg_d DESC
        """
        return self.execute_query(sql, {'year': year})

    # ==========================================
    # 综合数据查询
    # ==========================================

    def get_complete_data(self, year: int) -> pd.DataFrame:
        """获取完整数据视图"""
        sql = """
            SELECT
                p.province_code, p.province_name, p.region_type,
                i.year, i.disposable_income, i.real_income,
                i.wage_income, i.business_income, i.property_income, i.transfer_income,
                c.consumption_expenditure, c.real_consumption,
                c.food_expenditure, c.clothing_expenditure, c.housing_expenditure,
                c.transport_expenditure, c.education_expenditure, c.medical_expenditure,
                m.cpi, m.unemployment_rate, m.urbanization_rate,
                cr.coupling_degree_c, cr.coordination_degree_d, cr.coordination_level
            FROM provinces p
            LEFT JOIN income_data i ON p.province_code = i.province_code
                AND i.year = %(year)s AND i.data_type = '年度'
            LEFT JOIN consumption_data c ON p.province_code = c.province_code
                AND c.year = %(year)s AND c.data_type = '年度'
            LEFT JOIN macro_indicators m ON p.province_code = m.province_code
                AND m.year = %(year)s
            LEFT JOIN coupling_results cr ON p.province_code = cr.province_code
                AND cr.year = %(year)s
            ORDER BY p.province_code
        """
        return self.execute_query(sql, {'year': year})

    def get_region_summary(self, year: int) -> Dict:
        """获取区域汇总统计"""
        sql = """
            SELECT
                p.region_type,
                AVG(i.disposable_income) as avg_income,
                AVG(c.consumption_expenditure) as avg_consumption,
                AVG(cr.coupling_degree_c) as avg_coupling,
                AVG(cr.coordination_degree_d) as avg_coordination,
                COUNT(DISTINCT p.province_code) as province_count
            FROM provinces p
            LEFT JOIN income_data i ON p.province_code = i.province_code
                AND i.year = %(year)s AND i.data_type = '年度'
            LEFT JOIN consumption_data c ON p.province_code = c.province_code
                AND c.year = %(year)s AND c.data_type = '年度'
            LEFT JOIN coupling_results cr ON p.province_code = cr.province_code
                AND cr.year = %(year)s
            GROUP BY p.region_type
        """
        df = self.execute_query(sql, {'year': year})

        result = {}
        for _, row in df.iterrows():
            result[row['region_type']] = {
                'avg_income': float(row['avg_income']) if pd.notna(row['avg_income']) else None,
                'avg_consumption': float(row['avg_consumption']) if pd.notna(row['avg_consumption']) else None,
                'avg_coupling': float(row['avg_coupling']) if pd.notna(row['avg_coupling']) else None,
                'avg_coordination': float(row['avg_coordination']) if pd.notna(row['avg_coordination']) else None,
                'province_count': int(row['province_count'])
            }
        return result

    # ==========================================
    # 数据质量检查
    # ==========================================

    def check_data_quality(self, year: int) -> Dict:
        """检查数据质量"""
        results = {}

        # 收入数据完整率
        income_sql = """
            SELECT
                COUNT(*) as total_provinces,
                SUM(CASE WHEN disposable_income IS NOT NULL THEN 1 ELSE 0 END) as has_income,
                SUM(CASE WHEN data_status = '原始' THEN 1 ELSE 0 END) as original_count
            FROM income_data
            WHERE year = %(year)s AND data_type = '年度'
        """
        income_df = self.execute_query(income_sql, {'year': year})
        results['income'] = {
            'total': int(income_df.iloc[0]['total_provinces']),
            'complete': int(income_df.iloc[0]['has_income']),
            'original': int(income_df.iloc[0]['original_count']),
            'complete_rate': float(income_df.iloc[0]['has_income']) / 31 * 100
        }

        # 消费数据完整率
        consumption_sql = """
            SELECT
                COUNT(*) as total_provinces,
                SUM(CASE WHEN consumption_expenditure IS NOT NULL THEN 1 ELSE 0 END) as has_consumption
            FROM consumption_data
            WHERE year = %(year)s AND data_type = '年度'
        """
        cons_df = self.execute_query(consumption_sql, {'year': year})
        results['consumption'] = {
            'total': int(cons_df.iloc[0]['total_provinces']),
            'complete': int(cons_df.iloc[0]['has_consumption']),
            'complete_rate': float(cons_df.iloc[0]['has_consumption']) / 31 * 100
        }

        # 耦合度计算状态
        coupling_sql = """
            SELECT COUNT(*) as calculated
            FROM coupling_results
            WHERE year = %(year)s
        """
        coup_df = self.execute_query(coupling_sql, {'year': year})
        results['coupling'] = {
            'calculated': int(coup_df.iloc[0]['calculated']),
            'expected': 31
        }

        return results

    def get_data_gaps(self, year: int) -> pd.DataFrame:
        """获取数据缺失情况"""
        sql = """
            SELECT
                p.province_name, p.region_type,
                i.disposable_income IS NULL as income_missing,
                c.consumption_expenditure IS NULL as consumption_missing
            FROM provinces p
            LEFT JOIN income_data i ON p.province_code = i.province_code
                AND i.year = %(year)s AND i.data_type = '年度'
            LEFT JOIN consumption_data c ON p.province_code = c.province_code
                AND c.year = %(year)s AND c.data_type = '年度'
            WHERE i.disposable_income IS NULL OR c.consumption_expenditure IS NULL
            ORDER BY p.region_type, p.province_name
        """
        return self.execute_query(sql, {'year': year})


# 单例模式
db_manager = DatabaseManager()
