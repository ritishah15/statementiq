import React from 'react';
import { useStatement } from '../context/StatementContext';
import { 
  Building2, 
  ChevronRight, 
  Play, 
  Cpu, 
  Download, 
  FileSpreadsheet, 
  Layers,
  AlertCircle,
  CheckCircle,
  FileText,
  RefreshCw
} from 'lucide-react';
import { api } from '../services/api';

export const Navbar = () => {
  const { 
    statements, 
    currentStatementId, 
    statementData, 
    selectStatement, 
    processStatement, 
    retryStatement,
    classifyStatement, 
    loading, 
    error,
    activeModule,
    setActiveModule 
  } = useStatement();

  const meta = statementData?.metadata;

  return (
    <header className="sticky top-0 h-16 w-full bg-white/95 backdrop-blur-md border-b border-slate-200 z-40 px-8 flex items-center justify-between gap-6">
      {/* Breadcrumb & Context */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-xs text-slate-400 font-medium">
          <Building2 className="w-4 h-4 text-slate-500" />
          <span>StatementIQ Workspace</span>
          <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
          <span className="text-navy font-semibold">Bank Statement Processing & Classification</span>
        </div>
      </div>

      {/* Statement Switcher Dropdown */}
      <div className="flex-1 max-w-md">
        {statements.length > 0 ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-medium shrink-0">Statement:</span>
            <select
              value={currentStatementId || ''}
              onChange={(e) => selectStatement(e.target.value)}
              className="w-full h-9 px-3 text-xs font-medium rounded-lg bg-slate-50 border border-slate-200 text-slate-800 focus:outline-none focus:ring-1 focus:ring-teal cursor-pointer"
            >
              {statements.map((s) => (
                <option 
                  key={s.statement_id} 
                  value={s.statement_id}
                  title={`${s.filename} — ${s.pdf_type ? s.pdf_type.toUpperCase() : 'PDF'} (${s.stage_name || s.status})`}
                >
                  {s.statement_id} • {s.filename.length > 20 ? s.filename.substring(0, 18) + '...' : s.filename} ({s.pdf_type ? s.pdf_type.toUpperCase() : 'PDF'})
                </option>
              ))}
            </select>
          </div>
        ) : meta ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-medium shrink-0">Statement:</span>
            <span className="text-xs font-semibold text-navy truncate">{meta.filename} ({meta.stage_name || meta.status})</span>
          </div>
        ) : (
          <span className="text-xs text-slate-400 italic">No statement uploaded yet</span>
        )}
      </div>

      {/* Actions & Pipeline Trigger Buttons */}
      <div className="flex items-center gap-3">
        {meta && (
          <>
            {/* If error -> Retry button */}
            {meta.status === 'error' && (
              <button
                onClick={() => retryStatement(meta.statement_id)}
                disabled={loading}
                className="h-9 px-4 rounded-xl bg-red-600 text-white text-xs font-semibold hover:bg-red-700 transition-all shadow-sm flex items-center gap-1.5 disabled:opacity-50"
              >
                <RefreshCw className="w-3.5 h-3.5 text-white" />
                <span>{loading ? 'Retrying...' : 'Retry Processing'}</span>
              </button>
            )}

            {/* If stage 1 or 2 and valid -> Process button */}
            {meta.status !== 'error' && meta.current_stage <= 2 && (
              <button
                onClick={() => processStatement(meta.statement_id)}
                disabled={loading || meta.pdf_type === 'UNKNOWN'}
                className="h-9 px-4 rounded-xl bg-navy text-white text-xs font-semibold hover:bg-navy-light transition-all shadow-sm flex items-center gap-1.5 disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 text-teal fill-teal" />
                <span>{loading ? 'Processing...' : 'Process Statement'}</span>
              </button>
            )}

            {/* If stage 4 (parsed) -> Run Classifier */}
            {meta.current_stage === 4 && (
              <button
                onClick={() => classifyStatement(meta.statement_id)}
                disabled={loading}
                className="h-9 px-4 rounded-xl bg-teal text-white text-xs font-semibold hover:bg-teal-hover transition-all shadow-sm flex items-center gap-1.5 disabled:opacity-50"
              >
                <Cpu className="w-4 h-4 text-white" />
                <span>{loading ? 'Classifying...' : 'Classify (Non-LLM)'}</span>
              </button>
            )}

            {/* If stage 6 (completed) -> Quick Excel Export */}
            {meta.current_stage >= 5 && (
              <a
                href={api.getExcelExportUrl(meta.statement_id)}
                download
                className="h-9 px-3.5 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold hover:bg-emerald-100 transition-all flex items-center gap-1.5"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                <span>Export Excel</span>
              </a>
            )}
          </>
        )}
      </div>
    </header>
  );
};
