import { useState, useCallback } from 'react';
import { getData } from './lib/storage.js';
import { today } from './lib/dates.js';
import AppHeader from './components/AppHeader.jsx';
import MotivationBanner from './components/MotivationBanner.jsx';
import Dashboard from './components/Dashboard.jsx';
import HeatmapCalendar from './components/HeatmapCalendar.jsx';
import WeightTracker from './components/WeightTracker.jsx';
import StatsView from './components/StatsView.jsx';

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
  const todayStr = today();

  const showToast = useCallback((msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 2500);
  }, []);

  const refresh = useCallback(() => {
    setData(getData());
  }, []);

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <AppHeader data={data} todayStr={todayStr} />
      <MotivationBanner data={data} todayStr={todayStr} />

      <div className="border-b border-zinc-800 sticky top-0 z-10 bg-zinc-950/95 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4">
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
