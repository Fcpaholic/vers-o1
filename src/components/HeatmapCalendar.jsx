import {
  getChallengeWeeks,
  CHALLENGE_START,
  CHALLENGE_END,
  isToday,
  shortLabel,
  getWeekCalorieTarget,
} from '../lib/dates.js';
import { getDayStatus, getDayKm } from '../lib/calculations.js';

const STATUS_STYLES = {
  future: 'bg-zinc-900 border-zinc-800 text-zinc-700',
  empty: 'bg-zinc-800 border-zinc-700 text-zinc-500',
  perfect: 'bg-emerald-600 border-emerald-500 text-white',
  deficit: 'bg-emerald-900 border-emerald-800 text-emerald-300',
  active: 'bg-sky-900 border-sky-800 text-sky-300',
  warning: 'bg-amber-900 border-amber-800 text-amber-300',
  surplus: 'bg-red-900 border-red-800 text-red-300',
  partial: 'bg-zinc-700 border-zinc-600 text-zinc-300',
};

const STATUS_LABEL = {
  future: 'Future',
  empty: 'No data',
  perfect: 'Perfect day',
  deficit: 'Deficit (no activity)',
  active: 'Active (no deficit)',
  warning: 'Over target',
  surplus: 'Over maintenance',
  partial: 'Partial log',
};

const DAY_HEADERS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function DayCell({ dateStr, dayData, allDays }) {
  const status = getDayStatus(dateStr, allDays);
  const style = STATUS_STYLES[status];
  const dayNum = dateStr.slice(8);
  const isCurrentDay = isToday(dateStr);
  const inChallenge = dateStr >= CHALLENGE_START && dateStr <= CHALLENGE_END;

  if (!inChallenge) {
    return <div className="w-full aspect-square rounded-md bg-transparent" />;
  }

  const d = dayData || {};
  const km = getDayKm(d);
  const gym = d.gymSessions || 0;

  return (
    <div
      className={`w-full aspect-square rounded-md border text-xs flex flex-col items-center justify-center gap-0.5 select-none cursor-default transition-all ${style} ${
        isCurrentDay ? 'ring-2 ring-white/40 ring-offset-1 ring-offset-zinc-950' : ''
      }`}
      title={`${shortLabel(dateStr)} — ${STATUS_LABEL[status]}${d.calories !== null ? ` · ${d.calories} kcal` : ''}${km > 0 ? ` · ${km}km` : ''}${gym > 0 ? ` · ${gym}x gym` : ''}`}
    >
      <span className="font-semibold leading-none">{dayNum}</span>
      {/* Mini indicators */}
      <div className="flex gap-0.5 items-center">
        {gym > 0 && <span className="text-[8px] leading-none">🏋</span>}
        {km > 0 && <span className="text-[8px] leading-none">🏃</span>}
      </div>
    </div>
  );
}

export default function HeatmapCalendar({ data, todayStr }) {
  const allDays = data.days || {};
  const weeks = getChallengeWeeks();

  return (
    <div className="space-y-6">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
        <div className="mb-4">
          <h2 className="text-sm font-bold text-zinc-300">Challenge Calendar</h2>
          <p className="text-xs text-zinc-500 mt-0.5">March 23 → April 23, 2026 · 32 days</p>
        </div>

        {/* Day headers */}
        <div className="grid grid-cols-8 gap-1 mb-1">
          <div /> {/* week label column */}
          {DAY_HEADERS.map((h) => (
            <div key={h} className="text-center text-xs text-zinc-600 font-medium">
              {h}
            </div>
          ))}
        </div>

        {/* Week rows */}
        <div className="space-y-1">
          {weeks.map(({ weekNumber, weekStart, days }) => {
            // Pad to 7 days (some weeks may be truncated at start/end)
            const firstDow = new Date(weekStart + 'T12:00:00').getDay();
            // weekStart is always Monday for this challenge
            const cells = days;

            return (
              <div key={weekStart} className="grid grid-cols-8 gap-1 items-center">
                {/* Week label */}
                <div className="text-xs text-zinc-600 text-right pr-1">W{weekNumber}</div>

                {/* Pad cells if week is truncated (only affects last week with Apr 20) */}
                {Array.from({ length: 7 }).map((_, i) => {
                  const dateStr = cells[i];
                  if (!dateStr) {
                    return <div key={i} className="w-full aspect-square" />;
                  }
                  return (
                    <DayCell
                      key={dateStr}
                      dateStr={dateStr}
                      dayData={allDays[dateStr]}
                      allDays={allDays}
                    />
                  );
                })}
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="mt-5 pt-4 border-t border-zinc-800">
          <p className="text-xs text-zinc-600 mb-2">Legend</p>
          <div className="flex flex-wrap gap-3">
            {[
              { status: 'perfect', label: 'Perfect (deficit + activity)' },
              { status: 'deficit', label: 'Deficit only' },
              { status: 'active', label: 'Active, no deficit' },
              { status: 'warning', label: 'Over target' },
              { status: 'surplus', label: 'Surplus' },
              { status: 'empty', label: 'No data' },
            ].map(({ status, label }) => (
              <div key={status} className="flex items-center gap-1.5">
                <div className={`w-3 h-3 rounded-sm border ${STATUS_STYLES[status]}`} />
                <span className="text-xs text-zinc-500">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Per-week summary strip */}
      <WeekSummaryStrip data={data} weeks={weeks} />
    </div>
  );
}

function WeekSummaryStrip({ data, weeks }) {
  const allDays = data.days || {};

  const calcStats = (days) => {
    let km = 0, gym = 0, deficit = 0;
    for (const day of days) {
      const d = allDays[day];
      if (!d) continue;
      km += getDayKm(d);
      gym += d.gymSessions || 0;
      const { target: dayTarget } = getWeekCalorieTarget(day);
      if (d.calories !== null && d.calories <= dayTarget) deficit++;
    }
    return { km: Math.round(km * 10) / 10, gym, deficit };
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {weeks.map(({ weekNumber, weekStart, days }) => {
        const stats = calcStats(days);
        const kmPct = Math.min((stats.km / 25) * 100, 100);
        const gymPct = Math.min((stats.gym / 3) * 100, 100);
        const defPct = Math.min((stats.deficit / 7) * 100, 100);

        return (
          <div key={weekStart} className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 space-y-2">
            <p className="text-xs font-semibold text-zinc-400">Week {weekNumber}</p>
            <div className="space-y-1.5">
              <Strip label={`🏃 ${stats.km}/25 km`} pct={kmPct} color="bg-emerald-600" />
              <Strip label={`🏋 ${stats.gym}/3 sess`} pct={gymPct} color="bg-sky-600" />
              <Strip label={`🥗 ${stats.deficit}/7 days`} pct={defPct} color="bg-violet-600" />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Strip({ label, pct, color }) {
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between items-center">
        <span className="text-xs text-zinc-500">{label}</span>
        <span className="text-xs text-zinc-600">{Math.round(pct)}%</span>
      </div>
      <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
