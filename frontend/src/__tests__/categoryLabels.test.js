import { describe, it, expect } from 'vitest';
import { getCategoryLabel, CATEGORY_LABELS } from '../constants/categoryLabels';

describe('getCategoryLabel', () => {
  it('returns Korean label for known category', () => {
    expect(getCategoryLabel('delivery_delay')).toBe('배송 지연');
    expect(getCategoryLabel('poor_quality')).toBe('품질 불량');
    expect(getCategoryLabel('wrong_item')).toBe('오배송');
  });

  it('returns original name for unknown category', () => {
    expect(getCategoryLabel('unknown_thing')).toBe('unknown_thing');
  });

  it('handles all defined categories', () => {
    for (const [key, value] of Object.entries(CATEGORY_LABELS)) {
      expect(getCategoryLabel(key)).toBe(value);
    }
  });

  it('returns empty string for empty input', () => {
    expect(getCategoryLabel('')).toBe('');
  });
});
