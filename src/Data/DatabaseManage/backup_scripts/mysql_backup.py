"""
MySQL 数据库备份脚本

用途：备份 MySQL 数据库（mysqldump 方式）
用法：
    from backup_scripts.mysql_backup import backup_mysql
    backup_mysql(host='localhost', port=3306, dbname='lott', user='root', password='xxx', dest_dir='/backup')
"""

import os
import subprocess
from datetime import datetime
from typing import Optional


def backup_mysql(
    host: str = 'localhost',
    port: int = 3306,
    dbname: str = 'lott',
    user: str = 'root',
    password: Optional[str] = None,
    dest_dir: str = '.'
) -> str:
    """
    使用 mysqldump 备份 MySQL 数据库
    
    Args:
        host: 数据库主机
        port: 端口
        dbname: 数据库名
        user: 用户名
        password: 密码（建议使用环境变量）
        dest_dir: 备份文件存放目录
    
    Returns:
        str: 备份文件路径
    """
    os.makedirs(dest_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(dest_dir, f"{dbname}_backup_{timestamp}.sql")
    
    env = os.environ.copy()
    if password:
        env['MYSQL_PWD'] = password
    
    cmd = [
        'mysqldump',
        f'-h{host}',
        f'-P{port}',
        f'-u{user}',
        '--single-transaction',  # 事务性备份
        '--quick',                # 大表快速导出
        '--routines',             # 包含存储过程
        '--triggers',             # 包含触发器
        '--events',               # 包含事件
        '--master-data=2',        # 包含 CHANGE MASTER TO
        '--add-drop-table',       # DROP TABLE 语句
        dbname,
    ]
    
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            result = subprocess.run(
                cmd,
                env=env,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True
            )
        
        if result.returncode == 0:
            size = os.path.getsize(backup_file)
            print(f"✅ MySQL 备份完成: {backup_file} ({size:,} bytes)")
            return backup_file
        else:
            raise RuntimeError(f"mysqldump 失败: {result.stderr}")
    except FileNotFoundError:
        raise RuntimeError("mysqldump 未安装，请先安装 MySQL 客户端")


def backup_mysql_all(
    host: str = 'localhost',
    port: int = 3306,
    user: str = 'root',
    password: Optional[str] = None,
    dest_dir: str = '.'
) -> str:
    """
    备份 MySQL 所有数据库
    
    Args:
        host: 数据库主机
        port: 端口
        user: 用户名
        password: 密码
        dest_dir: 备份文件存放目录
    
    Returns:
        str: 备份文件路径
    """
    os.makedirs(dest_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(dest_dir, f"mysql_all_backup_{timestamp}.sql")
    
    env = os.environ.copy()
    if password:
        env['MYSQL_PWD'] = password
    
    cmd = [
        'mysqldump',
        f'-h{host}',
        f'-P{port}',
        f'-u{user}',
        '--all-databases',
        '--single-transaction',
        '--quick',
        '--routines',
        '--triggers',
        '--events',
        '--add-drop-database',
        '--master-data=2',
    ]
    
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            result = subprocess.run(cmd, env=env, stdout=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            size = os.path.getsize(backup_file)
            print(f"✅ MySQL 全量备份完成: {backup_file} ({size:,} bytes)")
            return backup_file
        else:
            raise RuntimeError(f"mysqldump 失败: {result.stderr}")
    except FileNotFoundError:
        raise RuntimeError("mysqldump 未安装")


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("用法: python mysql_backup.py <数据库名> [备份目录]")
        print("示例: python mysql_backup.py lott /backup")
    else:
        dbname = sys.argv[1]
        dest = sys.argv[2] if len(sys.argv) > 2 else '.'
        backup_mysql(dbname=dbname, dest_dir=dest)
