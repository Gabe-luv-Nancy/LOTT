"""
SQLite 数据库备份脚本

用途：备份 SQLite 数据库文件（开发调试用）
用法：
    from backup_scripts.sqlite_backup import backup_sqlite
    backup_sqlite('source.db', 'dest.db')
"""

import shutil
import os
from datetime import datetime


def backup_sqlite(source_db: str, dest_db: str = None) -> str:
    """
    备份 SQLite 数据库文件
    
    Args:
        source_db: 源数据库路径
        dest_db: 目标路径，默认在同目录加时间戳
    
    Returns:
        str: 备份文件路径
    """
    if not os.path.exists(source_db):
        raise FileNotFoundError(f"源数据库不存在: {source_db}")
    
    if dest_db is None:
        base, ext = os.path.splitext(source_db)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest_db = f"{base}_backup_{timestamp}{ext}"
    
    shutil.copy2(source_db, dest_db)
    size = os.path.getsize(dest_db)
    print(f"✅ SQLite 备份完成: {dest_db} ({size:,} bytes)")
    return dest_db


def backup_sqlite_to_folder(source_db: str, folder: str) -> str:
    """
    备份到指定文件夹
    
    Args:
        source_db: 源数据库路径
        folder: 目标文件夹
    
    Returns:
        str: 备份文件完整路径
    """
    os.makedirs(folder, exist_ok=True)
    db_name = os.path.basename(source_db)
    base, ext = os.path.splitext(db_name)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest_db = os.path.join(folder, f"{base}_backup_{timestamp}{ext}")
    return backup_sqlite(source_db, dest_db)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("用法: python sqlite_backup.py <源数据库路径> [目标路径]")
    else:
        source = sys.argv[1]
        dest = sys.argv[2] if len(sys.argv) > 2 else None
        backup_sqlite(source, dest)
