import { useParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { reportsApi } from '../api/client';

export function ReportPage() {
  const { sessionId } = useParams<{ sessionId: string }>();

  const { data: report, refetch, isLoading } = useQuery({
    queryKey: ['report', sessionId],
    queryFn: () => reportsApi.get(sessionId!).then((r) => r.data),
    enabled: !!sessionId,
    refetchInterval: (query) =>
      query.state.data?.status === 'pending' ? 5000 : false,
  });

  const trigger = useMutation({
    mutationFn: () => reportsApi.trigger(sessionId!),
    onSuccess: () => refetch(),
  });

  if (isLoading) return <p className="text-slate-500">Loading report…</p>;

  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold">Session Report</h1>
      <p className="text-sm text-slate-600">Status: {report?.status ?? 'unknown'}</p>

      {report?.signed_url ? (
        <a
          href={report.signed_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg"
        >
          Download PDF
        </a>
      ) : (
        <button
          onClick={() => trigger.mutate()}
          disabled={trigger.isPending}
          className="px-4 py-2 bg-slate-800 text-white rounded-lg"
        >
          {trigger.isPending ? 'Generating…' : 'Generate Report'}
        </button>
      )}
    </div>
  );
}
