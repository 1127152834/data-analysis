import { getEntity } from '@/api/graph';
import { Loader } from '@/components/loader';
import { toastError, toastSuccess } from '@/lib/ui-error';
import { cn } from '@/lib/utils';
import { useContext, useEffect, useMemo, useState } from 'react';
import type { IdType } from '../network/Network';
import { useRemote } from '../remote';
import { useDirtyEntity } from '../useDirtyEntity';
import { type Entity, handleServerEntity } from '../utils';
import { EditingButton } from './EditingButton';
import { InputField } from './InputField';
import { JsonField } from './JsonField';
import { NetworkContext } from './NetworkContext';
import { TextareaField } from './TextareaField';

const loadEntity = (kbId: number, id: number) => getEntity(kbId, id).then(handleServerEntity);

export function NodeDetails ({
  knowledgeBaseId,
  entity,
  onClickTarget,
  onUpdate,
  onEnterSubgraph,
}: {
  knowledgeBaseId: number,
  entity: Entity,
  onClickTarget?: (target: { type: string, id: IdType }) => void;
  onUpdate?: (newData: Entity) => void
  onEnterSubgraph: (type: string, entityId: IdType) => void
}) {
  const [editing, setEditing] = useState(false);
  const network = useContext(NetworkContext);

  const neighbors = useMemo(() => {
    return Array.from(network.nodeNeighborhoods(entity.id) ?? []).map(id => network.node(id)!);
  }, [network, entity.id]);

  // 处理带连字符的ID (例如: "60001-600")
  const entityId = useMemo(() => {
    const id = String(entity.id);
    if (id.includes('-')) {
      // 如果是形如"60001-600"的格式，取"-"后面的部分
      return Number(id.split('-')[1]);
    }
    return Number(id);
  }, [entity.id]);

  console.log('entity', entity);

  console.log('knowledgeBaseId', knowledgeBaseId);

  const latestData = useRemote(entity, loadEntity, knowledgeBaseId, entityId);
  const dirtyEntity = useDirtyEntity(knowledgeBaseId, entity.id);

  // dirty set
  // entity = latestData.data;

  console.log('entity', entity);

  const handleSave = () => {
    void dirtyEntity.save()
      .then((newEntityData) => {
        setEditing(false);
        onUpdate?.(latestData.mutate(prev => Object.assign({}, prev, newEntityData)));
        toastSuccess('保存成功');
      })
      .catch((error: any) => {
        toastError('保存实体失败', error);
      });
  };

  const handleReset = () => {
    dirtyEntity.resetSave();
    dirtyEntity.reset(entity);
    setEditing(false);
  };

  useEffect(() => {
    handleReset();
    onUpdate?.(latestData.data);
  }, [latestData.data]);

  const busy = dirtyEntity.saving || latestData.revalidating;
  const controlsDisabled = !editing || busy;
  return (
    <div className="p-4 space-y-4 h-full overflow-y-auto">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground font-normal ">
          <b>#{entity.id}</b> {entity.entity_type} 实体
        </span>
        <EditingButton onEnterSubgraph={() => onEnterSubgraph('entity', entity.id)} editing={editing} onStartEdit={() => setEditing(true)} onSave={handleSave} onReset={handleReset} busy={busy} />
      </div>
      {entity.synopsis_info?.topic && <section>
        <h6 className="text-xs font-bold text-accent-foreground mb-1">摘要主题</h6>
        <p className="block w-full text-xs text-accent-foreground">
          {entity.synopsis_info.topic}
        </p>
      </section>}
      <InputField label="名称" ref={dirtyEntity.nameRef} defaultValue={entity.name} disabled={controlsDisabled} />
      <TextareaField label="描述" ref={dirtyEntity.descriptionRef} defaultValue={entity.description} disabled={controlsDisabled} />
      <JsonField label="元数据" ref={dirtyEntity.metaRef} defaultValue={entity.meta} disabled={controlsDisabled} />
      <section>
        <h6 className="text-xs font-bold text-accent-foreground mb-1">相邻实体</h6>
        <ul className={cn('w-full max-h-40 overflow-y-auto bg-card rounded border transition-opacity', editing && 'opacity-50 pointer-events-none')}>
          {neighbors.map(entity => (
            <li
              key={entity.id}
              className={'text-xs p-1 border-b last-of-type:border-b-0 cursor-pointer hover:text-primary hover:bg-primary/10 transition-colors'}
              onClick={() => {
                if (!editing) {
                  onClickTarget?.({ type: 'node', id: entity.id });
                }
              }}
            >
              {entity.name}
              <span className="text-muted-foreground">
                {' '}#{entity.id}
              </span>
            </li>
          ))}
        </ul>
      </section>
      <Loader loading={latestData.revalidating}>
        正在加载实体 #{entity.id}
      </Loader>
    </div>
  );
}