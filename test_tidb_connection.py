from sqlalchemy import create_engine, text

try:
    # 创建到TiDB的连接
    engine = create_engine('mysql+pymysql://root:@localhost:4000/mysql?charset=utf8mb4')
    
    # 测试连接并获取版本信息
    with engine.connect() as conn:
        # 获取数据库版本
        result = conn.execute(text('SELECT VERSION()'))
        version = result.fetchone()[0]
        print(f'连接成功！TiDB 版本: {version}')
        
        # 显示所有数据库
        result = conn.execute(text('SHOW DATABASES'))
        print('\n可用数据库:')
        for row in result:
            print(f'- {row[0]}')
            
except Exception as e:
    print(f'连接失败: {str(e)}') 