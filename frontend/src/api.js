export const api = (path, opts) =>
  fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  }).then(async (r) => {
    const data = await r.json();
    if (!r.ok) throw data;
    return data;
  });

export function cellOf(roster, nurseId, day) {
  return roster?.assignments?.find(
    (a) => a.nurse_id === nurseId && a.day_index === day
  )?.shift;
}

export function cellTaught(rules, nurseId, day, weekday) {
  return (rules || []).some((r) => {
    if (!r.nurse_ids?.includes(nurseId)) return false;
    if (r.kind === "block_cell" && r.day_index === day) return true;
    if (
      ["block_weekday", "prefer_off_weekday", "block_shift_type"].includes(r.kind) &&
      r.weekday === weekday
    ) {
      return true;
    }
    return false;
  });
}
