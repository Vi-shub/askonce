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
