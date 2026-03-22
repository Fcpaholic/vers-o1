import {
  CALORIE_MAINTENANCE,
  WEEKLY_KM_TARGET,
  WEEKLY_GYM_TARGET,
  today,
  isPast,
  daysLeftInWeek,
  getChallengeWeeks,
  getAllChallengeDays,
  getWeekStart,
  getWeekDays,
  getWeekCalorieTarget,
} from './dates.js';

// ─── Day helpers ────────────────────────────────────────────────────────────

export const getDayKm = (dayData) =>
  (dayData?.runs ?? []).reduce((s, km) => s + km, 0);

/**
 * Returns calorie status for a given intake against the week-specific target.
 * @param {number|null} calories
 * @param {string} dateStr  YYYY-MM-DD — used to look up the week's target
 */
export const getCalorieStatus = (calories, dateStr) => {
  if (calories === null || calories === undefined) return 'unlogged';
  const target = dateStr ? getWeekCalorieTarget(dateStr).target : 1200;
  if (calories <= target) return 'deficit';
  if (calories < CALORIE_MAINTENANCE) return 'warning';
  return 'surplus';
};

/** Returns one of: future | empty | perfect | deficit | active | warning | surplus | partial */
export const getDayStatus = (dateStr, allDays) => {
  const todayStr = today();
  if (dateStr > todayStr) return 'future';

  const d = allDays[dateStr];
  const hasAny =
    d &&
    (d.calories !== null ||
      (d.gymSessions && d.gymSessions > 0) ||
      (d.runs && d.runs.length > 0));

  if (!d || !hasAny) return 'empty';

  const { target } = getWeekCalorieTarget(dateStr);
  const inDeficit = d.calories !== null && d.calories <= target;
  const surplus = d.calories !== null && d.calories >= CALORIE_MAINTENANCE;
  const overTarget = d.calories !== null && d.calories > target;
  const hasActivity = (d.gymSessions || 0) > 0 || (d.runs && d.runs.length > 0);

  if (inDeficit && hasActivity) return 'perfect';
  if (inDeficit) return 'deficit';
  if (surplus) return 'surplus';
  if (overTarget) return 'warning';
  if (hasActivity) return 'active';
  return 'partial';
};

// ─── Week stats ─────────────────────────────────────────────────────────────

export const getWeekStats = (weekDays, allDays) => {
  let km = 0;
  let gymSessions = 0;
  let deficitDays = 0;
  let loggedDays = 0;

  for (const day of weekDays) {
    const d = allDays[day];
    if (!d) continue;
    km += getDayKm(d);
    gymSessions += d.gymSessions || 0;
    const { target: dayTarget } = getWeekCalorieTarget(day);
    if (d.calories !== null && d.calories <= dayTarget) deficitDays++;
    if (
      d.calories !== null ||
      (d.runs && d.runs.length > 0) ||
      (d.gymSessions && d.gymSessions > 0)
    )
      loggedDays++;
  }

  return {
    km: Math.round(km * 10) / 10,
    gymSessions,
    deficitDays,
    loggedDays,
    kmDone: km >= WEEKLY_KM_TARGET,
    gymDone: gymSessions >= WEEKLY_GYM_TARGET,
  };
};

// ─── Streak ──────────────────────────────────────────────────────────────────

export const getCurrentStreak = (data) => {
  const allDays = data.days || {};
  const todayStr = today();

  const dayActive = (dateStr) => {
    const d = allDays[dateStr];
    return (
      d &&
      (d.calories !== null ||
        (d.gymSessions && d.gymSessions > 0) ||
        (d.runs && d.runs.length > 0))
    );
  };

  let streak = 0;
  const parseLocal = (dateStr) => {
    const [y, m, dd] = dateStr.split('-').map(Number);
    return new Date(y, m - 1, dd, 12, 0, 0);
  };

  let cursor = parseLocal(todayStr);
  if (!dayActive(todayStr)) {
    cursor.setDate(cursor.getDate() - 1);
  }

  while (true) {
    const y = cursor.getFullYear();
    const m = String(cursor.getMonth() + 1).padStart(2, '0');
    const d = String(cursor.getDate()).padStart(2, '0');
    const dateStr = `${y}-${m}-${d}`;

    if (dateStr < '2026-03-22') break;
    if (!dayActive(dateStr)) break;

    streak++;
    cursor.setDate(cursor.getDate() - 1);
  }

  return streak;
};

