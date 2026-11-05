import React, { useState } from 'react';
import { useStatement } from '../context/StatementContext';
import { 
  Building2, 
  User, 
  CreditCard, 
  Hash, 
  Calendar, 
  ArrowUpRight, 
  ArrowDownLeft, 
  Search, 
  Edit3, 
  Check, 
  X, 
  AlertCircle, 
  Eye, 
  EyeOff, 
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  FileSpreadsheet,
  Cpu
} from 'lucide-react';

export const StatementParserAudit = () => {
  const { 
    statementData, 
    updateTransaction, 
    classifyStatement, 
    setActiveModule,
    loading 
  } = useStatement();

  const [showFullAccount, setShowFullAccount] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingTxnId, setEditingTxnId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [saveSuccessId, setSaveSuccessId] = useState(null);

  const meta = statementData?.metadata;
  const acc = statementData?.account_details || {};
  const transactions = statementData?.transactions || [];

  const handleStartEdit = (txn) => {
    setEditingTxnId(txn.id);
    setEditForm({
      date: txn.date,
      description: txn.description,
      debit: txn.debit,
      credit: txn.credit,
      balance: txn.balance,
      category: txn.category
    });
  };

  const handleSaveEdit = async (txnId) => {
    try {
      await updateTransaction(txnId, editForm);
      setEditingTxnId(null);
      setSaveSuccessId(txnId);
      setTimeout(() => setSaveSuccessId(null), 2000);
    } catch (err) {
      alert('Failed to save transaction correction');
    }
  };

  const handleCancelEdit = () => {
    setEditingTxnId(null);
    setEditForm({});
  };

  // Filter transactions
  const filteredTxns = transactions.filter(t => {
    const s = searchTerm.toLowerCase();
    return (
      (t.description || '').toLowerCase().includes(s) ||
      (t.date || '').toLowerCase().includes(s) ||
      (t.category || '').toLowerCase().includes(s)
    );
  });

  const reviewNeededCount = transactions.filter(t => t.review_status === 'Needs Review').length;

  if (!statementData || !meta) {
    return (
      <div className="p-12 text-center text-slate-400">
        <Building2 className="w-12 h-12 mx-auto text-slate-300 mb-3 stroke-1" />
        <h3 className="text-base font-semibold text-slate-700">No Statement Loaded</h3>
        <p className="text-xs text-slate-400 mt-1">Please upload or select a bank statement.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8 p-8 max-w-7xl mx-auto">
      {/* Page Title & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy tracking-tight">Statement Extraction & Validation</h1>
          <p className="text-sm text-slate-500 mt-1">
            Account Details, Transaction Extraction & Data Review
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => classifyStatement()}
            disabled={loading || transactions.length === 0}
            className="px-5 py-2.5 rounded-xl bg-teal text-white text-xs font-semibold hover:bg-teal-hover transition-all shadow-sm flex items-center gap-2 disabled:opacity-50"
          >
            <Cpu className="w-4 h-4 text-white" />
            <span>Proceed to Non-LLM Classification</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Account Details Extracted Card */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-5 border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-teal" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-navy">
              Account Holder & Institution Details
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Extraction Method:</span>
            <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
              meta.ocr_applied ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
            }`}>
              {meta.ocr_applied ? 'Tesseract OCR Pipeline' : 'Direct Digital PyMuPDF'}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 text-xs">
          {/* Bank Name */}
          <div className="flex flex-col gap-1 p-3.5 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-slate-400 font-medium">Bank Name</span>
            <span className="text-sm font-bold text-navy truncate">
              {acc.bank_name || 'Not Found'}
            </span>
          </div>

          {/* Account Holder */}
          <div className="flex flex-col gap-1 p-3.5 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-slate-400 font-medium">Account Holder</span>
            <span className="text-sm font-bold text-navy truncate">
              {acc.account_holder || 'Not Found'}
            </span>
          </div>

          {/* Account Number */}
          <div className="flex flex-col gap-1 p-3.5 rounded-xl bg-slate-50 border border-slate-100 relative group">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 font-medium">Account Number</span>
              <button 
                onClick={() => setShowFullAccount(!showFullAccount)}
                className="text-slate-400 hover:text-teal transition-colors"
                title="Toggle unmasked view"
              >
                {showFullAccount ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
            <span className="text-sm font-mono font-bold text-navy truncate">
              {showFullAccount ? (acc.account_number || 'Not Found') : (acc.masked_account_number || 'Not Found')}
            </span>
          </div>

          {/* IFSC Code */}
          <div className="flex flex-col gap-1 p-3.5 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-slate-400 font-medium">IFSC / Routing Code</span>
            <span className="text-sm font-mono font-bold text-navy truncate">
              {acc.ifsc_code || 'Not Found'}
            </span>
          </div>

          {/* Statement Period */}
          <div className="flex flex-col gap-1 p-3.5 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-slate-400 font-medium">Statement Period</span>
            <span className="text-xs font-semibold text-slate-800 truncate">
              {acc.statement_period_start} to {acc.statement_period_end}
            </span>
          </div>

          {/* Opening Balance */}
          <div className="flex flex-col gap-1 p-3.5 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-slate-400 font-medium">Opening Balance</span>
            <span className="text-sm font-bold font-mono text-slate-800">
              {acc.opening_balance !== null && acc.opening_balance !== undefined
                ? `${acc.currency || 'INR'} ${acc.opening_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                : 'Not Found'}
            </span>
          </div>

          {/* Closing Balance */}
          <div className="flex flex-col gap-1 p-3.5 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-slate-400 font-medium">Closing Balance</span>
            <span className="text-sm font-bold font-mono text-slate-800">
              {acc.closing_balance !== null && acc.closing_balance !== undefined
                ? `${acc.currency || 'INR'} ${acc.closing_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                : 'Not Found'}
            </span>
          </div>

          {/* Audit Metrics */}
          <div className="flex flex-col gap-1 p-3.5 rounded-xl bg-teal-soft/40 border border-teal/20">
            <span className="text-teal font-medium">Audit Summary</span>
            <div className="flex items-center justify-between text-xs font-semibold text-navy">
              <span>{transactions.length} Extracted</span>
              <span className={reviewNeededCount > 0 ? 'text-amber-600' : 'text-emerald-600'}>
                {reviewNeededCount} Need Review
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Editable Transaction Table Section */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        {/* Table Toolbar */}
        <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50/50">
          <div className="flex items-center gap-3">
            <span className="font-bold text-navy text-sm">Extracted Transactions</span>
            <span className="px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 text-xs font-semibold">
              {filteredTxns.length} records
            </span>
            <span className="text-xs text-slate-400 italic">
              (Click the edit icon on any row to correct dates, descriptions, or amounts)
            </span>
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search narration, date, category..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full h-9 pl-9 pr-3 rounded-lg bg-white border border-slate-200 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-teal"
            />
          </div>
        </div>

        {/* Transactions Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4 w-12 text-center">#</th>
                <th className="py-3 px-4 w-28">Date</th>
                <th className="py-3 px-6">Description / Narration</th>
                <th className="py-3 px-4 text-right w-32">Debit (Dr)</th>
                <th className="py-3 px-4 text-right w-32">Credit (Cr)</th>
                <th className="py-3 px-4 text-right w-36">Balance</th>
                <th className="py-3 px-4 w-32">Status</th>
                <th className="py-3 px-4 text-center w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredTxns.map((t, idx) => {
                const isEditing = editingTxnId === t.id;
                const hasFlags = t.validation_flags && t.validation_flags.length > 0;
                return (
                  <tr 
                    key={t.id}
                    className={`hover:bg-slate-50/80 transition-colors ${
                      isEditing ? 'bg-amber-50/40' : saveSuccessId === t.id ? 'bg-emerald-50/40' : ''
                    }`}
                  >
                    <td className="py-3 px-4 text-center text-slate-400 font-mono text-[11px]">
                      {idx + 1}
                    </td>

                    {/* Date */}
                    <td className="py-3 px-4 font-mono">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editForm.date || ''}
                          onChange={(e) => setEditForm({ ...editForm, date: e.target.value })}
                          className="w-full h-7 px-2 border border-slate-300 rounded text-xs bg-white focus:outline-none focus:ring-1 focus:ring-teal"
                        />
                      ) : (
                        <span className="text-slate-700">{t.date}</span>
                      )}
                    </td>

                    {/* Description */}
                    <td className="py-3 px-6">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editForm.description || ''}
                          onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                          className="w-full h-7 px-2 border border-slate-300 rounded text-xs bg-white focus:outline-none focus:ring-1 focus:ring-teal"
                        />
                      ) : (
                        <div className="flex flex-col">
                          <span className="font-medium text-slate-900">{t.description}</span>
                          {hasFlags && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {t.validation_flags.map((flag, fIdx) => (
                                <span key={fIdx} className="px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 text-[9px] font-mono">
                                  {flag}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </td>

                    {/* Debit */}
                    <td className="py-3 px-4 text-right font-mono">
                      {isEditing ? (
                        <input
                          type="number"
                          step="0.01"
                          value={editForm.debit || 0}
                          onChange={(e) => setEditForm({ ...editForm, debit: parseFloat(e.target.value) || 0 })}
                          className="w-full h-7 px-2 border border-slate-300 rounded text-xs text-right bg-white focus:outline-none focus:ring-1 focus:ring-teal"
                        />
                      ) : t.debit && t.debit > 0 ? (
                        <span className="text-red-600 font-medium">
                          -{t.debit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </span>
                      ) : (
                        <span className="text-slate-300">-</span>
                      )}
                    </td>

                    {/* Credit */}
                    <td className="py-3 px-4 text-right font-mono">
                      {isEditing ? (
                        <input
                          type="number"
                          step="0.01"
                          value={editForm.credit || 0}
                          onChange={(e) => setEditForm({ ...editForm, credit: parseFloat(e.target.value) || 0 })}
                          className="w-full h-7 px-2 border border-slate-300 rounded text-xs text-right bg-white focus:outline-none focus:ring-1 focus:ring-teal"
                        />
                      ) : t.credit && t.credit > 0 ? (
                        <span className="text-emerald-600 font-medium">
                          +{t.credit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </span>
                      ) : (
                        <span className="text-slate-300">-</span>
                      )}
                    </td>

                    {/* Balance */}
                    <td className="py-3 px-4 text-right font-mono font-medium text-slate-800">
                      {isEditing ? (
                        <input
                          type="number"
                          step="0.01"
                          value={editForm.balance !== null ? editForm.balance : ''}
                          onChange={(e) => setEditForm({ ...editForm, balance: parseFloat(e.target.value) || 0 })}
                          className="w-full h-7 px-2 border border-slate-300 rounded text-xs text-right bg-white focus:outline-none focus:ring-1 focus:ring-teal"
                        />
                      ) : t.balance !== null && t.balance !== undefined ? (
                        t.balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })
                      ) : (
                        <span className="text-slate-300">N/A</span>
                      )}
                    </td>

                    {/* Review Status */}
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold flex items-center gap-1 w-fit ${
                        t.review_status === 'Verified'
                          ? 'bg-emerald-100 text-emerald-800'
                          : t.review_status === 'Corrected'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}>
                        {t.review_status === 'Verified' && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                        {t.review_status === 'Needs Review' && <AlertCircle className="w-3 h-3 text-amber-600" />}
                        <span>{t.review_status}</span>
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="py-3 px-4 text-center">
                      {isEditing ? (
                        <div className="flex items-center justify-center gap-1">
                          <button
                            onClick={() => handleSaveEdit(t.id)}
                            className="p-1 rounded bg-teal text-white hover:bg-teal-hover"
                            title="Save changes"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="p-1 rounded bg-slate-200 text-slate-700 hover:bg-slate-300"
                            title="Cancel"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleStartEdit(t)}
                          className="p-1 text-slate-400 hover:text-teal hover:bg-slate-100 rounded transition-colors"
                          title="Edit transaction"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
