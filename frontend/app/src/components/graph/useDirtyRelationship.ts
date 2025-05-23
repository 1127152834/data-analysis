import { updateRelationship } from '@/api/graph';
import { useRef, useMemo } from 'react';
import { useAction } from './action';
import { type Relationship } from './utils';
import type { JsonFieldInstance } from './components/JsonField';

export function useDirtyRelationship (kbId: number, id: any) {
  const descriptionRef = useRef<HTMLTextAreaElement>(null);
  const weightRef = useRef<HTMLInputElement>(null);
  const metaRef = useRef<JsonFieldInstance | null>(null);

  // 处理带连字符的ID (例如: "60001-600")
  const relationshipId = useMemo(() => {
    const idStr = String(id);
    if (idStr.includes('-')) {
      // 如果是形如"60001-600"的格式，取"-"后面的部分
      return Number(idStr.split('-')[1]);
    }
    return Number(idStr);
  }, [id]);

  const { loading: saving, reset: resetSave, run: save, data: saveReturns, error: saveError, pending: savePending } = useAction(async () => {
    const current = getCurrent();

    if (!current) {
      throw new Error('bad editor state');
    }

    return await updateRelationship(kbId, relationshipId, current);
  });

  const reset = (relationship: Relationship) => {
    if (weightRef.current) {
      weightRef.current.value = String(relationship.weight);
    }
    if (descriptionRef.current) {
      descriptionRef.current.value = relationship.description;
    }
    if (metaRef.current) {
      metaRef.current.value = relationship.meta;
    }
  };

  const getCurrent = () => {
    const weight = weightRef.current?.value;
    const description = descriptionRef.current?.value;
    const meta = metaRef.current?.value;

    if (weight == null || description == null || meta == null) {
      return undefined;
    }
    return {
      weight: parseInt(weight),
      description,
      relationship_desc: description,
      meta,
    };
  };

  return {
    weightRef,
    descriptionRef,
    metaRef,
    reset,
    save,
    saving,
    saveError,
    savePending,
    saveReturns,
    resetSave,
  };
}