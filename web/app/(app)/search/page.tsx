"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { KeyRound, ShieldCheck, Boxes } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SearchBox } from "@/components/search/search-box";
import { FilterBar, type FilterValues } from "@/components/search/filter-bar";
import { AnswerCard } from "@/components/search/answer-card";
import { AnswerSkeleton } from "@/components/search/answer-skeleton";
import { CitationCard } from "@/components/search/citation-card";
import { ErrorState } from "@/components/shared/error-state";
import { useAsk } from "@/hooks/use-ask";
import { useDisplayName } from "@/hooks/use-display-name";
import type { ApiResult, AskResponse, ConversationTurn } from "@/lib/types";

const SUGGESTED_PROMPTS = [
  {
    question: "How do I troubleshoot VPN after MFA?",
    category: "IT Support",
    icon: ShieldCheck,
  },
  {
    question: "What systems require MFA?",
    category: "Policy",
    icon: KeyRound,
  },
  {
    question: "What caused the Kubernetes pod crash loop?",
    category: "Incident",
    icon: Boxes,
  },
];

interface Turn {
  id: string;
  question: string;
  result?: ApiResult<AskResponse>;
}

export default function SearchPage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [filters, setFilters] = useState<FilterValues>({});
  const { mutateAsync, isPending } = useAsk();
  const [displayName] = useDisplayName();

  async function handleAsk(question: string) {
    // Prior successful turns, sent on every request so follow-ups can be rewritten
    // against them server-side (see generation/query_rewriter.py) -- there's no
    // server-side conversation store, so the client is the source of truth for history.
    const history = turns.reduce<ConversationTurn[]>((acc, turn) => {
      if (turn.result?.ok) {
        acc.push({ question: turn.question, answer: turn.result.data.answer });
      }
      return acc;
    }, []);

    const id = crypto.randomUUID();
    setTurns((prev) => [...prev, { id, question }]);

    const activeFilters = Object.fromEntries(
      Object.entries(filters).filter(([, value]) => Boolean(value)),
    );
    const result = await mutateAsync({
      question,
      user_id: displayName,
      filters: activeFilters,
      history,
    });

    setTurns((prev) => prev.map((turn) => (turn.id === id ? { ...turn, result } : turn)));
  }

  const hasTurns = turns.length > 0;

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col p-6">
      {!hasTurns ? (
        <div className="relative flex flex-1 flex-col items-center justify-center gap-6">
          <div
            aria-hidden
            className="pointer-events-none absolute top-1/2 left-1/2 size-72 -translate-x-1/2 -translate-y-1/2 rounded-full bg-gradient-brand opacity-15 blur-3xl"
          />
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="relative text-center"
          >
            <h2 className="text-display-l text-foreground">
              Ask <span className="text-gradient-brand">Nexus</span> anything
            </h2>
            <p className="mt-2 text-body-l text-muted-foreground">
              Grounded answers from your enterprise knowledge base, with citations.
            </p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.05, ease: "easeOut" }}
            className="relative w-full max-w-xl"
          >
            <SearchBox onSubmit={handleAsk} pending={isPending} large />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.1, ease: "easeOut" }}
            className="relative grid w-full max-w-xl grid-cols-1 gap-2 sm:grid-cols-3"
          >
            {SUGGESTED_PROMPTS.map(({ question, category, icon: Icon }) => (
              <button
                key={question}
                type="button"
                onClick={() => handleAsk(question)}
                disabled={isPending}
                className="group flex flex-col items-start gap-2 rounded-lg border border-border bg-card p-3 text-left shadow-card outline-none transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-glow focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50"
              >
                <span className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary transition-colors group-hover:bg-primary/15">
                  <Icon className="size-3.5" />
                </span>
                <span className="text-label uppercase tracking-wide text-muted-foreground">
                  {category}
                </span>
                <span className="text-body-s text-foreground">{question}</span>
              </button>
            ))}
          </motion.div>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between pb-4">
            <FilterBar values={filters} onChange={setFilters} />
            <Button variant="ghost" size="sm" onClick={() => setTurns([])}>
              New search
            </Button>
          </div>

          <div className="flex-1 space-y-6 overflow-y-auto pb-4">
            {turns.map((turn, index) => {
              const isLastTurn = index === turns.length - 1;
              return (
                <motion.div
                  key={turn.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25, ease: "easeOut" }}
                  className="space-y-3"
                >
                  <div className="flex justify-end">
                    <div className="max-w-md rounded-xl bg-gradient-brand px-4 py-2 text-body text-white shadow-card">
                      {turn.question}
                    </div>
                  </div>

                  {!turn.result ? (
                    <AnswerSkeleton />
                  ) : turn.result.ok ? (
                    <>
                      <AnswerCard response={turn.result.data} />
                      {turn.result.data.sources.length > 0 ? (
                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                          {turn.result.data.sources.map((source) => (
                            <CitationCard key={source.chunk_id} source={source} />
                          ))}
                        </div>
                      ) : null}
                      {isLastTurn && !isPending && turn.result.data.follow_up_questions.length > 0 ? (
                        <div className="flex flex-wrap gap-2 pt-1">
                          {turn.result.data.follow_up_questions.map((followUp) => (
                            <button
                              key={followUp}
                              type="button"
                              onClick={() => handleAsk(followUp)}
                              className="rounded-full border border-border bg-card px-3 py-1.5 text-body-s text-foreground outline-none transition-colors hover:border-primary/40 hover:bg-primary/5 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                            >
                              {followUp}
                            </button>
                          ))}
                        </div>
                      ) : null}
                    </>
                  ) : (
                    <ErrorState result={turn.result} />
                  )}
                </motion.div>
              );
            })}
          </div>

          <div className="pt-2">
            <SearchBox onSubmit={handleAsk} pending={isPending} placeholder="Ask a follow-up..." />
          </div>
        </>
      )}
    </div>
  );
}
