# import sys
# sys.path.append('X:/LOTT/src/Cross_Layer')
# from global_imports import *


# # 添加项目根目录到系统路径
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# # 从正确位置导入所需类
# from core.time_series_db import TimeSeriesDB
# from core.data_manager import DataManager

# def load_json_data(file_path):
#     """统一JSON数据加载函数"""
#     storage = JSONStorage(file_path)
#     return storage.read()

# def save_json_data(file_path, data):
#     """统一JSON数据保存函数"""
#     storage = JSONStorage(file_path)
#     storage.write(data)

# # 页面配置
# st.set_page_config(
#     page_title="LOTT 算法分析面板",
#     layout="wide"
# )

# # 初始化数据平台
# DB_PATH = 'database.db'
# data_platform = TimeSeriesDB(DB_PATH)


# class FrontendApp:
#     """前端应用类，封装Streamlit UI和业务逻辑"""

#     def __init__(self):
#         """初始化应用状态"""
#         self.data_handler = DataManager(DB_PATH)
#         self.analysis_results = None
#         self.matrix_results = None
#         self.selected_data = None

#     def load_data(self, start_date: str, end_date: str, column_indices: List[int]) -> Optional[pd.DataFrame]:
#         """加载选定日期范围和列的数据

#         Args:
#             start_date: 开始日期 (YYYY-MM-DD)
#             end_date: 结束日期 (YYYY-MM-DD)
#             column_indices: 选定的列索引列表

#         Returns:
#             包含选定数据的DataFrame，加载失败返回None
#         """
#         try:
#             # 按日期范围加载数据
#             data_records = self.data_handler.read_data_by_date_range(start_date, end_date)

#             if not data_records:
#                 st.warning(f"在 {start_date} 到 {end_date} 范围内没有找到数据")
#                 return None

#             # 提取选定列的数据
#             dates = []
#             all_arrays = []
#             for record in data_records:
#                 array_data = record['array_data']
#                 # 只保留选定的列
#                 selected_data = [array_data[i] for i in column_indices if i < len(array_data)]
#                 dates.append(record['date'])
#                 all_arrays.append(selected_data)

#             # 创建DataFrame
#             df = pd.DataFrame({
#                 '日期': dates,
#                 '数据': all_arrays
#             }).set_index('日期')

#             return df
#         except Exception as e:
#             st.error(f"数据加载失败: {str(e)}")
#             return None

#     def analyze_data(self, df: pd.DataFrame, analysis_type: str, **kwargs) -> Optional[pd.DataFrame]:
#         """分析数据并返回结果

#         Args:
#             df: 包含数据的DataFrame
#             analysis_type: 分析类型
#             kwargs: 分析参数

#         Returns:
#             分析结果DataFrame，分析失败返回None
#         """
#         try:
#             results = []
#             for array in df['数据'].tolist():
#                 # 计算奇偶比（在所有分析类型中都需要）
#                 even_count = sum(1 for x in array if x % 2 == 0) if array else 0
#                 odd_count = sum(1 for x in array if x % 2 != 0) if array else 0
#                 ratio = even_count / odd_count if odd_count != 0 else float('inf')
                
