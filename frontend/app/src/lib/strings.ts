const cache = new Map<string, string[]>;

/**
 * 提取文本中的模板变量
 * 从文本中提取 ${variable} 格式的模板变量名称
 * 例如："Hello, ${name}!" 将返回 ["name"]
 * 
 * @param text - 包含模板变量的文本字符串
 * @returns 提取出的模板变量名称数组
 */
export function extractTemplates (text: string) {
  // 检查缓存中是否已有结果
  const cached = cache.get(text);
  if (cached) {
    return cached;
  }

  // 状态常量定义
  const STATE_NO = 0;     // 普通文本状态
  const STATE_DOLLAR = 1; // 刚遇到$符号的状态
  const STATE_BRACE = 2;  // 在${...}内部的状态

  const names = new Set<string>();

  let state: 0 | 1 | 2 = STATE_NO;

  let s = -1; // 变量名开始位置
  let i = 0;  // 当前字符位置

  while (i < text.length) {
    const c = text[i];

    switch (c) {
      case '\\': // 处理转义字符
        i += 1;
        break;
      case '$':
        if (state !== STATE_BRACE) {
          state = STATE_DOLLAR;
        }
        break;
      case '{':
        if (state === STATE_DOLLAR) {
          state = STATE_BRACE;
          s = i;
        }
        break;
      case '}':
        if (state === STATE_BRACE) {
          names.add(text.slice(s + 1, i)); // 提取变量名
          state = STATE_NO;
        }
        break;
      default:
        break;
    }

    i += 1;
  }

  // 将结果保存到缓存中
  const result = Array.from(names);
  cache.set(text, result);
  return result;
}
