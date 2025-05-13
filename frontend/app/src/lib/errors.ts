import { ZodError } from 'zod';

export function getErrorMessage (e: unknown) {
  if (!e) {
    return '未知错误';
  }
  if (typeof e !== 'object') {
    return String(e);
  }

  if (e instanceof ZodError) {
    return `JSON验证失败: ${e.format()._errors.join(', ')}.`;
  }

  return ((e as any).message) || ((e as any).name) || String(e);
}

export function getErrorName (error: unknown) {
  if (!error) {
    return 'UNKNOWN';
  }
  if (typeof error === 'object') {
    return error.constructor.name;
  }
  return String(error);
}
