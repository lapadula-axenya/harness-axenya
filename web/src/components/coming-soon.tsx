import { Sparkles } from "lucide-react";

export function ComingSoon({
  title,
  body,
  phase,
}: {
  title: string;
  body: string;
  phase: string;
}) {
  return (
    <div className="flex h-full items-center justify-center px-6 py-10">
      <div className="w-full max-w-xl rounded-lg border border-dashed border-border/60 bg-card/30 p-8 text-center">
        <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-foreground/10">
          <Sparkles className="h-5 w-5" />
        </div>
        <h2 className="mt-4 text-base font-semibold">{title}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{body}</p>
        <div className="mt-5 inline-flex items-center gap-2 rounded-full border border-border/60 bg-background/60 px-3 py-1 text-[11px] uppercase tracking-wider text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
          chega em {phase}
        </div>
      </div>
    </div>
  );
}
