"""
测试获取chunk API
"""

import requests
import sys


def test_get_chunk_by_id(chunk_id):
    """测试通过ID获取chunk的API"""
    url = f"http://localhost:3001/api/v1/chunks/id/{chunk_id}"
    print(f"测试URL: {url}")

    try:
        response = requests.get(url)

        if response.status_code == 200:
            print("请求成功！")
            data = response.json()
            print("\n--- 返回数据 ---")
            print(f"ID: {data.get('id')}")
            print(f"哈希: {data.get('hash')}")
            print(f"文档ID: {data.get('document_id')}")
            print(f"源URI: {data.get('source_uri')}")
            print("\n--- 文本内容 ---")
            print(data.get("text", "无文本内容"))
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"发生错误: {e}")


def test_get_chunk_by_hash(chunk_hash):
    """测试通过哈希获取chunk的API"""
    url = f"http://localhost:3001/api/v1/chunks/hash/{chunk_hash}"
    print(f"测试URL: {url}")

    try:
        response = requests.get(url)

        if response.status_code == 200:
            print("请求成功！")
            data = response.json()
            print("\n--- 返回数据 ---")
            print(f"ID: {data.get('id')}")
            print(f"哈希: {data.get('hash')}")
            print(f"文档ID: {data.get('document_id')}")
            print(f"源URI: {data.get('source_uri')}")
            print("\n--- 文本内容 ---")
            print(data.get("text", "无文本内容"))
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"发生错误: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python test_chunk_api.py [id|hash] <chunk_id_or_hash>")
        sys.exit(1)

    query_type = sys.argv[1].lower()
    query_value = sys.argv[2]

    if query_type == "id":
        print(f"通过ID获取chunk: {query_value}")
        test_get_chunk_by_id(query_value)
    elif query_type == "hash":
        print(f"通过哈希获取chunk: {query_value}")
        test_get_chunk_by_hash(query_value)
    else:
        print(f"未知的查询类型: {query_type}，请使用 'id' 或 'hash'")
        sys.exit(1)
