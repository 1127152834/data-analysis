import DocumentWrapper from './DocumentWrapper';

export default function DocumentViewPage({ params }: { params: { id: string } }) {
  return <DocumentWrapper id={params.id} />;
} 