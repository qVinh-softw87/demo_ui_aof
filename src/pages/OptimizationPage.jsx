export default function OptimizationPage() {
  return (
    <div className="max-w-container-max mx-auto px-margin-desktop py-12 w-full">
      {/* Header Section */}
      <div className="mb-stack-lg animate-in fade-in slide-in-from-bottom-4 duration-500">
        <h1 className="text-display-lg font-display-lg text-primary mb-stack-sm font-bold">Tối ưu hóa danh mục</h1>
        <p className="text-body-lg text-on-surface-variant max-w-3xl">
          Dựa trên khẩu vị rủi ro và mục tiêu tài chính của bạn, chúng tôi đề xuất 3 phương án danh mục tối ưu. Hãy so sánh và chọn lộ trình phù hợp nhất.
        </p>
      </div>

      {/* Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter mb-stack-lg">
        {/* Simple Plan */}
        <div className="bg-white rounded-xl border border-outline-variant p-6 flex flex-col hover:-translate-y-1 hover:shadow-lg transition-all duration-300">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h3 className="text-headline-md font-headline-md text-on-surface font-bold">Cơ bản (Simple)</h3>
              <p className="text-label-mono text-outline uppercase text-xs font-bold mt-1">Bảo toàn vốn</p>
            </div>
            <div className="bg-surface-container-low p-2 rounded-lg">
              <span className="material-symbols-outlined text-primary">shield</span>
            </div>
          </div>
          <div className="flex flex-col items-center mb-8">
            <div className="relative w-32 h-32 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="64" cy="64" fill="transparent" r="58" stroke="#E2E8F0" strokeWidth="10"></circle>
                <circle className="transition-all duration-300" cx="64" cy="64" fill="transparent" r="58" stroke="#0D259F" strokeDasharray="364" strokeDashoffset="260" strokeLinecap="round" strokeWidth="12"></circle>
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-headline-md font-bold text-primary text-[24px]">2.5</span>
                <span className="text-[10px] text-outline font-bold uppercase mt-1">Rủi ro Thấp</span>
              </div>
            </div>
          </div>
          <div className="space-y-4 mb-8">
            <div className="flex justify-between items-center pb-3 border-b border-surface-variant">
              <span className="text-on-surface-variant text-sm">Lợi nhuận kỳ vọng</span>
              <span className="font-bold text-on-surface">~6.5% / năm</span>
            </div>
            <div className="flex justify-between items-center pb-3 border-b border-surface-variant">
              <span className="text-on-surface-variant text-sm">Drawdown tối đa</span>
              <span className="font-bold text-error">-3.2%</span>
            </div>
            <div className="flex justify-between items-center pb-3 border-b border-surface-variant">
              <span className="text-on-surface-variant text-sm">Số lượng sản phẩm</span>
              <span className="font-bold text-on-surface">04</span>
            </div>
            <div className="flex justify-between items-center pb-3 border-b border-surface-variant">
              <span className="text-on-surface-variant text-sm">Điểm thanh khoản</span>
              <div className="flex gap-0.5">
                <div className="w-3 h-1.5 rounded-full bg-primary"></div>
                <div className="w-3 h-1.5 rounded-full bg-primary"></div>
                <div className="w-3 h-1.5 rounded-full bg-primary"></div>
                <div className="w-3 h-1.5 rounded-full bg-primary"></div>
                <div className="w-3 h-1.5 rounded-full bg-outline-variant"></div>
              </div>
            </div>
          </div>
          <button className="w-full py-4 border-2 border-primary text-primary rounded-xl font-bold hover:bg-primary-container/10 transition-all mt-auto active:scale-[0.98]">
            Chọn phương án này
          </button>
        </div>

        {/* Balanced Plan (Recommended) */}
        <div className="bg-white rounded-xl border-2 border-primary p-6 flex flex-col relative overflow-hidden ring-4 ring-primary/10 hover:-translate-y-1 hover:shadow-xl transition-all duration-300">
          <div className="absolute top-0 right-0 bg-primary text-white px-4 py-1 rounded-bl-xl text-xs font-bold uppercase tracking-widest z-10">
            Khuyên dùng
          </div>
          <div className="flex justify-between items-start mb-6">
            <div>
              <h3 className="text-headline-md font-headline-md text-primary font-bold">Cân bằng (Balanced)</h3>
              <p className="text-label-mono text-primary uppercase text-xs font-bold mt-1">Tăng trưởng ổn định</p>
            </div>
            <div className="bg-primary-container/10 p-2 rounded-lg">
              <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>balance</span>
            </div>
          </div>
          <div className="flex flex-col items-center mb-8">
            <div className="relative w-32 h-32 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="64" cy="64" fill="transparent" r="58" stroke="#E2E8F0" strokeWidth="10"></circle>
                <circle className="transition-all duration-300" cx="64" cy="64" fill="transparent" r="58" stroke="#0D259F" strokeDasharray="364" strokeDashoffset="180" strokeLinecap="round" strokeWidth="12"></circle>
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-headline-md font-bold text-primary text-[24px]">5.2</span>
                <span className="text-[10px] text-outline font-bold uppercase mt-1">Rủi ro Vừa</span>
              </div>
            </div>
          </div>
          <div className="space-y-4 mb-8">
            <div className="flex justify-between items-center pb-3 border-b border-surface-variant">
              <span className="text-on-surface-variant text-sm">Lợi nhuận kỳ vọng</span>
              <span className="font-bold text-on-surface">~11.2% / năm</span>
            </div>
            <div className="flex justify-between items-center pb-3 border-b border-surface-variant">
              <span className="text-on-surface-variant text-sm">Drawdown tối đa</span>
              <span className="font-bold text-error">-8.5%</span>
            </div>
            <div className="flex justify-between items-center pb-3 border-b border-surface-variant">
              <span className="text-on-surface-variant text-sm">Số lượng sản phẩm</span>
              <span className="font-bold text-on-surface">08</span>
            </div>
            <div className="flex justify-between items-center pb-3 border-b border-surface-variant">
              <span className="text-on-surface-variant text-sm">Điểm thanh khoản</span>
              <div className="flex gap-0.5">
                <div className="w-3 h-1.5 rounded-full bg-primary"></div>
                <div className="w-3 h-1.5 rounded-full bg-primary"></div>
                <div className="w-3 h-1.5 rounded-full bg-primary"></div>
                <div className="w-3 h-1.5 rounded-full bg-outline-variant"></div>
                <div className="w-3 h-1.5 rounded-full bg-outline-variant"></div>
              </div>
            </div>
          </div>
          <button className="w-full py-4 bg-primary text-white rounded-xl font-bold shadow-lg shadow-primary/20 hover:opacity-90 transition-all mt-auto active:scale-[0.98]">
            Chọn phương án này
          </button>
        </div>

        {/* Growth Plan */}
        <div className="bg-white rounded-xl border border-outline-variant p-6 flex flex-col hover:-translate-y-1 hover:shadow-lg transition-all duration-300">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h3 className="text-headline-md font-headline-md text-on-surface font-bold">Tăng trưởng (Growth)</h3>
              <p className="text-label-mono text-outline uppercase text-xs font-bold mt-1">Tối đa hóa tài sản</p>
            </div>
            <div className="bg-surface-container-low p-2 rounded-lg">
              <span className="material-symbols-outlined text-primary">rocket_launch</span>
            </div>
          </div>
          <div className="flex flex-col items-center mb-8">
            <div className="relative w-32 h-32 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="64" cy="64" fill="transparent" r="58" stroke="#E2E8F0" strokeWidth="10"></circle>
                <circle className="transition-all duration-300" cx="64" cy="64" fill="transparent" r="58" stroke="#0D259F" strokeDasharray="364" strokeDashoffset="90" strokeLinecap="round" strokeWidth="12"></circle>
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-headline-md font-bold text-primary text-[24px]">8.4</span>
                <span className="text-[10px] text-outline font-bold uppercase mt-1">Rủi ro Cao</span>
              </div>
            </div>
          </div>
          <div className="space-y-4 mb-8">
            <div className="flex justify-between items-center pb-3 border-b border-surface-variant">
              <span className="text-on-surface-variant text-sm">Lợi nhuận kỳ vọng</span>
              <span className="font-bold text-on-surface">~18.5% / năm</span>
            </div>
            <div className="flex justify-between items-center pb-3 border-b border-surface-variant">
              <span className="text-on-surface-variant text-sm">Drawdown tối đa</span>
              <span className="font-bold text-error">-15.4%</span>
            </div>
            <div className="flex justify-between items-center pb-3 border-b border-surface-variant">
              <span className="text-on-surface-variant text-sm">Số lượng sản phẩm</span>
              <span className="font-bold text-on-surface">12</span>
            </div>
            <div className="flex justify-between items-center pb-3 border-b border-surface-variant">
              <span className="text-on-surface-variant text-sm">Điểm thanh khoản</span>
              <div className="flex gap-0.5">
                <div className="w-3 h-1.5 rounded-full bg-primary"></div>
                <div className="w-3 h-1.5 rounded-full bg-primary"></div>
                <div className="w-3 h-1.5 rounded-full bg-outline-variant"></div>
                <div className="w-3 h-1.5 rounded-full bg-outline-variant"></div>
                <div className="w-3 h-1.5 rounded-full bg-outline-variant"></div>
              </div>
            </div>
          </div>
          <button className="w-full py-4 border-2 border-primary text-primary rounded-xl font-bold hover:bg-primary-container/10 transition-all mt-auto active:scale-[0.98]">
            Chọn phương án này
          </button>
        </div>
      </div>

      {/* Bottom Section: Projected Cash Flow Analysis */}
      <div className="bg-white rounded-xl border border-outline-variant p-8 shadow-sm">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-10 gap-4">
          <div>
            <h2 className="text-headline-md font-headline-md text-on-surface font-bold mb-1">Dòng tiền dự kiến (5 năm)</h2>
            <p className="text-on-surface-variant text-sm">Mô phỏng tăng trưởng tài sản dựa trên kế hoạch 'Cân bằng' được chọn</p>
          </div>
          <div className="flex gap-4 items-center">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-primary"></div>
              <span className="text-xs font-label-mono text-outline font-bold">Vốn gốc</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-surface-container-high"></div>
              <span className="text-xs font-label-mono text-outline font-bold">Lãi lũy kế</span>
            </div>
          </div>
        </div>
        
        <div className="relative h-80 w-full flex items-end justify-between px-4 mt-8">
          {/* Grid Lines */}
          <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
            <div className="w-full border-t border-dashed border-outline-variant/30"></div>
            <div className="w-full border-t border-dashed border-outline-variant/30"></div>
            <div className="w-full border-t border-dashed border-outline-variant/30"></div>
            <div className="w-full border-t border-dashed border-outline-variant/30"></div>
            <div className="w-full border-b border-outline-variant"></div>
          </div>
          
          {/* Bars */}
          <div className="flex-1 flex flex-col items-center z-10 group cursor-pointer">
            <div className="w-16 flex flex-col-reverse relative hover:-translate-y-1 transition-transform">
              <div className="h-32 bg-primary rounded-t-sm transition-all group-hover:opacity-80"></div>
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-inverse-surface text-white text-[10px] py-1 px-2 rounded whitespace-nowrap font-bold">
                1,200 Tr
              </div>
            </div>
            <span className="mt-4 text-xs font-label-mono text-outline font-bold">Năm 1</span>
          </div>
          
          <div className="flex-1 flex flex-col items-center z-10 group cursor-pointer">
            <div className="w-16 flex flex-col-reverse relative hover:-translate-y-1 transition-transform">
              <div className="h-32 bg-primary group-hover:opacity-80 transition-all"></div>
              <div className="h-8 bg-surface-container-high rounded-t-sm transition-all group-hover:bg-primary-fixed"></div>
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-inverse-surface text-white text-[10px] py-1 px-2 rounded whitespace-nowrap font-bold">
                1,350 Tr
              </div>
            </div>
            <span className="mt-4 text-xs font-label-mono text-outline font-bold">Năm 2</span>
          </div>
          
          <div className="flex-1 flex flex-col items-center z-10 group cursor-pointer">
            <div className="w-16 flex flex-col-reverse relative hover:-translate-y-1 transition-transform">
              <div className="h-32 bg-primary group-hover:opacity-80 transition-all"></div>
              <div className="h-16 bg-surface-container-high rounded-t-sm transition-all group-hover:bg-primary-fixed"></div>
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-inverse-surface text-white text-[10px] py-1 px-2 rounded whitespace-nowrap font-bold">
                1,520 Tr
              </div>
            </div>
            <span className="mt-4 text-xs font-label-mono text-outline font-bold">Năm 3</span>
          </div>
          
          <div className="flex-1 flex flex-col items-center z-10 group cursor-pointer">
            <div className="w-16 flex flex-col-reverse relative hover:-translate-y-1 transition-transform">
              <div className="h-32 bg-primary group-hover:opacity-80 transition-all"></div>
              <div className="h-28 bg-surface-container-high rounded-t-sm transition-all group-hover:bg-primary-fixed"></div>
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-inverse-surface text-white text-[10px] py-1 px-2 rounded whitespace-nowrap font-bold">
                1,780 Tr
              </div>
            </div>
            <span className="mt-4 text-xs font-label-mono text-outline font-bold">Năm 4</span>
          </div>
          
          <div className="flex-1 flex flex-col items-center z-10 group cursor-pointer">
            <div className="w-16 flex flex-col-reverse relative hover:-translate-y-1 transition-transform">
              <div className="h-32 bg-primary group-hover:opacity-80 transition-all"></div>
              <div className="h-44 bg-surface-container-high rounded-t-sm transition-all group-hover:bg-primary-fixed"></div>
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-inverse-surface text-white text-[10px] py-1 px-2 rounded whitespace-nowrap font-bold">
                2,150 Tr
              </div>
            </div>
            <span className="mt-4 text-xs font-label-mono text-outline font-bold">Năm 5</span>
          </div>
        </div>
        
        <div className="mt-12 p-4 bg-surface-container-low rounded-lg flex items-start gap-4 border border-outline-variant/50">
          <span className="material-symbols-outlined text-primary mt-0.5" style={{ fontVariationSettings: "'FILL' 1" }}>info</span>
          <p className="text-sm text-on-surface-variant leading-relaxed">
            Dự báo dựa trên dữ liệu lịch sử và các giả định kinh tế. Kết quả thực tế có thể thay đổi tùy theo biến động thị trường.
          </p>
        </div>
      </div>
    </div>
  );
}
