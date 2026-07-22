import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function StatCardSkeleton() {
  return (
    <Card>
      <CardContent>
        <Skeleton className="h-3 w-20" />
        <Skeleton className="mt-3 h-7 w-16" />
      </CardContent>
    </Card>
  );
}
