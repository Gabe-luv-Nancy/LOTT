import sys
sys.path.append('X:/LOTT/src/Cross_Layer')
from global_imports import *
def multiindex_report(df, filename="multiindex_report.xlsx"):
    """
    DataFrame列信息报告，使用示例：
    result = multiindex_report(data, "X:/LOTT/my_reports/analysis.xlsx")
    """
    # 确保输出目录存在
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    
    # 收集所有列信息
    column_info_rows = []
    
    for i, col in enumerate(df.columns):
        row_data = {'列索引': i}
        
        # 处理多级列名
        if isinstance(col, tuple):
            for level_idx, level_value in enumerate(col):
                row_data[f'级别_{level_idx}'] = str(level_value) if level_value is not None else ''
        else:
            row_data['级别_0'] = str(col) if col is not None else ''
        
        # 添加基本统计信息
        row_data['非空值数量'] = int(df[col].count())
        row_data['空值数量'] = int(df[col].isnull().sum())
        row_data['总行数'] = len(df)
        row_data['空值比例(%)'] = round((df[col].isnull().sum() / len(df)) * 100, 2)
        
        column_info_rows.append(row_data)
    
    # 创建主数据框
    column_info_df = pd.DataFrame(column_info_rows)
    
    # 创建摘要信息
    summary_data = {
        '统计项目': ['总行数', '总列数', '数据形状'],
        '数值': [df.shape[0], df.shape[1], f"{df.shape[0]}行×{df.shape[1]}列"]
    }
    summary_df = pd.DataFrame(summary_data)
    
    # 写入单个Excel文件
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # 先写入列详细信息
        column_info_df.to_excel(writer, sheet_name='列信息报告', index=False, startrow=0)
        
        # 在数据下方空2行后写入摘要
        start_row = len(column_info_df) + 3
        summary_df.to_excel(writer, sheet_name='列信息报告', index=False, startrow=start_row)
        
        # 在工作表中添加标题
        worksheet = writer.sheets['列信息报告']
        worksheet.cell(row=1, column=1, value=f"DataFrame列信息报告 - 共{len(column_info_df)}列")
        worksheet.cell(row=start_row, column=1, value="数据摘要")
    
    print(f"文件已保存至: {os.path.abspath(filename)}")
    return column_info_df