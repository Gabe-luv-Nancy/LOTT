"""
表结构定义模块 - MetaColData、TimeSeriesData、CrossSectionalData
"""

from .database_config import *


def _now():
    return str(datetime.now().replace(microsecond=0)).replace(":", "-")


# ==================== 表定义模块 ====================

Base = declarative_base()


class MetaColData(Base):
    """
    元数据表 - 存储列的统计信息
    
    Columns: id, original_colname, colname_hash, 
             level_0, level_1, level_2, 
             invalid_count, total_count, 
             mean, std, variance, skewness, kurtosis, 
             min, max, unique_count, unique_ratio, 
             first_valid_date, last_valid_date, 
             data_type, created_at, updated_at, update_count
    """
    __tablename__ = '_metacoldata'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # MultiIndex 列信息
    original_colname = Column(Text, nullable=False)
    colname_hash = Column(String(64), nullable=False, unique=True, index=True)
    
    # 分解存储 MultiIndex
    level_0 = Column(String(10), index=True)   # 代码
    level_1 = Column(String(20), index=True)   # 标的
    level_2 = Column(String(20), index=True)   # 指标
    
    # 数据质量统计
    invalid_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    
    # 数值统计
    mean = Column(Float)
    std = Column(Float)
    variance = Column(Float)
    skewness = Column(Float)
    kurtosis = Column(Float)
    min = Column(Float)
    max = Column(Float)
    
    # 唯一性统计
    unique_count = Column(Integer)
    unique_ratio = Column(Float)
    
    # 时间范围
    first_valid_date = Column(DateTime)
    last_valid_date = Column(DateTime)
    
    # 数据类型信息
    data_type = Column(String(50))
    
    # 时间戳
    created_at = Column(DateTime, default=_now())
    updated_at = Column(DateTime, default=_now(), onupdate=_now())
    update_count = Column(Integer, default=0)
    
    # 索引优化
    __table_args__ = (
        Index('idx_metacoldata_levels', 'level_0', 'level_1', 'level_2'),
        Index('idx_metacoldata_hashedcolname', 'colname_hash'),
    )


class TimeSeriesData(Base):
    """时间序列主数据表"""
    __tablename__ = 'time_series_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date_index = Column(DateTime, nullable=False, index=True)
    
    # 动态列将通过 ALTER TABLE 添加
    
    __table_args__ = (
        UniqueConstraint('date_index', name='uq_timeseries_date'),
        Index('idx_date_index', 'date_index'),
    )


class CrossSectionalData(Base):
    """截面数据主数据表"""
    __tablename__ = 'cross_sectional_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 动态列将通过 ALTER TABLE 添加
