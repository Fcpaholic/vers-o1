import {
  challengeDaysRemaining,
  challengeDayNumber,
  TOTAL_CHALLENGE_DAYS,
} from '../lib/dates.js';
import { getCurrentStreak, getDisciplineScore } from '../lib/calculations.js';

export default function AppHeader({ data, todayStr }) {
  const daysRemaining = challengeDaysRemaining();
  const dayNumber = challengeDayNumber();
  const streak = getCurrentStreak(data);
  const score = getDisciplineScore(data);
  const progressPct = Math.round((dayNumber / TOTAL_CHALLENGE_DAYS) * 100);

  const scoreColor =
    score >= 80
      ? 'text-emerald-400'
      : score >= 55
      ? 'text-amber-400'
      : 'text-red-400';

  const scoreBg =
    score >= 80
      ? 'bg-emerald-950 border-emerald-800'
      : score >= 55
      ? 'bg-amber-950 border-amber-800'
      : 'bg-red-950 border-red-800';

  return (
    <header className="border-b border-zinc-800 bg-zinc-950">
      <div className="max-w-6xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between gap-4">
          {/* Left: title */}
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white">
              MIGUEL'S CHALLENGE
            </h1>
            <p className="text-xs text-zinc-500 mt-0.5">
              Mar 23 → Apr 23, 2026
            </p>
          </div>

          {/* Center: challenge progress */}
          <div className="flex-1 max-w-xs hidden sm:block">
            <div className="flex items-center justify-between text-xs text-zinc-400 mb-1.5">
              <span>Day {dayNumber} of {TOTAL_CHALLENGE_DAYS}</span>
              <span className={daysRemaining === 0 ? 'text-emerald-400 font-semibold' : ''}>
                {daysRemaining === 0 ? 'Challenge complete' : `${daysRemaining} days left`}
              </span>
            </div>
            <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>

          {/* Right: streak + score */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-1.5">
              <span className="text-base">{streak > 0 ? '🔥' : '💤'}</span>
              <span className="text-sm font-bold text-white">{streak}</span>
              <span className="text-xs text-zinc-500">streak</span>
            </div>

            <div className={`flex items-center gap-1.5 border rounded-lg px-3 py-1.5 ${scoreBg}`}>
              <span className={`text-sm font-bold ${scoreColor}`}>{score}%</span>
              <span className="text-xs text-zinc-500">discipline</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
