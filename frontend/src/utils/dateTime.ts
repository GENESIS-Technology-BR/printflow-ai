export function parseApiDate(
  value: string,
): Date {
  const normalized = value.trim();

  const hasTimezone =
    /(?:Z|[+-]\\d{2}:\\d{2})$/i.test(
      normalized,
    );

  return new Date(
    hasTimezone
      ? normalized
      : `${normalized}Z`,
  );
}
