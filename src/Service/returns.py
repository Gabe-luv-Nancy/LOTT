import sys
sys.path.append('X:/LOTT/src/Cross_Layer')
from global_imports import *

class Returns:
    """
    收益率，收益率和累计收益率，支持简单收益率和对数收益率计算。
    提供数据质量报告和灵活的缺失值处理功能。
    Attributes:
        df (pd.DataFrame): 输入的MultiIndex DataFrame，索引为时间，列为资产
    """
    
    def __init__(self, df: pd.DataFrame) -> None:
        """
        初始化收益率计算器
        """
        self.df = df
    def _report(self):
        """
        生成数据质量报告
        
        首先展示数据的时间范围，其次展示数据的缺失情况，最后展示数据多少列。
        如果输入的是多列数据，则逐列展示缺失情况并列成表格。
        """
        if self.df.empty:
            print("数据框为空")
            return
            
        total = len(self.df)
        latest = self.df.index.get_level_values(0).max() 
        earliest = self.df.index.get_level_values(0).min()
        duration = latest - earliest
        
        print(f"SPECTRUM: {earliest} - {latest}")
        print(f"COMPLETION:  {total}个数据点, 时间跨度: {duration.days}天, 覆盖率: {total/(duration.days + 1)*100:.1f}%")
        
        # 逐列展示缺失情况
        missing_info = []
        for col in self.df.columns:
            nan_count = self.df[col].isna().sum()
            nan_pct = nan_count / len(self.df) * 100
            missing_info.append({
                'column': col,
                'missing_count': nan_count,
                'missing_pct': nan_pct
            })
            print(f"{col}: 缺失值: {nan_count}/{len(self.df)} ({nan_pct:.1f}%)")

        return missing_info

    def _first_value(self, columns: Optional[List[str]] = None,
                     start_date: Optional[str] = None, 
                     end_date: Optional[str] = None) -> Dict[str, Dict]:
        """
        找到起始值，首先认定所提供的Dataframe的各列的第一个值，
        如果第一个值是无效值(已经定义过特定字符串组成的列表)，
        则从第一个可用行开始，向下/后寻找第一个有效值，并且报告最终找到的值是哪个（报告引用值的行索引）
        
        Returns:
            Dict[str, Dict]: 每列的首个有效值信息 {'column': {'value': x, 'index': idx}}
        """
        df = self._filter_by_date(start_date, end_date)
        cols = columns if columns else df.columns.tolist()
        
        result = {}
        for col in cols:
            if col not in df.columns:
                continue
            series = df[col].dropna()
            if len(series) > 0:
                first_idx = series.index[0]
                first_val = series.iloc[0]
                result[col] = {'value': first_val, 'index': first_idx}
            else:
                result[col] = {'value': None, 'index': None}
        
        return result

    def _last_value(self, columns: Optional[List[str]] = None,
                    start_date: Optional[str] = None, 
                    end_date: Optional[str] = None) -> Dict[str, Dict]:
        """
        找到末尾值，首先认定所提供的Dataframe的各列的最后一个值，
        如果最后一个值是无效值(已经定义过特定字符串组成的列表)，
        则从最后一个可用行开始，向上/前寻找第一个有效值，并且报告最终找到的值是哪个（报告引用值的行索引）
        
        Returns:
            Dict[str, Dict]: 每列的末尾有效值信息 {'column': {'value': x, 'index': idx}}
        """
        df = self._filter_by_date(start_date, end_date)
        cols = columns if columns else df.columns.tolist()
        
        result = {}
        for col in cols:
            if col not in df.columns:
                continue
            series = df[col].dropna()
            if len(series) > 0:
                last_idx = series.index[-1]
                last_val = series.iloc[-1]
                result[col] = {'value': last_val, 'index': last_idx}
            else:
                result[col] = {'value': None, 'index': None}
        
        return result

    def _filter_by_date(self, start_date: Optional[str] = None, 
                        end_date: Optional[str] = None) -> pd.DataFrame:
        """按日期范围过滤数据"""
        df = self.df
        if start_date:
            df = df[df.index.get_level_values(0) >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df.index.get_level_values(0) <= pd.to_datetime(end_date)]
        return df

    def _operator(self, first_values: Dict, last_values: Dict, 
                  __function: str = "default") -> pd.DataFrame:
        """
        计算收益率运算
        
        Args:
            first_values: 首值字典
            last_values: 末值字典
            __function: 运算类型
            
        Returns:
            pd.DataFrame: 计算结果
        """
        if __function == "default":
            result = {}
            for col in first_values:
                if first_values[col]['value'] is not None and last_values[col]['value'] is not None:
                    first_val = first_values[col]['value']
                    last_val = last_values[col]['value']
                    if first_val != 0:
                        result[col] = (last_val - first_val) / first_val
                    else:
                        result[col] = None
            return pd.Series(result)
        return pd.DataFrame()

    def returns(self, columns: Optional[List[str]] = None,
                start_date: Optional[str] = None,
                end_date: Optional[str] = None,
                return_type: str = 'simple',
                period: int = 1,
                missing_method: str = 'auto',
                missings_preserve: bool = True) -> pd.DataFrame:
        """
        计算收益率
        
        Parameters:
            columns: 要计算收益率的列名
            start_date: 开始日期
            end_date: 结束日期
            return_type: 收益率类型 ('simple', 'log')
            period: 收益率周期
            missing_method: 缺失值处理方法
            missings_preserve: 是否保留缺失值
            
        Returns:
            pd.DataFrame: 收益率序列
        """
        df = self._filter_by_date(start_date, end_date)
        cols = columns if columns else df.columns.tolist()
        
        returns_df = pd.DataFrame(index=df.index)
        
        for col in cols:
            if col not in df.columns:
                continue
                
            series = df[col]
            
            if return_type == 'simple':
                returns = series.pct_change(period)
            else:  # log return
                returns = np.log(series / series.shift(period))
            
            returns_df[f'{col}_return'] = returns
        
        return returns_df

    def cumulative_returns(self, columns: Optional[List[str]] = None, 
                          start_date: Optional[str] = None, 
                          end_date: Optional[str] = None,
                          return_type: str = 'simple', 
                          initial_value: float = 1.0, 
                          reinvest: bool = True, 
                          annualize: bool = False, 
                          missing_method: str = 'auto') -> pd.DataFrame:
        """
        计算累计收益率
        
        Parameters:
            columns (List[str]): 要计算收益率的列名
            start_date (str): 开始日期 (yyyy-mm-dd)
            end_date (str): 结束日期 (yyyy-mm-dd)
            return_type (str): 收益率类型 ('simple', 'log')
            initial_value (float): 初始投资额
            reinvest (bool): 是否再投资
            annualize (bool): 是否年化
            missing_method (str): 缺失值处理方法
            
        Returns:
            pd.DataFrame: 累计收益率序列
        """
        # 先计算收益率
        returns_df = self.returns(
            columns=columns, 
            start_date=start_date, 
            end_date=end_date, 
            return_type=return_type, 
            period=1, 
            missing_method=missing_method,
            missings_preserve=False  # 累计收益率不保留缺失值
        )
        
        cumulative_df = pd.DataFrame(index=returns_df.index)
        
        for col in returns_df.columns:
            returns_series = returns_df[col].dropna()
            
            if len(returns_series) == 0:
                continue
                
            if return_type == 'simple':
                if reinvest:
                    # 再投资：几何累计
                    cumulative_returns = (1 + returns_series).cumprod() * initial_value
                else:
                    # 不再投资：算术累计
                    cumulative_returns = (1 + returns_series).cumsum() * initial_value
            else:  # log return
                cumulative_returns = np.exp(returns_series.cumsum()) * initial_value
            
            # 年化处理
            if annualize:
                n_periods = len(returns_series)
                if n_periods > 1:
                    n_years = n_periods / 252  # 假设252个交易日
                    total_return = cumulative_returns.iloc[-1] / initial_value - 1
                    annualized_return = (1 + total_return) ** (1/n_years) - 1
                    
                    # 重新计算年化累计收益率
                    time_factor = np.arange(n_periods) / 252
                    if return_type == 'simple':
                        if reinvest:
                            cumulative_returns = initial_value * (1 + annualized_return) ** time_factor
                        else:
                            cumulative_returns = initial_value * (1 + annualized_return * time_factor)
                    else:  # log return
                        cumulative_returns = initial_value * np.exp(annualized_return * time_factor)
            
            cumulative_df[f'{col.replace("_return", "")}_cumulative'] = cumulative_returns
        
        return cumulative_df

