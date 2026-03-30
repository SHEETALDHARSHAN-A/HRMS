import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export interface CandidateTableRow {
  id: string;
  name: string;
  role: string;
  stage: string;
  status: 'shortlisted' | 'in_review' | 'rejected' | 'hired';
  score: number;
  appliedAt: string;
}

interface DataTableProps {
  data: CandidateTableRow[];
}

const statusVariant = (status: CandidateTableRow['status']) => {
  switch (status) {
    case 'hired':
      return 'default';
    case 'shortlisted':
      return 'secondary';
    case 'rejected':
      return 'destructive';
    default:
      return 'outline';
  }
};

const statusLabel = (status: CandidateTableRow['status']) => {
  switch (status) {
    case 'in_review':
      return 'In Review';
    case 'shortlisted':
      return 'Shortlisted';
    case 'rejected':
      return 'Rejected';
    case 'hired':
      return 'Hired';
    default:
      return status;
  }
};

export function DataTable({ data }: DataTableProps) {
  return (
    <div className="px-4 lg:px-6">
      <Card>
        <CardHeader>
          <CardTitle>Recent Candidate Activity</CardTitle>
          <CardDescription>
            Live tracking of the latest candidate movement across interview stages.
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead>
              <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th className="px-3 py-2 font-medium">Candidate</th>
                <th className="px-3 py-2 font-medium">Role</th>
                <th className="px-3 py-2 font-medium">Stage</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Score</th>
                <th className="px-3 py-2 font-medium">Applied</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.id} className="border-b transition-colors hover:bg-muted/40">
                  <td className="px-3 py-2 font-medium">{row.name}</td>
                  <td className="px-3 py-2 text-muted-foreground">{row.role}</td>
                  <td className="px-3 py-2">{row.stage}</td>
                  <td className="px-3 py-2">
                    <Badge variant={statusVariant(row.status)}>{statusLabel(row.status)}</Badge>
                  </td>
                  <td className="px-3 py-2">{row.score}</td>
                  <td className="px-3 py-2 text-muted-foreground">{row.appliedAt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
