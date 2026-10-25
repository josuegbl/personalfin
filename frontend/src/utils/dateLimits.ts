// The app has no meaningful historical data before this month; Dashboard and
// Forecast/Balance must not navigate further back than this.
export const MIN_YEAR = 2026;
export const MIN_MONTH = 1;

export function isAtOrBeforeMinMonth(year: number, month: number): boolean {
  return year < MIN_YEAR || (year === MIN_YEAR && month <= MIN_MONTH);
}
