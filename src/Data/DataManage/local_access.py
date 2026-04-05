import sys
sys.path.append('X:/LOTT/src/Cross_Layer')
from global_imports import *

class LocalData:
    """
    本地接入JSON、Excel、SQLite等多种数据源，转为DataFrame
    """
    
    def __init__(self, default_base_path: str = r'X:/LOTT/notebooks'):
        """
        初始化数据管理器
        Args:
            default_base_path: 默认数据存储基础路径
        """
        self.default_base_path = default_base_path
        self._processed_files = set()
        
    def load_json_data(self, file_path: str, orient: str = 'split', 
                      if_multiindex: bool = True) -> pd.DataFrame:
        """
        .json -> pd.DataFrame
        Args:
            file_path: str 文件绝对路径或已定义默认值的相对路径
            orient: str JSON格式方向，默认'split'
            if_multiindex: bool 实际上是否MultiIndex
            
        Returns:
            pd.DataFrame: 正确记录multiindex的pandas dataframe类型对象
        """
        try:
            # If the file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"JSON文件不存在: {file_path}")
            
            # Read JSON data using pandas
            temp_data = pd.read_json(file_path, orient=orient)
            temp_data.index = pd.to_datetime(temp_data.index)
            
            # Recover Multiindex
            if if_multiindex:
                load_data = temp_data
                load_data.columns = pd.MultiIndex.from_tuples(temp_data.columns)
                return load_data
            else:
                return temp_data
            
        # Other exceptions        
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"JSON解析错误: {str(e)}")
        except pd.errors.EmptyDataError:
            raise ValueError("JSON文件为空")
        except Exception as e:
            raise ValueError(f"JSON数据读取失败: {str(e)}")

    def save_to_json(self,
                    df: pd.DataFrame, 
                    file_path: Union[str, Path], 
                    overwrite: bool = False,
                    orient: str = 'split',
                    force_ascii: bool = False,
                    indent: Optional[int] = None,
                    **kwargs) -> bool:
        """
        保存含有 MultiIndex 的 pandas DataFrame 到本地 JSON 文件
        Args:
            df: 要保存的 pandas DataFrame（支持 MultiIndex）
            file_path: 保存的文件路径
            overwrite: 如果文件已存在是否覆盖，默认为 False
            orient: JSON 格式方向，默认 'split'（最适合 MultiIndex）
            force_ascii: 是否强制 ASCII 编码，默认为 False（支持中文）
            indent: JSON 缩进级别，None 为不缩进
            **kwargs: 其他传递给 df.to_json() 的参数
        Returns:
            bool: 保存成功返回 True，否则返回 False
        Raises:
            FileExistsError: 文件已存在且 overwrite=False
            ValueError: 文件路径或数据格式错误
            PermissionError: 没有文件写入权限
        """
        try:
            # 转换路径为 Path 对象
            file_path = Path(file_path)
            
            # 检查文件是否已存在
            if file_path.exists() and not overwrite:
                raise FileExistsError(
                    f"文件已存在: {file_path}。如需覆盖请设置 overwrite=True"
                )
            
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 检查写入权限
            if not os.access(file_path.parent, os.W_OK):
                raise PermissionError(f"没有写入权限: {file_path.parent}")
            
            # 验证 DataFrame
            if df.empty:
                raise ValueError("DataFrame 为空，无法保存")
            
            # 处理 MultiIndex 的特殊情况
            save_kwargs = {
                'orient': orient,
                'force_ascii': force_ascii,
                'index': True,  # 确保索引被保存
                **kwargs
            }
            
            if indent is not None:
                save_kwargs['indent'] = indent
            
            # 特殊处理：对于包含元组的 MultiIndex，确保正确序列化
            if isinstance(df.columns, pd.MultiIndex) or isinstance(df.index, pd.MultiIndex):
                # 对于 MultiIndex，'split' 格式是最安全的选择
                if orient not in ['split', 'table']:
                    print(f"警告: MultiIndex 数据使用 'split' 格式保存以确保完整性")
                    save_kwargs['orient'] = 'split'
            
            # 保存到文件
            df.to_json(file_path, **save_kwargs)
            
            # 验证文件是否成功创建
            if file_path.exists() and file_path.stat().st_size > 0:
                print(f"数据成功保存到: {file_path}")
                return True
            else:
                raise IOError(f"文件保存失败: {file_path}")
                
        except Exception as e:
            print(f"保存失败: {str(e)}")
            return False
   
    def load_excel_data(self, 
                        file_path: Union[str, List[str]], 
                        sheet_name: Union[str, List[str], None] = None,
                        header: Union[int, List[int]] = [0, 1, 2],
                        index_col: Union[int, List[int]] = [0],
                        parse_dates: bool = True,
                        skip_tail_rows: int = 0,
                        merge_method: str = 'outer',
                        optimize_memory: bool = True,
                        drop_na_threshold: float = 0.8,
                        **kwargs) -> pd.DataFrame:
        """
        读取本地Excel数据源并转换为标准化DataFrame [1,4](@ref)
        Args:
            file_path: Excel文件路径、文件夹路径或文件列表
            sheet_name: 工作表名称，默认为第一个工作表（None等价于0）
            header: 表头行位置，如0表示第一行，[0,1]表示前两行作为多级表头 [6,8](@ref)
            index_col: 作为行索引的列位置
            parse_dates: 是否解析日期列，默认True
            skip_tail_rows: 跳过的末尾行数
            merge_method: 多文件合并方式 ('outer', 'inner', 'left', 'right')
            optimize_memory: 是否优化内存使用
            drop_na_threshold: 缺失值比例超过该阈值则删除列（0-1）
        Returns:
            pd.DataFrame: 标准化DataFrame对象
        """
        # 对齐pandas默认值：sheet_name=None等价于读取所有sheet，0为第一个sheet
        if sheet_name is None:
            sheet_name = 0
        
        if isinstance(file_path, list):
            return self._load_multiple_excel_files(
                file_path, sheet_name, header, index_col, parse_dates, 
                skip_tail_rows, merge_method, optimize_memory, drop_na_threshold, **kwargs
            )
        elif os.path.isdir(file_path):
            return self._load_excel_from_folder(
                file_path, sheet_name, header, index_col, parse_dates,
                skip_tail_rows, merge_method, optimize_memory, drop_na_threshold, **kwargs
            )
        else:
            return self._load_single_excel_file(
                file_path, sheet_name, header, index_col, parse_dates,
                skip_tail_rows, optimize_memory, drop_na_threshold, **kwargs
            )

    def _load_single_excel_file(self, 
                               file_path: str, 
                               sheet_name: Union[str, List[str], None] = 0,
                               header: Union[int, List[int]] = [0, 1, 2],
                               index_col: Union[int, List[int]] = [0],
                               parse_dates: bool = True,
                               skip_tail_rows: int = 0,
                               optimize_memory: bool = True,
                               drop_na_threshold: float = 0.8,
                               **kwargs) -> pd.DataFrame:
        """读取单个Excel文件 [9](@ref)"""
        
        abs_path = os.path.abspath(file_path)
        if abs_path in self._processed_files:
            warnings.warn(f"文件已读取过，跳过: {file_path}")
            return pd.DataFrame()
        
        try:
            self._validate_excel_structure(file_path, sheet_name)
            
            # 读取Excel文件 [6,9](@ref)
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                header=header,
                index_col=index_col,
                parse_dates=parse_dates,
                engine='openpyxl' if file_path.endswith('.xlsx') else 'xlrd',
                **kwargs
            )
            
            # 处理多sheet情况 [4](@ref)
            if isinstance(df, dict):
                sheet_dfs = []
                for sheet_name, sheet_df in df.items():
                    # 为多sheet数据添加sheet名标识
                    if not sheet_df.empty:
                        sheet_dfs.append(sheet_df)
                
                if sheet_dfs:
                    df = pd.concat(sheet_dfs, axis=0, ignore_index=False)
                    # 添加sheet名作为多级索引的一级（如果非多级索引）
                    if not isinstance(df.index, pd.MultiIndex):
                        # 创建包含sheet名的索引映射
                        new_index_tuples = []
                        for sheet_idx, (orig_sheet_name, sheet_df) in enumerate(df.items()):
                            for idx_val in sheet_df.index:
                                new_index_tuples.append((orig_sheet_name, idx_val))
                        df.index = pd.MultiIndex.from_tuples(new_index_tuples)
                else:
                    df = pd.DataFrame()
            
            # 处理多级表头 [6,8](@ref)
            df = self._handle_multiindex_columns(df)
            
            # 处理日期索引
            if parse_dates:
                df = self._handle_date_index(df)
            
            # 数据后处理
            df = self._postprocess_data(df, skip_tail_rows, drop_na_threshold)
            
            # 内存优化
            if optimize_memory:
                df = self._optimize_dataframe(df)
            
            self._processed_files.add(abs_path)
            return df
            
        except Exception as e:
            raise ValueError(f"Excel文件读取失败 {file_path}: {str(e)}")

    def _load_multiple_excel_files(self, 
                                  file_list: List[str], 
                                  sheet_name: Union[str, List[str], None] = 0,
                                  header: Union[int, List[int]] = [0, 1, 2], 
                                  index_col: Union[int, List[int]] = [0],
                                  parse_dates: bool = True,
                                  skip_tail_rows: int = 0,
                                  merge_method: str = 'outer',
                                  optimize_memory: bool = True,
                                  drop_na_threshold: float = 0.8,
                                  **kwargs) -> pd.DataFrame:
        """读取多个Excel文件并合并（支持left/right/inner/outer）[9,10](@ref)"""
        
        data_frames = []
        file_names = []
        
        for file_path in tqdm(file_list, desc="处理Excel文件"):
            try:
                df = self._load_single_excel_file(
                    file_path, sheet_name, header, index_col, parse_dates,
                    skip_tail_rows, optimize_memory, drop_na_threshold, **kwargs
                )
                if not df.empty:
                    data_frames.append(df)
                    file_names.append(os.path.basename(file_path))
            except Exception as e:
                warnings.warn(f"文件读取跳过 {file_path}: {str(e)}")
                continue
        
        if not data_frames:
            warnings.warn("未成功读取任何Excel文件")
            return pd.DataFrame()
        
        # 实现多种合并逻辑 [9](@ref)
        if len(data_frames) == 1:
            result = data_frames[0]
        elif merge_method in ['left', 'right']:
            # left/right合并：以第一个或最后一个DataFrame为基准，横向合并
            base_idx = 0 if merge_method == 'left' else -1
            base_df = data_frames[base_idx]
            
            for i, df in enumerate(data_frames):
                if i == base_idx:
                    continue
                # 横向合并，保留基准表的索引
                base_df = pd.merge(
                    base_df, df, 
                    left_index=True, right_index=True, 
                    how='left' if merge_method == 'left' else 'right',
                    suffixes=(f'_{file_names[base_idx][:8]}', f'_{file_names[i][:8]}')
                )
            result = base_df
        else:
            # inner/outer使用concat纵向合并 [9](@ref)
            join_type = 'inner' if merge_method == 'inner' else 'outer'
            result = pd.concat(data_frames, axis=0, join=join_type, ignore_index=False)
        
        # 列名去重处理 [7](@ref)
        result = self._deduplicate_columns(result)
        
        return result

    def _deduplicate_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理重复列名，添加后缀区分"""
        if df.empty:
            return df
            
        seen_columns = {}
        new_columns = []
        
        for col in df.columns:
            if isinstance(col, tuple):
                col_str = '_'.join(str(c) for c in col if c)
            else:
                col_str = str(col)
            
            if col_str in seen_columns:
                seen_columns[col_str] += 1
                new_col_str = f"{col_str}_{seen_columns[col_str]}"
            else:
                seen_columns[col_str] = 0
                new_col_str = col_str
            
            # 保持多级列名结构或转换为单级
            if isinstance(col, tuple):
                new_col = tuple(new_col_str.split('_'))
                new_columns.append(new_col)
            else:
                new_columns.append(new_col_str)
        
        # 如果所有新列名都是单级，则使用单级列名
        if all(isinstance(col, str) for col in new_columns):
            df.columns = new_columns
        else:
            df.columns = pd.MultiIndex.from_tuples(new_columns)
        
        return df

    def _load_excel_from_folder(self, 
                               folder_path: str, 
                               sheet_name: Union[str, List[str], None] = 0,
                               header: Union[int, List[int]] = [0, 1, 2], 
                               index_col: Union[int, List[int]] = [0],
                               parse_dates: bool = True,
                               skip_tail_rows: int = 0,
                               merge_method: str = 'outer',
                               optimize_memory: bool = True,
                               drop_na_threshold: float = 0.8,
                               **kwargs) -> pd.DataFrame:
        """从文件夹读取所有Excel文件（去重同名文件）[10,11](@ref)"""
        
        # 递归获取所有Excel文件并去重（优先.xlsx）
        excel_files = {}
        for file in Path(folder_path).rglob("*.xlsx"):
            file_key = file.stem.lower()
            excel_files[file_key] = str(file)
        
        for file in Path(folder_path).rglob("*.xls"):
            file_key = file.stem.lower()
            if file_key not in excel_files:
                excel_files[file_key] = str(file)
        
        file_list = list(excel_files.values())
        if not file_list:
            warnings.warn(f"文件夹 {folder_path} 中未找到Excel文件(.xlsx/.xls)")
            return pd.DataFrame()
        
        return self._load_multiple_excel_files(
            file_list, sheet_name, header, index_col, parse_dates,
            skip_tail_rows, merge_method, optimize_memory, drop_na_threshold, **kwargs
        )

    def _validate_excel_structure(self, file_path: str, sheet_name: Union[str, List[str], None] = 0) -> bool:
        """验证Excel文件结构完整性（支持指定sheet）[4,5](@ref)"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            if not file_path.lower().endswith(('.xlsx', '.xls')):
                raise ValueError(f"仅支持 .xlsx 或 .xls 文件格式，当前文件: {file_path}")
            
            # 尝试读取文件结构
            test_df = pd.read_excel(
                file_path, 
                sheet_name=sheet_name if sheet_name not in [None, 0] else 0,
                nrows=5,
                engine='openpyxl' if file_path.endswith('.xlsx') else 'xlrd'
            )
            
            if isinstance(test_df, dict):
                has_data = any(not df.empty for df in test_df.values())
                if not has_data:
                    raise ValueError("Excel文件所有指定sheet均为空")
            else:
                if test_df.empty:
                    raise ValueError("Excel文件指定sheet为空")
                
            return True
            
        except ImportError as e:
            if "openpyxl" in str(e):
                raise ImportError("请安装openpyxl库: pip install openpyxl")
            elif "xlrd" in str(e):
                raise ImportError("请安装xlrd库: pip install xlrd==1.2.0（兼容.xls）")
            raise e
        except Exception as e:
            raise ValueError(f"Excel结构验证失败: {str(e)}")

    def _handle_multiindex_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """增强的多级表头处理：清理空值、合并无效层级 [6,8](@ref)"""
        try:
            if isinstance(df.columns, pd.MultiIndex):
                new_tuples = []
                for col_tuple in df.columns:
                    cleaned_tuple = tuple(
                        '' if ('Unnamed' in str(x) or pd.isna(x) or x == '') else str(x).strip()
                        for x in col_tuple
                    )
                    # 移除空字符串并确保至少有一个非空级别
                    cleaned_tuple = tuple(x for x in cleaned_tuple if x != '')
                    if not cleaned_tuple:
                        cleaned_tuple = ('未知列',)
                    new_tuples.append(cleaned_tuple)
                
                # 如果所有列都只有单一层级，转换为单级列名
                if all(len(t) == 1 for t in new_tuples):
                    df.columns = [t[0] for t in new_tuples]
                else:
                    # 统一层级数量，用空字符串填充
                    max_levels = max(len(t) for t in new_tuples)
                    padded_tuples = [t + ('',) * (max_levels - len(t)) for t in new_tuples]
                    df.columns = pd.MultiIndex.from_tuples(padded_tuples)
                
                return df
            
            # 处理单级表头
            df.columns = [
                str(col).replace('Unnamed: ', '列_').strip() if 'Unnamed' in str(col) else str(col).strip()
                for col in df.columns
            ]
            
            return df
            
        except Exception as e:
            warnings.warn(f"多级表头处理失败: {str(e)}")
            return df

    def _postprocess_data(self, df: pd.DataFrame, 
                         skip_tail_rows: int = 0,
                         drop_na_threshold: float = 0.8) -> pd.DataFrame:
        """数据后处理：跳过末尾行、处理缺失值、去重索引 [3,5](@ref)"""
        try:
            original_shape = df.shape
            if df.empty:
                return df
            
            if skip_tail_rows > 0 and len(df) > skip_tail_rows:
                df = df.iloc[:-skip_tail_rows]
            
            # 删除缺失值过多的列
            if len(df) > 0:
                na_ratio = df.isna().sum() / len(df)
                columns_to_drop = na_ratio[na_ratio > drop_na_threshold].index
                if len(columns_to_drop) > 0:
                    df = df.drop(columns=columns_to_drop)
                    warnings.warn(f"已删除缺失值比例超过{drop_na_threshold:.0%}的列: {list(columns_to_drop)}")
            
            # 删除全空行
            df = df.dropna(how='all')
            
            # 处理重复索引
            if not df.index.is_unique:
                dup_count = df.index.duplicated().sum()
                df = df[~df.index.duplicated(keep='first')]
                warnings.warn(f"发现{dup_count}个重复索引，已保留第一个出现值")
            
            print(f"数据后处理完成: {original_shape} -> {df.shape}")
            return df
            
        except Exception as e:
            warnings.warn(f"数据后处理失败: {str(e)}")
            return df

    def _handle_date_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """确保日期索引正确解析（兼容多级索引）"""
        try:
            if not isinstance(df.index, pd.MultiIndex):
                if hasattr(df.index, 'dtype') and df.index.dtype == 'object':
                    df.index = pd.to_datetime(df.index, errors='coerce')
                    success_rate = df.index.notna().mean()
                    if success_rate < 0.8:
                        warnings.warn(f"日期索引转换成功率较低: {success_rate:.1%}")
                return df
            
            return df
            
        except Exception as e:
            warnings.warn(f"日期索引处理失败: {str(e)}")
            return df

    def _optimize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """优化DataFrame内存使用"""
        try:
            original_memory = df.memory_usage(deep=True).sum()
            
            # 优化数值列
            for col in df.select_dtypes(include=['int64']).columns:
                df[col] = pd.to_numeric(df[col], downcast='integer')
            
            for col in df.select_dtypes(include=['float64']).columns:
                df[col] = pd.to_numeric(df[col], downcast='float')
            
            # 优化对象列
            for col in df.select_dtypes(include=['object']).columns:
                if len(df) > 0:
                    num_unique = df[col].nunique()
                    num_total = len(df[col])
                    if num_total > 0 and (num_unique / num_total) < 0.5:
                        df[col] = df[col].astype('category')
            
            optimized_memory = df.memory_usage(deep=True).sum()
            reduction = (original_memory - optimized_memory) / original_memory
            
            if reduction > 0.01:
                print(f"内存优化: {original_memory/1024/1024:.2f}MB -> {optimized_memory/1024/1024:.2f}MB (减少{reduction:.1%})")
            
            return df
            
        except Exception as e:
            warnings.warn(f"内存优化失败: {str(e)}")
            return df

    def get_processed_files(self) -> set:
        """获取已处理的文件列表"""
        return self._processed_files.copy()
    
    def reset_processed_files(self):
        """重置已处理文件记录"""
        self._processed_files.clear()
    
    def export_to_excel(self, df: pd.DataFrame, output_path: str, sheet_name: str = "data") -> None:
        """导出处理后的数据到Excel文件 [4](@ref)"""
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, freeze_panes=(1, 1))
            
            print(f"数据已导出: {output_path}")
        except Exception as e:
            raise ValueError(f"Excel导出失败: {str(e)}")

    def load_csv_data(self, file_path: Union[str, List[str]], 
                      sep: str = ',',
                      header: Union[int, List[int]] = 0,
                      index_col: Union[int, List[int]] = None,
                      parse_dates: bool = True,
                      encoding: str = 'utf-8',
                      **kwargs) -> pd.DataFrame:
        """
        加载 CSV 数据
        
        Args:
            file_path: CSV 文件路径或文件列表
            sep: 分隔符，默认逗号
            header: 表头行位置
            index_col: 作为行索引的列位置
            parse_dates: 是否解析日期列
            encoding: 文件编码
            **kwargs: 其他传递给 pd.read_csv 的参数
            
        Returns:
            pd.DataFrame: 加载的数据
        """
        try:
            if isinstance(file_path, list):
                # 多文件合并
                dfs = []
                for fp in file_path:
                    df = pd.read_csv(
                        fp, sep=sep, header=header, index_col=index_col,
                        parse_dates=parse_dates, encoding=encoding, **kwargs
                    )
                    dfs.append(df)
                result = pd.concat(dfs, axis=0)
            else:
                result = pd.read_csv(
                    file_path, sep=sep, header=header, index_col=index_col,
                    parse_dates=parse_dates, encoding=encoding, **kwargs
                )
            
            # 处理日期索引
            if parse_dates and result.index.dtype == 'object':
                result.index = pd.to_datetime(result.index, errors='coerce')
            
            return result
            
        except Exception as e:
            raise ValueError(f"CSV文件读取失败 {file_path}: {str(e)}")

    def save_data(self, df: pd.DataFrame, file_path: Union[str, Path], 
                  format: str = 'excel', **kwargs) -> bool:
        """
        保存数据到文件（统一接口）
        
        Args:
            df: 要保存的 DataFrame
            file_path: 保存路径
            format: 格式 ('excel', 'csv', 'json')
            **kwargs: 其他参数
            
        Returns:
            bool: 保存成功返回 True
        """
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            format = format.lower()
            
            if format == 'excel':
                sheet_name = kwargs.get('sheet_name', 'data')
                self.export_to_excel(df, str(file_path), sheet_name)
                return True
            elif format == 'csv':
                encoding = kwargs.get('encoding', 'utf-8')
                index = kwargs.get('index', True)
                df.to_csv(file_path, encoding=encoding, index=index)
                print(f"数据已保存到: {file_path}")
                return True
            elif format == 'json':
                return self.save_to_json(df, file_path, **kwargs)
            else:
                raise ValueError(f"不支持的格式: {format}。支持: excel, csv, json")
                
        except Exception as e:
            print(f"保存失败: {str(e)}")
            return False

    def list_available_files(self, directory: str, 
                             extensions: List[str] = None) -> List[str]:
        """
        列出目录中可用的数据文件
        
        Args:
            directory: 目录路径
            extensions: 文件扩展名列表，默认支持常见数据格式
            
        Returns:
            List[str]: 可用文件路径列表
        """
        if extensions is None:
            extensions = ['.xlsx', '.xls', '.csv', '.json']
        
        directory = Path(directory)
        if not directory.exists():
            warnings.warn(f"目录不存在: {directory}")
            return []
        
        files = []
        for ext in extensions:
            files.extend(directory.glob(f'*{ext}'))
            files.extend(directory.glob(f'**/*{ext}'))  # 递归搜索
        
        # 去重并排序
        unique_files = sorted(set(str(f) for f in files))
        
        return unique_files

