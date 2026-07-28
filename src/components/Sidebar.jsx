import { NavLink } from 'react-router-dom';

const navItems = [
  { path: '/phase-1', icon: 'person_add', label: 'Onboarding' },
  { path: '/', icon: 'account_circle', label: 'User Profile' },
  { path: '/phase-3', icon: 'savings', label: 'Capital Planning' },
  { path: '/phase-4', icon: 'policy', label: 'Investment Policy' },
  { path: '/phase-5', icon: 'verified', label: 'Product Eligibility' },
  { path: '/phase-6', icon: 'analytics', label: 'Risk & Return' },
  { path: '/phase-7', icon: 'query_stats', label: 'Portfolio Optimization' },
  { path: '/phase-8', icon: 'fact_check', label: 'Review & Confirm' },
];

export default function Sidebar() {
  return (
    <aside className="h-screen w-64 fixed left-0 top-0 bg-surface border-r border-outline-variant flex flex-col py-stack-lg z-50">
      <div className="px-6 mb-10 flex items-center gap-3">
        <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
          <span className="material-symbols-outlined text-white" style={{ fontVariationSettings: "'FILL' 1" }}>account_balance_wallet</span>
        </div>
        <div>
          <h1 className="text-headline-md font-headline-md font-bold text-primary leading-tight">Indigo Wealth</h1>
          <p className="text-caption text-on-surface-variant leading-none">Wealth Management</p>
        </div>
      </div>
      <nav className="flex-1 px-4 space-y-2 overflow-y-auto custom-scrollbar">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                isActive
                  ? 'text-primary font-bold border-r-4 border-primary bg-primary-container/10'
                  : 'text-on-surface-variant hover:bg-surface-container-high hover:text-primary'
              }`
            }
          >
            <span className="material-symbols-outlined">{item.icon}</span>
            <span className="text-body-md font-medium">{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="px-4 mt-auto">
        <button className="w-full py-3 bg-primary text-white rounded-xl font-bold flex items-center justify-center gap-2 hover:opacity-90 transition-opacity">
          <span className="material-symbols-outlined text-sm">support_agent</span>
          Contact Advisor
        </button>
      </div>
    </aside>
  );
}
