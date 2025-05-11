"""
MongoDB数据库连接器模块

提供MongoDB数据库的连接和操作功能
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from contextlib import contextmanager

import pymongo
from pymongo import MongoClient
from bson import ObjectId, json_util

from app.models.database_connection import DatabaseConnection
from app.parameters.database_connection import MongoDBParameters
from app.rag.database.base import BaseConnector, ConnectionTestResult
from app.utils.crypto import decrypt_dict_values


logger = logging.getLogger(__name__)


class MongoDBConnector(BaseConnector):
    """
    MongoDB数据库连接器
    
    提供与MongoDB数据库交互的功能
    """
    
    def __init__(self, connection: DatabaseConnection):
        """
        初始化MongoDB连接器
        
        参数:
            connection: 数据库连接配置
        """
        self.connection_config = connection
        self.client: Optional[pymongo.MongoClient] = None
        self.db: Optional[pymongo.database.Database] = None
        self.parameters: Optional[MongoDBParameters] = None
        
        # 初始化参数
        self._init_parameters()
    
    def _init_parameters(self) -> None:
        """
        初始化连接参数
        
        从连接配置中解析和解密参数
        """
        # 解密配置中的敏感字段
        config = decrypt_dict_values(
            self.connection_config.config, 
            MongoDBParameters.SENSITIVE_FIELDS
        )
        
        # 创建参数对象
        self.parameters = MongoDBParameters.from_dict(config)
    
    def connect(self) -> bool:
        """
        建立数据库连接
        
        创建MongoDB客户端并建立连接
        
        返回:
            bool: 连接是否成功
        """
        try:
            # 创建MongoDB客户端
            if not self.parameters:
                self._init_parameters()
            
            # 构建连接参数
            connection_params = {
                "host": self.parameters.host,
                "port": self.parameters.port,
                "username": self.parameters.user if self.parameters.user else None,
                "password": self.parameters.password if self.parameters.password else None,
                "ssl": self.parameters.ssl,
                "maxPoolSize": 10,
                "serverSelectionTimeoutMS": 5000,  # 5秒超时
            }
            
            # 添加认证参数
            if self.parameters.auth_source:
                connection_params["authSource"] = self.parameters.auth_source
                
            if self.parameters.auth_mechanism:
                connection_params["authMechanism"] = self.parameters.auth_mechanism
            
            # 创建客户端
            self.client = MongoClient(**connection_params)
            
            # 测试连接
            self.client.server_info()
            
            # 获取数据库
            self.db = self.client[self.parameters.database]
            
            logger.info(f"Successfully connected to MongoDB database: {self.parameters.database}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB database: {str(e)}")
            if self.client:
                self.client.close()
                self.client = None
            self.db = None
            return False
    
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接的上下文管理器
        
        返回一个上下文管理的数据库连接
        
        异常:
            Exception: 如果无法获取连接
        """
        if not self.client or not self.db:
            self.connect()
            
        if not self.client or not self.db:
            raise Exception("Failed to establish database connection")
            
        try:
            yield self.db
        finally:
            pass  # MongoDB的连接由连接池管理，不需要在这里关闭
    
    def test_connection(self) -> ConnectionTestResult:
        """
        测试数据库连接
        
        测试与数据库的连接并返回详细结果
        
        返回:
            ConnectionTestResult: 连接测试结果
        """
        try:
            start_time = time.time()
            
            # 尝试连接
            if not self.client or not self.db:
                self.connect()
                
            if not self.client or not self.db:
                return ConnectionTestResult(
                    success=False,
                    message="Failed to create database connection",
                    details=None
                )
            
            # 获取数据库版本和信息
            server_info = self.client.server_info()
            version = server_info.get("version", "Unknown")
            
            # 获取集合数量
            collection_count = len(self.db.list_collection_names())
            
            # 计算连接时间
            connection_time = time.time() - start_time
            
            return ConnectionTestResult(
                success=True,
                message=f"Successfully connected to MongoDB {version}",
                details={
                    "version": version,
                    "database": self.parameters.database,
                    "collection_count": collection_count,
                    "connection_time_ms": round(connection_time * 1000, 2),
                    "read_only": self.connection_config.read_only
                }
            )
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details=None
            )
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取数据库元数据
        
        获取数据库的集合、索引等信息
        
        返回:
            Dict[str, Any]: 数据库元数据
        """
        if not self.client or not self.db:
            self.connect()
            
        if not self.client or not self.db:
            return {"error": "Failed to connect to database"}
            
        try:
            # 获取所有集合信息
            collections_metadata = {}
            for collection_name in self.db.list_collection_names():
                collection = self.db[collection_name]
                
                # 获取索引信息
                indexes = []
                for index in collection.list_indexes():
                    indexes.append({
                        "name": index.get("name", ""),
                        "key": index.get("key", {}),
                        "unique": index.get("unique", False),
                        "sparse": index.get("sparse", False)
                    })
                
                # 获取示例文档
                sample_document = None
                try:
                    if not self.connection_config.read_only:
                        sample = list(collection.find().limit(1))
                        if sample:
                            # 将ObjectId转换为字符串
                            sample_document = json_util.loads(json_util.dumps(sample[0]))
                except Exception as sample_err:
                    logger.warning(f"Failed to get sample document: {str(sample_err)}")
                
                collections_metadata[collection_name] = {
                    "indexes": indexes,
                    "sample_document": sample_document,
                    "count": collection.estimated_document_count()
                }
            
            return {
                "database": self.parameters.database,
                "collections": collections_metadata,
                "collection_count": len(collections_metadata),
                "updated_at": time.time()
            }
        except Exception as e:
            logger.error(f"Failed to get metadata: {str(e)}")
            return {"error": str(e)}
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        执行MongoDB查询
        
        执行查询并返回结果和可能的错误
        
        参数:
            query: MongoDB查询字符串(JSON格式)
            params: 查询参数
            
        返回:
            Tuple[List[Dict[str, Any]], Optional[str]]: 查询结果和错误信息
        """
        if not self.client or not self.db:
            self.connect()
            
        if not self.client or not self.db:
            return [], "Failed to connect to database"
        
        try:
            # 解析查询
            query_dict = json_util.loads(query)
            
            # 提取操作类型和集合名称
            if "operation" not in query_dict or "collection" not in query_dict:
                return [], "Query must include 'operation' and 'collection'"
            
            operation = query_dict["operation"]
            collection_name = query_dict["collection"]
            
            # 如果是只读模式，禁止执行写操作
            if self.connection_config.read_only and operation not in ["find", "count", "distinct", "aggregate"]:
                return [], "Write operations are not allowed in read-only mode"
            
            collection = self.db[collection_name]
            results = []
            
            # 执行查询
            if operation == "find":
                filter_dict = query_dict.get("filter", {})
                projection = query_dict.get("projection", None)
                limit = query_dict.get("limit", 100)
                skip = query_dict.get("skip", 0)
                sort = query_dict.get("sort", None)
                
                cursor = collection.find(filter_dict, projection)
                
                if sort:
                    cursor = cursor.sort(sort)
                    
                cursor = cursor.skip(skip).limit(limit)
                
                # 转换结果
                for doc in cursor:
                    # 将ObjectId转换为字符串
                    results.append(json_util.loads(json_util.dumps(doc)))
                
            elif operation == "count":
                filter_dict = query_dict.get("filter", {})
                count = collection.count_documents(filter_dict)
                results = [{"count": count}]
                
            elif operation == "distinct":
                key = query_dict.get("key")
                filter_dict = query_dict.get("filter", {})
                
                if not key:
                    return [], "Missing 'key' for distinct operation"
                    
                values = collection.distinct(key, filter_dict)
                results = [{"values": values}]
                
            elif operation == "aggregate":
                pipeline = query_dict.get("pipeline", [])
                
                if not pipeline:
                    return [], "Missing 'pipeline' for aggregate operation"
                    
                cursor = collection.aggregate(pipeline)
                
                # 转换结果
                for doc in cursor:
                    results.append(json_util.loads(json_util.dumps(doc)))
                    
            elif operation == "insert_one" and not self.connection_config.read_only:
                document = query_dict.get("document", {})
                
                if not document:
                    return [], "Missing 'document' for insert_one operation"
                    
                result = collection.insert_one(document)
                results = [{"inserted_id": str(result.inserted_id)}]
                
            elif operation == "insert_many" and not self.connection_config.read_only:
                documents = query_dict.get("documents", [])
                
                if not documents:
                    return [], "Missing 'documents' for insert_many operation"
                    
                result = collection.insert_many(documents)
                results = [{"inserted_ids": [str(id) for id in result.inserted_ids]}]
                
            elif operation == "update_one" and not self.connection_config.read_only:
                filter_dict = query_dict.get("filter", {})
                update = query_dict.get("update", {})
                
                if not update:
                    return [], "Missing 'update' for update_one operation"
                    
                result = collection.update_one(filter_dict, update)
                results = [{"matched_count": result.matched_count, "modified_count": result.modified_count}]
                
            elif operation == "update_many" and not self.connection_config.read_only:
                filter_dict = query_dict.get("filter", {})
                update = query_dict.get("update", {})
                
                if not update:
                    return [], "Missing 'update' for update_many operation"
                    
                result = collection.update_many(filter_dict, update)
                results = [{"matched_count": result.matched_count, "modified_count": result.modified_count}]
                
            elif operation == "delete_one" and not self.connection_config.read_only:
                filter_dict = query_dict.get("filter", {})
                
                if not filter_dict:
                    return [], "Missing 'filter' for delete_one operation"
                    
                result = collection.delete_one(filter_dict)
                results = [{"deleted_count": result.deleted_count}]
                
            elif operation == "delete_many" and not self.connection_config.read_only:
                filter_dict = query_dict.get("filter", {})
                
                if not filter_dict:
                    return [], "Missing 'filter' for delete_many operation"
                    
                result = collection.delete_many(filter_dict)
                results = [{"deleted_count": result.deleted_count}]
                
            else:
                return [], f"Unsupported or unauthorized operation: {operation}"
            
            return results, None
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return [], str(e)
    
    def close(self) -> None:
        """
        关闭数据库连接
        
        释放数据库连接资源
        """
        if self.client:
            self.client.close()
            self.client = None
            self.db = None 