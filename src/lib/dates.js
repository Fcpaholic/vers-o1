export const CHALLENGE_START = '2026-03-23';
export const CHALLENGE_END = '2026-04-23';
export const CALORIE_MAINTENANCE = 1500;
export const WEEKLY_KM_TARGET = 25;
export const WEEKLY_GYM_TARGET = 3;
export const TOTAL_CHALLENGE_DAYS = 32;

/**
 * Miguel's Challenge — adaptive calorie protocol (Mar 23 → Apr 23).
 * Maintenance: 1500 kcal. Week 4 = diet break to prevent metabolic adaptation.
 * Based on MATADOR Protocol (Byrne et al. 2017).
 */
export const CALORIE_SCHEDULE = [
  {
    weekNumber: 1,
    target: 1200,
    deficit: 300,
    label: 'Moderate Start',
    rationale: 'Conservative 300 kcal deficit while your body adapts to the training load. Keeps energy high for gym + running. ~270g fat/week.',
  },
  {
    weekNumber: 2,
    target: 1200,
    deficit: 300,
    label: 'Stay the Course',
    rationale: 'Same deficit maintained. Body now adapted to training rhythm. Consistent execution compounds. ~270g fat/week.',
  },
  {
    weekNumber: 3,
    target: 1150,
    deficit: 350,
    label: 'Deeper Deficit',
    rationale: 'Training momentum established — increase deficit slightly. Still safe with your activity level. ~320g fat/week.',
  },
  {
    weekNumber: 4,
    target: 1500,
    deficit: 0,
    label: 'Maintenance Reset',
    rationale: 'MATADOR Protocol: 1 week at maintenance restores leptin, T3 thyroid, and metabolic rate after 3 weeks of restriction. Not a cheat week — stay exactly at 1500 kcal. This makes Week 5 far more effective.',
    isDietBreak: true,
  },
  {
    weekNumber: 5,
    target: 1200,
    deficit: 300,
    label: 'Final Push',
    rationale: 'Post-reset metabolism is fully responsive again. Back to 300 kcal deficit for a strong finish. The diet break makes this week\'s deficit significantly more effective. ~270g fat/week.',
  },
];

/**
 * Returns the calorie schedule entry for any date in the challenge.
 * Falls back to Week 5 targets for any dates beyond week 5.
 */
export const getWeekCalorieTarget = (dateStr) => {
  // We need getChallengeWeeks but it's defined below — inline the logic
  const start = CHALLENGE_START;
  const ws_date = parseDate_local(dateStr);
  const ws_start = parseDate_local(start);
  const dayDiff = Math.floor((ws_date - ws_start) / (1000 * 60 * 60 * 24));
  const weekNumber = Math.floor(dayDiff / 7) + 1;
  return (
    CALORIE_SCHEDULE.find((s) => s.weekNumber === weekNumber) ||
    CALORIE_SCHEDULE[CALORIE_SCHEDULE.length - 1]
  );
};

// Internal helper (avoids hoisting issue with parseDate exported below)
const parseDate_local = (dateStr) => {
  const [y, m, d] = dateStr.split('-').map(Number);
  return new Date(y, m - 1, d, 12, 0, 0);
};

/** Returns YYYY-MM-DD for a Date object (uses local date) */
export const formatDate = (date) => {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
};

/** Returns today as YYYY-MM-DD */
export const today = () => formatDate(new Date());

/** Parses a YYYY-MM-DD string to a local Date at noon (avoids DST issues) */
export const parseDate = (dateStr) => {
  const [y, m, d] = dateStr.split('-').map(Number);
  return new Date(y, m - 1, d, 12, 0, 0);
};

/** Returns the Monday of the week containing the given date string */
export const getWeekStart = (dateStr) => {
  const date = parseDate(dateStr);
  const day = date.getDay(); // 0=Sun, 1=Mon
  const diff = day === 0 ? -6 : 1 - day;
  date.setDate(date.getDate() + diff);
  return formatDate(date);
};

/** Returns array of 7 YYYY-MM-DD strings starting from the given Monday */
export const getWeekDays = (weekStartStr) => {
  const days = [];
  const start = parseDate(weekStartStr);
  for (let i = 0; i < 7; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    days.push(formatDate(d));
  }
  return days;
};

/** Returns all days from challenge start to end */
export const getAllChallengeDays = () => {
  const days = [];
  const start = parseDate(CHALLENGE_START);
  const end = parseDate(CHALLENGE_END);
  const cur = new Date(start);
  while (cur <= end) {
    days.push(formatDate(cur));
    cur.setDate(cur.getDate() + 1);
  }
  return days;
};

/**
 * Returns challenge weeks as array of { weekStart, days, weekNumber }
 * Challenge starts March 17 (Tuesday).
 */
export const getChallengeWeeks = () => {
  const weeks = [];
  let weekStart = CHALLENGE_START;
  let weekNum = 1;

  while (weekStart <= CHALLENGE_END) {
    const allDays = getWeekDays(weekStart);
    const days = allDays.filter((d) => d >= CHALLENGE_START && d <= CHALLENGE_END);
    weeks.push({ weekStart, days, weekNumber: weekNum });

    const next = parseDate(weekStart);
    next.setDate(next.getDate() + 7);
    weekStart = formatDate(next);
    weekNum++;
  }

  return weeks;
};

/** How many full days remain in the current week (including today) */
export const daysLeftInWeek = (dateStr) => {
  const weekStart = getWeekStart(dateStr);
  const days = getWeekDays(weekStart);
  const idx = days.indexOf(dateStr);
  return idx === -1 ? 1 : 7 - idx;
};

/** Days remaining in the challenge from today */
export const challengeDaysRemaining = () => {
  const end = parseDate(CHALLENGE_END);
  const now = new Date();
  now.setHours(12, 0, 0, 0);
  const diff = Math.ceil((end - now) / (1000 * 60 * 60 * 24));
  return Math.max(0, diff);
};

/** Which day of the challenge is today (1-36) */
export const challengeDayNumber = () => {
  const start = parseDate(CHALLENGE_START);
  const now = new Date();
  now.setHours(12, 0, 0, 0);
  const diff = Math.floor((now - start) / (1000 * 60 * 60 * 24)) + 1;
  return Math.min(Math.max(1, diff), TOTAL_CHALLENGE_DAYS);
};

export const isToday = (dateStr) => dateStr === today();
export const isPast = (dateStr) => dateStr < today();
export const isFuture = (dateStr) => dateStr > today();
export const isInChallenge = (dateStr) =>
  dateStr >= CHALLENGE_START && dateStr <= CHALLENGE_END;

/** Short human-readable date label like "Mon Mar 16" */
export const shortLabel = (dateStr) => {
  const d = parseDate(dateStr);
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
};

/** Week label like "Week 1 · Mar 16–22" */
export const weekLabel = (weekStart) => {
  const days = getWeekDays(weekStart);
  const first = parseDate(days[0]);
  const last = parseDate(days[6]);
  const startLabel = first.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  const endLabel = last.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  return `${startLabel} – ${endLabel}`;
};
