"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, FileText, Folder, FolderOpen } from "lucide-react";
import type { KnowledgeNode } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  nodes: KnowledgeNode[];
  selectedPath: string;
  onSelect: (path: string) => void;
}

export function KnowledgeTree({ nodes, selectedPath, onSelect }: Props) {
  const byPath = Object.fromEntries(nodes.map((n) => [n.path, n]));
  const roots = nodes.filter((n) => !n.parentPath);

  return (
    <ul className="flex flex-col gap-0.5">
      {roots.map((n) => (
        <Item
          key={n.id}
          node={n}
          byPath={byPath}
          depth={0}
          selectedPath={selectedPath}
          onSelect={onSelect}
        />
      ))}
    </ul>
  );
}

function Item({
  node,
  byPath,
  depth,
  selectedPath,
  onSelect,
}: {
  node: KnowledgeNode;
  byPath: Record<string, KnowledgeNode>;
  depth: number;
  selectedPath: string;
  onSelect: (path: string) => void;
}) {
  const [open, setOpen] = useState(depth < 1);
  const isFolder = node.kind === "folder";
  const isSelected = selectedPath === node.path;

  return (
    <li>
      <button
        onClick={() => {
          if (isFolder) setOpen((o) => !o);
          else onSelect(node.path);
        }}
        className={cn(
          "flex w-full items-center gap-1 rounded px-1.5 py-1 text-left text-[12.5px] transition-colors",
          isSelected
            ? "bg-foreground/10 text-foreground"
            : "text-foreground/80 hover:bg-foreground/5"
        )}
        style={{ paddingLeft: `${depth * 12 + 6}px` }}
      >
        {isFolder ? (
          open ? (
            <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />
          )
        ) : (
          <span className="w-3 shrink-0" />
        )}
        {isFolder ? (
          open ? (
            <FolderOpen className="h-3.5 w-3.5 shrink-0 text-amber-300/80" />
          ) : (
            <Folder className="h-3.5 w-3.5 shrink-0 text-amber-300/80" />
          )
        ) : (
          <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        )}
        <span className="truncate">{node.name}</span>
      </button>
      {isFolder && open && node.children && (
        <ul className="flex flex-col gap-0.5">
          {node.children
            .map((id) => byPath[id])
            .filter(Boolean)
            .map((child) => (
              <Item
                key={child.id}
                node={child}
                byPath={byPath}
                depth={depth + 1}
                selectedPath={selectedPath}
                onSelect={onSelect}
              />
            ))}
        </ul>
      )}
    </li>
  );
}
