import { useEffect } from 'react';

export default function CapitalPlanningPage() {
  useEffect(() => {
    // Micro-interaction for Waterfall Bars
    const bars = document.querySelectorAll('.waterfall-bar');
    bars.forEach((bar, index) => {
      const originalHeight = bar.style.height || getComputedStyle(bar).height;
      bar.style.height = '0px';
      setTimeout(() => {
        bar.style.height = originalHeight;
      }, 100 + (index * 150));
    });
  }, []);

  return (
    <div className="max-w-container-max mx-auto p-margin-desktop space-y-stack-lg w-full">
      {/* Header Section */}
      <section className="flex flex-col md:flex-row md:items-end justify-between gap-gutter">
        <div>
          <span className="text-label-mono font-label-mono text-outline uppercase tracking-wider mb-2 block">Giai đoạn 2: Kế hoạch vốn</span>
          <h2 className="font-headline-md text-[32px] font-bold text-on-surface">Phân bổ nguồn vốn Investable Capital</h2>
          <p className="text-body-lg text-on-surface-variant max-w-2xl mt-unit">Xác định tỷ lệ vốn sẵn sàng đầu tư sau khi đã trừ đi các quỹ dự phòng khẩn cấp và mục tiêu ngắn hạn.</p>
        </div>
        <div className="flex gap-stack-sm">
          <button className="px-6 py-2 border border-outline text-on-surface rounded-full font-medium hover:bg-surface-container transition-colors">Xuất báo cáo</button>
          <button className="px-6 py-2 bg-primary text-white rounded-full font-medium hover:opacity-90 shadow-lg shadow-primary/20 transition-all">Lưu kế hoạch</button>
        </div>
      </section>

      {/* Bento Grid Content */}
      <div className="grid grid-cols-12 gap-gutter">
        {/* Waterfall Visualization Card */}
        <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl p-8 shadow-sm flex flex-col min-h-[480px] hover:shadow-md transition-shadow">
          <div className="flex justify-between items-center mb-10">
            <h3 className="font-headline-md text-body-lg font-bold">Waterfall Flow: Nguồn vốn đến Đầu tư</h3>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-primary"></span>
                <span className="text-caption font-caption text-outline">Tổng vốn</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-error"></span>
                <span className="text-caption font-caption text-outline">Dự phòng</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-secondary-container"></span>
                <span className="text-caption font-caption text-outline">Đầu tư</span>
              </div>
            </div>
          </div>
          
          {/* Simplified Waterfall Chart Visualization */}
          <div className="flex-1 flex items-end justify-between px-10 pb-12 relative border-b border-outline-variant">
            {/* Grid Lines */}
            <div className="absolute inset-0 flex flex-col justify-between py-12 pointer-events-none opacity-20">
              <div className="border-t border-outline"></div>
              <div className="border-t border-outline"></div>
              <div className="border-t border-outline"></div>
              <div className="border-t border-outline"></div>
            </div>
            {/* Bar 1: Total Funds */}
            <div className="relative group w-24 flex flex-col items-center">
              <div className="absolute -top-10 text-label-mono font-label-mono font-bold text-primary">1,250M</div>
              <div className="w-full h-[320px] bg-primary rounded-t-lg shadow-md waterfall-bar" style={{ height: '320px' }}></div>
              <div className="mt-4 text-center">
                <p className="text-caption font-label-mono uppercase tracking-wider">Tổng vốn</p>
              </div>
            </div>
            {/* Bar 2: Emergency Reserve (Outflow) */}
            <div className="relative group w-24 flex flex-col items-center">
              <div className="absolute -top-10 text-label-mono font-label-mono font-bold text-error">-300M</div>
              <div className="w-full h-[80px] bg-error/80 rounded-lg shadow-sm waterfall-bar translate-y-[-240px]" style={{ height: '80px' }}></div>
              <div className="mt-4 text-center">
                <p className="text-caption font-label-mono uppercase tracking-wider">Dự phòng</p>
              </div>
            </div>
            {/* Bar 3: Near-term Goal (Outflow) */}
            <div className="relative group w-24 flex flex-col items-center">
              <div className="absolute -top-10 text-label-mono font-label-mono font-bold text-error">-500M</div>
              <div className="w-full h-[130px] bg-error/60 rounded-lg shadow-sm waterfall-bar translate-y-[-110px]" style={{ height: '130px' }}></div>
              <div className="mt-4 text-center">
                <p className="text-caption font-label-mono uppercase tracking-wider">Mục tiêu ngắn</p>
              </div>
            </div>
            {/* Bar 4: Investable Capital (Final) */}
            <div className="relative group w-24 flex flex-col items-center">
              <div className="absolute -top-10 text-label-mono font-label-mono font-bold text-secondary">450M</div>
              <div className="w-full h-[110px] bg-secondary-container rounded-t-lg shadow-lg border-2 border-secondary waterfall-bar" style={{ height: '110px' }}></div>
              <div className="mt-4 text-center">
                <p className="text-caption font-label-mono uppercase tracking-wider font-bold text-on-surface">Investable</p>
              </div>
            </div>
          </div>
          <div className="mt-6 flex items-start gap-4 p-4 bg-surface-container-low rounded-lg border-l-4 border-primary">
            <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>info</span>
            <p className="text-body-md text-on-surface-variant italic">
              Số vốn đầu tư thực tế (450,000,000đ) chiếm 36% tổng tài sản khả dụng của bạn. Đây là mức phân bổ an toàn dựa trên hồ sơ rủi ro hiện tại.
            </p>
          </div>
        </div>

        {/* Stats & Buckets Sidebar */}
        <div className="col-span-12 lg:col-span-4 space-y-gutter">
          {/* Highlight Bucket: Investable Capital */}
          <div className="bg-primary text-white rounded-xl p-6 shadow-xl relative overflow-hidden group hover:translate-y-[-2px] transition-all">
            <div className="absolute top-0 right-0 p-8 opacity-10">
              <span className="material-symbols-outlined text-[120px]" style={{ fontVariationSettings: "'FILL' 1" }}>trending_up</span>
            </div>
            <p className="text-label-mono uppercase tracking-widest opacity-80">Vốn đầu tư khả dụng</p>
            <h4 className="text-[40px] font-bold mt-2 leading-tight">450,000,000đ</h4>
            <p className="text-body-md mt-4 font-medium flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px]">verified</span>
              Sẵn sàng để tối ưu hóa
            </p>
            <button className="mt-8 w-full py-3 bg-white text-primary rounded-lg font-bold hover:bg-opacity-90 transition-all flex items-center justify-center gap-2">
              Tiếp tục bước 3
              <span className="material-symbols-outlined">arrow_forward</span>
            </button>
          </div>

          {/* Bucket: Emergency Reserve */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 hover:border-primary transition-colors cursor-pointer group">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-caption font-label-mono text-outline uppercase mb-1">Dự phòng khẩn cấp</p>
                <h5 className="text-headline-md font-bold text-on-surface">300,000,000đ</h5>
              </div>
              <div className="p-2 bg-surface-container-high rounded-lg group-hover:bg-primary-fixed transition-colors">
                <span className="material-symbols-outlined text-outline group-hover:text-primary">emergency</span>
              </div>
            </div>
            <div className="mt-4 w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
              <div className="bg-error h-full" style={{ width: '24%' }}></div>
            </div>
            <p className="text-caption text-on-surface-variant mt-3">6 tháng chi phí sinh hoạt được bảo vệ.</p>
          </div>

          {/* Bucket: Near-term Goals */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 hover:border-primary transition-colors cursor-pointer group">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-caption font-label-mono text-outline uppercase mb-1">Mục tiêu ngắn hạn</p>
                <h5 className="text-headline-md font-bold text-on-surface">500,000,000đ</h5>
              </div>
              <div className="p-2 bg-surface-container-high rounded-lg group-hover:bg-primary-fixed transition-colors">
                <span className="material-symbols-outlined text-outline group-hover:text-primary">event_upcoming</span>
              </div>
            </div>
            <div className="mt-4 w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
              <div className="bg-primary-container h-full" style={{ width: '40%' }}></div>
            </div>
            <p className="text-caption text-on-surface-variant mt-3">Quỹ mua nhà & giáo dục con cái (0-3 năm).</p>
          </div>
        </div>
      </div>

      {/* Detailed Adjustments Table / Grid */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-gutter">
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center gap-3 mb-4">
            <span className="material-symbols-outlined text-primary">tune</span>
            <h6 className="font-bold text-body-lg">Điều chỉnh tham số</h6>
          </div>
          <div className="space-y-6">
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-body-md text-on-surface-variant">Tháng dự phòng</label>
                <span className="text-body-md font-bold">6 tháng</span>
              </div>
              <input className="w-full h-2 bg-surface-container-high rounded-lg appearance-none cursor-pointer accent-primary" max="12" min="3" type="range" defaultValue="6" />
            </div>
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-body-md text-on-surface-variant">Mức độ ưu tiên vốn</label>
                <span className="text-body-md font-bold">Cân bằng</span>
              </div>
              <div className="flex gap-2">
                <button className="flex-1 py-1 text-caption font-bold border border-outline-variant rounded hover:bg-surface-container transition-all">An toàn</button>
                <button className="flex-1 py-1 text-caption font-bold bg-primary text-white rounded">Cân bằng</button>
                <button className="flex-1 py-1 text-caption font-bold border border-outline-variant rounded hover:bg-surface-container transition-all">Tối ưu</button>
              </div>
            </div>
          </div>
        </div>
        
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center gap-3 mb-4">
            <span className="material-symbols-outlined text-primary">insights</span>
            <h6 className="font-bold text-body-lg">Phân tích dòng tiền</h6>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between py-2 border-b border-outline-variant">
              <span className="text-body-md text-on-surface-variant">Thu nhập ròng</span>
              <span className="text-body-md font-bold text-on-surface">+85,000,000đ</span>
            </div>
            <div className="flex justify-between py-2 border-b border-outline-variant">
              <span className="text-body-md text-on-surface-variant">Chi tiêu cố định</span>
              <span className="text-body-md font-bold text-error">-40,000,000đ</span>
            </div>
            <div className="flex justify-between py-2 border-b border-outline-variant">
              <span className="text-body-md text-on-surface-variant">Thặng dư khả dụng</span>
              <span className="text-body-md font-bold text-primary">+45,000,000đ</span>
            </div>
          </div>
        </div>

        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 overflow-hidden relative hover:shadow-md transition-shadow group">
          <div className="flex items-center gap-3 mb-4">
            <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>auto_awesome</span>
            <h6 className="font-bold text-body-lg">Gợi ý từ AI Advisor</h6>
          </div>
          <p className="text-body-md text-on-surface-variant leading-relaxed mb-4">
            Dựa trên lạm phát hiện tại, bạn có thể cân nhắc chuyển 50tr từ quỹ mục tiêu ngắn hạn sang đầu tư trái phiếu thanh khoản cao để bảo toàn sức mua.
          </p>
          <a className="text-primary font-bold text-body-md flex items-center gap-1 hover:underline" href="#">
            Xem phân tích chi tiết
            <span className="material-symbols-outlined text-[16px]">open_in_new</span>
          </a>
        </div>
      </section>
    </div>
  );
}
