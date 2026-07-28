import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import DashboardPage from './pages/DashboardPage';
import DataCheckPage from './pages/DataCheckPage';
import CapitalPlanningPage from './pages/CapitalPlanningPage';
import ProductEligibilityPage from './pages/ProductEligibilityPage';
import RiskReturnPage from './pages/RiskReturnPage';
import OptimizationPage from './pages/OptimizationPage';
import ReviewConfirmPage from './pages/ReviewConfirmPage';

// Placeholder components for the ones not implemented yet
const Placeholder = ({ title }) => (
  <div className="flex items-center justify-center h-[calc(100vh-64px)] w-full">
    <h2 className="text-headline-md font-bold text-on-surface-variant">{title} Page (Coming Soon)</h2>
  </div>
);

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="phase-1" element={<DataCheckPage />} />
          <Route path="phase-3" element={<CapitalPlanningPage />} />
          <Route path="phase-4" element={<Placeholder title="Investment Policy" />} />
          <Route path="phase-5" element={<ProductEligibilityPage />} />
          <Route path="phase-6" element={<RiskReturnPage />} />
          <Route path="phase-7" element={<OptimizationPage />} />
          <Route path="phase-8" element={<ReviewConfirmPage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
