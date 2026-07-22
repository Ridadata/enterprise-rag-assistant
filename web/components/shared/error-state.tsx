import { AlertTriangle, KeyRound, WifiOff } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { ApiResult } from "@/lib/types";

/** Renders the same 401/503/network-error branches the app already special-cases
 * end-to-end, from the FastAPI status codes through the Next.js proxy. */
export function ErrorState<T>({ result }: { result: Extract<ApiResult<T>, { ok: false }> }) {
  if (result.status === 401) {
    return (
      <Alert variant="destructive">
        <KeyRound />
        <AlertTitle>Invalid or missing API key</AlertTitle>
        <AlertDescription>Check NEXUS_API_KEY in the server environment.</AlertDescription>
      </Alert>
    );
  }

  if (result.status === 503) {
    return (
      <Alert variant="destructive">
        <WifiOff />
        <AlertTitle>Backend unavailable</AlertTitle>
        <AlertDescription>The database isn&apos;t reachable right now.</AlertDescription>
      </Alert>
    );
  }

  if (result.status === 502) {
    return (
      <Alert variant="destructive">
        <WifiOff />
        <AlertTitle>Can&apos;t reach Nexus</AlertTitle>
        <AlertDescription>The API server doesn&apos;t appear to be running.</AlertDescription>
      </Alert>
    );
  }

  return (
    <Alert variant="destructive">
      <AlertTriangle />
      <AlertTitle>Something went wrong</AlertTitle>
      <AlertDescription>{result.message}</AlertDescription>
    </Alert>
  );
}
