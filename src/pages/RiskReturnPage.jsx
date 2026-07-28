export default function RiskReturnPage() {
  return (
    <div className="max-w-container-max mx-auto space-y-gutter p-stack-lg w-full">
      {/* Bento Grid Dashboard Section */}
      <div className="grid grid-cols-12 gap-gutter">
        {/* Primary Metric Cards */}
        <div className="col-span-12 lg:col-span-3 space-y-gutter">
          {/* Volatility Card */}
          <div className="elevation-l1 rounded-xl p-stack-md bg-white border border-outline-variant shadow-sm hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-2">
              <span className="text-label-mono font-label-mono text-on-surface-variant font-bold">VOLATILITY (σ)</span>
              <span className="material-symbols-outlined text-primary">show_chart</span>
            </div>
            <div className="text-[32px] font-bold text-primary">12.4%</div>
            <div className="flex items-center mt-2 text-green-600 font-medium">
              <span className="material-symbols-outlined text-[16px] mr-1">arrow_downward</span>
              <span className="text-caption font-caption font-bold">0.8% from prev. month</span>
            </div>
            <p className="mt-4 text-caption text-on-surface-variant leading-relaxed">
              Portfolio annualized volatility remains within the 10-15% target band for moderate-aggressive profiles.
            </p>
          </div>
          
          {/* Max Drawdown Card */}
          <div className="elevation-l1 rounded-xl p-stack-md bg-white border border-outline-variant shadow-sm hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-2">
              <span className="text-label-mono font-label-mono text-on-surface-variant font-bold">MAX DRAWDOWN</span>
              <span className="material-symbols-outlined text-error">trending_down</span>
            </div>
            <div className="text-[32px] font-bold text-on-surface">-8.2%</div>
            <div className="w-full h-1 bg-surface-container mt-4 rounded-full overflow-hidden">
              <div className="h-full bg-error rounded-full" style={{ width: '40%' }}></div>
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-caption font-caption text-on-surface-variant">Current</span>
              <span className="text-caption font-caption text-on-surface-variant">Limit: -20%</span>
            </div>
          </div>

          {/* VaR Card */}
          <div className="elevation-l1 rounded-xl p-stack-md bg-white border border-outline-variant shadow-sm hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-2">
              <span className="text-label-mono font-label-mono text-on-surface-variant font-bold">VaR (95%)</span>
              <span className="material-symbols-outlined text-tertiary">analytics</span>
            </div>
            <div className="text-[32px] font-bold text-on-surface">2.1%</div>
            <p className="mt-2 text-caption text-on-surface-variant italic">
              Daily Value-at-Risk indicates a $21k potential loss on a $1M portfolio with 95% confidence.
            </p>
          </div>
        </div>

        {/* Correlation Heatmap (High-Density Visualization) */}
        <div className="col-span-12 lg:col-span-6 elevation-l1 rounded-xl p-stack-md flex flex-col bg-white border border-outline-variant shadow-sm hover:shadow-md transition-shadow">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-headline-md font-headline-md text-primary font-bold">Asset Correlation Heatmap</h3>
              <p className="text-label-mono font-label-mono text-on-surface-variant">Cross-Asset Class Dependency Matrix</p>
            </div>
            <div className="flex gap-2">
              <button className="p-2 border border-outline-variant rounded-lg hover:bg-surface-container transition-colors flex items-center justify-center">
                <span className="material-symbols-outlined">filter_list</span>
              </button>
              <button className="p-2 border border-outline-variant rounded-lg hover:bg-surface-container transition-colors flex items-center justify-center">
                <span className="material-symbols-outlined">download</span>
              </button>
            </div>
          </div>
          
          <div className="flex-1 grid grid-cols-6 grid-rows-6 gap-2">
            {/* Header Labels */}
            <div className="flex items-end justify-center text-[10px] font-label-mono text-on-surface-variant font-bold -rotate-45 mb-2">EQUITY</div>
            <div className="flex items-end justify-center text-[10px] font-label-mono text-on-surface-variant font-bold -rotate-45 mb-2">FIXED</div>
            <div className="flex items-end justify-center text-[10px] font-label-mono text-on-surface-variant font-bold -rotate-45 mb-2">REIT</div>
            <div className="flex items-end justify-center text-[10px] font-label-mono text-on-surface-variant font-bold -rotate-45 mb-2">GOLD</div>
            <div className="flex items-end justify-center text-[10px] font-label-mono text-on-surface-variant font-bold -rotate-45 mb-2">CRYPTO</div>
            <div className="flex items-end justify-center text-[10px] font-label-mono text-on-surface-variant font-bold -rotate-45 mb-2">CASH</div>

            {/* Row 1: Equity */}
            <div className="heatmap-cell bg-primary rounded-sm flex items-center justify-center text-white text-[10px] font-bold">1.00</div>
            <div className="heatmap-cell bg-primary-container rounded-sm flex items-center justify-center text-on-primary-container text-[10px] font-bold">0.45</div>
            <div className="heatmap-cell bg-primary/80 rounded-sm flex items-center justify-center text-white text-[10px] font-bold">0.72</div>
            <div className="heatmap-cell bg-surface-container rounded-sm flex items-center justify-center text-on-surface-variant text-[10px] font-bold">0.12</div>
            <div className="heatmap-cell bg-primary-container rounded-sm flex items-center justify-center text-on-primary-container text-[10px] font-bold">0.55</div>
            <div className="heatmap-cell bg-surface-container-lowest border border-outline-variant rounded-sm flex items-center justify-center text-on-surface-variant text-[10px] font-bold">-0.05</div>

            {/* Row 2: Fixed Income */}
            <div className="heatmap-cell bg-primary-container rounded-sm flex items-center justify-center text-on-primary-container text-[10px] font-bold">0.45</div>
            <div className="heatmap-cell bg-primary rounded-sm flex items-center justify-center text-white text-[10px] font-bold">1.00</div>
            <div className="heatmap-cell bg-primary-container rounded-sm flex items-center justify-center text-on-primary-container text-[10px] font-bold">0.30</div>
            <div className="heatmap-cell bg-primary-container rounded-sm flex items-center justify-center text-on-primary-container text-[10px] font-bold">0.25</div>
            <div className="heatmap-cell bg-surface-container-lowest border border-outline-variant rounded-sm flex items-center justify-center text-on-surface-variant text-[10px] font-bold">-0.15</div>
            <div className="heatmap-cell bg-primary-container rounded-sm flex items-center justify-center text-on-primary-container text-[10px] font-bold">0.40</div>

            {/* Row 3: REITs */}
            <div className="heatmap-cell bg-primary/80 rounded-sm flex items-center justify-center text-white text-[10px] font-bold">0.72</div>
            <div className="heatmap-cell bg-primary-container rounded-sm flex items-center justify-center text-on-primary-container text-[10px] font-bold">0.30</div>
            <div className="heatmap-cell bg-primary rounded-sm flex items-center justify-center text-white text-[10px] font-bold">1.00</div>
            <div className="heatmap-cell bg-surface-container rounded-sm flex items-center justify-center text-on-surface-variant text-[10px] font-bold">0.18</div>
            <div className="heatmap-cell bg-primary-container rounded-sm flex items-center justify-center text-on-primary-container text-[10px] font-bold">0.42</div>
            <div className="heatmap-cell bg-surface-container-lowest border border-outline-variant rounded-sm flex items-center justify-center text-on-surface-variant text-[10px] font-bold">-0.02</div>

            {/* Remaining rows visually approximated */}
            <div className="heatmap-cell bg-surface-container rounded-sm"></div>
            <div className="heatmap-cell bg-primary-container rounded-sm"></div>
            <div className="heatmap-cell bg-surface-container rounded-sm"></div>
            <div className="heatmap-cell bg-primary rounded-sm"></div>
            <div className="heatmap-cell bg-primary-container rounded-sm"></div>
            <div className="heatmap-cell bg-surface-container-lowest border border-outline-variant rounded-sm"></div>

            <div className="heatmap-cell bg-primary-container rounded-sm"></div>
            <div className="heatmap-cell bg-surface-container-lowest border border-outline-variant rounded-sm"></div>
            <div className="heatmap-cell bg-primary-container rounded-sm"></div>
            <div className="heatmap-cell bg-primary-container rounded-sm"></div>
            <div className="heatmap-cell bg-primary rounded-sm"></div>
            <div className="heatmap-cell bg-surface-container-lowest border border-outline-variant rounded-sm"></div>

            <div className="heatmap-cell bg-surface-container-lowest border border-outline-variant rounded-sm"></div>
            <div className="heatmap-cell bg-primary-container rounded-sm"></div>
            <div className="heatmap-cell bg-surface-container-lowest border border-outline-variant rounded-sm"></div>
            <div className="heatmap-cell bg-surface-container-lowest border border-outline-variant rounded-sm"></div>
            <div className="heatmap-cell bg-surface-container-lowest border border-outline-variant rounded-sm"></div>
            <div className="heatmap-cell bg-primary rounded-sm"></div>
          </div>
          
          <div className="mt-6 flex items-center justify-end gap-4">
            <span className="text-caption font-caption text-on-surface-variant">Inversely Correlated</span>
            <div className="w-32 h-2 rounded-full bg-gradient-to-r from-white via-primary-container to-primary border border-outline-variant"></div>
            <span className="text-caption font-caption text-on-surface-variant">Highly Correlated</span>
          </div>
        </div>

        {/* Risk Parameter Controls */}
        <div className="col-span-12 lg:col-span-3 elevation-l1 rounded-xl p-stack-md flex flex-col gap-6 bg-white border border-outline-variant shadow-sm hover:shadow-md transition-shadow">
          <h3 className="text-headline-md font-headline-md text-primary font-bold">Risk Parameters</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-end">
              <span className="text-label-mono font-label-mono text-on-surface-variant font-bold">RISK TOLERANCE</span>
              <span className="text-body-md font-bold text-primary">7.5 / 10</span>
            </div>
            <div className="relative h-2 w-full bg-surface-container-high rounded-full overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 to-amber-500"></div>
              <div className="absolute left-[75%] top-1/2 -translate-y-1/2 w-4 h-4 bg-white border-2 border-primary rounded-full shadow-md cursor-pointer"></div>
            </div>
            <div className="flex justify-between text-caption font-caption text-on-surface-variant font-bold">
              <span>Conservative</span>
              <span>Aggressive</span>
            </div>
          </div>
          
          <div className="h-px bg-outline-variant"></div>
          
          <div className="space-y-4">
            <h4 className="text-label-mono font-label-mono text-on-surface-variant uppercase tracking-wider font-bold">Active Hedge Layers</h4>
            <div className="space-y-2">
              <label className="flex items-center gap-3 p-2 border border-outline-variant rounded-lg hover:border-primary cursor-pointer transition-colors">
                <input defaultChecked className="rounded text-primary focus:ring-primary h-4 w-4" type="checkbox" />
                <span className="text-body-md font-medium">Tail Risk Protection</span>
                <span className="ml-auto text-caption bg-surface-container-high px-2 py-0.5 rounded font-bold">Active</span>
              </label>
              <label className="flex items-center gap-3 p-2 border border-outline-variant rounded-lg hover:border-primary cursor-pointer transition-colors">
                <input className="rounded text-primary focus:ring-primary h-4 w-4" type="checkbox" />
                <span className="text-body-md font-medium">Currency Overlay</span>
                <span className="ml-auto text-caption bg-surface-container-low px-2 py-0.5 rounded text-outline font-bold">Disabled</span>
              </label>
            </div>
          </div>
          
          <div className="mt-auto p-4 bg-primary-container/10 border border-primary/20 rounded-xl">
            <div className="flex items-start gap-3">
              <span className="material-symbols-outlined text-primary">lightbulb</span>
              <p className="text-caption leading-relaxed text-on-primary-fixed-variant">
                Reducing Equity concentration by 5% and increasing Gold could lower Max Drawdown by ~1.2%.
              </p>
            </div>
          </div>
        </div>
        
        {/* Stress Test Scenario Simulations (Wide Bottom Row) */}
        <div className="col-span-12 elevation-l1 rounded-xl p-stack-md bg-white border border-outline-variant shadow-sm hover:shadow-md transition-shadow">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
            <div>
              <h3 className="text-headline-md font-headline-md text-primary font-bold">Stress Test Scenario Simulations</h3>
              <p className="text-label-mono font-label-mono text-on-surface-variant">Projected Portfolio Performance under Historical & Hypothetical Market Shocks</p>
            </div>
            <div className="flex bg-surface-container rounded-lg p-1">
              <button className="px-4 py-1.5 rounded-md bg-white shadow-sm text-body-md font-medium text-primary">3 Year Projection</button>
              <button className="px-4 py-1.5 rounded-md text-body-md font-medium text-on-surface-variant hover:text-on-surface">10 Year Projection</button>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter">
            {/* Base Case */}
            <div className="p-6 border border-outline-variant rounded-2xl bg-surface-container-lowest hover:border-primary transition-colors group cursor-pointer hover:shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 rounded-full bg-primary-container/20 flex items-center justify-center">
                  <span className="material-symbols-outlined text-primary">trending_up</span>
                </div>
                <h4 className="text-headline-md text-lg font-bold">Base Case</h4>
              </div>
              <div className="space-y-4">
                <div className="flex justify-between border-b border-outline-variant pb-2">
                  <span className="text-body-md text-on-surface-variant">Annualized Return</span>
                  <span className="text-body-md font-bold text-green-600">+8.4%</span>
                </div>
                <div className="flex justify-between border-b border-outline-variant pb-2">
                  <span className="text-body-md text-on-surface-variant">Volatility</span>
                  <span className="text-body-md font-bold">12.1%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-body-md text-on-surface-variant">Sharpe Ratio</span>
                  <span className="text-body-md font-bold">0.69</span>
                </div>
              </div>
              <button className="w-full mt-6 py-2 border border-primary text-primary rounded-lg font-bold group-hover:bg-primary group-hover:text-white transition-all">View Detail</button>
            </div>
            
            {/* 2008 Crisis Scenario */}
            <div className="p-6 border border-outline-variant rounded-2xl bg-surface-container-lowest hover:border-error transition-colors group cursor-pointer hover:shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 rounded-full bg-error-container/20 flex items-center justify-center">
                  <span className="material-symbols-outlined text-error">emergency_home</span>
                </div>
                <h4 className="text-headline-md text-lg font-bold">2008 GFC Shock</h4>
              </div>
              <div className="space-y-4">
                <div className="flex justify-between border-b border-outline-variant pb-2">
                  <span className="text-body-md text-on-surface-variant">Portfolio Drawdown</span>
                  <span className="text-body-md font-bold text-error">-34.2%</span>
                </div>
                <div className="flex justify-between border-b border-outline-variant pb-2">
                  <span className="text-body-md text-on-surface-variant">Recovery Time</span>
                  <span className="text-body-md font-bold">2.4 Years</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-body-md text-on-surface-variant">Worst Month</span>
                  <span className="text-body-md font-bold text-error">-14.1%</span>
                </div>
              </div>
              <button className="w-full mt-6 py-2 border border-error text-error rounded-lg font-bold group-hover:bg-error group-hover:text-white transition-all">Recalibrate Hedge</button>
            </div>
            
            {/* Hyper-inflation Scenario */}
            <div className="p-6 border border-outline-variant rounded-2xl bg-surface-container-lowest hover:border-secondary transition-colors group cursor-pointer hover:shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 rounded-full bg-secondary-container/20 flex items-center justify-center">
                  <span className="material-symbols-outlined text-secondary" style={{ fontVariationSettings: "'FILL' 1" }}>local_fire_department</span>
                </div>
                <h4 className="text-headline-md text-lg font-bold">Hyper-inflation</h4>
              </div>
              <div className="space-y-4">
                <div className="flex justify-between border-b border-outline-variant pb-2">
                  <span className="text-body-md text-on-surface-variant">Real Return (Adj.)</span>
                  <span className="text-body-md font-bold text-secondary-container">-2.1%</span>
                </div>
                <div className="flex justify-between border-b border-outline-variant pb-2">
                  <span className="text-body-md text-on-surface-variant">Bond Yield Impact</span>
                  <span className="text-body-md font-bold">+450bps</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-body-md text-on-surface-variant">Hedge Performance</span>
                  <span className="text-body-md font-bold text-green-600">+12.4%</span>
                </div>
              </div>
              <button className="w-full mt-6 py-2 border border-secondary text-secondary rounded-lg font-bold group-hover:bg-secondary group-hover:text-white transition-all">Optimize Commodities</button>
            </div>
          </div>
          
          {/* Performance Chart Placeholder (Using Atmospheric Shader) */}
          <div className="mt-gutter h-64 rounded-xl relative overflow-hidden bg-surface-container">
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-headline-md font-headline-md text-primary mb-2 font-bold">Simulated Yield Curve (Projected)</span>
              <div className="flex gap-4 items-center">
                <div className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-primary"></span><span className="text-caption font-label-mono font-bold">Portfolio</span></div>
                <div className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-outline"></span><span className="text-caption font-label-mono font-bold">Benchmark</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Sticky Footer CTA for Review */}
      <div className="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-2xl border border-outline-variant shadow-lg mt-stack-lg">
        <div className="flex items-center gap-4 mb-4 md:mb-0">
          <div className="h-12 w-12 rounded-full bg-green-100 flex items-center justify-center">
            <span className="material-symbols-outlined text-green-700" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
          </div>
          <div>
            <h4 className="font-bold text-on-surface">Analytics Completed</h4>
            <p className="text-caption text-on-surface-variant">Your risk profile aligns with your capital plan objectives.</p>
          </div>
        </div>
        <div className="flex gap-4">
          <button className="px-6 py-2 border border-outline text-on-surface-variant rounded-lg font-medium hover:bg-surface-container transition-colors whitespace-nowrap">Export Report</button>
          <button className="px-8 py-2 bg-primary text-white rounded-lg font-bold hover:opacity-90 transition-opacity flex items-center gap-2 whitespace-nowrap">
            Next: Portfolio Optimization
            <span className="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      </div>
    </div>
  );
}
