import { getRelationship } from '@/api/graph';
import { Loader } from '@/components/loader';
import { toastError, toastSuccess } from '@/lib/ui-error';
import { cn } from '@/lib/utils';
import { useContext, useEffect, useMemo, useState } from 'react';
import { handleServerRelationship, type Relationship } from '../utils';
import type { IdType } from '../network/Network';
import { useRemote } from '../remote';
import { useDirtyRelationship } from '../useDirtyRelationship';
// import { EditingButton } from './EditingButton';
import { InputField } from './InputField';
import { JsonField } from './JsonField';
import { NetworkContext } from './NetworkContext';
import { TextareaField } from './TextareaField';

const loadRelationship = (kbId: number, id: number) => getRelationship(kbId, id).then(handleServerRelationship);

export function LinkDetails ({
  knowledgeBaseId,
  relationship,
  onClickTarget,
  onUpdate,
  onEnterSubgraph,
}: {
  knowledgeBaseId: number,
  relationship: Relationship,
  onClickTarget?: (target: { type: string, id: IdType }) => void;
  onUpdate?: (newRelationship: Relationship) => void;
  onEnterSubgraph: (type: string, entityId: IdType) => void
}) {
  const network = useContext(NetworkContext);

  const { source, target } = useMemo(() => {
    return {
      source: network.node(relationship.source)!,
      target: network.node(relationship.target)!,
    };
  }, [network, relationship.source, relationship.target]);

  // 处理带连字符的ID (例如: "60001-600")
  const relationshipId = useMemo(() => {
    const id = String(relationship.id);
    if (id.includes('-')) {
      // 如果是形如"60001-600"的格式，取"-"后面的部分
      return Number(id.split('-')[1]);
    }
    return Number(id);
  }, [relationship.id]);

  const [editing, setEditing] = useState(false);
  const latestData = useRemote(relationship, loadRelationship, knowledgeBaseId, relationshipId);
  const dirtyRelationship = useDirtyRelationship(knowledgeBaseId, relationship.id);

  relationship = latestData.data;

  const handleSave = () => {
    void dirtyRelationship.save()
      .then((newRelationshipData) => {
        setEditing(false);
        onUpdate?.(latestData.mutate(prev => Object.assign({}, prev, newRelationshipData)));
        toastSuccess('保存成功');
      })
      .catch((error: any) => {
        toastError('保存关系失败', error);
      });
  };

  const handleReset = () => {
    dirtyRelationship.resetSave();
    dirtyRelationship.reset(relationship);
    setEditing(false);
  };

  useEffect(() => {
    handleReset();
  }, [latestData.data]);
  onUpdate?.(latestData.data);

  const busy = dirtyRelationship.saving || latestData.revalidating;
  const controlsDisabled = !editing || busy;

  return (
    <div className="p-2 space-y-4 h-full overflow-y-auto">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground font-normal ">
          <b>#{relationship.id}</b> 关系
        </span>
        {/*<EditingButton editing={editing} onStartEdit={() => setEditing(true)} onSave={handleSave} onReset={handleReset} busy={busy} onEnterSubgraph={() => onEnterSubgraph('document', relationship.meta.doc_id)} subGraphTitle="Document subgraph" />*/}
      </div>
      {relationship.meta.doc_id && <section>
        <h6 className="text-xs font-bold text-accent-foreground mb-1">文档 URI</h6>
        <p className="block w-full text-xs text-accent-foreground">
          <a className="underline" href={relationship.meta.source_uri} target="_blank">{relationship.meta.source_uri}</a>
        </p>
      </section>}
      <TextareaField label="描述" ref={dirtyRelationship.descriptionRef} defaultValue={relationship.description} disabled={controlsDisabled} />
      <InputField label="权重" ref={dirtyRelationship.weightRef} defaultValue={relationship.weight} disabled={controlsDisabled} min={0} step={1} type="number" />
      <JsonField label="元数据" ref={dirtyRelationship.metaRef} defaultValue={relationship.meta} disabled={controlsDisabled} />
      <section className="space-y-2">
        <h6 className="text-xs font-bold text-accent-foreground mb-1">源实体</h6>
        <div className={cn('text-sm cursor-pointer transition-all hover:text-primary', editing && 'pointer-events-none opacity-50')} onClick={() => !editing && onClickTarget?.({ type: 'node', id: source.id })}>{source.name} <span className="text-muted-foreground">#{source.id}</span></div>
        <p className={cn('text-xs text-accent-foreground max-h-40 overflow-y-auto border p-1 bg-card rounded', editing && 'opacity-50')}>{source.description}</p>
      </section>
      <section className="space-y-2">
        <h6 className="text-xs font-bold text-accent-foreground mb-1">目标实体</h6>
        <div className={cn('text-sm cursor-pointer transition-all hover:text-primary', editing && 'pointer-events-none opacity-50')} onClick={() => !editing && onClickTarget?.({ type: 'node', id: target.id })}>{target.name} <span className="text-muted-foreground">#{target.id}</span></div>
        <p className={cn('text-xs text-accent-foreground max-h-40 overflow-y-auto border p-1 bg-card rounded', editing && 'opacity-50')}>{target.description}</p>
      </section>
      <Loader loading={latestData.revalidating}>
        正在加载关系 #{relationship.id}
      </Loader>
    </div>
  );
}