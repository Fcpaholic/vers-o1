import { useState, useCallback, useEffect, useRef } from 'react';
import { getData, saveData } from './lib/storage.js';
import { today } from './lib/dates.js';
import {
  getSyncToken, getSyncGistId, clearSyncToken,
  findOrCreateGist, fetchFromGist, pushToGist,
} from './lib/gistSync.js';
import AppHeader from './components/AppHeader.jsx';
import MotivationBanner from './components/MotivationBanner.jsx';
import Dashboard from './components/Dashboard.jsx';
import HeatmapCalendar from './components/HeatmapCalendar.jsx';
import WeightTracker from './components/WeightTracker.jsx';
import StatsView from './components/StatsView.jsx';
import SyncSetup from './components/SyncSetup.jsx';

const TABS = [
  { id: 'dashboard', label: '⚡ Dashboard' },
  { id: 'calendar', label: '📅 Calendar' },
  { id: 'weight', label: '⚖ Weight' },
  { id: 'stats', label: '📊 Stats' },
];

export default function App() {
  const [data, setData] = useState(() => getData());
  const [activeTab, setActiveTab] = useState('dashboard');
  const [toast, setToast] = useState(null);
  const [syncStatus, setSyncStatus] = useState('idle');
  const [showSetup, setShowSetup] = useState(false);
  const [hasToken, setHasToken] = useState(() => !!getSyncToken());
  const [ghUser, setGhUser] = useState('');
  const pushTimer = useRef(null);
  const lastEditAt = useRef(0);
  const todayStr = today();

  const showToast = useCallback((msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 2500);
  }, []);

  // Pull from gist → overwrite local. Skip if user edited in last 5s (avoid clobbering in-progress input).
  const pullNow = useCallback(async () => {
    const token = getSyncToken();
    if (!token) return;
    if (Date.now() - lastEditAt.current < 5000) return;
    setSyncStatus('syncing');
    try {
      const gistId = await findOrCreateGist(token);
      const remote = await fetchFromGist(token, gistId);
      if (remote) {
        saveData(remote);
        setData(remote);
      }
      setSyncStatus('synced');
    } catch {
      setSyncStatus('error');
    }
  }, []);

  // On mount: fetch username + pull data, or show setup
  useEffect(() => {
    const token = getSyncToken();
    if (token) {
      fetch('https://api.github.com/user', { headers: { Authorization: `token ${token}` } })
        .then((r) => r.json()).then((u) => { if (u.login) setGhUser(u.login); }).catch(() => {});
      pullNow();
    } else {
      setShowSetup(true);
    }
  }, []);

  // Browser notification reminder — request permission once, then remind at 8 PM if nothing logged
  useEffect(() => {
    if (!('Notification' in window)) return;
    if (Notification.permission === 'default') {
      Notification.requestPermission();
    }

    const checkAndNotify = () => {
      const now = new Date();
      const hour = now.getHours();
      if (hour < 20) return; // only after 8 PM

      const d = getData().days?.[todayStr];
      const hasLog = d && (d.calories !== null || (d.gymSessions || 0) > 0 || (d.runs || []).length > 0);
      if (hasLog) return;

      const lastNotified = localStorage.getItem('last_notified');
      if (lastNotified === todayStr) return;

      if (Notification.permission === 'granted') {
        new Notification("Miguel's Challenge", {
          body: "Nothing logged today. The day is counting — open the app and log it.",
          icon: '/favicon.ico',
        });
        localStorage.setItem('last_notified', todayStr);
      }
    };

    const interval = setInterval(checkAndNotify, 60 * 1000); // check every minute
    checkAndNotify(); // check immediately on mount
    return () => clearInterval(interval);
  }, [todayStr]);

  // Pull every 30s and when tab becomes visible
  useEffect(() => {
    if (!hasToken) return;
    const interval = setInterval(pullNow, 30000);
    const onVisible = () => { if (document.visibilityState === 'visible') pullNow(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => { clearInterval(interval); document.removeEventListener('visibilitychange', onVisible); };
  }, [hasToken, pullNow]);

  // Called after every local data change — push to gist
  const refresh = useCallback(() => {
    lastEditAt.current = Date.now();
    setData(getData());
    const token = getSyncToken();
    const gistId = getSyncGistId();
    if (!token || !gistId) return;
    clearTimeout(pushTimer.current);
    setSyncStatus('syncing');
    pushTimer.current = setTimeout(async () => {
      try {
        await pushToGist(token, gistId, getData());
        setSyncStatus('synced');
      } catch {
        setSyncStatus('error');
      }
    }, 800);
  }, []);

  // After setup: PULL from gist (don't push — would overwrite other device's data)
  const handleSyncComplete = useCallback((token, gistId) => {
    setShowSetup(false);
    if (token && gistId) {
      setHasToken(true);
      fetch('https://api.github.com/user', { headers: { Authorization: `token ${token}` } })
        .then((r) => r.json()).then((u) => { if (u.login) setGhUser(u.login); }).catch(() => {});
      showToast('Sync enabled!', 'success');
      pullNow();
    }
  }, [showToast, pullNow]);

  const handleDisconnectSync = useCallback(() => {
    clearSyncToken();
    setHasToken(false);
    setSyncStatus('idle');
    showToast('Sync disconnected.', 'warn');
  }, [showToast]);

  const syncColor = syncStatus === 'synced' ? 'text-emerald-400'
    : syncStatus === 'error' ? 'text-red-400'
    : 'text-zinc-400';

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {showSetup && <SyncSetup onComplete={handleSyncComplete} />}

      <AppHeader data={data} todayStr={todayStr} />
      <MotivationBanner data={data} todayStr={todayStr} />

      <div className="border-b border-zinc-800 sticky top-0 z-10 bg-zinc-950/95 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 flex items-center justify-between">
          <nav className="flex">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-5 py-3 text-sm font-medium transition-all border-b-2 -mb-px ${
                  activeTab === tab.id
                    ? 'border-emerald-500 text-emerald-400'
                    : 'border-transparent text-zinc-400 hover:text-zinc-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-2 text-xs pr-1">
            {hasToken ? (
              <>
                <span className={`${syncColor} ${syncStatus === 'syncing' ? 'animate-spin' : ''}`}>
                  {syncStatus === 'syncing' ? '↻' : syncStatus === 'synced' ? '✓' : '⚠'}
                </span>
                <span className={`${syncColor} hidden sm:inline`}>
                  {syncStatus === 'syncing' ? 'Syncing…' : syncStatus === 'synced' ? 'Synced' : 'Sync error'}
                </span>
                {syncStatus === 'error' ? (
                  <button onClick={() => { handleDisconnectSync(); setShowSetup(true); }} className="text-red-400 hover:text-red-300 ml-1 underline text-xs">
                    Fix
                  </button>
                ) : (
                  <button onClick={handleDisconnectSync} className="text-zinc-600 hover:text-zinc-400 ml-1 hidden sm:inline">✕</button>
                )}
              </>
            ) : (
              <button onClick={() => setShowSetup(true)} className="text-zinc-500 hover:text-emerald-400 transition-colors">
                🔄 Sync
              </button>
            )}
          </div>
        </div>
      </div>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {activeTab === 'dashboard' && <Dashboard data={data} onRefresh={refresh} todayStr={todayStr} showToast={showToast} />}
        {activeTab === 'calendar' && <HeatmapCalendar data={data} todayStr={todayStr} />}
        {activeTab === 'weight' && <WeightTracker data={data} onRefresh={refresh} todayStr={todayStr} showToast={showToast} />}
        {activeTab === 'stats' && <StatsView data={data} todayStr={todayStr} />}
      </main>

      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 px-5 py-3 rounded-lg text-sm font-semibold shadow-xl animate-slide-in ${
          toast.type === 'success' ? 'bg-emerald-600 text-white'
          : toast.type === 'danger' ? 'bg-red-600 text-white'
          : 'bg-amber-600 text-white'
        }`}>
          {toast.msg}
        </div>
      )}
    </div>
  );
}