def filter_trading_days(df: pd.DataFrame, 
                      country: str = 'CN', 
                      start_year: int = 2000,
                      inplace: bool = False) -> Optional[pd.DataFrame]:
    """
    过滤MultiIndex DataFrame中的非交易日（周末和法定节假日）
    
    参数:
    ----------
    df : pd.DataFrame
        需要过滤的DataFrame，行索引应包含日期信息（可以是单级或多级索引）
    country : str, 默认 'CN'
        国家代码，用于确定节假日规则（如：'CN'为中国，'US'为美国）
    start_year : int, 默认 2000
        起始年份，用于生成节假日日历
    inplace : bool, 默认 False
        是否原地修改DataFrame
    
    返回:
    -------
    pd.DataFrame or None
        过滤后的DataFrame（如果inplace=True则返回None）
    
    异常:
    ------
    ValueError
        当DataFrame索引中不包含日期信息时抛出
    """
    
    # 参数验证
    if not isinstance(df, pd.DataFrame):
        raise TypeError("输入必须为pandas DataFrame")
    
    if df.empty:
        print("警告: 输入DataFrame为空")
        return df if not inplace else None
    
    # 创建副本（如果不是原地修改）
    if not inplace:
        df = df.copy()
    
    # 获取索引中的日期信息
    date_index = _extract_dates_from_index(df.index)
    
    if date_index is None:
        raise ValueError("无法从DataFrame索引中提取日期信息")
    
    # 获取交易日掩码
    trading_mask = _create_trading_day_mask(date_index, country, start_year)
    detail(trading_mask)


    # 应用过滤
    trading_mask.index = df.index  # 确保掩码与DataFrame索引对齐
    detail(trading_mask)


    filtered_df = df.loc[trading_mask]
    
    # 输出过滤信息
    original_count = len(df)
    filtered_count = len(filtered_df)
    removed_count = original_count - filtered_count
    
    print(f"交易日过滤完成: {original_count} -> {filtered_count} (移除{removed_count}个非交易日)")
    print(f"过滤比例: {removed_count/original_count*100:.1f}%")
    detail(filtered_df)
    
    if not inplace:
        return filtered_df
    else:
        # 原地修改时更新原DataFrame
        df.drop(df.index[~trading_mask], inplace=True)

