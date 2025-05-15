'use client';

import { DatabaseConnectionDetail } from './DatabaseConnectionDetail';

export default function DbPageWrapper({ id }: { id: string }) {
  return <DatabaseConnectionDetail connectionId={id} />;
} 