// ─── Discipline score (0-100) ─────────────────────────────────────────────
// Weights: Running 35%, Gym 30%, Nutrition 35%

export const getDisciplineScore = (data) => {
  const allDays = data.days || {};
  const todayStr = today();

  const challengeDays = getAllChallengeDays().filter((d) => d <= todayStr);
  if (challengeDays.length === 0) return 0;

  const daysElapsed = challengeDays.length;
  const weeksElapsed = daysElapsed / 7;

  let totalKm = 0;
  let totalGym = 0;
  let deficitDays = 0;

  for (const day of challengeDays) {
    const d = allDays[day];
    if (!d) continue;
    totalKm += getDayKm(d);
    totalGym += d.gymSessions || 0;
    const { target: dayTarget } = getWeekCalorieTarget(day);
    if (d.calories !== null && d.calories <= dayTarget) deficitDays++;
  }

  const expectedKm = weeksElapsed * WEEKLY_KM_TARGET;
  const expectedGym = weeksElapsed * WEEKLY_GYM_TARGET;

  const runScore = expectedKm > 0 ? Math.min((totalKm / expectedKm) * 100, 100) : 0;
  const gymScore = expectedGym > 0 ? Math.min((totalGym / expectedGym) * 100, 100) : 0;
  const nutritionScore = (deficitDays / daysElapsed) * 100;

  return Math.round(runScore * 0.35 + gymScore * 0.30 + nutritionScore * 0.35);
};

// ─── Badges ──────────────────────────────────────────────────────────────────

export const getBadges = (data) => {
  const allDays = data.days || {};
  const todayStr = today();
  const badges = [];

  for (const { weekNumber, days } of getChallengeWeeks()) {
    const weekElapsed = days.every((d) => d < todayStr);
    if (!weekElapsed) continue;

    const stats = getWeekStats(days, allDays);
    const loggedDays = days.filter((d) => allDays[d] && allDays[d].calories !== null);
    const allDeficit =
      loggedDays.length === days.length &&
      loggedDays.every((d) => {
        const { target } = getWeekCalorieTarget(d);
        return allDays[d].calories <= target;
      });

    if (stats.gymSessions >= WEEKLY_GYM_TARGET) {
      badges.push({
        id: `gym-w${weekNumber}`,
        label: `Wk ${weekNumber} Iron`,
        icon: '🏋',
        type: 'gym',
      });
    }
    if (stats.km >= WEEKLY_KM_TARGET) {
      badges.push({
        id: `run-w${weekNumber}`,
        label: `Wk ${weekNumber} Road`,
        icon: '🏃',
        type: 'run',
      });
    }
    if (stats.gymSessions >= WEEKLY_GYM_TARGET && stats.km >= WEEKLY_KM_TARGET && allDeficit) {
      badges.push({
        id: `perfect-w${weekNumber}`,
        label: `Wk ${weekNumber} Perfect`,
        icon: '⭐',
        type: 'perfect',
      });
    }
  }

  const streak = getCurrentStreak(data);
  if (streak >= 7) badges.push({ id: 'streak-7', label: '7-Day Streak', icon: '🔥', type: 'streak' });
  if (streak >= 14) badges.push({ id: 'streak-14', label: '14-Day Streak', icon: '💥', type: 'streak' });
  if (streak >= 21) badges.push({ id: 'streak-21', label: '21-Day Streak', icon: '⚡', type: 'streak' });

  return badges;
};

// ─── Motivation message ───────────────────────────────────────────────────────

