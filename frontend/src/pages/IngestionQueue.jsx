import React, { useState, useRef } from 'react';
import { useStatement } from '../context/StatementContext';
import { 
  CloudUpload, 
  FileText, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  Trash2, 
  Play, 
  Scan, 
  Binary, 
  Layers,
  FileCheck,
  Eye,
  FileCode,
  ShieldCheck,
  ArrowRight,
  RefreshCw,
  Copy,
  Info
} from 'lucide-react';

export const IngestionQueue = () => {
  const { 
    statements, 
    currentStatementId, 
    statementData, 
    uploadMultipleFiles,
    loadSample, 
    processStatement, 
    retryStatement,
    deleteStatement, 
    clearAllStatements,
    selectStatement, 
    setActiveModule,
    loading, 
    error,
    availableSamples 
  } = useStatement();

  const [isDragging, setIsDragging] = useState(false);
  const [feedbackError, setFeedbackError] = useState(null);
  const [deleteModalState, setDeleteModalState] = useState({ isOpen: false, statement: null });
  const [clearAllModalOpen, setClearAllModalOpen] = useState(false);
  const fileInputRef = useRef(null);

  const meta = statementData?.metadata;

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleFiles = async (fileList) => {
    setFeedbackError(null);
    const pdfFiles = fileList.filter(f => f.name.toLowerCase().endsWith('.pdf'));
    if (pdfFiles.length === 0) {
      setFeedbackError('Invalid file format: Please select or drop standard PDF bank statements.');
      return;
    }
    const res = await uploadMultipleFiles(pdfFiles);
    if (!res.success && res.errors.length > 0) {
      setFeedbackError(res.errors.join(' | '));
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDeleteClick = (s) => {
    // If statement has been processed (stage >= 3 or parsed/completed), require user confirmation
    if (s.current_stage >= 3 || s.status === 'parsed' || s.status === 'completed') {
      setDeleteModalState({ isOpen: true, statement: s });
    } else {
      deleteStatement(s.statement_id);
    }
  };

  const confirmDelete = async () => {
    if (deleteModalState.statement) {
      await deleteStatement(deleteModalState.statement.statement_id);
      setDeleteModalState({ isOpen: false, statement: null });
    }
  };

  // Actual processing stages defined in assessment requirements
  const stages = [
    { num: 1, title: 'File Uploaded', desc: 'File verified & hashed' },
    { num: 2, title: 'Type Detected', desc: 'DIGITAL, SCANNED or MIXED' },
    { num: 3, title: 'Text/OCR Extraction', desc: 'PyMuPDF stream / Tesseract 5.5' },
    { num: 4, title: 'Transaction Parsing', desc: 'Accounts & Ledger Table' },
    { num: 5, title: 'Classification', desc: 'Non-LLM Rules & Machine Learning Classification' },
    { num: 6, title: 'Reconciliation & Export Ready', desc: 'Balance Audit & Export' }
  ];

  const currentStage = meta?.current_stage || 1;

  const getTypeBadge = (type) => {
    const t = (type || 'UNKNOWN').toUpperCase();
    switch (t) {
      case 'DIGITAL':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'SCANNED':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'MIXED':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      default:
        return 'bg-red-100 text-red-800 border-red-200';
    }
  };

  return (
    <div className="flex flex-col gap-8 p-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy tracking-tight">Statement Upload & Processing</h1>
          <p className="text-sm text-slate-500 mt-1">
            PDF Upload, Type Detection & Processing Queue
          </p>
        </div>

        {/* Quick Sample Loaders */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-400 font-medium">Quick Test Statements:</span>
          {availableSamples
            .filter((s) => ['hdfc_digital_statement.pdf', 'scanned_statement.pdf'].includes(s.filename))
            .map((sample) => (
            <button
              key={sample.filename}
              onClick={() => loadSample(sample.filename)}
              disabled={loading}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 shadow-sm ${
                sample.type === 'SCANNED'
                  ? 'bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100'
                  : 'bg-blue-50 text-blue-800 border-blue-200 hover:bg-blue-100'
              }`}
            >
              {sample.type === 'SCANNED' ? <Scan className="w-3.5 h-3.5 text-amber-600" /> : <Binary className="w-3.5 h-3.5 text-blue-600" />}
              <span>{sample.type === 'SCANNED' ? 'Load Image-Based PDF (OCR)' : 'Load Text-Based PDF (HDFC)'}</span>
            </button>
          ))}
        </div>
      </div>

      {feedbackError && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-sm flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
            <span>{feedbackError}</span>
          </div>
          <button 
            onClick={() => setFeedbackError(null)} 
            className="text-xs font-bold text-red-600 hover:text-red-800"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Upload Zone & Stage Stepper Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Upload Card (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                Upload Bank Statement(s)
              </h2>
              <span className="text-[11px] text-teal font-medium">
                Multiple File Support
              </span>
            </div>
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
                isDragging 
                  ? 'border-teal bg-teal-soft/40' 
                  : 'border-slate-300 hover:border-teal/60 hover:bg-slate-50'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                multiple
                onChange={handleFileInput}
                className="hidden"
              />
              <div className="w-14 h-14 rounded-2xl bg-teal-soft flex items-center justify-center text-teal mb-3 shadow-inner">
                <CloudUpload className="w-7 h-7" />
              </div>
              <span className="text-sm font-semibold text-navy">
                Click to browse or drag & drop PDF(s)
              </span>
              <span className="text-xs text-slate-400 mt-1">
                Select one or multiple digital, scanned, or mixed statements
              </span>
              <div className="mt-4 flex flex-wrap gap-1.5 justify-center">
                <span className="px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 text-[10px] font-semibold border border-blue-200">DIGITAL</span>
                <span className="px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 text-[10px] font-semibold border border-amber-200">SCANNED (OCR)</span>
                <span className="px-2 py-0.5 rounded-md bg-purple-50 text-purple-700 text-[10px] font-semibold border border-purple-200">MIXED</span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              SHA-256 Duplicate Protection
            </span>
            <span>Local Non-LLM Pipeline</span>
          </div>
        </div>

        {/* Active Statement Pipeline Stepper (7 cols) */}
        <div className="lg:col-span-7 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <h2 className="text-base font-bold text-navy">Processing Pipeline Status</h2>
                {meta && (
                  <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 text-xs font-mono font-medium">
                    {meta.statement_id}
                  </span>
                )}
              </div>
              {meta && (
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${meta.status === 'error' ? 'bg-red-500' : 'bg-teal animate-pulse'}`}></span>
                  <span className={`text-xs font-semibold ${meta.status === 'error' ? 'text-red-600' : 'text-teal'}`}>
                    Stage {currentStage} of 6: {meta.stage_name}
                  </span>
                </div>
              )}
            </div>

            {/* Stage Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {stages.map((st) => {
                const isPassed = (currentStage > st.num || (st.num === 6 && currentStage >= 6 && (meta?.status === 'completed' || meta?.current_stage >= 6))) && meta?.status !== 'error';
                const isCurrent = currentStage === st.num && !isPassed;
                const isError = meta?.status === 'error' && isCurrent;
                return (
                  <div
                    key={st.num}
                    className={`p-3.5 rounded-xl border transition-all ${
                      isError
                        ? 'bg-red-50 border-red-300 text-red-900 shadow-sm ring-1 ring-red-400'
                        : isPassed
                        ? 'bg-emerald-50/60 border-emerald-200 text-slate-800'
                        : isCurrent
                        ? 'bg-teal-soft/50 border-teal text-navy shadow-sm ring-1 ring-teal/30'
                        : 'bg-slate-50/70 border-slate-200 text-slate-400'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider">
                        Stage 0{st.num}
                      </span>
                      {isError ? (
                        <AlertTriangle className="w-4 h-4 text-red-600" />
                      ) : isPassed ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      ) : isCurrent ? (
                        <div className="w-2 h-2 rounded-full bg-teal animate-ping" />
                      ) : (
                        <Clock className="w-3.5 h-3.5 text-slate-300" />
                      )}
                    </div>
                    <div className="font-semibold text-xs leading-tight">{st.title}</div>
                    <div className="text-[11px] text-slate-500 mt-1">{st.desc}</div>
                  </div>
                );
              })}
            </div>

            {/* Error banner if statement has failed */}
            {meta?.error_message && (
              <div className="mt-3 p-3 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                  <span>{meta.error_message}</span>
                </div>
                <button
                  onClick={() => retryStatement(meta.statement_id)}
                  className="px-2.5 py-1 rounded-md bg-red-600 text-white font-semibold text-[11px] hover:bg-red-700 flex items-center gap-1 shrink-0"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Retry</span>
                </button>
              </div>
            )}
          </div>

          {/* Action Footer for active statement */}
          {meta && (
            <div className="mt-5 pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-3 text-xs">
                <span className="text-slate-400">PDF Type:</span>
                <span className={`px-2.5 py-0.5 rounded-full font-bold uppercase text-[10px] border ${getTypeBadge(meta.pdf_type)}`}>
                  {meta.pdf_type}
                </span>
                {meta.detection_explanation && (
                  <span className="text-slate-500 truncate max-w-xs" title={meta.detection_explanation}>
                    {meta.detection_explanation}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                {meta.status === 'error' && (
                  <button
                    onClick={() => retryStatement(meta.statement_id)}
                    disabled={loading}
                    className="px-4 py-2 rounded-xl bg-red-600 text-white text-xs font-semibold hover:bg-red-700 transition-all shadow-sm flex items-center gap-1.5"
                  >
                    <RefreshCw className="w-3.5 h-3.5 text-white" />
                    <span>Retry Pipeline</span>
                  </button>
                )}

                {meta.status !== 'error' && currentStage <= 2 && (
                  <button
                    onClick={() => processStatement(meta.statement_id)}
                    disabled={loading || meta.pdf_type === 'UNKNOWN'}
                    className="px-4 py-2 rounded-xl bg-navy text-white text-xs font-semibold hover:bg-navy-light transition-all shadow-sm flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <Play className="w-3.5 h-3.5 text-teal fill-teal" />
                    <span>Process Statement</span>
                  </button>
                )}

                {currentStage >= 4 && (
                  <button
                    onClick={() => setActiveModule('parser')}
                    className="px-4 py-2 rounded-xl bg-teal text-white text-xs font-semibold hover:bg-teal-hover transition-all shadow-sm flex items-center gap-1.5"
                  >
                    <span>View Extracted Audit</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Uploaded Statements Queue Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-navy text-base">Statement Queue</h3>
            <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-xs font-semibold">
              {statements.length} files
            </span>
          </div>
          <div className="flex items-center gap-3">
            {statements.length > 0 && (
              <button
                onClick={() => setClearAllModalOpen(true)}
                disabled={loading}
                className="px-3 py-1 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
                title="Clear all statements from ingestion queue"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear Queue</span>
              </button>
            )}
            <span className="text-xs text-slate-400">
              Click row to view or audit statement data
            </span>
          </div>
        </div>

        {statements.length === 0 ? (
          <div className="p-12 text-center flex flex-col items-center justify-center text-slate-400">
            <FileText className="w-10 h-10 text-slate-300 mb-2 stroke-1" />
            <span className="text-sm font-medium">No bank statements in queue</span>
            <span className="text-xs text-slate-400 mt-1">Upload a PDF or select a test statement above</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-6">Statement File</th>
                  <th className="py-3 px-4">Size</th>
                  <th className="py-3 px-4">PDF Type</th>
                  <th className="py-3 px-4">Pipeline Status</th>
                  <th className="py-3 px-4">Pages</th>
                  <th className="py-3 px-4">Uploaded At</th>
                  <th className="py-3 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {statements.map((s) => {
                  const isSelected = s.statement_id === currentStatementId;
                  const record = (isSelected && statementData?.metadata) ? statementData.metadata : s;
                  const isError = record.status === 'error';
                  return (
                    <tr 
                      key={record.statement_id}
                      onClick={() => selectStatement(record.statement_id)}
                      className={`hover:bg-slate-50 transition-colors cursor-pointer ${
                        isSelected ? 'bg-teal-soft/20 font-medium' : ''
                      }`}
                    >
                      <td className="py-3.5 px-6 flex items-center gap-2.5">
                        <FileText className={`w-4 h-4 shrink-0 ${isSelected ? 'text-teal' : isError ? 'text-red-400' : 'text-slate-400'}`} />
                        <div>
                          <div className="font-semibold text-slate-900 flex items-center gap-1.5">
                            <span>{record.filename}</span>
                            {record.is_duplicate && (
                              <span className="px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 text-[9px] font-mono font-semibold" title={record.duplicate_notice || `Identical to ${record.duplicate_of}`}>
                                {record.upload_status === 'already_processed' ? 'PROCESSED' : 'DUPLICATE'}
                              </span>
                            )}
                          </div>
                          <div className="text-[10px] text-slate-400 font-mono flex items-center gap-2">
                            <span>{record.statement_id}</span>
                            {record.file_hash && (
                              <span className="text-slate-300 truncate max-w-[100px]" title={`SHA-256: ${record.file_hash}`}>
                                #{record.file_hash.substring(0, 8)}
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-slate-600">
                        {(record.file_size / 1024).toFixed(1)} KB
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex flex-col gap-0.5">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase w-fit border ${getTypeBadge(record.pdf_type)}`}>
                            {record.pdf_type || 'DETECTING...'}
                          </span>
                          {record.detection_explanation && (
                            <span className="text-[10px] text-slate-400 truncate max-w-[160px]" title={record.detection_explanation}>
                              {record.detection_explanation}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium ${
                          isError ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-slate-100 text-slate-700'
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            record.status === 'completed' ? 'bg-emerald-500' :
                            record.status === 'parsed' ? 'bg-blue-500' :
                            record.status === 'error' ? 'bg-red-500' : 'bg-teal animate-pulse'
                          }`} />
                          {record.stage_name || record.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-600 font-mono">
                        {record.page_count || 1}
                      </td>
                      <td className="py-3.5 px-4 text-slate-500">
                        {record.created_at}
                      </td>
                      <td className="py-3.5 px-6 text-right">
                        <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                          {isError && (
                            <button
                              onClick={() => retryStatement(s.statement_id)}
                              className="px-2.5 py-1 rounded-md bg-red-600 text-white text-[11px] font-semibold hover:bg-red-700 flex items-center gap-1"
                              title="Retry processing"
                            >
                              <RefreshCw className="w-3 h-3" />
                              <span>Retry</span>
                            </button>
                          )}

                          {!isError && s.current_stage <= 2 && (
                            <button
                              onClick={() => processStatement(s.statement_id)}
                              disabled={loading || s.pdf_type === 'UNKNOWN'}
                              className="px-2.5 py-1 rounded-md bg-navy text-white text-[11px] font-semibold hover:bg-navy-light flex items-center gap-1 disabled:opacity-40"
                              title="Process statement"
                            >
                              <Play className="w-3 h-3 text-teal fill-teal" />
                              <span>Process</span>
                            </button>
                          )}

                          {s.current_stage >= 4 && (
                            <button
                              onClick={() => {
                                selectStatement(s.statement_id);
                                setActiveModule('parser');
                              }}
                              className="px-2.5 py-1 rounded-md bg-teal text-white text-[11px] font-semibold hover:bg-teal-hover flex items-center gap-1"
                              title="Audit extracted ledger"
                            >
                              <span>Audit</span>
                            </button>
                          )}

                          <button
                            onClick={() => handleDeleteClick(s)}
                            className="p-1 rounded-md text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                            title="Remove statement"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Confirmation Modal Before Deleting Processed Statement */}
      {deleteModalState.isOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 flex flex-col gap-4">
            <div className="w-12 h-12 rounded-2xl bg-red-50 text-red-600 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>

            <div className="text-center">
              <h3 className="text-base font-bold text-navy">Confirm Deletion</h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Are you sure you want to delete processed statement <strong className="text-navy">{deleteModalState.statement?.filename}</strong> ({deleteModalState.statement?.statement_id})?
              </p>
              <div className="mt-3 p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-[11px] text-left">
                All extracted account details, transactions, and reconciliation audit data will be permanently deleted.
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
              <button
                onClick={() => setDeleteModalState({ isOpen: false, statement: null })}
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 text-xs font-semibold hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="px-4 py-2 rounded-xl bg-red-600 text-white text-xs font-semibold hover:bg-red-700 shadow-sm"
              >
                Delete Statement
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal Before Clearing All Statements */}
      {clearAllModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 flex flex-col gap-4">
            <div className="w-12 h-12 rounded-2xl bg-red-50 text-red-600 flex items-center justify-center mx-auto">
              <Trash2 className="w-6 h-6" />
            </div>

            <div className="text-center">
              <h3 className="text-base font-bold text-navy">Clear Entire Queue?</h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Are you sure you want to clear all <strong className="text-navy">{statements.length} statements</strong> from the processing queue?
              </p>
              <div className="mt-3 p-3 rounded-xl bg-red-50 border border-red-200 text-red-800 text-[11px] text-left">
                Warning: All uploaded PDFs, extracted transactions, ledger audits, and classifications in this session will be permanently cleared.
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
              <button
                onClick={() => setClearAllModalOpen(false)}
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 text-xs font-semibold hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  await clearAllStatements();
                  setClearAllModalOpen(false);
                }}
                className="px-4 py-2 rounded-xl bg-red-600 text-white text-xs font-semibold hover:bg-red-700 shadow-sm"
              >
                Clear All Statements
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
