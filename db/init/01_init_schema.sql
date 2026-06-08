-- ==========================================
-- CICCAS 数据库初始化脚本
-- 中国城镇居民收入-消费耦合协调分析系统
-- ==========================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS ciccas_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE ciccas_db;

-- ==========================================
-- 1. 基础数据表 - 省份信息
-- ==========================================
CREATE TABLE provinces (
    province_code VARCHAR(6) PRIMARY KEY COMMENT '省份编码（国家统计局6位区划码）',
    province_name VARCHAR(20) NOT NULL COMMENT '省份名称',
    region_type ENUM('东部', '中部', '西部', '东北') NOT NULL COMMENT '区域类型',
    abbreviation VARCHAR(10) COMMENT '简称',
    capital_city VARCHAR(20) COMMENT '省会城市',
    longitude DECIMAL(10, 6) COMMENT '经度',
    latitude DECIMAL(10, 6) COMMENT '纬度',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_region (region_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='中国31个省级行政区基础信息';

-- ==========================================
-- 2. 核心数据表 - 城镇居民收入数据
-- ==========================================
CREATE TABLE income_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    province_code VARCHAR(6) NOT NULL COMMENT '省份编码',
    year INT NOT NULL COMMENT '年份',
    quarter INT DEFAULT NULL COMMENT '季度（1-4，年度数据为NULL）',
    data_type ENUM('年度', '季度') NOT NULL DEFAULT '年度' COMMENT '数据类型',

    -- 收入指标（元）
    disposable_income DECIMAL(12, 2) COMMENT '人均可支配收入',
    wage_income DECIMAL(12, 2) COMMENT '工资性收入',
    business_income DECIMAL(12, 2) COMMENT '经营净收入',
    property_income DECIMAL(12, 2) COMMENT '财产净收入',
    transfer_income DECIMAL(12, 2) COMMENT '转移净收入',

    -- 收入增长率（%）
    income_growth_rate DECIMAL(6, 2) COMMENT '收入同比增长率',
    wage_growth_rate DECIMAL(6, 2) COMMENT '工资性收入增长率',
    business_growth_rate DECIMAL(6, 2) COMMENT '经营净收入增长率',
    property_growth_rate DECIMAL(6, 2) COMMENT '财产净收入增长率',
    transfer_growth_rate DECIMAL(6, 2) COMMENT '转移净收入增长率',

    -- 不变价收入（2010年基期）
    real_income DECIMAL(12, 2) COMMENT '实际可支配收入',
    real_wage_income DECIMAL(12, 2) COMMENT '实际工资性收入',
    real_business_income DECIMAL(12, 2) COMMENT '实际经营净收入',
    real_property_income DECIMAL(12, 2) COMMENT '实际财产净收入',
    real_transfer_income DECIMAL(12, 2) COMMENT '实际转移净收入',

    -- 数据质量标记
    data_source VARCHAR(50) COMMENT '数据来源',
    data_status ENUM('原始', '插值', '校验', '审核通过') DEFAULT '原始' COMMENT '数据状态',
    is_valid BOOLEAN DEFAULT TRUE COMMENT '是否有效',
    notes TEXT COMMENT '备注说明',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_province_year_quarter (province_code, year, quarter, data_type),
    INDEX idx_year (year),
    INDEX idx_province_year (province_code, year),
    FOREIGN KEY (province_code) REFERENCES provinces(province_code) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='城镇居民收入数据明细表';

-- ==========================================
-- 3. 核心数据表 - 城镇居民消费数据
-- ==========================================
CREATE TABLE consumption_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    province_code VARCHAR(6) NOT NULL COMMENT '省份编码',
    year INT NOT NULL COMMENT '年份',
    quarter INT DEFAULT NULL COMMENT '季度（1-4，年度数据为NULL）',
    data_type ENUM('年度', '季度') NOT NULL DEFAULT '年度' COMMENT '数据类型',

    -- 消费支出指标（元）
    consumption_expenditure DECIMAL(12, 2) COMMENT '人均消费支出',
    food_expenditure DECIMAL(12, 2) COMMENT '食品烟酒支出',
    clothing_expenditure DECIMAL(12, 2) COMMENT '衣着支出',
    housing_expenditure DECIMAL(12, 2) COMMENT '居住支出',
    goods_expenditure DECIMAL(12, 2) COMMENT '生活用品及服务支出',
    transport_expenditure DECIMAL(12, 2) COMMENT '交通通信支出',
    education_expenditure DECIMAL(12, 2) COMMENT '教育文化娱乐支出',
    medical_expenditure DECIMAL(12, 2) COMMENT '医疗保健支出',
    other_expenditure DECIMAL(12, 2) COMMENT '其他用品及服务支出',

    -- 消费增长率（%）
    consumption_growth_rate DECIMAL(6, 2) COMMENT '消费同比增长率',
    food_growth_rate DECIMAL(6, 2) COMMENT '食品烟酒增长率',
    clothing_growth_rate DECIMAL(6, 2) COMMENT '衣着增长率',
    housing_growth_rate DECIMAL(6, 2) COMMENT '居住增长率',
    goods_growth_rate DECIMAL(6, 2) COMMENT '生活用品增长率',
    transport_growth_rate DECIMAL(6, 2) COMMENT '交通通信增长率',
    education_growth_rate DECIMAL(6, 2) COMMENT '教育文化增长率',
    medical_growth_rate DECIMAL(6, 2) COMMENT '医疗保健增长率',
    other_growth_rate DECIMAL(6, 2) COMMENT '其他支出增长率',

    -- 不变价消费（2010年基期）
    real_consumption DECIMAL(12, 2) COMMENT '实际消费支出',
    real_food_expenditure DECIMAL(12, 2) COMMENT '实际食品烟酒支出',
    real_clothing_expenditure DECIMAL(12, 2) COMMENT '实际衣着支出',
    real_housing_expenditure DECIMAL(12, 2) COMMENT '实际居住支出',
    real_goods_expenditure DECIMAL(12, 2) COMMENT '实际生活用品支出',
    real_transport_expenditure DECIMAL(12, 2) COMMENT '实际交通通信支出',
    real_education_expenditure DECIMAL(12, 2) COMMENT '实际教育文化支出',
    real_medical_expenditure DECIMAL(12, 2) COMMENT '实际医疗保健支出',
    real_other_expenditure DECIMAL(12, 2) COMMENT '实际其他支出',

    -- 数据质量标记
    data_source VARCHAR(50) COMMENT '数据来源',
    data_status ENUM('原始', '插值', '校验', '审核通过') DEFAULT '原始' COMMENT '数据状态',
    is_valid BOOLEAN DEFAULT TRUE COMMENT '是否有效',
    notes TEXT COMMENT '备注说明',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_province_year_quarter (province_code, year, quarter, data_type),
    INDEX idx_year (year),
    INDEX idx_province_year (province_code, year),
    FOREIGN KEY (province_code) REFERENCES provinces(province_code) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='城镇居民消费数据明细表';

-- ==========================================
-- 4. 核心数据表 - 宏观经济指标
-- ==========================================
CREATE TABLE macro_indicators (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    province_code VARCHAR(6) NOT NULL COMMENT '省份编码',
    year INT NOT NULL COMMENT '年份',
    quarter INT DEFAULT NULL COMMENT '季度',

    -- 价格与就业指标
    cpi DECIMAL(6, 2) COMMENT '居民消费价格指数（上年=100）',
    cpi_cumulative DECIMAL(6, 2) COMMENT 'CPI累计指数',
    unemployment_rate DECIMAL(5, 2) COMMENT '城镇登记失业率（%）',
    survey_unemployment_rate DECIMAL(5, 2) COMMENT '城镇调查失业率（%）',

    -- 价格指数（2010=100）
    cpi_base2010 DECIMAL(6, 2) COMMENT '以2010为基期的CPI',
    food_price_index DECIMAL(6, 2) COMMENT '食品价格指数',
    housing_price_index DECIMAL(6, 2) COMMENT '居住价格指数',

    -- GDP相关
    gdp DECIMAL(15, 2) COMMENT '地区生产总值（亿元）',
    gdp_per_capita DECIMAL(12, 2) COMMENT '人均GDP（元）',
    gdp_growth_rate DECIMAL(6, 2) COMMENT 'GDP增长率（%）',

    -- 城镇化与人口
    urbanization_rate DECIMAL(5, 2) COMMENT '城镇化率（%）',
    urban_population DECIMAL(12, 2) COMMENT '城镇人口（万人）',

    data_source VARCHAR(50) COMMENT '数据来源',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_province_year_quarter (province_code, year, quarter),
    INDEX idx_year (year),
    FOREIGN KEY (province_code) REFERENCES provinces(province_code) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='宏观经济指标表';

-- ==========================================
-- 5. 衍生数据表 - 耦合协调度计算结果
-- ==========================================
CREATE TABLE coupling_results (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    province_code VARCHAR(6) NOT NULL COMMENT '省份编码',
    year INT NOT NULL COMMENT '年份',
    quarter INT DEFAULT NULL COMMENT '季度',

    -- 系统发展水平（0-1标准化）
    income_system_u1 DECIMAL(8, 4) COMMENT '收入系统发展水平U1',
    consumption_system_u2 DECIMAL(8, 4) COMMENT '消费系统发展水平U2',

    -- 耦合协调度指标
    coupling_degree_c DECIMAL(8, 4) COMMENT '耦合度C',
    comprehensive_level_t DECIMAL(8, 4) COMMENT '综合发展水平T',
    coordination_degree_d DECIMAL(8, 4) COMMENT '协调度D',

    -- 协调等级
    coordination_level VARCHAR(20) COMMENT '协调等级',
    coordination_description VARCHAR(50) COMMENT '等级描述',

    -- 计算参数
    weight_income DECIMAL(4, 2) DEFAULT 0.50 COMMENT '收入权重α',
    weight_consumption DECIMAL(4, 2) DEFAULT 0.50 COMMENT '消费权重β',
    calculation_method VARCHAR(50) COMMENT '计算方法',

    -- 趋势分析
    d_growth_rate DECIMAL(6, 2) COMMENT '协调度增长率',
    d_change_from_last DECIMAL(6, 2) COMMENT '较上期变化',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_province_year_quarter (province_code, year, quarter),
    INDEX idx_year (year),
    INDEX idx_coordination_level (coordination_level),
    FOREIGN KEY (province_code) REFERENCES provinces(province_code) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='耦合协调度计算结果表';

-- ==========================================
-- 6. 衍生数据表 - 空间分析结果
-- ==========================================
CREATE TABLE spatial_analysis (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    year INT NOT NULL COMMENT '年份',

    -- 全局空间自相关
    moran_i DECIMAL(8, 4) COMMENT "Moran's I指数",
    moran_pvalue DECIMAL(8, 4) COMMENT 'Moran I显著性',
    geary_c DECIMAL(8, 4) COMMENT "Geary's c指数",

    -- 收敛性检验
    sigma_convergence DECIMAL(8, 4) COMMENT 'σ收敛系数',
    beta_convergence DECIMAL(8, 4) COMMENT 'β收敛系数',
    convergence_speed DECIMAL(8, 4) COMMENT '收敛速度',

    -- 核密度参数
    kde_peak DECIMAL(8, 4) COMMENT '核密度峰值',
    kde_variance DECIMAL(8, 4) COMMENT '核密度方差',
    polarization_index DECIMAL(8, 4) COMMENT '极化指数',

    calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_year (year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='空间计量分析结果表';

-- ==========================================
-- 7. 衍生数据表 - 计量模型结果
-- ==========================================
CREATE TABLE econometric_models (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(50) NOT NULL COMMENT '模型名称',
    model_type VARCHAR(30) NOT NULL COMMENT '模型类型',
    year_start INT COMMENT '样本起始年',
    year_end INT COMMENT '样本结束年',

    -- 模型参数（JSON格式存储）
    model_params JSON COMMENT '模型估计参数',
    diagnostic_stats JSON COMMENT '诊断统计量',

    -- 模型评估
    r_squared DECIMAL(6, 4) COMMENT 'R²',
    adj_r_squared DECIMAL(6, 4) COMMENT '调整R²',
    f_statistic DECIMAL(10, 4) COMMENT 'F统计量',
    rmse DECIMAL(10, 4) COMMENT '均方根误差',

    model_equation TEXT COMMENT '模型方程',
    result_summary TEXT COMMENT '结果摘要',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_model_type (model_type),
    INDEX idx_year_range (year_start, year_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='计量经济模型结果表';

-- ==========================================
-- 8. 数据导入日志表
-- ==========================================
CREATE TABLE data_import_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    import_batch_id VARCHAR(36) COMMENT '导入批次ID',
    import_type VARCHAR(30) NOT NULL COMMENT '导入类型',
    file_name VARCHAR(255) COMMENT '文件名',
    file_path VARCHAR(500) COMMENT '文件路径',
    data_source VARCHAR(50) COMMENT '数据来源',

    -- 导入统计
    records_total INT DEFAULT 0 COMMENT '总记录数',
    records_success INT DEFAULT 0 COMMENT '成功导入数',
    records_failed INT DEFAULT 0 COMMENT '失败记录数',
    records_skipped INT DEFAULT 0 COMMENT '跳过记录数',

    -- 处理详情
    processing_status ENUM('待处理', '处理中', '已完成', '失败') DEFAULT '待处理',
    error_message TEXT COMMENT '错误信息',
    processing_details JSON COMMENT '处理详情',

    -- 操作信息
    operator VARCHAR(50) COMMENT '操作人',
    started_at TIMESTAMP NULL COMMENT '开始时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_batch_id (import_batch_id),
    INDEX idx_import_type (import_type),
    INDEX idx_status (processing_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据导入日志表';

-- ==========================================
-- 9. 系统配置表
-- ==========================================
CREATE TABLE system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(50) NOT NULL UNIQUE COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    config_type ENUM('string', 'int', 'float', 'boolean', 'json') DEFAULT 'string',
    description VARCHAR(255) COMMENT '配置说明',
    is_editable BOOLEAN DEFAULT TRUE COMMENT '是否可编辑',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- ==========================================
-- 10. CPI转换系数表
-- ==========================================
CREATE TABLE cpi_conversion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    year INT NOT NULL COMMENT '年份',
    cpi_value DECIMAL(8, 4) NOT NULL COMMENT 'CPI指数（上年=100）',
    cumulative_cpi DECIMAL(8, 4) COMMENT '累计CPI（2010=100）',
    deflator DECIMAL(8, 4) COMMENT '折算系数',
    UNIQUE KEY uk_year (year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='CPI价格指数转换表';

-- ==========================================
-- 插入省份基础数据
-- ==========================================
INSERT INTO provinces (province_code, province_name, region_type, abbreviation, capital_city) VALUES
-- 东部地区
('110000', '北京', '东部', '京', '北京'),
('120000', '天津', '东部', '津', '天津'),
('130000', '河北', '东部', '冀', '石家庄'),
('310000', '上海', '东部', '沪', '上海'),
('320000', '江苏', '东部', '苏', '南京'),
('330000', '浙江', '东部', '浙', '杭州'),
('350000', '福建', '东部', '闽', '福州'),
('370000', '山东', '东部', '鲁', '济南'),
('440000', '广东', '东部', '粤', '广州'),
('460000', '海南', '东部', '琼', '海口'),
-- 中部地区
('140000', '山西', '中部', '晋', '太原'),
('340000', '安徽', '中部', '皖', '合肥'),
('360000', '江西', '中部', '赣', '南昌'),
('410000', '河南', '中部', '豫', '郑州'),
('420000', '湖北', '中部', '鄂', '武汉'),
('430000', '湖南', '中部', '湘', '长沙'),
-- 西部地区
('150000', '内蒙古', '西部', '蒙', '呼和浩特'),
('450000', '广西', '西部', '桂', '南宁'),
('500000', '重庆', '西部', '渝', '重庆'),
('510000', '四川', '西部', '川', '成都'),
('520000', '贵州', '西部', '黔', '贵阳'),
('530000', '云南', '西部', '滇', '昆明'),
('540000', '西藏', '西部', '藏', '拉萨'),
('610000', '陕西', '西部', '陕', '西安'),
('620000', '甘肃', '西部', '甘', '兰州'),
('630000', '青海', '西部', '青', '西宁'),
('640000', '宁夏', '西部', '宁', '银川'),
('650000', '新疆', '西部', '新', '乌鲁木齐'),
-- 东北地区
('210000', '辽宁', '东北', '辽', '沈阳'),
('220000', '吉林', '东北', '吉', '长春'),
('230000', '黑龙江', '东北', '黑', '哈尔滨');

-- ==========================================
-- 插入系统配置
-- ==========================================
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
('base_year', '2010', 'int', '不变价基期年份'),
('data_quality_threshold', '0.98', 'float', '数据质量阈值'),
('coupling_weight_income', '0.5', 'float', '耦合度收入默认权重'),
('coupling_weight_consumption', '0.5', 'float', '耦合度消费默认权重'),
('enable_auto_calculation', 'true', 'boolean', '是否启用自动计算'),
('default_regions', '["东部","中部","西部","东北"]', 'json', '默认区域列表'),
('data_retention_days', '365', 'int', '日志保留天数'),
('system_version', '3.0.0', 'string', '系统版本号');

-- ==========================================
-- 插入CPI转换系数（示例数据，需根据实际数据更新）
-- ==========================================
INSERT INTO cpi_conversion (year, cpi_value, cumulative_cpi, deflator) VALUES
(2010, 100.00, 100.00, 1.0000),
(2011, 105.40, 105.40, 0.9488),
(2012, 102.60, 108.14, 0.9247),
(2013, 102.60, 110.95, 0.9013),
(2014, 102.00, 113.17, 0.8836),
(2015, 101.40, 114.76, 0.8714),
(2016, 102.00, 117.05, 0.8543),
(2017, 101.60, 118.93, 0.8408),
(2018, 102.10, 121.43, 0.8235),
(2019, 102.90, 124.95, 0.8003),
(2020, 102.50, 128.07, 0.7808),
(2021, 100.90, 129.22, 0.7739),
(2022, 102.00, 131.80, 0.7587),
(2023, 100.20, 132.06, 0.7572),
(2024, 100.30, 132.46, 0.7550);

-- ==========================================
-- 创建常用视图
-- ==========================================

-- 视图1: 完整数据视图
CREATE VIEW v_complete_data AS
SELECT
    p.province_code,
    p.province_name,
    p.region_type,
    i.year,
    i.quarter,
    i.disposable_income,
    i.real_income,
    c.consumption_expenditure,
    c.real_consumption,
    m.cpi,
    m.unemployment_rate,
    m.urbanization_rate,
    cr.coupling_degree_c,
    cr.coordination_degree_d,
    cr.coordination_level
FROM provinces p
LEFT JOIN income_data i ON p.province_code = i.province_code
LEFT JOIN consumption_data c ON p.province_code = c.province_code
    AND i.year = c.year AND i.quarter = c.quarter
LEFT JOIN macro_indicators m ON p.province_code = m.province_code
    AND i.year = m.year AND i.quarter = m.quarter
LEFT JOIN coupling_results cr ON p.province_code = cr.province_code
    AND i.year = cr.year AND i.quarter = cr.quarter
WHERE i.data_type = '年度' OR i.data_type IS NULL;

-- 视图2: 区域汇总视图
CREATE VIEW v_region_summary AS
SELECT
    p.region_type,
    i.year,
    AVG(i.disposable_income) as avg_income,
    AVG(c.consumption_expenditure) as avg_consumption,
    AVG(cr.coupling_degree_c) as avg_coupling,
    AVG(cr.coordination_degree_d) as avg_coordination,
    COUNT(DISTINCT p.province_code) as province_count
FROM provinces p
JOIN income_data i ON p.province_code = i.province_code
JOIN consumption_data c ON p.province_code = c.province_code AND i.year = c.year
LEFT JOIN coupling_results cr ON p.province_code = cr.province_code AND i.year = cr.year
WHERE i.data_type = '年度' AND c.data_type = '年度'
GROUP BY p.region_type, i.year;

-- ==========================================
-- 创建触发器 - 自动计算协调等级
-- ==========================================
DELIMITER //

CREATE TRIGGER trg_calc_coordination_level
BEFORE INSERT ON coupling_results
FOR EACH ROW
BEGIN
    SET NEW.coordination_level = CASE
        WHEN NEW.coordination_degree_d >= 0.90 THEN '优质协调'
        WHEN NEW.coordination_degree_d >= 0.80 THEN '良好协调'
        WHEN NEW.coordination_degree_d >= 0.70 THEN '中级协调'
        WHEN NEW.coordination_degree_d >= 0.60 THEN '初级协调'
        WHEN NEW.coordination_degree_d >= 0.50 THEN '濒临失调'
        ELSE '轻度失调'
    END;
END//

CREATE TRIGGER trg_calc_coordination_level_update
BEFORE UPDATE ON coupling_results
FOR EACH ROW
BEGIN
    IF NEW.coordination_degree_d != OLD.coordination_degree_d THEN
        SET NEW.coordination_level = CASE
            WHEN NEW.coordination_degree_d >= 0.90 THEN '优质协调'
            WHEN NEW.coordination_degree_d >= 0.80 THEN '良好协调'
            WHEN NEW.coordination_degree_d >= 0.70 THEN '中级协调'
            WHEN NEW.coordination_degree_d >= 0.60 THEN '初级协调'
            WHEN NEW.coordination_degree_d >= 0.50 THEN '濒临失调'
            ELSE '轻度失调'
        END;
    END IF;
END//

DELIMITER ;

-- ==========================================
-- 创建存储过程
-- ==========================================
DELIMITER //

-- 存储过程1: 计算指定年份所有省份的耦合协调度
CREATE PROCEDURE sp_calculate_coupling(IN p_year INT)
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_province VARCHAR(6);
    DECLARE v_income_u1 DECIMAL(8,4);
    DECLARE v_consumption_u2 DECIMAL(8,4);
    DECLARE v_c DECIMAL(8,4);
    DECLARE v_t DECIMAL(8,4);
    DECLARE v_d DECIMAL(8,4);

    DECLARE cur CURSOR FOR
        SELECT province_code FROM provinces;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    OPEN cur;
    read_loop: LOOP
        FETCH cur INTO v_province;
        IF done THEN
            LEAVE read_loop;
        END IF;

        -- 获取标准化后的发展水平（简化计算）
        SELECT
            COALESCE(real_income / 80000, 0),
            COALESCE((SELECT real_consumption FROM consumption_data
                     WHERE province_code = v_province AND year = p_year
                     AND data_type = '年度' LIMIT 1) / 50000, 0)
        INTO v_income_u1, v_consumption_u2
        FROM income_data
        WHERE province_code = v_province AND year = p_year
        AND data_type = '年度' LIMIT 1;

        -- 计算耦合度和协调度
        IF v_income_u1 > 0 AND v_consumption_u2 > 0 THEN
            SET v_c = 2 * SQRT(v_income_u1 * v_consumption_u2) / (v_income_u1 + v_consumption_u2);
            SET v_t = 0.5 * v_income_u1 + 0.5 * v_consumption_u2;
            SET v_d = SQRT(v_c * v_t);

            -- 插入或更新结果
            INSERT INTO coupling_results
                (province_code, year, income_system_u1, consumption_system_u2,
                 coupling_degree_c, comprehensive_level_t, coordination_degree_d)
            VALUES
                (v_province, p_year, v_income_u1, v_consumption_u2, v_c, v_t, v_d)
            ON DUPLICATE KEY UPDATE
                income_system_u1 = v_income_u1,
                consumption_system_u2 = v_consumption_u2,
                coupling_degree_c = v_c,
                comprehensive_level_t = v_t,
                coordination_degree_d = v_d;
        END IF;
    END LOOP;
    CLOSE cur;
END//

-- 存储过程2: 获取数据质量报告
CREATE PROCEDURE sp_data_quality_report(IN p_year INT)
BEGIN
    SELECT
        p_year as 统计年份,
        COUNT(DISTINCT i.province_code) as 收入数据省份数,
        COUNT(DISTINCT c.province_code) as 消费数据省份数,
        COUNT(DISTINCT CASE WHEN i.data_status = '原始' THEN i.province_code END) as 原始数据数,
        COUNT(DISTINCT CASE WHEN i.data_status = '插值' THEN i.province_code END) as 插值数据数,
        ROUND(AVG(CASE WHEN i.disposable_income IS NOT NULL THEN 1 ELSE 0 END) * 100, 2) as 收入完整率,
        ROUND(AVG(CASE WHEN c.consumption_expenditure IS NOT NULL THEN 1 ELSE 0 END) * 100, 2) as 消费完整率
    FROM provinces p
    LEFT JOIN income_data i ON p.province_code = i.province_code AND i.year = p_year
    LEFT JOIN consumption_data c ON p.province_code = c.province_code AND c.year = p_year
    WHERE i.data_type = '年度' OR i.data_type IS NULL;
END//

DELIMITER ;

-- ==========================================
-- 初始化完成
-- ==========================================
SELECT 'CICCAS数据库初始化完成' as status;
