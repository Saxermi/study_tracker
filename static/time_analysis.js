'use strict';
/* Pure focus-time analysis. No network calls, no third-party libraries.
 * Dates use the user's local timezone for weekdays and clock hours.
 * Each timer focus interval is exact; historical sessions without intervals
 * are estimated across the recorded wall time, excluding recorded breaks.
 */
(function (root, factory) {
  const exported = factory();
  if (typeof module === 'object' && module.exports) module.exports = exported;
  if (root) root.StudyTime = exported;
})(typeof globalThis !== 'undefined' ? globalThis : null, function () {
  const HOUR = 3600000;
  const minute = 60000;
  const milliseconds = value => value ? new Date(value).getTime() : NaN;
  const valid = (start, end) => Number.isFinite(start) && Number.isFinite(end) && end > start;
  const startOfHour = ms => {const d = new Date(ms); d.setMinutes(0, 0, 0); return d.getTime()};
  const mondayKey = ms => {const d = new Date(ms); d.setHours(12, 0, 0, 0); d.setDate(d.getDate() - (d.getDay() + 6) % 7); return [d.getFullYear(), d.getMonth(), d.getDate()].join('-')};

  function subtractBreaks(begin, end, breaks) {
    let spans = [{start: begin, end}];
    for (const b of breaks || []) {
      const bs = milliseconds(b.started_at), be = milliseconds(b.ended_at);
      if (!valid(bs, be)) continue;
      const next = [];
      for (const s of spans) {
        if (be <= s.start || bs >= s.end) { next.push(s); continue; }
        if (bs > s.start) next.push({start:s.start, end:Math.min(bs,s.end)});
        if (be < s.end) next.push({start:Math.max(be,s.start), end:s.end});
      }
      spans = next;
    }
    return spans;
  }

  function focusSpans(session, nowMs = Date.now()) {
    if (!session) return [];
    const exact = Array.isArray(session.focus_intervals) ? session.focus_intervals : [];
    const spans = exact.map(pair => ({start:milliseconds(pair.started_at), end:milliseconds(pair.ended_at), factor:1}))
      .filter(s => valid(s.start, s.end));
    if (session.mode === 'focus' && session.mode_since) {
      const start = milliseconds(session.mode_since);
      if (valid(start, nowMs)) spans.push({start, end:nowMs, factor:1});
    }
    // An active timer can have zero completed intervals. Do NOT infer its
    // elapsed time from first_started_at (it may have been paused for hours).
    if (session.mode || exact.length) return spans;
    const begin = milliseconds(session.started_at), duration = Number(session.duration_seconds) || 0;
    if (!Number.isFinite(begin) || duration <= 0) return [];
    const wallEnd = milliseconds(session.ended_at);
    const end = valid(begin, wallEnd) ? wallEnd : begin + duration*1000;
    const candidates = subtractBreaks(begin, end, session.breaks);
    const available = candidates.reduce((sum, s) => sum + s.end - s.start, 0);
    if (!available) return [{start:begin, end:begin + duration*1000, factor:1, estimated:true}];
    // Legacy timestamps did not record paused intervals. Distribute the
    // measured focus proportionally across non-break time; never invent focus.
    const factor = Math.min(1, duration*1000 / available);
    return candidates.map(s => ({...s, factor, estimated:true}));
  }

  function accumulate(sessions, view='week-average', nowMs=Date.now()) {
    const isRecent = view === '24' || view === '48';
    const isToday = view === 'today';
    const windowHours = isRecent ? Number(view) : 0;
    const hours = isRecent ? windowHours + 1 : isToday ? 24 : 168; // partial first and last clock hours
    const localMidnight = new Date(nowMs); localMidnight.setHours(0,0,0,0);
    const from = isRecent ? nowMs - windowHours*HOUR : isToday ? localMidnight.getTime() : -Infinity;
    const recentStartHour = isRecent ? startOfHour(from) : null;
    const totals = Array(hours).fill(0);
    const samples = Array(hours).fill(0);
    const weeks = new Set();
    let estimated = false;
    for (const session of sessions || []) {
      const segments = focusSpans(session, nowMs);
      for (const span of segments) {
        const start = Math.max(span.start, from), end = Math.min(span.end, nowMs);
        if (!valid(start, end)) continue;
        if (span.estimated) estimated = true;
        for (let cursor = start, guard=0; cursor < end && guard++ < 20000;) {
          const hourStart = startOfHour(cursor);
          const boundary = hourStart + HOUR; // DST transitions handled by local date on next iteration.
          const sliceEnd = Math.min(end, boundary);
          if (sliceEnd <= cursor) break;
          const day = new Date(cursor);
          const index = isRecent ? Math.floor((hourStart - recentStartHour)/HOUR)
            : isToday ? day.getHours() : ((day.getDay()+6)%7)*24 + day.getHours();
          if (index >= 0 && index < totals.length) {
            const sec = (sliceEnd - cursor)/1000 * (span.factor ?? 1);
            totals[index] += sec;
            samples[index] += 1;
          }
          if (!isRecent && !isToday) weeks.add(mondayKey(cursor));
          cursor = sliceEnd;
        }
      }
    }
    const weekCount = Math.max(1, weeks.size);
    const values = view === 'week-average' ? totals.map(t => t/weekCount) : totals;
    return {view, values, totals, totalSeconds:totals.reduce((a,b)=>a+b,0), weekCount, estimated,
      startHour:recentStartHour,
      computedAt:nowMs};
  }
  return {focusSpans, accumulate, mondayKey};
});
