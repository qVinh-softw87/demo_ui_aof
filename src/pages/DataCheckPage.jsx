export default function DataCheckPage() {
  return (
    <div className="p-margin-desktop flex flex-col gap-gutter max-w-container-max mx-auto w-full custom-scrollbar overflow-y-auto h-[calc(100vh-64px)]">
      {/* Breadcrumbs & Stage Info */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-label-mono font-label-mono text-outline uppercase tracking-wider">Phase 1: Foundation</span>
          <h2 className="text-display-lg font-display-lg text-[48px] text-on-surface mt-1 font-bold leading-tight">Data Integrity Check</h2>
        </div>
        <div className="flex flex-col items-end">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-label-mono font-label-mono text-outline">Completion Confidence</span>
            <span className="text-headline-md font-headline-md text-primary font-bold">65%</span>
          </div>
          <div className="w-48 h-2 bg-surface-container rounded-full overflow-hidden">
            <div className="h-full bg-primary rounded-full" style={{ width: '65%' }}></div>
          </div>
        </div>
      </div>

      {/* Bento Grid Layout */}
      <div className="grid grid-cols-12 gap-gutter mt-4">
        {/* Step Navigation (Horizontal Multi-step) */}
        <div className="col-span-12 bg-white p-6 rounded-xl border border-outline-variant shadow-sm">
          <div className="flex justify-between relative">
            {/* Connector Line */}
            <div className="absolute top-5 left-0 right-0 h-0.5 bg-surface-container z-0"></div>
            <div className="absolute top-5 left-0 h-0.5 bg-primary z-0" style={{ width: '40%' }}></div>
            {/* Steps */}
            {[
              { num: 1, label: 'Demographics', active: true, current: false },
              { num: 2, label: 'Financials', active: true, current: false },
              { num: 3, label: 'Goals', active: false, current: true },
              { num: 4, label: 'Risk Profile', active: false, current: false, disabled: true },
              { num: 5, label: 'Convenience', active: false, current: false, disabled: true },
            ].map((step, i) => (
              <div key={i} className={`relative z-10 flex flex-col items-center gap-2 group cursor-pointer ${step.disabled ? 'opacity-50' : ''}`}>
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                  step.active ? 'bg-primary text-white' : 
                  step.current ? 'bg-white border-2 border-primary text-primary' : 
                  'bg-white border-2 border-outline-variant text-outline'
                }`}>
                  {step.num}
                </div>
                <span className={`text-caption font-caption ${
                  step.active ? 'text-primary font-bold' : 
                  step.current ? 'text-on-surface font-semibold' : 
                  'text-outline'
                }`}>
                  {step.label}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Main Questionnaire Card */}
        <div className="col-span-12 lg:col-span-8 space-y-gutter">
          <section className="bg-white p-8 rounded-xl border border-outline-variant shadow-sm relative overflow-hidden group hover:translate-y-[-2px] transition-all hover:shadow-lg">
            <div className="absolute top-0 right-0 p-4">
              <span className="bg-secondary-container/20 text-secondary text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-widest">In Progress</span>
            </div>
            <h3 className="text-headline-md font-headline-md mb-6 font-bold">Investment Objectives & Goals</h3>
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-label-mono font-label-mono text-outline">Primary Goal</label>
                  <select className="w-full p-3 bg-surface-container-low border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none">
                    <option>Retirement Planning</option>
                    <option>Capital Preservation</option>
                    <option>Legacy & Inheritance</option>
                    <option>Aggressive Growth</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-label-mono font-label-mono text-outline">Time Horizon (Years)</label>
                  <input className="w-full p-3 bg-surface-container-low border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none" type="number" defaultValue="15" />
                </div>
              </div>

              <div className="space-y-4">
                <label className="text-label-mono font-label-mono text-outline">Annual Income vs. Expenses Projection</label>
                
                {/* Warning Section */}
                <div className="p-4 bg-error-container rounded-lg flex items-start gap-3 border border-error/20">
                  <span className="material-symbols-outlined text-error" style={{ fontVariationSettings: "'FILL' 1" }}>warning</span>
                  <div>
                    <h4 className="font-bold text-on-error-container text-sm">Action Required: Negative Savings Gap</h4>
                    <p className="text-caption font-caption text-on-error-container/80 mt-1">
                      Based on current inputs, your projected annual expenses ($145,000) exceed your net annual income ($132,000). To achieve a 15-year retirement goal, a monthly surplus of $2,500 is recommended.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                  <div className="p-4 bg-surface rounded-lg border border-outline-variant/50">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-caption font-caption text-outline">Net Annual Income</span>
                      <span className="text-label-mono font-label-mono text-primary font-bold">$132,000</span>
                    </div>
                    <div className="w-full h-1 bg-surface-container rounded-full">
                      <div className="h-full bg-primary" style={{ width: '80%' }}></div>
                    </div>
                  </div>
                  <div className="p-4 bg-surface rounded-lg border border-outline-variant/50">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-caption font-caption text-outline">Net Annual Expenses</span>
                      <span className="text-label-mono font-label-mono text-error font-bold">$145,000</span>
                    </div>
                    <div className="w-full h-1 bg-surface-container rounded-full">
                      <div className="h-full bg-error" style={{ width: '88%' }}></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-6 border-t border-outline-variant flex justify-between mt-6">
              <button className="px-6 py-2.5 border border-outline text-on-surface rounded-lg hover:bg-surface-container-low transition-colors">Previous</button>
              <button className="px-8 py-2.5 bg-primary text-white rounded-lg font-bold hover:opacity-90 transition-opacity">Save & Continue</button>
            </div>
          </section>

          {/* Profile Visualizer */}
          <div className="grid grid-cols-2 gap-gutter">
            <div className="bg-white p-6 rounded-xl border border-outline-variant shadow-sm h-64 flex flex-col justify-between group hover:translate-y-[-2px] transition-all hover:shadow-lg">
              <div className="flex justify-between items-start">
                <h4 className="text-headline-md font-headline-md text-sm font-bold">Asset Distribution</h4>
                <span className="material-symbols-outlined text-outline">pie_chart</span>
              </div>
              <div className="flex items-center justify-center flex-1">
                <div className="w-32 h-32 rounded-full border-[12px] border-primary-container relative flex items-center justify-center">
                  <div className="absolute inset-0 border-[12px] border-secondary-container rounded-full" style={{ clipPath: 'polygon(50% 50%, 50% 0, 100% 0, 100% 50%)' }}></div>
                  <div className="text-center">
                    <p className="text-label-mono font-label-mono text-[10px] text-outline">TOTAL</p>
                    <p className="text-headline-md font-headline-md text-sm font-bold">$480k</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white p-6 rounded-xl border border-outline-variant shadow-sm h-64 flex flex-col justify-between group hover:translate-y-[-2px] transition-all hover:shadow-lg">
              <div className="flex justify-between items-start">
                <h4 className="text-headline-md font-headline-md text-sm font-bold">Net Worth Growth</h4>
                <span className="material-symbols-outlined text-outline">trending_up</span>
              </div>
              <div className="flex-1 flex items-end gap-2 px-2 pb-2">
                <div className="w-full bg-primary-container/20 h-[30%] rounded-t-sm"></div>
                <div className="w-full bg-primary-container/40 h-[45%] rounded-t-sm"></div>
                <div className="w-full bg-primary-container/60 h-[55%] rounded-t-sm"></div>
                <div className="w-full bg-primary-container/80 h-[75%] rounded-t-sm"></div>
                <div className="w-full bg-primary h-[90%] rounded-t-sm"></div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Sidebar / Insights */}
        <div className="col-span-12 lg:col-span-4 space-y-gutter">
          <div className="bg-inverse-surface text-white p-6 rounded-xl shadow-lg group hover:translate-y-[-2px] transition-all hover:shadow-lg">
            <div className="flex items-center gap-3 mb-6">
              <span className="material-symbols-outlined text-primary-fixed" style={{ fontVariationSettings: "'FILL' 1" }}>verified_user</span>
              <h3 className="text-label-mono font-label-mono font-bold">Identity Verification</h3>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/10">
                <div className="flex items-center gap-3">
                  <span className="material-symbols-outlined text-sm text-primary-fixed">check_circle</span>
                  <span className="text-caption font-caption">KYC Documents</span>
                </div>
                <span className="text-label-mono font-label-mono text-[10px] text-primary-fixed">VERIFIED</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/10">
                <div className="flex items-center gap-3">
                  <span className="material-symbols-outlined text-sm text-outline">pending</span>
                  <span className="text-caption font-caption">Bank Integration</span>
                </div>
                <span className="text-label-mono font-label-mono text-[10px] text-outline">PENDING</span>
              </div>
            </div>
            <div className="mt-6 pt-6 border-t border-white/10">
              <p className="text-caption font-caption text-white/60 mb-4">Complete financial linking to unlock real-time portfolio tracking and tax-loss harvesting.</p>
              <button className="w-full py-2 bg-primary-fixed text-on-primary-fixed rounded-lg font-bold text-sm hover:opacity-90 transition-opacity">Link Institution</button>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-outline-variant shadow-sm group hover:translate-y-[-2px] transition-all hover:shadow-lg">
            <h4 className="text-label-mono font-label-mono text-outline mb-4">Advisor Insights</h4>
            <div className="relative rounded-lg overflow-hidden h-40 mb-4">
              <img className="w-full h-full object-cover" alt="Advisor insight" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCIMe_bLuZVjFK3fZXjQYzIZPtupur1A6DDeykH1w1WDOgBcEVbAUFCVVD8TiQTPsYeevDSYc8kiOC9zxMaDpaVP_PinDLW5rxfxv5VhssXuhASp2JMAODcmNUFCu-abTw8liIBROpUPBCPMWOjuUxIRV1LF3xKNgyARvZ-xFXqW-5zXdo_77bPJyQR1fIZybyHvb2qza2zweoqtmNmvrRUeUeKtYq5gTFkIRhjcxwJhpuN5LvqHqGO"/>
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent flex items-end p-4">
                <p className="text-white text-caption font-caption font-bold">Q4 Portfolio Rebalancing Tips</p>
              </div>
            </div>
            <p className="text-caption font-caption text-on-surface-variant">Your current "Income vs Expense" alert suggests a need for a liquidity buffer. We recommend allocating 6 months of expenses to a High-Yield Savings account before increasing equity exposure.</p>
          </div>

          <div className="bg-surface-container p-6 rounded-xl border border-outline-variant">
            <div className="flex justify-between items-center mb-4">
              <h4 className="text-label-mono font-label-mono font-bold">Expected Risk</h4>
              <span className="text-caption font-caption bg-white px-2 py-0.5 rounded-full text-primary border border-outline-variant">Stage 1/2</span>
            </div>
            <div className="space-y-4">
              <div className="h-2 w-full bg-white rounded-full overflow-hidden flex">
                <div className="h-full bg-green-500" style={{ width: '33%' }}></div>
                <div className="h-full bg-amber-400" style={{ width: '33%' }}></div>
                <div className="h-full bg-red-400" style={{ width: '34%' }}></div>
              </div>
              <div className="flex justify-between text-[10px] font-label-mono text-outline uppercase">
                <span>Conservative</span>
                <span>Moderate</span>
                <span>Aggressive</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
