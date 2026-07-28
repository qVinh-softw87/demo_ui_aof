export default function Header({ title }) {
  return (
    <header className="fixed top-0 right-0 left-64 h-16 bg-surface border-b border-outline-variant flex justify-between items-center px-margin-desktop z-40">
      <div className="flex-1 max-w-md flex items-center gap-2">
        {title ? (
          <span className="text-headline-md font-headline-md text-primary font-bold">{title}</span>
        ) : (
          <div className="relative group w-full">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline group-focus-within:text-primary">search</span>
            <input 
              className="w-full bg-surface-container-low border border-outline-variant rounded-full py-2 pl-10 pr-4 text-body-md focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all" 
              placeholder="Search..." 
              type="text"
            />
          </div>
        )}
      </div>
      <div className="flex items-center gap-6">
        {title && (
           <div className="relative hidden lg:block mr-4">
             <input className="bg-surface-container-low border border-outline-variant rounded-full py-1.5 pl-10 pr-4 text-sm focus:outline-none focus:border-primary w-64" placeholder="Search data..." type="text"/>
             <span className="material-symbols-outlined absolute left-3 top-1.5 text-[18px] text-outline">search</span>
           </div>
        )}
        <div className="flex items-center gap-4 text-on-surface-variant">
          <span className="material-symbols-outlined hover:text-primary cursor-pointer transition-colors">notifications</span>
          <span className="material-symbols-outlined hover:text-primary cursor-pointer transition-colors">settings</span>
          <span className="material-symbols-outlined hover:text-primary cursor-pointer transition-colors">help</span>
        </div>
        <div className="h-8 w-[1px] bg-outline-variant"></div>
        <div className="flex items-center gap-3 cursor-pointer group">
          <div className="text-right hidden sm:block">
            <p className="text-label-mono font-bold leading-none">Minh Tran</p>
            <p className="text-caption text-on-surface-variant">Premium Member</p>
          </div>
          <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-primary-container">
            <img 
              className="w-full h-full object-cover" 
              alt="Profile" 
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuA8v1j5XtI1ZEUGXbZX5F8ceq4Islt5pQPHO52u1LyKT76OfiWMU663OzQUmWqhpuhhKo3igF3S5z_JCehkMRPybXS3Ec42u8H95cMitsNIuPvPmmAxjeNWfw7Dd5B5R9_clBtuiRnnHam-u7jtUZp28Y_r6HYNvUNihDK8mR2rSAY7SHYPCMTnHp_I4Ff0SHSZ09WuqmajKvc6aY6oxS2hmyq2kYYjjlp-1eHRSkciUl3_Z5abEufR"
            />
          </div>
        </div>
      </div>
    </header>
  );
}
