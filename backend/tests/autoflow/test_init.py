"""
测试AutoFlow初始化功能
"""

import pytest
from unittest.mock import patch, MagicMock

from app import init_autoflow
from app.autoflow.tools.registry import ToolRegistry


@pytest.fixture
def mock_session():
    """创建模拟的数据库会话"""
    return MagicMock()


@pytest.fixture
def mock_engine_config():
    """创建模拟的引擎配置"""
    config = MagicMock()
    return config


def test_init_autoflow(mock_session, mock_engine_config):
    """测试init_autoflow函数能够正确初始化并注册工具"""
    
    # 模拟ToolRegistry和register_default_tools
    mock_registry = MagicMock()
    mock_registry.list_tools.return_value = ["tool1", "tool2", "tool3"]
    
    with patch("app.autoflow.tools.init.register_default_tools", return_value=mock_registry):
        # 调用init_autoflow函数
        result = init_autoflow(mock_session, mock_engine_config)
        
        # 验证结果
        assert result is mock_registry
        assert result.list_tools() == ["tool1", "tool2", "tool3"]


def test_tool_registry_singleton():
    """测试ToolRegistry是否正确实现了单例模式"""
    # 创建两个实例
    registry1 = ToolRegistry()
    registry2 = ToolRegistry()
    
    # 验证是同一个实例
    assert registry1 is registry2
    
    # 测试基本功能
    tool_name = "test_tool"
    mock_tool = MagicMock()
    mock_tool.name = tool_name
    
    # 在第一个实例上注册工具
    registry1.register_tool(mock_tool)
    
    # 验证在第二个实例上可以访问到
    assert tool_name in registry2.list_tools()
    assert registry2.get_tool(tool_name) is mock_tool 