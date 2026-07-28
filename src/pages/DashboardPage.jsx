export default function DashboardPage() {
  return (
    <div className="max-w-[1280px] mx-auto px-margin-desktop py-stack-lg w-full">
      <section className="mb-stack-lg">
        <h2 className="font-display-lg text-[48px] text-on-surface tracking-tight mb-2 font-bold leading-tight">Bạn cần hỗ trợ gì hôm nay?</h2>
        <p className="text-body-lg text-on-surface-variant max-w-2xl">Chào mừng quay trở lại. Hãy chọn một hành động để chúng tôi có thể điều phối chuyên gia phù hợp cho bạn.</p>
      </section>

      <section className="mb-gutter">
        <div className="hero-gradient rounded-3xl p-10 text-white relative overflow-hidden flex items-center shadow-xl">
          <div className="relative z-10 max-w-xl">
            <span className="inline-block px-4 py-1 bg-white/20 backdrop-blur-md rounded-full text-label-mono text-xs uppercase tracking-widest mb-4">Khuyến nghị cho bạn</span>
            <h3 className="font-display-lg text-[32px] md:text-[48px] font-bold mb-4 leading-tight">Xây danh mục mới</h3>
            <p className="text-body-lg text-primary-fixed-dim mb-8">Thiết kế lộ trình đầu tư cá nhân hóa dựa trên khẩu vị rủi ro và mục tiêu tài chính của bạn.</p>
            <button className="bg-white text-primary px-8 py-4 rounded-xl font-bold flex items-center gap-2 hover:bg-opacity-90 transition-all transform active:scale-95 shadow-lg">
                BẮT ĐẦU NGAY
                <span className="material-symbols-outlined">trending_flat</span>
            </button>
          </div>
          <div className="absolute right-0 top-0 bottom-0 w-1/2 opacity-20 pointer-events-none"></div>
        </div>
      </section>

      <section className="mb-gutter">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
          {[
            { icon: 'add_circle', title: 'Đầu tư thêm', desc: 'Nạp thêm vốn vào các danh mục hiện có để tối ưu hóa lãi suất kép.', color: 'text-secondary', bg: 'bg-secondary-container/20' },
            { icon: 'payments', title: 'Rút tiền', desc: 'Yêu cầu rút vốn về tài khoản ngân hàng liên kết một cách nhanh chóng.', color: 'text-error', bg: 'bg-error-container/20' },
            { icon: 'balance', title: 'Tái cân bằng', desc: 'Điều chỉnh tỷ trọng tài sản để duy trì mức độ rủi ro mục tiêu.', color: 'text-primary', bg: 'bg-primary-container/10' },
            { icon: 'manage_accounts', title: 'Cập nhật hồ sơ', desc: 'Thay đổi thông tin cá nhân, định danh KYC hoặc khẩu vị rủi ro.', color: 'text-tertiary', bg: 'bg-tertiary-container/10' },
            { icon: 'insights', title: 'Xem phân tích', desc: 'Báo cáo chi tiết về hiệu suất và biến động thị trường mới nhất.', color: 'text-on-surface-variant', bg: 'bg-surface-container-highest' },
          ].map((item, i) => (
            <div key={i} className="glass-card p-6 rounded-2xl flex flex-col h-full cursor-pointer group">
              <div className={`w-12 h-12 rounded-xl ${item.bg} flex items-center justify-center ${item.color} mb-4`}>
                <span className="material-symbols-outlined group-hover:font-[500]" style={{ fontVariationSettings: "'FILL' 1" }}>{item.icon}</span>
              </div>
              <h4 className="text-body-md font-bold mb-2">{item.title}</h4>
              <p className="text-caption text-on-surface-variant flex-1">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-end">
        <div className="lg:col-span-2">
          <div className="bg-surface-container-low border border-outline-variant p-8 rounded-3xl flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-6">
              <div className="relative w-20 h-20">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                  <path className="stroke-current text-outline-variant" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" strokeWidth="3"></path>
                  <path className="stroke-current text-primary" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" strokeDasharray="75, 100" strokeLinecap="round" strokeWidth="3"></path>
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-label-mono font-bold text-primary">75%</span>
                </div>
              </div>
              <div>
                <h5 className="text-body-lg font-bold text-on-surface">Bạn đang có 2 danh mục hoạt động</h5>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-headline-md font-bold text-emerald-600">+12.4%</span>
                  <span className="text-caption text-on-surface-variant">Lợi nhuận ròng</span>
                </div>
              </div>
            </div>
            <button className="bg-primary text-white px-8 py-3 rounded-full font-bold flex items-center gap-2 hover:shadow-lg transition-all">
              <span className="material-symbols-outlined">chat_bubble</span>
              Chat ngay
            </button>
          </div>
        </div>
        <div className="hidden lg:block relative h-48 w-full rounded-3xl overflow-hidden group">
          <img className="w-full h-full object-cover grayscale opacity-50 group-hover:grayscale-0 group-hover:opacity-100 transition-all duration-700" alt="Financial growth" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCkbKXgRRCXFBTw-ele2jp4KPUX2rcyGdZpd4bFVbJoZQVrdbsKjIe3gJ89Fj2_EYtoUfO0IRcEn_nVCw20rhaIyXK6xlGtFmLzZmZ4-EcWhkn6b5nrXUPV1iu0CFr3cRHTiXH48CCsng8Cf4lDTvngt130oZylJ70pYAkwIMAUBVoqy4OHGOHk-PhsQoswPtxOtSrMG1opQk741x9GK7SgmHPsdOFjWjYMkTFxk5oGlO1J8rYWYI8H"/>
          <div className="absolute inset-0 bg-gradient-to-t from-background to-transparent pointer-events-none"></div>
        </div>
      </div>
    </div>
  );
}
