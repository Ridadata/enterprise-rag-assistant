import { useQuery } from "@tanstack/react-query";
import { getCorpusSummary } from "@/lib/api-client";

export function useCorpusSummary() {
  return useQuery({
    queryKey: ["corpus-summary"],
    queryFn: getCorpusSummary,
  });
}