export const getMotivationMessage = (data, todayStr) => {
  const allDays = data.days || {};
  const d = allDays[todayStr] || {};

  const calories = d.calories ?? null;
  const gymSessions = d.gymSessions || 0;
  const hasRun = (d.runs || []).length > 0;

  const ws = getWeekStart(todayStr);
  const weekDaysToDate = getWeekDays(ws).filter((day) => day <= todayStr);
  const stats = getWeekStats(weekDaysToDate, allDays);

  const { target: calorieTarget, isDietBreak } = getWeekCalorieTarget(todayStr);
  const dLeft = daysLeftInWeek(todayStr);
  const kmLeft = Math.max(0, WEEKLY_KM_TARGET - stats.km);
  const gymLeft = Math.max(0, WEEKLY_GYM_TARGET - stats.gymSessions);

  if (gymLeft > 0 && gymLeft >= dLeft) {
    return {
      type: 'danger',
      msg: `${gymLeft} gym session${gymLeft !== 1 ? 's' : ''} needed in ${dLeft} day${dLeft !== 1 ? 's' : ''}. This is non-negotiable.`,
    };
  }

  if (calories !== null && calories >= CALORIE_MAINTENANCE && !isDietBreak) {
    return {
      type: 'danger',
      msg: "Over maintenance. You failed today's nutrition. No excuses — make tomorrow count.",
    };
  }

  // Diet break week — special messaging
  if (isDietBreak) {
    if (calories !== null && calories > CALORIE_MAINTENANCE) {
      return {
        type: 'danger',
        msg: `Over maintenance on diet break week (${calories} kcal). Stay at exactly ${CALORIE_MAINTENANCE}. This is not a free pass.`,
      };
    }
    if (calories !== null && calories <= CALORIE_MAINTENANCE) {
      return {
        type: 'success',
        msg: `Diet break on track (${calories} kcal). Maintenance locked. Your metabolism is recovering — this pays off in weeks 4-5.`,
      };
    }
    return {
      type: 'info',
      msg: `Diet break week. Target: ${CALORIE_MAINTENANCE} kcal exactly. Science at work — stay the course.`,
    };
  }

  if (calories === null && gymSessions === 0 && !hasRun) {
    return {
      type: 'warning',
      msg: 'Nothing logged today. The day is counting whether you track it or not.',
    };
  }

  const kmPerDayNeeded = dLeft > 0 ? kmLeft / dLeft : kmLeft;
  if (kmLeft > 0 && kmPerDayNeeded > 8) {
    return {
      type: 'warning',
      msg: `${kmLeft.toFixed(1)} km left, ${dLeft} day${dLeft !== 1 ? 's' : ''} remaining. You're falling behind on running.`,
    };
  }

  if (calories !== null && calories > calorieTarget && calories < CALORIE_MAINTENANCE) {
    return {
      type: 'warning',
      msg: `${calories} kcal — over this week's target of ${calorieTarget}. Close is not good enough.`,
    };
  }

  if (kmLeft === 0 && gymLeft === 0 && calories !== null && calories <= calorieTarget) {
    return {
      type: 'success',
      msg: 'Weekly goals complete. Deficit locked. This is what discipline looks like.',
    };
  }

  if (calories !== null && calories <= calorieTarget && gymSessions > 0) {
    return {
      type: 'success',
      msg: "Deficit hit. Gym done. That's the standard — repeat tomorrow.",
    };
  }

  if (calories !== null && calories <= calorieTarget) {
    return {
      type: 'info',
      msg: 'Deficit locked in. Still need the gym session. Get it done.',
    };
  }

  if (gymSessions > 0) {
    return {
      type: 'info',
      msg: 'Gym done. Log your calories. Every number matters.',
    };
  }

  return {
    type: 'info',
    msg: `${kmLeft.toFixed(1)} km and ${gymLeft} gym session${gymLeft !== 1 ? 's' : ''} left this week. No excuses.`,
  };
};

// ─── Weight chart data ────────────────────────────────────────────────────────

export const getWeightChartData = (data) => {
  const allDays = data.days || {};
  return getAllChallengeDays()
    .filter((d) => allDays[d] && allDays[d].weight !== null)
    .map((d) => ({
      date: d,
      label: d.slice(5).replace('-', '/'),
      weight: allDays[d].weight,
    }));
};

// ─── Weekly summaries ─────────────────────────────────────────────────────────

export const getWeeklySummaries = (data) => {
  const allDays = data.days || {};
  const todayStr = today();

  return getChallengeWeeks().map(({ weekNumber, weekStart, days }) => {
    const pastDays = days.filter((d) => d <= todayStr);
    const stats = getWeekStats(pastDays, allDays);
    const isCurrentWeek = days.includes(todayStr);
    const isElapsed = days.every((d) => d < todayStr);

    return { weekNumber, weekStart, days, pastDays, stats, isCurrentWeek, isElapsed };
  });
};
