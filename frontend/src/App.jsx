import React from 'react';
import { StatementProvider, useStatement } from './context/StatementContext';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { IngestionQueue } from './pages/IngestionQueue';
import { StatementParserAudit } from './pages/StatementParserAudit';
import { NonLLMClassifier } from './pages/NonLLMClassifier';
import { ReconciliationExport } from './pages/ReconciliationExport';
import { Loader2, AlertCircle } from 'lucide-react';

const MainContent = () => {
  const { activeModule, loading, error } = useStatement();

  const renderActiveModule = () => {
    switch (activeModule) {
      case 'ingestion':
        return <IngestionQueue />;
      case 'parser':
        return <StatementParserAudit />;
      case 'classifier':
        return <NonLLMClassifier />;
      case 'reconciliation':
        return <ReconciliationExport />;
      default:
        return <IngestionQueue />;
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex">
      {/* Sidebar Navigation */}
      <Sidebar />

      {/* Main Container */}
      <div className="pl-[260px] flex-1 flex flex-col min-w-0">
        <Navbar />

        {/* Global Error Banner */}
        {error && (
          <div className="mx-8 mt-4 p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Dynamic Module Page */}
        <main className="flex-1 pb-16 relative">
          {loading && (
            <div className="absolute inset-0 bg-white/70 backdrop-blur-[2px] z-30 flex flex-col items-center justify-center">
              <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-xl flex flex-col items-center gap-3">
                <Loader2 className="w-8 h-8 text-teal animate-spin" />
                <span className="text-sm font-semibold text-navy">Processing Statement Pipeline...</span>
                <span className="text-xs text-slate-400">Executing OCR / Parsing / Classification</span>
              </div>
            </div>
          )}
          {renderActiveModule()}
        </main>
      </div>
    </div>
  );
};

export default function App() {
  return (
    <StatementProvider>
      <MainContent />
    </StatementProvider>
  );
}
