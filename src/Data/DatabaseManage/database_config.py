"""
数据库配置模块 - 支持 SQLite 和 TimescaleDB
"""

from .utils import *


# ==================== 配置类 ====================

@dataclass
class DatabaseConfig:
    """数据库配置类 - 支持SQLite和TimescaleDB"""
    
    # 数据库类型: sqlite 或 timescaledb
    db_type: str = "sqlite"
    
    # 数据库连接配置
    db_url: str = "sqlite:///X:/LOTT/src/Data/DataSource/_db/data.db"
    
    # SQLite优化配置
    sqlite_optimizations: Dict = field(default_factory=lambda: {
        "journal_mode": "WAL",
        "cache_size": -10000,
        "synchronous": "NORMAL",
        "temp_store": "memory",
        "mmap_size": 268435456
    })
    
    # TimescaleDB/PostgreSQL配置
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "futures_data"
    pg_user: str = "postgres"
    pg_password: str = ""
    pg_pool_size: int = 10
    pg_max_overflow: int = 20
    
    # 数据操作配置
    commit_frequency: int = 10
    invalid_values: List[str] = field(default_factory=lambda: ['', 'NULL', 'NaN', 'None'])
    log_level: str = "INFO"
    log_format: str = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    
    def __post_init__(self):
        # 初始化默认的优化设置
        if self.sqlite_optimizations is None:
            self.sqlite_optimizations = {
                "journal_mode": "WAL",
                "synchronous": "NORMAL",
                "cache_size": -10000,
            }
        
        # 确保connect_args存在
        if not hasattr(self, 'connect_args'):
            self.connect_args = {}
    
    def get_postgresql_url(self) -> str:
        """获取PostgreSQL连接URL"""
        return f"postgresql://{self.pg_user}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_database}"
    
    def to_sqlite(self, db_url: Optional[str] = None):
        """切换到SQLite模式"""
        self.db_type = "sqlite"
        if db_url:
            self.db_url = db_url
    
    def to_timescaledb(self, host: str = "localhost", port: int = 5432, 
                       database: str = "futures_data", 
                       user: str = "postgres", password: str = ""):
        """切换到TimescaleDB模式"""
        self.db_type = "timescaledb"
        if host: self.pg_host = host
        if port: self.pg_port = port
        if database: self.pg_database = database
        if user: self.pg_user = user
        if password: self.pg_password = password
