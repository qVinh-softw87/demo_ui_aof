import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

export default function Layout({ title }) {
  return (
    <div className="bg-background text-on-surface min-h-screen font-body-md">
      <Sidebar />
      <Header title={title} />
      <main className="ml-64 pt-16 min-h-screen flex flex-col">
        <Outlet />
      </main>
    </div>
  );
}
