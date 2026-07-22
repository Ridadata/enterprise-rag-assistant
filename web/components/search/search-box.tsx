"use client";

import { useState } from "react";
import { ArrowUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface SearchBoxProps {
  onSubmit: (question: string) => void;
  pending?: boolean;
  large?: boolean;
  placeholder?: string;
}

export function SearchBox({ onSubmit, pending, large, placeholder }: SearchBoxProps) {
  const [value, setValue] = useState("");

  function submit() {
    const trimmed = value.trim();
    if (trimmed.length < 3 || pending) return;
    onSubmit(trimmed);
    setValue("");
  }

  return (
    <div
      className={cn(
        "flex items-end gap-2 rounded-xl border border-input bg-card p-2 shadow-sm transition-shadow focus-within:ring-3 focus-within:ring-ring/50",
        large && "p-3",
      )}
    >
      <Textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        placeholder={placeholder ?? "Ask about IT, data engineering, incidents, policies, or runbooks..."}
        rows={large ? 2 : 1}
        className={cn(
          "min-h-0 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0",
          large ? "text-body-l" : "text-body",
        )}
      />
      <Button
        size="icon"
        disabled={value.trim().length < 3 || pending}
        onClick={submit}
        aria-label="Submit question"
      >
        <ArrowUp className="size-4" />
      </Button>
    </div>
  );
}