#                 if analysis_type == "移动平均分析":
#                     window = kwargs.get('window_length', 5)
#                     if len(array) >= window:
#                         moving_avg = np.convolve(array, np.ones(window), 'valid') / window
#                         result = {
#                             '移动平均值': moving_avg[-1] if len(moving_avg) > 0 else 0
#                         }
#                     else:
#                         result = {'移动平均值': 0}
#                 elif analysis_type == "时间序列预测":
#                     # 使用简单的移动平均作为预测占位符
#                     window = 3
#                     if len(array) >= window:
#                         forecast = np.convolve(array, np.ones(window), 'valid') / window
#                         result = {
#                             '预测值': forecast[-1] if forecast else 0,
#                             '预测趋势': forecast
#                         }
#                     else:
#                         result = {'预测值': 0, '预测趋势': []}
#                 elif analysis_type == "假设检验":
#                     # 使用平均值作为假设检验的占位值
#                     mean_val = np.mean(array) if array else 0
#                     test_value = kwargs.get('test_value', 5.0)
#                     result = {
#                         '检验值': test_value,
#                         'p值': 0.05 if mean_val > test_value else 0.95,
#                         '是否拒绝原假设': mean_val > test_value
#                     }
#                 elif analysis_type == "奇偶比分析":
#                     result = {
#                         '奇偶比': ratio
#                     }
#                 elif analysis_type == "矩阵计算":
#                     # 矩阵计算占位符
#                     result = {
#                         '操作': 'mean',
#                         '结果': np.mean(array) if array else 0
#                     }
#                 else:
#                     # 默认统计分析
#                     result = {
#                         '平均值': np.mean(array) if array else 0,
#                         '最大值': np.max(array) if array else 0,
#                         '最小值': np.min(array) if array else 0,
#                         '标准差': np.std(array) if array else 0,
#                         '奇偶比': ratio
#                     }
#                 results.append(result)

#             return pd.DataFrame(results)
#         except Exception as e:
#             st.error(f"数据分析失败: {str(e)}")
#             return None

#     def display_results(self, df: pd.DataFrame, analysis_type: str, analysis_results: pd.DataFrame):
#         """显示分析结果

#         Args:
#             df: 原始数据DataFrame
#             analysis_type: 分析类型
#             analysis_results: 分析结果DataFrame
#         """
#         # 图表展示
#         st.subheader("图表展示")
#         if analysis_type == "移动平均分析":
#             # 计算移动平均值
#             window = st.session_state.get('window_length', 5)
#             moving_avg = df['数据'].apply(lambda x: np.mean(x[-window:]) if len(x) >= window else np.nan)
#             st.line_chart(moving_avg)
#         elif analysis_type == "时间序列预测":
#             # 显示预测趋势
#             if '预测趋势' in analysis_results.columns:
#                 trends = analysis_results['预测趋势'].dropna()
#                 if not trends.empty:
#                     st.line_chart(trends.apply(lambda x: x[-1] if x else 0))
#         elif analysis_type == "奇偶比分析":
#             st.bar_chart(analysis_results['奇偶比'])
#         elif analysis_type == "矩阵计算":
#             # 矩阵计算不需要图表
#             pass
#         else:
#             # 默认显示原始数据折线图
#             st.line_chart(df['数据'].apply(lambda x: np.mean(x) if x else 0))

#         # 数值结果展示
#         st.subheader("数值结果")
#         if analysis_results is not None:
#             st.dataframe(analysis_results.describe())

#             # 显示原始分析结果
#             st.text_area("详细分析结果",
#                          analysis_results.to_string(index=False),
#                          height=200)
#         else:
#             st.warning("无分析结果")

#         # 矩阵计算结果展示
#         if analysis_type == "矩阵计算":
#             st.subheader("矩阵计算结果")
#             # 使用占位符结果
#             matrix_result = {
#                 'operation': st.session_state.get('matrix_operation', 'mean'),
#                 'result': analysis_results['结果'].mean() if not analysis_results.empty else 0
#             }
#             st.table(pd.DataFrame([matrix_result]))

#     def run(self):
#         """运行前端应用"""
#         st.title("LOTT 算法分析面板")
#         st.markdown("---")

#         # 创建两列布局
#         left_col, right_col = st.columns([1, 3])

#         with left_col:
#             st.header("数据源控制面板")
#             with st.form("data_source_form"):
#                 # 日期范围选择
#                 today = datetime.today()
#                 one_month_ago = today - timedelta(days=30)

#                 st.subheader("时间范围")
#                 start_date = st.date_input("开始日期", one_month_ago).strftime('%Y-%m-%d')
#                 end_date = st.date_input("结束日期", today).strftime('%Y-%m-%d')

