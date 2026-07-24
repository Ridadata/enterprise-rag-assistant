"use client";

import { FileText, Hash } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { StatusBadge, scoreLevel } from "@/components/shared/status-badge";
import { cn } from "@/lib/utils";
import type { SourceCitation } from "@/lib/types";

const LEVEL_BORDER: Record<string, string> = {
  high: "border-l-success",
  medium: "border-l-warning",
  low: "border-l-destructive",
};

export function CitationCard({ source }: { source: SourceCitation }) {
  const level = scoreLevel(source.score);
  const matchLabel = `${Math.round(source.score * 100)}% match`;

  return (
    <Dialog>
      <DialogTrigger
        nativeButton={false}
        render={
          <Card
            role="button"
            tabIndex={0}
            className={cn(
              "cursor-pointer border-l-2 text-left transition-all duration-200 hover:-translate-y-0.5 hover:shadow-glow focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
              LEVEL_BORDER[level],
            )}
          />
        }
      >
        <CardContent className="space-y-2">
          <div className="flex items-start justify-between gap-2">
            <span className="flex items-center gap-1.5 text-body font-medium text-foreground">
              <FileText className="size-3.5 shrink-0 text-muted-foreground" />
              {source.title}
            </span>
            <StatusBadge level={level} className="shrink-0">
              {matchLabel}
            </StatusBadge>
          </div>
          <p className="line-clamp-3 text-body-s text-muted-foreground">{source.excerpt}</p>
          <p className="flex items-center gap-1 font-mono text-mono-caption text-muted-foreground/70">
            <Hash className="size-3 shrink-0" />
            Section {source.chunk_position}
          </p>
        </CardContent>
      </DialogTrigger>

      <DialogContent className="max-h-[80vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 pr-6">
            <FileText className="size-4 shrink-0 text-muted-foreground" />
            {source.title}
          </DialogTitle>
          <DialogDescription render={<div className="flex flex-wrap items-center gap-2" />}>
            <StatusBadge level={level}>{matchLabel}</StatusBadge>
            <span className="text-body-s text-muted-foreground">Section {source.chunk_position}</span>
          </DialogDescription>
        </DialogHeader>
        <p className="whitespace-pre-wrap text-body text-foreground">{source.excerpt}</p>
        <p className="font-mono text-mono-caption text-muted-foreground/70">{source.chunk_id}</p>
      </DialogContent>
    </Dialog>
  );
}
