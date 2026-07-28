export default function ProductEligibilityPage() {
  return (
    <div className="max-w-container-max mx-auto space-y-gutter p-stack-lg w-full">
      {/* Bento Grid Section */}
      <div className="grid grid-cols-12 gap-gutter">
        {/* Proposed Asset Allocation (Bento Item 1) */}
        <div className="col-span-12 lg:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow group">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-headline-md font-headline-md text-primary font-bold">Proposed Strategy</h3>
            <span className="material-symbols-outlined text-outline">donut_small</span>
          </div>
          <div className="space-y-6">
            {/* Bar Chart Component */}
            <div className="space-y-4">
              <div className="flex justify-between text-label-mono">
                <span className="text-on-surface-variant">Asset Mix</span>
                <span className="text-primary font-bold">Balanced Growth</span>
              </div>
              <div className="h-10 w-full flex rounded-lg overflow-hidden">
                <div className="h-full bg-primary-container flex items-center justify-center text-[10px] text-white font-bold" style={{ width: '40%' }} title="Cash (40%)">40%</div>
                <div className="h-full bg-primary flex items-center justify-center text-[10px] text-white font-bold" style={{ width: '50%' }} title="ETF (50%)">50%</div>
                <div className="h-full bg-secondary-container flex items-center justify-center text-[10px] text-white font-bold" style={{ width: '10%' }} title="Gold (10%)">10%</div>
              </div>
              <div className="grid grid-cols-3 gap-2 mt-2">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-primary-container rounded-sm"></div>
                  <span className="text-caption font-caption text-on-surface-variant">Cash</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-primary rounded-sm"></div>
                  <span className="text-caption font-caption text-on-surface-variant">ETF</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-secondary-container rounded-sm"></div>
                  <span className="text-caption font-caption text-on-surface-variant">Gold</span>
                </div>
              </div>
            </div>
            <div className="p-4 bg-surface-container-low rounded-lg border border-outline-variant/30">
              <p className="text-caption font-caption text-on-surface-variant leading-relaxed">
                Your allocation is optimized for low volatility while capturing upside in the equity markets through broad-market ETFs.
              </p>
            </div>
          </div>
        </div>

        {/* Product Grid (Bento Item 2) */}
        <div className="col-span-12 lg:col-span-8 space-y-gutter">
          {/* Filters */}
          <div className="flex gap-stack-md overflow-x-auto pb-2 custom-scrollbar">
            <button className="px-6 py-2 bg-primary text-white rounded-full text-label-mono font-bold whitespace-nowrap">All Products</button>
            <button className="px-6 py-2 bg-white border border-outline-variant text-on-surface-variant hover:border-primary hover:text-primary rounded-full text-label-mono transition-all whitespace-nowrap">Bank Savings</button>
            <button className="px-6 py-2 bg-white border border-outline-variant text-on-surface-variant hover:border-primary hover:text-primary rounded-full text-label-mono transition-all whitespace-nowrap">ETFs</button>
            <button className="px-6 py-2 bg-white border border-outline-variant text-on-surface-variant hover:border-primary hover:text-primary rounded-full text-label-mono transition-all whitespace-nowrap">Gold & Metals</button>
            <button className="px-6 py-2 bg-white border border-outline-variant text-on-surface-variant hover:border-primary hover:text-primary rounded-full text-label-mono transition-all whitespace-nowrap">Commodities</button>
          </div>

          {/* Data Table */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-surface-container-low border-b border-outline-variant">
                    <th className="px-6 py-4 text-label-mono text-on-surface-variant whitespace-nowrap">PRODUCT NAME</th>
                    <th className="px-6 py-4 text-label-mono text-on-surface-variant whitespace-nowrap">YIELD / INT.</th>
                    <th className="px-6 py-4 text-label-mono text-on-surface-variant whitespace-nowrap">MIN. AMOUNT</th>
                    <th className="px-6 py-4 text-label-mono text-on-surface-variant whitespace-nowrap">LIQUIDITY</th>
                    <th className="px-6 py-4 text-label-mono text-on-surface-variant whitespace-nowrap">RISK</th>
                    <th className="px-6 py-4"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/30">
                  {/* Row 1: Bank Savings */}
                  <tr className="hover:bg-surface-container transition-colors group cursor-pointer hover:-translate-y-[1px] hover:shadow-sm">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-primary">account_balance</span>
                        <div>
                          <div className="font-bold text-on-surface">Premium Savings</div>
                          <div className="text-caption font-caption text-on-surface-variant">High-yield Cash Account</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-label-mono text-primary">6.5%/year</td>
                    <td className="px-6 py-4 font-label-mono">$1,000</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-green-100 text-green-700 text-[10px] font-bold rounded uppercase whitespace-nowrap">T+0 Instant</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-1">
                        <div className="w-4 h-1.5 rounded-full bg-primary"></div>
                        <div className="w-4 h-1.5 rounded-full bg-outline-variant"></div>
                        <div className="w-4 h-1.5 rounded-full bg-outline-variant"></div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors">chevron_right</span>
                    </td>
                  </tr>
                  
                  {/* Row 2: ETF */}
                  <tr className="hover:bg-surface-container transition-colors group cursor-pointer hover:-translate-y-[1px] hover:shadow-sm">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-primary">monitoring</span>
                        <div>
                          <div className="font-bold text-on-surface">Global Equity ETF (IWGE)</div>
                          <div className="text-caption font-caption text-on-surface-variant">S&P 500 Tracking</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-label-mono text-primary">8.2% (Est.)</td>
                    <td className="px-6 py-4 font-label-mono">$500</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 text-[10px] font-bold rounded uppercase whitespace-nowrap">T+2 Days</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-1">
                        <div className="w-4 h-1.5 rounded-full bg-primary"></div>
                        <div className="w-4 h-1.5 rounded-full bg-primary"></div>
                        <div className="w-4 h-1.5 rounded-full bg-outline-variant"></div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors">chevron_right</span>
                    </td>
                  </tr>

                  {/* Row 3: Gold */}
                  <tr className="hover:bg-surface-container transition-colors group cursor-pointer hover:-translate-y-[1px] hover:shadow-sm">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-secondary" style={{ fontVariationSettings: "'FILL' 1" }}>toll</span>
                        <div>
                          <div className="font-bold text-on-surface">Digital Gold</div>
                          <div className="text-caption font-caption text-on-surface-variant">24K Bullion Backed</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-label-mono text-primary">N/A (Asset)</td>
                    <td className="px-6 py-4 font-label-mono">$100</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-green-100 text-green-700 text-[10px] font-bold rounded uppercase whitespace-nowrap">T+1 Day</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-1">
                        <div className="w-4 h-1.5 rounded-full bg-primary"></div>
                        <div className="w-4 h-1.5 rounded-full bg-outline-variant"></div>
                        <div className="w-4 h-1.5 rounded-full bg-outline-variant"></div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors">chevron_right</span>
                    </td>
                  </tr>

                  {/* Row 4: Commodities */}
                  <tr className="hover:bg-surface-container transition-colors group cursor-pointer hover:-translate-y-[1px] hover:shadow-sm">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-tertiary">factory</span>
                        <div>
                          <div className="font-bold text-on-surface">Agriculture Diversified</div>
                          <div className="text-caption font-caption text-on-surface-variant">Grains & Softs Futures</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-label-mono text-primary">12.4% (Var)</td>
                    <td className="px-6 py-4 font-label-mono">$5,000</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-amber-100 text-amber-700 text-[10px] font-bold rounded uppercase whitespace-nowrap">Monthly</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-1">
                        <div className="w-4 h-1.5 rounded-full bg-primary"></div>
                        <div className="w-4 h-1.5 rounded-full bg-primary"></div>
                        <div className="w-4 h-1.5 rounded-full bg-primary"></div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors">chevron_right</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Portfolio Performance Projection (Bento Item 3) */}
        <div className="col-span-12 grid grid-cols-1 md:grid-cols-3 gap-gutter">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex items-start gap-4 hover:shadow-md transition-shadow">
            <div className="p-3 bg-primary-container/10 rounded-lg">
              <span className="material-symbols-outlined text-primary">trending_up</span>
            </div>
            <div>
              <p className="text-caption font-caption text-on-surface-variant">Projected Annual Return</p>
              <h4 className="text-headline-md font-bold text-on-surface">7.4% - 9.1%</h4>
              <p className="text-[10px] text-green-600 font-bold">+1.2% vs Benchmark</p>
            </div>
          </div>
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex items-start gap-4 hover:shadow-md transition-shadow">
            <div className="p-3 bg-secondary-container/10 rounded-lg">
              <span className="material-symbols-outlined text-secondary">verified_user</span>
            </div>
            <div>
              <p className="text-caption font-caption text-on-surface-variant">Risk Score</p>
              <h4 className="text-headline-md font-bold text-on-surface">Low-Medium</h4>
              <p className="text-[10px] text-on-surface-variant">Standard Deviation: 4.2%</p>
            </div>
          </div>
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex items-start gap-4 hover:shadow-md transition-shadow">
            <div className="p-3 bg-tertiary-container/10 rounded-lg">
              <span className="material-symbols-outlined text-tertiary">water_drop</span>
            </div>
            <div>
              <p className="text-caption font-caption text-on-surface-variant">Portfolio Liquidity</p>
              <h4 className="text-headline-md font-bold text-on-surface">90% Instant</h4>
              <p className="text-[10px] text-on-surface-variant">Available for withdrawal</p>
            </div>
          </div>
        </div>
      </div>

      {/* Call to Action Section */}
      <div className="flex flex-col md:flex-row justify-between items-center bg-inverse-surface text-white p-8 rounded-2xl relative overflow-hidden group hover:shadow-xl transition-shadow mt-4">
        {/* Abstract Background Effect */}
        <div className="absolute inset-0 opacity-10 pointer-events-none">
          <div className="absolute -right-20 -top-20 w-96 h-96 bg-primary rounded-full blur-[100px]"></div>
          <div className="absolute -left-20 -bottom-20 w-64 h-64 bg-secondary rounded-full blur-[80px]"></div>
        </div>
        <div className="relative z-10 mb-6 md:mb-0">
          <h3 className="text-headline-md font-bold mb-2 text-[24px]">Ready to implement this allocation?</h3>
          <p className="text-body-md opacity-80 max-w-xl">Your selection of eligible products is aligned with your Stage 3 Investment Policy. Proceed to Risk & Return analysis to simulate performance.</p>
        </div>
        <div className="relative z-10 flex gap-4">
          <button className="px-8 py-3 bg-white text-primary font-bold rounded-lg hover:bg-opacity-90 transition-all flex items-center gap-2 whitespace-nowrap">
            Next Step: Risk Analysis
            <span className="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      </div>
    </div>
  );
}