#                 # 分析类型选择
#                 st.subheader("分析类型")
#                 analysis_type = st.selectbox(
#                     "选择分析类型",
#                     ["统计分析", "移动平均分析", "时间序列预测", "假设检验", "奇偶比分析", "矩阵计算"]
#                 )

#                 # 列选择
#                 st.subheader("数据列选择")
#                 num_columns = st.slider("选择列数", 1, 10, 1)
#                 column_indices = st.multiselect(
#                     "选择列索引",
#                     options=list(range(num_columns)),
#                     default=list(range(num_columns)))

#                 # 根据分析类型显示参数控件
#                 st.subheader("分析参数")
#                 if analysis_type == "移动平均分析":
#                     window_length = st.slider("移动平均窗口", 3, 15, 5)
#                     st.session_state.window_length = window_length
#                 elif analysis_type == "时间序列预测":
#                     forecast_steps = st.slider("预测步数", 1, 10, 5)
#                     st.session_state.forecast_steps = forecast_steps
#                 elif analysis_type == "假设检验":
#                     test_value = st.slider("假设检验值", 0.0, 10.0, 5.0)
#                     st.session_state.test_value = test_value
#                 elif analysis_type == "矩阵计算":
#                     matrix_operation = st.selectbox("矩阵计算操作", ["mean", "sum", "min", "max"])
#                     st.session_state.matrix_operation = matrix_operation

#                 # 提交按钮
#                 submitted = st.form_submit_button("开始分析")

#         with right_col:
#             st.header("分析结果展示区")
#             result_placeholder = st.empty()
#             progress_bar = st.progress(0)
#             status_text = st.empty()

#             # 处理分析请求
#             if submitted:
#                 # 清空旧结果
#                 result_placeholder.empty()

#                 # 加载数据
#                 status_text.info("正在加载数据...")
#                 df = self.load_data(start_date, end_date, column_indices)
#                 progress_bar.progress(30)

#                 if df is None or df.empty:
#                     st.error("无法进行分析：数据为空")
#                     progress_bar.progress(100)
#                     return

#                 # 分析数据
#                 status_text.info("正在分析数据...")
#                 analysis_params = {
#                     'column_indices': column_indices,
#                     'window_length': st.session_state.get('window_length', 5),
#                     'forecast_steps': st.session_state.get('forecast_steps', 5),
#                     'test_value': st.session_state.get('test_value', 5.0),
#                     'matrix_operation': st.session_state.get('matrix_operation', 'mean')
#                 }

#                 analysis_results = self.analyze_data(df, analysis_type, **analysis_params)
#                 progress_bar.progress(70)

#                 # 显示结果
#                 status_text.info("正在生成结果...")
#                 self.display_results(df, analysis_type, analysis_results)
#                 progress_bar.progress(100)

#                 status_text.success("分析完成！")
#                 progress_bar.empty()
#                 status_text.empty()

#         # 添加说明
#         st.markdown("---")
#         st.caption("说明：此面板为 LOTT 算法分析工具，配置参数后点击'开始分析'进行数据分析")


# # 运行应用
# if __name__ == "__main__":
#     app = FrontendApp()
#     app.run()


# def visualize_data(time_series, eigen_data, prediction_data, scores):
#     """
#     可视化展示时序数据、特征值、预测值和评分
#     """
#     # 以时间为横轴，绘制多图叠加的折线图
#     plot_multiple_lines(time_series, eigen_data, prediction_data)
    
#     # 展示最终评分靠前的预测值
#     display_top_predictions(prediction_data, scores)

# def plot_multiple_lines(time_series, eigen_data, prediction_data):
#     # 绘制多图叠加的折线图逻辑
#     pass

# def display_top_predictions(prediction_data, scores):
#     # 展示最终评分靠前的预测值逻辑
#     pass

# def create_parameter_selection_interface():
#     """
#     创建EIGEN算法参数选择界面
#     """
#     # 参数选择界面逻辑，可以是输入最好是拖动等
#     pass
