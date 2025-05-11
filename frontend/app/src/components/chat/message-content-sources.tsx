import type { ChatMessageSource } from '@/api/chats';
import { useChatMessageField, useChatMessageStreamContainsState, useChatMessageStreamState } from '@/components/chat/chat-hooks';
import { ChatMessageController } from '@/components/chat/chat-message-controller';
import { AppChatStreamState } from '@/components/chat/chat-stream-state';
import { isNotFinished, parseHref, parseSource } from '@/components/chat/utils';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';
import { LinkIcon, TextSearchIcon } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { getDocument } from '@/api/documents';
import { DocumentViewer } from '@/components/document-viewer';

export function MessageContextSources ({ message }: { message: ChatMessageController | undefined }) {
  const sources = useChatMessageField(message, 'sources');
  const ongoing = useChatMessageStreamState(message);

  const shouldShow = useChatMessageStreamContainsState(message, AppChatStreamState.SEARCH_RELATED_DOCUMENTS);

  if (!shouldShow) {
    return null;
  }

  const uriSet = new Set<string>();
  const reducedContext = sources?.filter(source => {
    if (uriSet.has(source.source_uri)) {
      return false;
    }
    uriSet.add(source.source_uri);
    return true;
  });

  const animation = isNotFinished(ongoing);
  const hasSources = !!sources?.length;
  const empty = sources && sources.length === 0;

  return (
    <>
      <div className={cn('font-normal text-lg flex items-center gap-2 transition-opacity opacity-100', !hasSources && 'opacity-50')}>
        <TextSearchIcon size="1em" />
        Sources
      </div>
      {hasSources && <ScrollArea className="h-max w-full">
        <ul className="flex gap-2 py-4">
          {reducedContext?.map((source, index) => (
            <MessageContextSource key={source.source_uri} context={source} animation={animation} index={index} />
          ))}
        </ul>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>}
      {empty && ongoing?.state !== AppChatStreamState.SEARCH_RELATED_DOCUMENTS && <div className="text-muted-foreground">Empty</div>}
      {empty && ongoing?.state === AppChatStreamState.SEARCH_RELATED_DOCUMENTS && (
        <ul className="flex gap-2 py-4">
          <Skeleton className="rounded" style={{ width: 198, height: 52 }} />
          <Skeleton className="rounded" style={{ width: 198, height: 52 }} />
          <Skeleton className="rounded" style={{ width: 198, height: 52 }} />
        </ul>
      )}
    </>
  );
}

function MessageContextSource ({ index, animation, context }: { index: number, animation: boolean, context: ChatMessageSource }) {
  const source = useMemo(() => {
    return parseSource(context.source_uri);
  }, [context.source_uri]);
  
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [documentContent, setDocumentContent] = useState<{content: string, mime: string} | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const handleOpenDocument = async (e: React.MouseEvent) => {
    // 仅处理非外部链接和非下载链接的情况
    if (!(/^https?:\/\//.test(context.source_uri)) && !context.source_uri.startsWith('uploads/')) {
      e.preventDefault();
      
      if (!documentContent && !isLoading) {
        setIsLoading(true);
        setError(null);
        
        try {
          const doc = await getDocument(context.id);
          setDocumentContent({
            content: doc.content,
            mime: doc.mime_type || 'text/plain'
          });
        } catch (err) {
          console.error('Failed to fetch document:', err);
          setError('无法加载文档内容，请稍后再试。');
        } finally {
          setIsLoading(false);
        }
      }
      
      setIsDialogOpen(true);
    }
  };

  const hrefProps = parseHref(context);

  return (
    <>
    <motion.li
      key={context.id}
      className="bg-card hover:bg-accent transition-colors w-[200px] overflow-hidden rounded-lg border text-xs"
      transition={{ delay: index * 0.1 }}
      initial={animation && { x: '-30%', opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
    >
        <a 
          className="flex flex-col justify-between space-y-1 p-2 max-w-full h-full" 
          href={hrefProps.href}
          download={hrefProps.download}
          target={hrefProps.target}
          onClick={handleOpenDocument}
        >
        <div className="font-normal line-clamp-3 opacity-90">
          {context.name}
        </div>
        <div className="opacity-70 mt-auto mb-0">
          <LinkIcon size="1em" className="inline-flex mr-1" />
          {source}
        </div>
      </a>
    </motion.li>
      
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-[720px] w-full">
          <DialogHeader>
            <DialogTitle>
              {context.name}
            </DialogTitle>
          </DialogHeader>
          <ScrollArea className="h-[80vh]">
            {isLoading && <div className="py-8 text-center">加载中...</div>}
            {error && <div className="py-8 text-center text-red-500">{error}</div>}
            {documentContent && (
              <DocumentViewer 
                content={documentContent.content} 
                mime={documentContent.mime} 
              />
            )}
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </>
  );
}

export function MessageContextSourceCard ({ title, href }: { title?: string, href?: string }) {
  const source = useMemo(() => {
    return parseSource(href);
  }, [href]);

  const isHttp = /^https?:\/\//.test(href ?? '');

  return (
    <a className="flex flex-col justify-between space-y-1 p-2 max-w-full h-full" href={isHttp ? href : 'javascript:(void)'} target="_blank">
      <div className="font-normal line-clamp-3 opacity-90">
        {title}
      </div>
      <div className="opacity-70 mt-auto mb-0">
        <LinkIcon size="1em" className="inline-flex mr-1" />
        {source}
      </div>
    </a>
  );
}
