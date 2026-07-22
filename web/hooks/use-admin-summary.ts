import { useQuery } from "@tanstack/react-query";
import { getAdminSummary } from "@/lib/api-client";

export function useAdminSummary() {
  return useQuery({
    queryKey: ["admin-summary"],
    queryFn: getAdminSummary,
    refetchInterval: 30_000,
  });
}
