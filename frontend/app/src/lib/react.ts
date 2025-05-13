import type { ChangeEvent, SyntheticEvent } from 'react';

/**
 * 以编程方式触发输入元素的input事件
 * 
 * 此函数用于模拟用户在输入框中键入内容的行为，
 * 会同时更新元素值并触发input事件
 * 
 * @param inputElement - 要触发事件的输入元素实例
 * @param Element - 输入元素的构造函数类型(HTMLTextAreaElement或HTMLInputElement)
 * @param value - 要设置的新值
 */
export function trigger<T extends typeof HTMLTextAreaElement | typeof HTMLInputElement> (inputElement: InstanceType<T>, Element: T, value: string) {
  // https://stackoverflow.com/questions/23892547/what-is-the-best-way-to-trigger-change-or-input-event-in-react-js
  const set = Object.getOwnPropertyDescriptor(Element.prototype, 'value')!.set!;
  set.call(inputElement, value);
  const event = new Event('input', { bubbles: true });
  inputElement.dispatchEvent(event);
}

/**
 * 检查值是否为React合成事件
 * 
 * 通过检查事件特有的方法来判断对象是否为合成事件
 * 
 * @param value - 要检查的值
 * @returns 如果值是React合成事件则返回true，否则返回false
 */
export function isEvent (value: unknown): value is SyntheticEvent {
  if (!value) {
    return false;
  }

  if (typeof value !== 'object') {
    return false;
  }

  for (const name of ['stopPropagation', 'preventDefault', 'type']) {
    if (!(name in value)) {
      return false;
    }
  }

  return true;
}

/**
 * 检查值是否为React的change事件
 * 
 * @param value - 要检查的值
 * @returns 如果值是React的change事件则返回true，否则返回false
 */
export function isChangeEvent (value: unknown): value is ChangeEvent {
  return isEvent(value) && value.type === 'change';
}
