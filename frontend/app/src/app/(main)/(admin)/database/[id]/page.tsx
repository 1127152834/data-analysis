// 将文件分为服务器部分和客户端部分
// 服务器部分负责获取路由参数并传递给客户端组件

import DbPageWrapper from './DbPageWrapper';

// 这是服务器组件，负责接收路由参数
export const dynamic = 'force-dynamic';

export default function DatabasePage({ params }: { params: { id: string } }) {
  // 从params中提取ID并将其作为prop传递给客户端组件
  return <DbPageWrapper id={params.id} />;
} 