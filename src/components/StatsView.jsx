import {
  WEEKLY_KM_TARGET,
  WEEKLY_GYM_TARGET,
  challengeDayNumber,
  challengeDaysRemaining,
  TOTAL_CHALLENGE_DAYS,
  weekLabel,
  getWeekCalorieTarget,
} from '../lib/dates.js';
import {
  getWeeklySummaries,
  getDisciplineScore,
  getCurrentStreak,
  getBadges,
  getDayKm,
} from '../lib/calculations.js';

const BADGE_COLORS = {
  gym: 'bg-sky-950 border-sky-800 text-sky-300',
  run: 'bg-emerald-950 border-emerald-800 text-emerald-300',
  perfect: 'bg-yellow-950 border-yellow-700 text-yellow-300',
  streak: 'bg-orange-950 border-orange-800 text-orange-300',
};

export default function StatsView({ data, todayStr }) {
  const allDays = data.days || {};
  const score = getDisciplineScore(data);
  const streak = getCurrentStreak(data);
  const badges = getBadges(data);
  const summaries = getWeeklySummaries(data);
  const dayNum = challengeDayNumber();
  const daysLeft = challengeDaysRemaining();

  // All-time totals
  let totalKm = 0;
  let totalGym = 0;
  let totalDeficitDays = 0;
  let totalLoggedDays = 0;

  for (const [dateStr, d] of Object.entries(allDays)) {
    totalKm += getDayKm(d);
    totalGym += d.gymSessions || 0;
    const { target: dayTarget } = getWeekCalorieTarget(dateStr);
    if (d.calories !== null && d.calories <= dayTarget) totalDeficitDays++;
    if (
      d.calories !== null ||
      (d.runs && d.runs.length > 0) ||
      (d.gymSessions && d.gymSessions > 0)
    )
      totalLoggedDays++;
  }

  const scoreColor =
    score >= 80
      ? 'text-emerald-400'
      : score >= 55
      ? 'text-amber-400'
      : 'text-red-400';

  return (
    <div className="space-y-6">
      {/* Top stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <BigStat
          label="Discipline score"
          value={`${score}%`}
          color={scoreColor}
          sub="overall"
        />
        <BigStat
          label="Current streak"
          value={streak}
          sub={streak === 1 ? 'day' : 'days'}
          icon={streak > 0 ? '🔥' : '💤'}
        />
        <BigStat
          label="Total km run"
          value={`${Math.round(totalKm * 10) / 10}`}
          sub="km"
        />
        <BigStat
          label="Total gym sessions"
          value={totalGym}
          sub="sessions"
        />
      </div>

      {/* Challenge overview */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
        <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-4">
          Challenge Overview
        </h2>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <OverviewItem label="Day" value={`${dayNum} / ${TOTAL_CHALLENGE_DAYS}`} />
          <OverviewItem label="Days remaining" value={daysLeft} />
          <OverviewItem
            label="Deficit compliance"
            value={
              totalLoggedDays > 0
                ? `${Math.round((totalDeficitDays / dayNum) * 100)}%`
                : '—'
            }
          />
        </div>

        {/* Overall progress bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-zinc-500">
            <span>Mar 23</span>
            <span>{Math.round((dayNum / TOTAL_CHALLENGE_DAYS) * 100)}% complete</span>
            <span>Apr 23</span>
          </div>
          <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-emerald-500 rounded-full transition-all duration-500"
              style={{ width: `${(dayNum / TOTAL_CHALLENGE_DAYS) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Badges */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
        <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">
          Badges Earned
        </h2>
        {badges.length === 0 ? (
          <p className="text-sm text-zinc-600">No badges yet. Complete weekly goals to earn them.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {badges.map((badge) => (
              <div
                key={badge.id}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold ${BADGE_COLORS[badge.type]}`}
              >
                <span>{badge.icon}</span>
                <span>{badge.label}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Weekly summaries */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
        <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-4">
          Weekly Summaries
        </h2>
        <div className="space-y-3">
          {summaries.map(({ weekNumber, weekStart, stats, isCurrentWeek, isElapsed }) => (
            <WeeklySummaryRow
              key={weekStart}
              weekNumber={weekNumber}
              weekStart={weekStart}
              stats={stats}
              isCurrentWeek={isCurrentWeek}
              isElapsed={isElapsed}
            />
          ))}
        </div>
      </div>

      {/* Predicted total */}
      {totalKm > 0 && (
        <PredictionCard
          totalKm={totalKm}
          totalGym={totalGym}
          dayNum={dayNum}
          totalDeficitDays={totalDeficitDays}
        />
      )}
    </div>
  );
}

function BigStat({ label, value, sub, color = 'text-white', icon }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 text-center">
      <p className="text-xs text-zinc-500 mb-1">{label}</p>
      <div className="flex items-center justify-center gap-1.5">
        {icon && <span className="text-xl">{icon}</span>}
        <p className={`text-2xl font-bold ${color}`}>{value}</p>
      </div>
      {sub && <p className="text-xs text-zinc-600 mt-0.5">{sub}</p>}
    </div>
  );
}

function OverviewItem({ label, value }) {
  return (
    <div>
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="text-lg font-bold text-white">{value}</p>
    </div>
  );
}

function WeeklySummaryRow({ weekNumber, weekStart, stats, isCurrentWeek, isElapsed }) {
  const kmPct = Math.min((stats.km / WEEKLY_KM_TARGET) * 100, 100);
  const gymPct = Math.min((stats.gymSessions / WEEKLY_GYM_TARGET) * 100, 100);

  const weekStatus = isElapsed
    ? stats.km >= WEEKLY_KM_TARGET && stats.gymSessions >= WEEKLY_GYM_TARGET
      ? 'complete'
      : 'partial'
    : isCurrentWeek
    ? 'current'
    : 'future';

  const statusBadge = {
    complete: 'bg-emerald-950 border-emerald-800 text-emerald-400',
    partial: 'bg-amber-950 border-amber-800 text-amber-400',
    current: 'bg-zinc-800 border-zinc-700 text-zinc-300',
    future: 'bg-zinc-900 border-zinc-800 text-zinc-600',
  };

  return (
    <div
      className={`border rounded-lg p-3 ${
        isCurrentWeek ? 'border-zinc-700 bg-zinc-800/50' : 'border-zinc-800'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-zinc-300">Week {weekNumber}</span>
          <span className="text-xs text-zinc-600">{weekLabel(weekStart)}</span>
          {isCurrentWeek && (
            <span className="text-xs bg-emerald-950 border border-emerald-800 text-emerald-400 px-1.5 py-0.5 rounded">
              current
            </span>
          )}
        </div>
        <div className={`text-xs px-2 py-0.5 rounded border ${statusBadge[weekStatus]}`}>
          {weekStatus === 'complete' && '✓ Complete'}
          {weekStatus === 'partial' && '⚠ Partial'}
          {weekStatus === 'current' && 'In progress'}
          {weekStatus === 'future' && 'Upcoming'}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 text-xs">
        <MiniStat
          label="Running"
          value={`${stats.km}/${WEEKLY_KM_TARGET} km`}
          pct={kmPct}
          barColor={stats.kmDone ? 'bg-emerald-500' : 'bg-amber-500'}
        />
        <MiniStat
          label="Gym"
          value={`${stats.gymSessions}/${WEEKLY_GYM_TARGET} sess`}
          pct={gymPct}
          barColor={stats.gymDone ? 'bg-emerald-500' : 'bg-sky-600'}
        />
        <MiniStat
          label="Deficit days"
          value={`${stats.deficitDays}/7`}
          pct={(stats.deficitDays / 7) * 100}
          barColor={stats.deficitDays >= 6 ? 'bg-emerald-500' : stats.deficitDays >= 4 ? 'bg-amber-500' : 'bg-red-500'}
        />
      </div>
    </div>
  );
}

function MiniStat({ label, value, pct, barColor }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between">
        <span className="text-zinc-500">{label}</span>
        <span className="text-zinc-300 font-medium">{value}</span>
      </div>
      <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function PredictionCard({ totalKm, totalGym, dayNum, totalDeficitDays }) {
  const remaining = TOTAL_CHALLENGE_DAYS - dayNum;
  const kmPerDay = totalKm / dayNum;
  const gymPerDay = totalGym / dayNum;
  const deficitRate = totalDeficitDays / dayNum;

  const projectedKm = Math.round((totalKm + kmPerDay * remaining) * 10) / 10;
  const projectedGym = Math.round(totalGym + gymPerDay * remaining);
  const projectedDeficit = Math.round(totalDeficitDays + deficitRate * remaining);

  // Estimated weekly fat loss at 350 kcal deficit
  const avgDeficitDaysPerWeek = (deficitRate * 7);
  const weeklyKcalDeficit = avgDeficitDaysPerWeek * 350;
  const weeklyFatLossG = Math.round(weeklyKcalDeficit / 7.7); // ~7700 kcal per kg fat

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
      <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">
        Projections (if current pace continues)
      </h2>
      <p className="text-xs text-zinc-600 mb-4">Based on {dayNum} days of data</p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <ProjectStat label="Projected total km" value={`${projectedKm} km`} />
        <ProjectStat label="Projected gym sessions" value={projectedGym} />
        <ProjectStat label="Projected deficit days" value={projectedDeficit} />
        <ProjectStat
          label="Est. weekly fat loss"
          value={`~${weeklyFatLossG}g`}
          sub="at current compliance"
          color={weeklyFatLossG >= 200 ? 'text-emerald-400' : 'text-amber-400'}
        />
      </div>
    </div>
  );
}

function ProjectStat({ label, value, sub, color = 'text-white' }) {
  return (
    <div>
      <p className="text-xs text-zinc-500 mb-0.5">{label}</p>
      <p className={`text-lg font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-zinc-600">{sub}</p>}
    </div>
  );
}
