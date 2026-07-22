"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { SearchBox } from "@/components/search/search-box";
import { FilterBar, type FilterValues } from "@/components/search/filter-bar";
import { AnswerCard } from "@/components/search/answer-card";
import { AnswerSkeleton } from "@/components/search/answer-skeleton";
import { CitationCard } from "@/components/search/citation-card";
import { ErrorState } from "@/components/shared/error-state";
import { useAsk } from "@/hooks/use-ask";
import { useDisplayName } from "@/hooks/use-display-name";
import type { ApiResult, AskResponse } from "@/lib/types";

const SUGGESTED_PROMPTS = [
  "How do I troubleshoot VPN after MFA?",
  "What systems require MFA?",
  "What caused the Kubernetes pod crash loop?",
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
    const id = crypto.randomUUID();
    setTurns((prev) => [...prev, { id, question }]);

    const activeFilters = Object.fromEntries(
      Object.entries(filters).filter(([, value]) => Boolean(value)),
    );
    const result = await mutateAsync({ question, user_id: displayName, filters: activeFilters });

    setTurns((prev) => prev.map((turn) => (turn.id === id ? { ...turn, result } : turn)));
  }

  const hasTurns = turns.length > 0;

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col p-6">
      {!hasTurns ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-6">
          <div className="text-center">
            <h2 className="text-display-l text-foreground">Ask Nexus anything</h2>
            <p className="mt-2 text-body-l text-muted-foreground">
              Grounded answers from your enterprise knowledge base, with citations.
            </p>
          </div>
          <div className="w-full max-w-xl">
            <SearchBox onSubmit={handleAsk} pending={isPending} large />
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            {SUGGESTED_PROMPTS.map((prompt) => (
              <Button
                key={prompt}
                variant="outline"
                size="sm"
                onClick={() => handleAsk(prompt)}
                disabled={isPending}
              >
                {prompt}
              </Button>
            ))}
          </div>
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
            {turns.map((turn) => (
              <div key={turn.id} className="space-y-3">
                <div className="flex justify-end">
                  <div className="max-w-md rounded-xl bg-primary px-4 py-2 text-body text-primary-foreground">
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
                  </>
                ) : (
                  <ErrorState result={turn.result} />
                )}
              </div>
            ))}
          </div>

          <div className="pt-2">
            <SearchBox onSubmit={handleAsk} pending={isPending} placeholder="Ask a follow-up..." />
          </div>
        </>
      )}
    </div>
  );
}
