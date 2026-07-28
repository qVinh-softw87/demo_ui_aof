export default function ReviewConfirmPage() {
  return (
    <div className="max-w-container-max mx-auto space-y-gutter p-stack-lg w-full">
      {/* Hero Section: Ready to Execute */}
      <section className="bg-surface-container-lowest rounded-xl border border-outline-variant p-10 shadow-sm relative overflow-hidden">
        <div className="absolute top-0 right-0 w-1/3 h-full opacity-10 pointer-events-none"></div>
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
          <div className="space-y-4 max-w-2xl">
            <div className="inline-flex items-center px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full border border-emerald-100">
              <span className="material-symbols-outlined text-[16px] mr-1.5" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
              <span className="text-label-mono text-xs font-bold">All risk criteria met</span>
            </div>
            <h2 className="text-display-lg font-display-lg text-primary tracking-tight font-bold text-[32px] md:text-[48px]">Sẵn sàng thực hiện</h2>
            <p className="text-body-lg text-on-surface-variant">Your tailored investment strategy has passed all internal compliance and risk checks. You are one step away from deploying your capital with data-backed confidence.</p>
          </div>
          <div className="bg-surface rounded-2xl border border-outline-variant p-6 w-full md:w-64 flex flex-col items-center text-center shadow-lg hover:shadow-xl transition-shadow">
            <span className="text-label-mono text-on-surface-variant mb-2 font-bold">FINAL RISK SCORE</span>
            <div className="relative w-32 h-32 flex items-center justify-center group cursor-pointer">
              <svg className="w-full h-full transform -rotate-90">
                <circle className="text-surface-container-high" cx="64" cy="64" fill="transparent" r="58" stroke="currentColor" strokeWidth="8"></circle>
                <circle className="text-secondary transition-all duration-300 group-hover:stroke-[10px]" cx="64" cy="64" fill="transparent" r="58" stroke="currentColor" strokeDasharray="364" strokeDashoffset="91" strokeWidth="8"></circle>
              </svg>
              <span className="absolute text-headline-md font-bold text-on-surface text-[24px]">7.5<span className="text-sm font-normal text-on-surface-variant">/10</span></span>
            </div>
            <p className="mt-4 font-bold text-secondary text-body-md uppercase tracking-wider">Growth Focused</p>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-gutter">
        {/* Rationale Section */}
        <div className="lg:col-span-1 space-y-gutter">
          <section className="bg-white rounded-xl border border-outline-variant p-6 h-full hover:-translate-y-1 hover:shadow-md transition-all duration-300">
            <div className="flex items-center gap-2 mb-6">
              <span className="material-symbols-outlined text-primary">lightbulb</span>
              <h3 className="text-headline-md font-headline-md text-on-surface font-bold">Why choose this portfolio?</h3>
            </div>
            <ul className="space-y-6">
              <li className="flex gap-4">
                <div className="w-10 h-10 rounded-full bg-primary-container/10 flex-shrink-0 flex items-center justify-center text-primary">
                  <span className="material-symbols-outlined text-xl">hub</span>
                </div>
                <div>
                  <h4 className="font-bold text-on-surface">Optimal Diversification</h4>
                  <p className="text-body-md text-on-surface-variant">Reduced exposure to single-market volatility through a calculated mix of domestic equities and global tech leaders.</p>
                </div>
              </li>
              <li className="flex gap-4">
                <div className="w-10 h-10 rounded-full bg-primary-container/10 flex-shrink-0 flex items-center justify-center text-primary">
                  <span className="material-symbols-outlined text-xl">trending_up</span>
                </div>
                <div>
                  <h4 className="font-bold text-on-surface">Goal Attainment</h4>
                  <p className="text-body-md text-on-surface-variant">A 84% statistical probability of achieving your 5-year capital appreciation target based on Monte Carlo simulations.</p>
                </div>
              </li>
              <li className="flex gap-4">
                <div className="w-10 h-10 rounded-full bg-primary-container/10 flex-shrink-0 flex items-center justify-center text-primary">
                  <span className="material-symbols-outlined text-xl">security</span>
                </div>
                <div>
                  <h4 className="font-bold text-on-surface">Downside Protection</h4>
                  <p className="text-body-md text-on-surface-variant">20% allocation to Gold and high-yield Bonds serves as a strategic buffer against inflation and market downturns.</p>
                </div>
              </li>
            </ul>
          </section>
        </div>
        
        {/* Portfolio Structure Section */}
        <div className="lg:col-span-2">
          <section className="bg-white rounded-xl border border-outline-variant overflow-hidden flex flex-col h-full hover:-translate-y-1 hover:shadow-md transition-all duration-300">
            <div className="p-6 border-b border-outline-variant flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">pie_chart</span>
                <h3 className="text-headline-md font-headline-md text-on-surface font-bold">Portfolio Structure</h3>
              </div>
              <span className="text-label-mono text-on-surface-variant font-bold text-[10px] md:text-sm">LAST UPDATED: TODAY, 10:45 AM</span>
            </div>
            <div className="flex-1 p-6 grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
              {/* Chart Placeholder */}
              <div className="relative group cursor-pointer flex justify-center items-center h-48 md:h-64 bg-surface-container rounded-lg">
                <div className="flex flex-col items-center">
                  <span className="material-symbols-outlined text-outline text-4xl mb-2">donut_large</span>
                  <span className="text-on-surface-variant text-sm font-bold">Donut Chart Visualization</span>
                </div>
                <div className="absolute inset-0 bg-primary/5 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center rounded-lg">
                  <span className="bg-white px-4 py-2 rounded-full shadow-lg text-sm font-bold text-primary">Click for deep analysis</span>
                </div>
              </div>
              
              {/* Asset List */}
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-surface flex flex-col sm:flex-row items-start sm:items-center justify-between border border-outline-variant gap-2 sm:gap-0 hover:border-primary transition-colors cursor-pointer">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-primary"></div>
                    <span className="font-bold">VN30 ETF</span>
                  </div>
                  <div className="flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-end">
                    <span className="text-on-surface-variant text-sm">Domestic Growth</span>
                    <span className="font-label-mono text-primary font-bold">50.0%</span>
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-surface flex flex-col sm:flex-row items-start sm:items-center justify-between border border-outline-variant gap-2 sm:gap-0 hover:border-primary transition-colors cursor-pointer">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-secondary"></div>
                    <span className="font-bold">Global Tech ETF</span>
                  </div>
                  <div className="flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-end">
                    <span className="text-on-surface-variant text-sm">Intl Innovation</span>
                    <span className="font-label-mono text-primary font-bold">30.0%</span>
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-surface flex flex-col sm:flex-row items-start sm:items-center justify-between border border-outline-variant gap-2 sm:gap-0 hover:border-primary transition-colors cursor-pointer">
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-tertiary"></div>
                    <span className="font-bold">Gold & Bonds</span>
                  </div>
                  <div className="flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-end">
                    <span className="text-on-surface-variant text-sm">Safe Haven</span>
                    <span className="font-label-mono text-primary font-bold">20.0%</span>
                  </div>
                </div>
                <button className="w-full mt-4 text-primary font-bold text-body-md hover:underline flex items-center justify-center gap-2 py-2">
                  <span>View Full Asset Breakdown</span>
                  <span className="material-symbols-outlined text-sm">open_in_new</span>
                </button>
              </div>
            </div>
          </section>
        </div>
      </div>

      {/* Compliance Warning & Action */}
      <section className="space-y-6">
        <div className="bg-error-container/30 border border-error/20 rounded-xl p-6 flex gap-4">
          <span className="material-symbols-outlined text-error" style={{ fontVariationSettings: "'FILL' 1" }}>warning</span>
          <div className="space-y-2">
            <h4 className="font-bold text-on-error-container">Legal Disclaimer & Compliance</h4>
            <p className="text-body-md text-on-surface-variant leading-relaxed text-sm md:text-base">
              By proceeding, you acknowledge that Indigo Wealth provides automated investment guidance based on your profile. Manual execution is required on your primary brokerage platform. Past performance is not indicative of future results. Please ensure you have read the <a className="text-primary font-bold hover:underline" href="#">Full Disclosure Agreement</a> before confirming.
            </p>
          </div>
        </div>
        
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 p-8 bg-surface-container-highest rounded-2xl border-2 border-primary/10">
          <div className="flex items-center gap-4 w-full md:w-auto">
            <div className="flex -space-x-3">
              <div className="w-10 h-10 rounded-full border-2 border-white bg-surface-container flex items-center justify-center z-10">
                <span className="material-symbols-outlined text-on-surface-variant text-[16px]">person</span>
              </div>
              <div className="w-10 h-10 rounded-full border-2 border-white bg-surface-container flex items-center justify-center">
                <span className="material-symbols-outlined text-on-surface-variant text-[16px]">admin_panel_settings</span>
              </div>
            </div>
            <p className="text-body-md text-on-surface-variant text-sm">Validated by our <strong className="text-on-surface">Advisory Board</strong> and <strong className="text-on-surface">Compliance AI</strong>.</p>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
            <button className="flex-1 md:flex-none px-8 py-4 bg-white border border-outline-variant hover:bg-surface-container-low text-on-surface font-bold rounded-xl transition-all shadow-sm">
              Save as Draft
            </button>
            <button className="flex-1 md:flex-none px-10 py-4 bg-primary hover:bg-primary/90 text-white font-bold rounded-xl shadow-lg shadow-primary/20 transition-all flex items-center justify-center gap-3 group">
              <span>Confirm & View Execution Guide</span>
              <span className="material-symbols-outlined transition-transform group-hover:translate-x-1">arrow_forward</span>
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
