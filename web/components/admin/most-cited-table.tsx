import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { CitedDocument } from "@/lib/types";

export function MostCitedTable({ documents }: { documents: CitedDocument[] }) {
  if (documents.length === 0) {
    return <p className="text-body text-muted-foreground">No documents have been cited yet.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Document</TableHead>
          <TableHead className="font-mono text-body-s text-muted-foreground">
            document_id
          </TableHead>
          <TableHead className="text-right">Citations</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {documents.map((doc) => (
          <TableRow key={doc.document_id}>
            <TableCell className="font-medium">{doc.title}</TableCell>
            <TableCell className="font-mono text-body-s text-muted-foreground">
              {doc.document_id}
            </TableCell>
            <TableCell className="text-right font-mono tabular-nums">
              {doc.citation_count}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
