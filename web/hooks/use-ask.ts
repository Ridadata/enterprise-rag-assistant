import { useMutation } from "@tanstack/react-query";
import { askQuestion } from "@/lib/api-client";
import type { AskRequest } from "@/lib/types";

export function useAsk() {
  return useMutation({
    mutationFn: (payload: AskRequest) => askQuestion(payload),
  });
}
