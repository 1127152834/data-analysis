import { MessageContextSourceCard } from '@/components/chat/message-content-sources';
import { CopyButton } from '@/components/copy-button';
import { RemarkContentContext } from '@/components/remark-content/context';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import { cn } from '@/lib/utils';
import { HoverCardArrow, HoverCardPortal } from '@radix-ui/react-hover-card';
import { cloneElement, useContext, useState } from 'react';
import { isElement, isFragment } from 'react-is';
import * as jsxRuntime from 'react/jsx-runtime';
import { Options as RehypeReactOptions } from 'rehype-react';
import { chunkSchema, getChunkById } from '@/api/chunks';
import { MarkdownRenderer } from '@/components/markdown-renderer';

function dirtyRewrite (some: any, id: string): any {
  if (some == null) return some;
  if (typeof some !== 'object') return some;

  if (isElement(some) || isFragment(some)) {
    const props = some.props as any;
    return cloneElement(some, {
      ...props,
      ...props.id ? { id: `${id}--${props.id}` } : {},
      children: dirtyRewrite(props.children, id),
    });
  }

  if (some instanceof Array) {
    return some.map(item => dirtyRewrite(item, id));
  }

  return some;
}

export const getRehypeReactOptions = ({ portalContainer }: { portalContainer: HTMLElement | undefined }): RehypeReactOptions => ({
  Fragment: (jsxRuntime as any).Fragment,
  jsx: (jsxRuntime as any).jsx,
  jsxs: (jsxRuntime as any).jsxs,
  passNode: true,
  components: {
    section ({ ...props }) {
      // eslint-disable-next-line react-hooks/rules-of-hooks
      const { reactId } = useContext(RemarkContentContext);

      if (!(props as any)['data-footnotes']) return <section {...props} />;
      return (
        <section {...props} className={cn(props.className /*, 'sr-only'*/)}>
          {dirtyRewrite(props.children, reactId)}
        </section>
      );
    },
    a ({ ...props }) {
      // eslint-disable-next-line react-hooks/rules-of-hooks
      const { reactId } = useContext(RemarkContentContext);

      // eslint-disable-next-line react-hooks/rules-of-hooks
      const [link, setLink] = useState<{ title: string, href: string | false, chunkContent?: string }>();
      // eslint-disable-next-line react-hooks/rules-of-hooks
      const [isLoading, setIsLoading] = useState(false);

      // 解析知识块链接，获取知识库ID、文档ID或块ID
      const parseChunkLink = (href: string) => {
        if (href && href.startsWith('knowledge://chunk/')) {
          // 支持两种格式：
          // 1. knowledge://chunk/{kbId}/{documentId}/{chunkId} - 完整格式
          // 3. knowledge://chunk/id/{chunkId} - ID格式
          const parts = href.replace('knowledge://chunk/', '').split('/');
          
          // 检查是否是ID格式
          if (parts.length >= 2 && parts[0] === 'id') {
            return {
              chunkId: parts[1],
              type: 'id_only' as const
            };
          }
        }
        return null;
      };

      // 根据解析的参数获取知识块内容
      const fetchChunkContent = async (href: string) => {
        const parsedLink = parseChunkLink(href);
        if (!parsedLink) return null;

        setIsLoading(true);
        try {
          // 根据不同的链接类型，使用不同的API获取内容
          if (parsedLink.type === 'id_only') {
            // 如果是ID格式，直接使用ID获取
            console.log(`使用ID获取: ${parsedLink.chunkId}`);
            try {
              const chunk = await getChunkById(parsedLink.chunkId);
              if (chunk && chunk.text) {
                return chunk.text;
              }
              console.warn(`通过ID获取内容为空`);
            } catch (error) {
              console.error(`通过ID获取失败: ${error instanceof Error ? error.message : String(error)}`);
              
            }
          }
          
          return "无法找到匹配的知识块内容";
        } catch (error) {
          console.error(`获取知识块内容失败: ${error instanceof Error ? error.message : String(error)}`);
          return "获取内容失败，请检查API路径和权限";
        } finally {
          setIsLoading(false);
        }
      };

      if (!(props as any)['data-footnote-ref']) {
        // 检查是否为知识块链接
        if (props.href?.startsWith('knowledge://chunk/')) {
          return (
            <HoverCard openDelay={0} onOpenChange={async (open) => {
              if (open) {
                setLink({ title: props.children?.toString() || "引用内容", href: props.href });
                const chunkContent = await fetchChunkContent(props.href);
                if (chunkContent) {
                  setLink(prev => prev ? { ...prev, chunkContent } : undefined);
                }
              }
            }}>
              <HoverCardTrigger asChild>
                <a {...props} target="_blank" />
              </HoverCardTrigger>
              <HoverCardPortal container={portalContainer}>
                <HoverCardContent onPointerDownOutside={e => e.preventDefault()} className="p-1 w-[700px] overflow-hidden rounded-lg border text-xs">
                  <HoverCardArrow className="fill-border" />
                  {isLoading ? (
                    <div className="p-2">加载中...</div>
                  ) : (
                    <>
                      <div className="text-sm font-semibold">{link?.title}</div>
                      {link?.chunkContent && (
                        <div className="text-xs mt-2 p-2 bg-muted rounded-md max-h-[550px] overflow-auto">
                          <MarkdownRenderer content={link.chunkContent} />
                        </div>
                      )}
                    </>
                  )}
                </HoverCardContent>
              </HoverCardPortal>
            </HoverCard>
          );
        }
        return <a {...props} target="_blank" />;
      }

      return (
        <HoverCard openDelay={0} onOpenChange={open => {
          if (open) {
            const id = props.href?.replace(/^#/, '');
            if (id) {
              const li = document.getElementById(reactId + '--' + id);
              if (li) {
                const a = li.querySelector(`a:first-child:not([data-footnote-backref])`) as HTMLAnchorElement | null;
                if (a) {
                  // 检查是否为知识块链接
                  if (a.href?.startsWith('knowledge://chunk/')) {
                    setLink({ title: a.textContent ?? a.href, href: a.href });
                    fetchChunkContent(a.href).then(chunkContent => {
                      if (chunkContent) {
                        setLink(prev => prev ? { ...prev, chunkContent } : undefined);
                      }
                    });
                    return;
                  }
                  setLink({ title: a.textContent ?? a.href, href: a.href });
                  return;
                } else {
                  const text = li.querySelector('p')?.childNodes?.item(0)?.textContent;
                  if (text) {
                    setLink({ title: text, href: false });
                    return;
                  }
                }
              }
            }
            setLink(undefined);
          }
        }}>
          <HoverCardTrigger asChild>
            <a
              {...props}
              className={cn(props.className, 'cursor-default')}
              href={undefined}
              onClick={event => {
                event.preventDefault();
                event.stopPropagation();
              }}
            />
          </HoverCardTrigger>
          <HoverCardPortal container={portalContainer}>
            <HoverCardContent onPointerDownOutside={e => e.preventDefault()} className="p-1 w-[500px] overflow-hidden rounded-lg border text-xs">
              <HoverCardArrow className="fill-border" />
              {isLoading ? (
                <div className="p-2">加载中...</div>
              ) : (
                link
                  ? link.href && link.href.startsWith('knowledge://chunk/') && link.chunkContent
                    ? <>
                        <div className="text-sm font-semibold">{link.title}</div>
                        <div className="text-xs mt-2 p-2 bg-muted rounded-md max-h-[400px] overflow-auto">
                          <MarkdownRenderer content={link.chunkContent} />
                        </div>
                      </>
                    : link.href
                      ? <MessageContextSourceCard title={link?.title} href={link?.href} />
                      : link.title
                  : null
              )}
            </HoverCardContent>
          </HoverCardPortal>
        </HoverCard>
      );
    },
    pre ({ children, node, ...props }) {
      // eslint-disable-next-line react-hooks/rules-of-hooks
      const { rawContent } = useContext(RemarkContentContext);

      let isCodeBlock = false;
      let range: [number, number] | undefined;
      const firstChild = node?.children[0];
      if (firstChild?.type === 'element' && firstChild.tagName === 'code') {
        isCodeBlock = true;
        if (firstChild.position && firstChild.position.start.offset && firstChild.position.end.offset) {
          range = [firstChild.position.start.offset, firstChild.position.end.offset];
        }
      }

      return (
        <pre {...props}>
          {children}
          {isCodeBlock && <div className="absolute right-1 top-1 transition-opacity opacity-30 hover:opacity-100" data-role="codeblock-addon">
            {range && <CopyButton text={() => parseCode(rawContent, range)} />}
          </div>}
        </pre>
      );
    },
  },
});

function parseCode (raw: string, range: [number, number]) {
  // Unindent prefix tabs?
  return raw.slice(...range)
    .replace(/^\s*```[^\n]*\n/, '')
    .replace(/\n[^\n]*```$/, '');
}
