"""
PostgreSQL 数据库备份脚本

用途：备份 PostgreSQL 数据库（pg_dump 方式）
用法：
    from backup_scripts.pg_backup import backup_pg
    backup_pg(host='localhost', port=5432, dbname='lott', user='postgres', password='xxx', dest_dir='/backup')
"""

import os
import subprocess
from datetime import datetime
from typing import Optional


def backup_pg(
    host: str = 'localhost',
    port: int = 5432,
    dbname: str = 'lott',
    user: str = 'postgres',
    password: Optional[str] = None,
    dest_dir: str = '.'
) -> str:
    """
    使用 pg_dump 备份 PostgreSQL 数据库
    
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
        env['PGPASSWORD'] = password
    
    cmd = [
        'pg_dump',
        '-h', host,
        '-p', str(port),
        '-U', user,
        '-d', dbname,
        '-f', backup_file,
        '--create',  # 包含创建数据库语句
        '--clean',   # DROP TABLE 语句
    ]
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            size = os.path.getsize(backup_file)
            print(f"✅ PostgreSQL 备份完成: {backup_file} ({size:,} bytes)")
            return backup_file
        else:
            raise RuntimeError(f"pg_dump 失败: {result.stderr}")
    except FileNotFoundError:
        raise RuntimeError("pg_dump 未安装，请先安装 PostgreSQL 客户端")


def backup_pg_custom(
    connection_string: str,
    dest_dir: str = '.'
) -> str:
    """
    使用连接字符串备份（方便 Docker 环境）
    
    Args:
        connection_string: PostgreSQL 连接字符串
            例: postgresql://postgres:password@localhost:5432/lott
        dest_dir: 备份文件存放目录
    
    Returns:
        str: 备份文件路径
    """
    os.makedirs(dest_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(dest_dir, f"pg_backup_{timestamp}.sql")
    
    env = os.environ.copy()
    env['PGPASSWORD'] = connection_string.split('://')[-1].split('@')[0].split(':')[-1]
    
    cmd = [
        'pg_dump',
        connection_string,
        '-f', backup_file,
        '--create',
        '--clean',
    ]
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode == 0:
            size = os.path.getsize(backup_file)
            print(f"✅ PostgreSQL 备份完成: {backup_file} ({size:,} bytes)")
            return backup_file
        else:
            raise RuntimeError(f"pg_dump 失败: {result.stderr}")
    except FileNotFoundError:
        raise RuntimeError("pg_dump 未安装")


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("用法: python pg_backup.py <连接字符串> [备份目录]")
        print("示例: python pg_backup.py postgresql://postgres:password@localhost:5432/lott /backup")
    else:
        conn_str = sys.argv[1]
        dest = sys.argv[2] if len(sys.argv) > 2 else '.'
        backup_pg_custom(conn_str, dest)
