"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";
import { Clock, Cpu } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge, type StatusLevel } from "@/components/shared/status-badge";
import type { AskResponse } from "@/lib/types";

const CONFIDENCE_LEVEL: Record<string, StatusLevel> = {
  high: "high",
  medium: "medium",
  low: "low",
};

export function AnswerCard({ response }: { response: AskResponse }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
    >
      <Card>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <StatusBadge level={CONFIDENCE_LEVEL[response.confidence] ?? "neutral"}>
              {response.confidence} confidence
            </StatusBadge>
          </div>

          <div className="prose prose-sm dark:prose-invert max-w-none text-body text-foreground prose-p:leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{response.answer}</ReactMarkdown>
          </div>

          {response.limitations ? (
            <p className="text-body-s text-muted-foreground">
              <span className="font-medium text-foreground">Limitations: </span>
              {response.limitations}
            </p>
          ) : null}

          {response.next_step ? (
            <p className="text-body-s text-muted-foreground">
              <span className="font-medium text-foreground">Next step: </span>
              {response.next_step}
            </p>
          ) : null}

          <div className="flex items-center gap-4 border-t border-border pt-3 text-mono-caption font-mono text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="size-3" />
              {response.latency_ms}ms
            </span>
            <span className="flex items-center gap-1">
              <Cpu className="size-3" />
              {response.model_name}
            </span>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