def _extract_dates_from_index(index: pd.Index) -> Optional[pd.DatetimeIndex]:
    """
    从索引中提取日期信息
    
    支持单级索引和多级索引的日期提取
    """
    # 如果是DatetimeIndex，直接返回
    if isinstance(index, pd.DatetimeIndex):
        return index
    
    # 如果是MultiIndex，查找包含日期的级别
    if isinstance(index, pd.MultiIndex):
        for level in range(index.nlevels):
            level_values = index.get_level_values(level)
            # 检查该级别是否是日期类型
            if pd.api.types.is_datetime64_any_dtype(level_values):
                return pd.DatetimeIndex(level_values)
            # 尝试将字符串转换为日期
            try:
                dates = pd.to_datetime(level_values, errors='coerce')
                if not dates.isna().all():  # 如果成功转换了一些日期
                    return pd.DatetimeIndex(dates)
            except:
                continue
    
    # 如果是普通索引，尝试转换为日期
    try:
        return pd.to_datetime(index, errors='coerce')
    except:
        return None

def _create_trading_day_mask(dates: pd.DatetimeIndex, 
                        country: str = 'CN', 
                        start_year: int = 2000) -> pd.Series:
    """
    创建交易日布尔掩码
    """
    if len(dates) == 0:
        return pd.Series([], dtype=bool)
    
    # 生成节假日日历
    country_holidays = holidays.CountryHoliday(
        country, 
        years=range(start_year, datetime.now().year + 1)
    )
    
    # 创建掩码：非周末且非节假日
    mask = pd.Series(True, index=range(len(dates)))
    
    for i, date in enumerate(dates):
        if pd.isna(date):  # 处理NaT值
            mask.iloc[i] = False
            continue
            
        # 检查周末（周六=5, 周日=6）
        if date.weekday() >= 5:
            mask.iloc[i] = False
            continue
        
        # 检查节假日
        if date in country_holidays:
            mask.iloc[i] = False
    
    return mask

# 高级版本：支持更复杂的过滤条件
def advanced_filter_trading_days(df: pd.DataFrame,
                               country: str = 'CN',
                               additional_holidays: list = [],
                               custom_weekend_days: list = [],
                               min_data_points: int = 10) -> pd.DataFrame:
    """
    高级版本的交易日过滤函数
    
    参数:
    ----------
    additional_holidays : list, 可选
        用户自定义的额外节假日列表
    custom_weekend_days : list, 可选
        自定义周末日期（0=周一, 6=周日）
    min_data_points : int, 默认 10
        过滤后要求的最小数据点数
    """
    
    # 提取日期
    date_index = _extract_dates_from_index(df.index)
    if date_index is None:
        raise ValueError("无法从索引中提取日期信息")
    
    # 使用基本过滤
    filtered_df = filter_trading_days(df, country=country, inplace=False)
    
    # 应用额外过滤条件
    if additional_holidays and len(filtered_df) > 0:
        additional_holidays_dt = pd.to_datetime(additional_holidays)
        holiday_mask = ~filtered_df.index.isin(additional_holidays_dt)
        filtered_df = filtered_df[holiday_mask]
    
    # 检查数据点数量
    if len(filtered_df) < min_data_points:
        print(f"警告: 过滤后数据点数量({len(filtered_df)})少于最小值({min_data_points})")
    
    return filtered_df

# # 示例用法
# filter_trading_days(df, country='CN', inplace=True)
# us_trading_cn_etfs = filter_trading_days(etfs, country='US')

# custom_holidays = ['2024-12-31']  # 自定义额外假日
# trading_etfs = advanced_filter_trading_days(
#     etfs, 
#     country='CN',
#     additional_holidays=custom_holidays,
#     min_data_points=50
# )
