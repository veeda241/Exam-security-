export function riskColor(level) {
  switch (level) {
    case 'suspicious':
      return 'bg-red-100 text-red-800 border-red-200';
    case 'review':
      return 'bg-amber-100 text-amber-800 border-amber-200';
    default:
      return 'bg-emerald-100 text-emerald-800 border-emerald-200';
  }
}

export function useRiskColor(level) {
  return riskColor(level);
}
