"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ content }: { content: string }) {
  return (
    <div className="prose-xenia">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (props) => (
            <h1
              className="mb-3 mt-1 text-xl font-semibold tracking-tight text-foreground"
              {...props}
            />
          ),
          h2: (props) => (
            <h2
              className="mb-2 mt-5 text-base font-semibold tracking-tight text-foreground"
              {...props}
            />
          ),
          h3: (props) => (
            <h3
              className="mb-1.5 mt-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground"
              {...props}
            />
          ),
          p: (props) => (
            <p className="mb-3 text-sm leading-relaxed text-foreground/85" {...props} />
          ),
          ul: (props) => (
            <ul className="mb-3 ml-5 list-disc space-y-1 text-sm text-foreground/85" {...props} />
          ),
          ol: (props) => (
            <ol className="mb-3 ml-5 list-decimal space-y-1 text-sm text-foreground/85" {...props} />
          ),
          li: (props) => <li className="leading-relaxed" {...props} />,
          blockquote: (props) => (
            <blockquote
              className="my-3 border-l-2 border-foreground/30 bg-card/40 px-3 py-2 text-sm italic text-foreground/80"
              {...props}
            />
          ),
          a: (props) => (
            <a
              className="text-foreground underline decoration-foreground/30 underline-offset-2 hover:decoration-foreground"
              {...props}
            />
          ),
          code: ({
            inline,
            ...props
          }: React.HTMLAttributes<HTMLElement> & { inline?: boolean }) =>
            inline ? (
              <code
                className="rounded bg-muted/60 px-1 py-0.5 font-mono text-[12px] text-foreground"
                {...props}
              />
            ) : (
              <code className="font-mono text-[12px]" {...props} />
            ),
          pre: (props) => (
            <pre
              className="mb-3 overflow-x-auto rounded-md border border-border/40 bg-background/60 p-3 text-[12px] leading-relaxed"
              {...props}
            />
          ),
          table: (props) => (
            <div className="mb-3 overflow-hidden rounded-md border border-border/50">
              <table className="w-full text-sm" {...props} />
            </div>
          ),
          thead: (props) => (
            <thead className="bg-card/60 text-[10px] uppercase tracking-wider text-muted-foreground" {...props} />
          ),
          th: (props) => (
            <th className="px-3 py-2 text-left font-medium" {...props} />
          ),
          td: (props) => (
            <td className="border-t border-border/30 px-3 py-2 text-foreground/85" {...props} />
          ),
          hr: () => <hr className="my-4 border-border/40" />,
          input: ({ checked, ...rest }) => (
            <input
              type="checkbox"
              disabled
              checked={!!checked}
              className="mr-1.5 align-middle accent-foreground"
              {...rest}
            />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
