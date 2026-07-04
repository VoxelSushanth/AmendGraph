import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import Dashboard from './components/Dashboard';
import AmendmentUpload from './components/AmendmentUpload';
import ImpactAnalysis from './components/ImpactAnalysis';
import DependencyGraph from './components/DependencyGraph';
import ReviewTasks from './components/ReviewTasks';
import AuditTrail from './components/AuditTrail';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-background">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<AmendmentUpload />} />
            <Route path="/impact/:id" element={<ImpactAnalysis />} />
            <Route path="/graph/:id" element={<DependencyGraph />} />
            <Route path="/tasks/:id" element={<ReviewTasks />} />
            <Route path="/audit/:id" element={<AuditTrail />} />
          </Routes>
        </div>
      </BrowserRouter>
      <Toaster position="top-right" />
    </QueryClientProvider>
  );
}

export default App;
