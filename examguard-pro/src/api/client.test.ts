import { describe, it, expect } from 'vitest';
import { riskColor } from '../hooks/useRiskColor';

describe('useRiskColor', () => {
  it('returns safe color for safe level', () => {
    expect(riskColor('safe')).toContain('emerald');
  });

  it('returns review color for review level', () => {
    expect(riskColor('review')).toContain('amber');
  });

  it('returns suspicious color for suspicious level', () => {
    expect(riskColor('suspicious')).toContain('red');
  });
});
