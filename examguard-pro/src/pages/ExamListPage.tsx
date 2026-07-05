import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { examsApi } from '../api/client';

export function ExamListPage() {
  const qc = useQueryClient();
  const [title, setTitle] = useState('');

  const { data: exams = [], isLoading } = useQuery({
    queryKey: ['exams'],
    queryFn: () => examsApi.list().then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: () => examsApi.create({ title, duration_minutes: 60 }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['exams'] });
      setTitle('');
    },
  });

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Exams</h1>

      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (title.trim()) createMutation.mutate();
        }}
      >
        <input
          className="flex-1 px-3 py-2 border border-slate-200 rounded-lg"
          placeholder="New exam title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          disabled={createMutation.isPending}
        >
          Create
        </button>
      </form>

      {isLoading ? (
        <p className="text-slate-500">Loading…</p>
      ) : (
        <ul className="divide-y divide-slate-100 bg-white rounded-xl border border-slate-200">
          {exams.map((exam) => (
            <li key={exam.id} className="p-4">
              <p className="font-medium">{exam.title}</p>
              <p className="text-xs text-slate-500">{exam.duration_minutes ?? 60} min</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
