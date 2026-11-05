import React, { useState } from 'react';
import { useStatement } from '../context/StatementContext';
import { 
  Scale, 
  CheckCircle2, 
  AlertTriangle, 
  FileSpreadsheet, 
  FileText, 
  Download, 
  Search, 
  ArrowUpDown, 
  ChevronLeft, 
  ChevronRight, 
  HelpCircle,
  Building2,
  TrendingDown,
  TrendingUp,
  Wallet
} from 'lucide-react';
import { api } from '../services/api';

const ITEMS_PER_PAGE = 10;

export const ReconciliationExport = () => {
  const { statementData, currentStatementId, statements } = useStatement();

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [sortField, setSortField] = useState('date');
  const [sortDirection, setSortDirection] = useState('asc'); // asc or desc
  const [currentPage, setCurrentPage] = useState(1);

  const recon = statementData?.reconciliation || {};
  const meta = statementData?.metadata;
  const acc = statementData?.account_details || {};
  const transactions = statementData?.transactions || [];

  // Filter & Search
  let processedTxns = transactions.filter(t => {
    const s = searchTerm.toLowerCase();
    const matchSearch = (t.description || '').toLowerCase().includes(s) || (t.date || '').toLowerCase().includes(s);
    const matchCat = selectedCategory === 'All' || t.category === selectedCategory;
    return matchSearch && matchCat;
  });

  // Sort
  processedTxns.sort((a, b) => {
    let aVal = a[sortField];
    let bVal = b[sortField];
    if (sortField === 'debit' || sortField === 'credit' || sortField === 'balance') {
      aVal = aVal || 0;
      bVal = bVal || 0;
    }
    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  const totalPages = Math.ceil(processedTxns.length / ITEMS_PER_PAGE) || 1;
  const paginatedTxns = processedTxns.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  if (!statementData || !meta) {
    return (
      <div className="p-12 text-center text-slate-400">
        <Scale className="w-12 h-12 mx-auto text-slate-300 mb-3 stroke-1" />
        <h3 className="text-base font-semibold text-slate-700">No Statement Data Available</h3>
        <p className="text-xs text-slate-400 mt-1">Please upload and process a bank statement first.</p>
      </div>
    );
  }

  const isReconciled = recon.is_reconciled;
  const hasDiscrepancy = recon.reconciliation_status === 'Discrepancy Detected';
  const isMissingBal = recon.reconciliation_status === 'Missing Balance Information';

  return (
    <div className="flex flex-col gap-8 p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy tracking-tight">Reconciliation & Export</h1>
          <p className="text-sm text-slate-500 mt-1">
            Balance Verification, Transaction Summary & Excel/CSV Export
          </p>
        </div>

        {/* Download Deliverable Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <a
            href={api.getCsvExportUrl(meta.statement_id)}
            download
            className="h-10 px-3.5 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-semibold hover:bg-slate-50 transition-all shadow-sm flex items-center gap-1.5"
            title="Download CSV for current statement"
          >
            <Download className="w-4 h-4 text-slate-500" />
            <span>CSV (.csv)</span>
          </a>

          <a
            href={api.getExcelExportUrl(meta.statement_id)}
            download
            className="h-10 px-4 rounded-xl bg-teal text-white text-xs font-semibold hover:bg-teal-hover transition-all shadow-sm flex items-center gap-2"
            title="Download 7-Sheet Styled Excel Report"
          >
            <FileSpreadsheet className="w-4 h-4 text-white" />
            <span>Excel (.xlsx)</span>
          </a>

          {statements && statements.length > 1 && (
            <>
              <div className="h-6 w-px bg-slate-200 mx-1 hidden sm:block"></div>
              <a
                href={api.getAllCsvExportUrl()}
                download
                className="h-10 px-3.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 text-xs font-semibold transition-all flex items-center gap-1.5"
                title="Download combined CSV across all uploaded statements"
              >
                <Download className="w-4 h-4 text-slate-600" />
                <span>All Statements CSV</span>
              </a>

              <a
                href={api.getAllExcelExportUrl()}
                download
                className="h-10 px-4 rounded-xl bg-navy text-white text-xs font-semibold hover:bg-navy-light transition-all shadow-sm flex items-center gap-2"
                title="Download consolidated multi-statement Excel workbook"
              >
                <FileSpreadsheet className="w-4 h-4 text-teal" />
                <span>Export All ({statements.length}) Excel</span>
              </a>
            </>
          )}
        </div>
      </div>

      {/* Mathematical Reconciliation Verification Banner */}
      <div className={`p-6 rounded-2xl border transition-all shadow-sm ${
        isReconciled 
          ? 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
          : hasDiscrepancy
          ? 'bg-amber-50/80 border-amber-300 text-amber-950'
          : 'bg-slate-50 border-slate-200 text-slate-800'
      }`}>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className={`p-2.5 rounded-xl shrink-0 mt-0.5 ${
              isReconciled ? 'bg-emerald-100 text-emerald-700' : hasDiscrepancy ? 'bg-amber-100 text-amber-800' : 'bg-slate-200 text-slate-700'
            }`}>
              {isReconciled ? <CheckCircle2 className="w-6 h-6" /> : hasDiscrepancy ? <AlertTriangle className="w-6 h-6" /> : <HelpCircle className="w-6 h-6" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider">
                  Reconciliation Status:
                </span>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase ${
                  isReconciled ? 'bg-emerald-200 text-emerald-900' : hasDiscrepancy ? 'bg-amber-200 text-amber-900' : 'bg-slate-200 text-slate-700'
                }`}>
                  {recon.reconciliation_status}
                </span>
              </div>
              <p className="text-sm mt-1.5 font-medium leading-relaxed">
                {recon.notes}
              </p>
            </div>
          </div>

          {/* Mathematical Formula Preview */}
          <div className="p-3.5 rounded-xl bg-white/80 border border-slate-200 text-xs font-mono flex flex-col gap-1 shrink-0">
            <span className="text-[10px] text-slate-400 font-sans uppercase font-bold tracking-wider">
              Mathematical Balance Formula:
            </span>
            <div className="text-slate-800">
              Opening ({recon.opening_balance?.toLocaleString() || 'N/A'}) + Credits ({recon.total_credits?.toLocaleString()}) - Debits ({recon.total_debits?.toLocaleString()})
            </div>
            <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-slate-900 font-bold">
              <span>Calculated Closing:</span>
              <span className="text-teal font-mono">
                {recon.calculated_closing_balance !== null && recon.calculated_closing_balance !== undefined
                  ? recon.calculated_closing_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })
                  : 'N/A'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Financial Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Metric 1: Total Extracted */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Total Transactions</span>
          <div className="mt-3">
            <div className="text-2xl font-bold text-navy">{recon.total_transactions}</div>
            <span className="text-xs text-slate-400">Verified Line Items</span>
          </div>
        </div>

        {/* Metric 2: Total Debits */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Total Debits</span>
            <TrendingDown className="w-4 h-4 text-red-500" />
          </div>
          <div className="mt-3">
            <div className="text-xl font-bold font-mono text-red-600">
              -{recon.total_debits.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <span className="text-xs text-slate-400">Outflows</span>
          </div>
        </div>

        {/* Metric 3: Total Credits */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Total Credits</span>
            <TrendingUp className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-3">
            <div className="text-xl font-bold font-mono text-emerald-600">
              +{recon.total_credits.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <span className="text-xs text-slate-400">Inflows</span>
          </div>
        </div>

        {/* Metric 4: Net Liquidity Flow */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Net Flow</span>
            <Wallet className="w-4 h-4 text-teal" />
          </div>
          <div className="mt-3">
            <div className={`text-xl font-bold font-mono ${recon.net_flow >= 0 ? 'text-teal' : 'text-red-500'}`}>
              {recon.net_flow >= 0 ? '+' : ''}{recon.net_flow.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <span className="text-xs text-slate-400">Net Liquidity</span>
          </div>
        </div>

        {/* Metric 5: Closing Balance */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Closing Balance</span>
          <div className="mt-3">
            <div className="text-xl font-bold font-mono text-navy">
              {acc.closing_balance !== null && acc.closing_balance !== undefined
                ? acc.closing_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })
                : 'Not Found'}
            </div>
            <span className="text-xs text-slate-400">{acc.bank_name || 'Bank'}</span>
          </div>
        </div>
      </div>

      {/* Final Transactions Audit Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        {/* Table Filter Bar */}
        <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50/50">
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative w-64">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search ledger..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full h-9 pl-9 pr-3 rounded-lg bg-white border border-slate-200 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-teal"
              />
            </div>

            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="h-9 px-3 rounded-lg bg-white border border-slate-200 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-teal"
            >
              <option value="All">All Categories</option>
              {[...new Set(transactions.map(t => t.category))].map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span>
              Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong> ({processedTxns.length} records)
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="p-1 rounded border border-slate-200 hover:bg-slate-100 disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="p-1 rounded border border-slate-200 hover:bg-slate-100 disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Table Content */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th onClick={() => handleSort('date')} className="py-3 px-4 w-28 cursor-pointer hover:text-navy">
                  <div className="flex items-center gap-1">
                    <span>Date</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-3 px-6">Description</th>
                <th onClick={() => handleSort('debit')} className="py-3 px-4 text-right w-28 cursor-pointer hover:text-navy">
                  <div className="flex items-center justify-end gap-1">
                    <span>Debit</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th onClick={() => handleSort('credit')} className="py-3 px-4 text-right w-28 cursor-pointer hover:text-navy">
                  <div className="flex items-center justify-end gap-1">
                    <span>Credit</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th onClick={() => handleSort('balance')} className="py-3 px-4 text-right w-32 cursor-pointer hover:text-navy">
                  <div className="flex items-center justify-end gap-1">
                    <span>Balance</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-3 px-4 w-36">Category</th>
                <th className="py-3 px-4 w-32">Method</th>
                <th className="py-3 px-4 w-28">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {paginatedTxns.map((t) => (
                <tr key={t.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4 font-mono text-slate-700">{t.date}</td>
                  <td className="py-3 px-6 font-medium text-slate-900">{t.description}</td>
                  
                  {/* Debit */}
                  <td className="py-3 px-4 text-right font-mono">
                    {t.debit && t.debit > 0 ? (
                      <span className="text-red-600 font-medium">
                        -{t.debit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </span>
                    ) : <span className="text-slate-300">-</span>}
                  </td>

                  {/* Credit */}
                  <td className="py-3 px-4 text-right font-mono">
                    {t.credit && t.credit > 0 ? (
                      <span className="text-emerald-600 font-medium">
                        +{t.credit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </span>
                    ) : <span className="text-slate-300">-</span>}
                  </td>

                  {/* Balance */}
                  <td className="py-3 px-4 text-right font-mono font-medium text-slate-800">
                    {t.balance !== null && t.balance !== undefined
                      ? t.balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })
                      : 'N/A'}
                  </td>

                  {/* Category */}
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-800 border border-slate-200">
                      {t.category}
                    </span>
                  </td>

                  {/* Method */}
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                      t.classification_method === 'Rule-Based'
                        ? 'bg-blue-100 text-blue-800'
                        : t.classification_method === 'ML Classifier'
                        ? 'bg-purple-100 text-purple-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}>
                      {t.classification_method}
                    </span>
                  </td>

                  {/* Status */}
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold flex items-center gap-1 w-fit ${
                      t.review_status === 'Verified' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                    }`}>
                      {t.review_status === 'Verified' ? <CheckCircle2 className="w-3 h-3 text-emerald-600" /> : <AlertTriangle className="w-3 h-3 text-amber-600" />}
                      <span>{t.review_status}</span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
