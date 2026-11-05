import React, { useState, useEffect } from 'react';
import { useStatement } from '../context/StatementContext';
import { 
  Cpu, 
  Layers, 
  CheckCircle2, 
  AlertCircle, 
  Sliders, 
  RefreshCw, 
  Plus, 
  Search, 
  Filter, 
  ArrowRight,
  TrendingDown,
  TrendingUp,
  BrainCircuit,
  Settings,
  Scale
} from 'lucide-react';
import { api } from '../services/api';

const CATEGORY_COLORS = {
  'Salary': 'bg-emerald-100 text-emerald-800 border-emerald-200',
  'Food & Dining': 'bg-orange-100 text-orange-800 border-orange-200',
  'Food': 'bg-orange-100 text-orange-800 border-orange-200',
  'Shopping': 'bg-pink-100 text-pink-800 border-pink-200',
  'Rent': 'bg-purple-100 text-purple-800 border-purple-200',
  'Utilities & Bills': 'bg-cyan-100 text-cyan-800 border-cyan-200',
  'Utilities': 'bg-cyan-100 text-cyan-800 border-cyan-200',
  'Travel & Transport': 'bg-amber-100 text-amber-800 border-amber-200',
  'Travel': 'bg-amber-100 text-amber-800 border-amber-200',
  'ATM/Cash Withdrawal': 'bg-rose-100 text-rose-800 border-rose-200',
  'ATM Withdrawal': 'bg-rose-100 text-rose-800 border-rose-200',
  'Bank Charges': 'bg-red-100 text-red-800 border-red-200',
  'Interest': 'bg-emerald-50 text-emerald-700 border-emerald-300',
  'Refunds': 'bg-teal-50 text-teal-700 border-teal-300',
  'EMI/Loan': 'bg-amber-50 text-amber-900 border-amber-300',
  'Investments': 'bg-indigo-100 text-indigo-800 border-indigo-200',
  'Transfers': 'bg-blue-100 text-blue-800 border-blue-200',
  'Healthcare': 'bg-teal-100 text-teal-800 border-teal-200',
  'Education': 'bg-lime-100 text-lime-800 border-lime-200',
  'Other Income': 'bg-green-50 text-green-800 border-green-200',
  'Other Expenses': 'bg-stone-100 text-stone-800 border-stone-200',
  'Others': 'bg-slate-100 text-slate-800 border-slate-200'
};

const STANDARD_CATEGORIES = [
  'Salary',
  'Food & Dining',
  'Shopping',
  'Travel & Transport',
  'Utilities & Bills',
  'Rent',
  'Healthcare',
  'Education',
  'EMI/Loan',
  'ATM/Cash Withdrawal',
  'Bank Charges',
  'Interest',
  'Refunds',
  'Transfers',
  'Other Income',
  'Other Expenses',
  'Investments',
  'Others'
];

export const NonLLMClassifier = () => {
  const { 
    statementData, 
    classifyStatement, 
    updateTransaction, 
    setActiveModule,
    loading 
  } = useStatement();

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState('All');
  const [selectedMethodFilter, setSelectedMethodFilter] = useState('All');
  const [showRuleModal, setShowRuleModal] = useState(false);
  const [newRuleCategory, setNewRuleCategory] = useState('Food & Dining');
  const [newRuleKeywords, setNewRuleKeywords] = useState('');
  const [rulesList, setRulesList] = useState({});
  const [modelInfo, setModelInfo] = useState(null);
  const [isRetraining, setIsRetraining] = useState(false);

  const stats = statementData?.classification_stats;
  const transactions = statementData?.transactions || [];

  useEffect(() => {
    fetchRulesAndModel();
  }, []);

  const fetchRulesAndModel = async () => {
    try {
      const [r, info] = await Promise.all([
        api.getRules(),
        api.getClassifierInfo()
      ]);
      setRulesList(r);
      setModelInfo(info);
    } catch (err) {
      console.error('Failed to load classifier details:', err);
    }
  };

  const handleAddRule = async (e) => {
    e.preventDefault();
    if (!newRuleKeywords.trim()) return;
    const keywords = newRuleKeywords.split(',').map(k => k.trim()).filter(Boolean);
    try {
      await api.addRule(newRuleCategory, keywords);
      setNewRuleKeywords('');
      await fetchRulesAndModel();
      // Re-run classifier
      await classifyStatement();
      setShowRuleModal(false);
    } catch (err) {
      alert('Failed to add custom rule');
    }
  };

  const handleRetrain = async () => {
    setIsRetraining(true);
    try {
      await api.retrainClassifier();
      await fetchRulesAndModel();
      await classifyStatement();
    } catch (err) {
      alert('Retraining failed');
    } finally {
      setIsRetraining(false);
    }
  };

  const handleManualReclassify = async (txnId, newCategory) => {
    try {
      await updateTransaction(txnId, { category: newCategory });
    } catch (err) {
      alert('Failed to override category');
    }
  };

  // Filter logic
  const filteredTxns = transactions.filter(t => {
    const s = searchTerm.toLowerCase();
    const matchSearch = (t.description || '').toLowerCase().includes(s) || (t.category || '').toLowerCase().includes(s);
    const matchCat = selectedCategoryFilter === 'All' || t.category === selectedCategoryFilter;
    const matchMethod = selectedMethodFilter === 'All' || t.classification_method === selectedMethodFilter;
    return matchSearch && matchCat && matchMethod;
  });

  return (
    <div className="flex flex-col gap-8 p-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy tracking-tight">Non-LLM Transaction Classification</h1>
          <p className="text-sm text-slate-500 mt-1">
            Rule-Based Classification & Traditional Machine Learning
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowRuleModal(true)}
            className="px-4 py-2 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-semibold hover:bg-slate-50 transition-all shadow-sm flex items-center gap-2"
          >
            <Sliders className="w-3.5 h-3.5 text-teal" />
            <span>Manage Classification Rules</span>
          </button>

          <button
            onClick={() => setActiveModule('reconciliation')}
            className="px-5 py-2 rounded-xl bg-navy text-white text-xs font-semibold hover:bg-navy-light transition-all shadow-sm flex items-center gap-2"
          >
            <Scale className="w-4 h-4 text-teal" />
            <span>Proceed to Reconciliation & Export</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* KPI Metrics Grid (Stitch Styled Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Classified */}
        <div className="p-5 rounded-2xl bg-[#E8EFFF] border border-blue-100 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-blue-700">Auto-Classified</span>
            <div className="w-8 h-8 rounded-lg bg-white/80 flex items-center justify-center text-blue-700">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold text-navy">
              {stats?.total_classified || transactions.length}
              <span className="text-xs font-medium text-slate-500 ml-1">txns</span>
            </div>
            <p className="text-xs text-blue-800/80 mt-1">
              Avg. Confidence: <strong>{Math.round((stats?.average_confidence || 0) * 100)}%</strong>
            </p>
          </div>
        </div>

        {/* Card 2: Rule-Based Matches */}
        <div className="p-5 rounded-2xl bg-[#E5F7EF] border border-emerald-100 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-700">Rule-Based Matches</span>
            <div className="w-8 h-8 rounded-lg bg-white/80 flex items-center justify-center text-emerald-700">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold text-navy">
              {stats?.rule_based_pct || 0}%
              <span className="text-xs font-medium text-slate-500 ml-1">({stats?.rule_based_count || 0} txns)</span>
            </div>
            <p className="text-xs text-emerald-800/80 mt-1">
              Deterministic vendor & merchant keywords
            </p>
          </div>
        </div>

        {/* Card 3: Machine Learning Matches */}
        <div className="p-5 rounded-2xl bg-[#F0EBFF] border border-purple-100 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-purple-700">Machine Learning Classification</span>
            <div className="w-8 h-8 rounded-lg bg-white/80 flex items-center justify-center text-purple-700">
              <BrainCircuit className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold text-navy">
              {stats?.ml_pct || 0}%
              <span className="text-xs font-medium text-slate-500 ml-1">({stats?.ml_count || 0} txns)</span>
            </div>
            <p className="text-xs text-purple-800/80 mt-1">
              TF-IDF Vectorizer + Naive Bayes Classifier
            </p>
          </div>
        </div>

        {/* Card 4: Needs Review */}
        <div className="p-5 rounded-2xl bg-[#FFF0E5] border border-orange-100 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-orange-700">Exceptions & Review</span>
            <div className="w-8 h-8 rounded-lg bg-white/80 flex items-center justify-center text-orange-700">
              <AlertCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold text-navy">
              {stats?.needs_review_count || 0}
              <span className="text-xs font-medium text-slate-500 ml-1">({stats?.needs_review_pct || 0}%)</span>
            </div>
            <p className="text-xs text-orange-800/80 mt-1">
              Confidence &lt; 70% or unclassified entries
            </p>
          </div>
        </div>
      </div>

      {/* Transaction Amount by Category Bar */}
      {stats?.spend_by_category && Object.keys(stats.spend_by_category).length > 0 && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
          <h2 className="text-sm font-bold text-navy uppercase tracking-wider mb-4">
            Transaction Amount by Category
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {Object.entries(stats.spend_by_category)
              .filter(([_, val]) => val > 0)
              .sort((a, b) => b[1] - a[1])
              .map(([cat, amount]) => {
                const badgeClass = CATEGORY_COLORS[cat] || 'bg-slate-100 text-slate-800 border-slate-200';
                return (
                  <div key={cat} className={`p-3 rounded-xl border flex flex-col justify-between ${badgeClass}`}>
                    <span className="text-[11px] font-semibold truncate">{cat}</span>
                    <span className="text-sm font-bold font-mono mt-2">
                      INR {amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Classified Transactions Audit Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        {/* Filter Controls Bar */}
        <div className="p-4 border-b border-slate-100 flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-slate-50/50">
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative w-64">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search transactions..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full h-9 pl-9 pr-3 rounded-lg bg-white border border-slate-200 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-teal"
              />
            </div>

            {/* Category Filter */}
            <select
              value={selectedCategoryFilter}
              onChange={(e) => setSelectedCategoryFilter(e.target.value)}
              className="h-9 px-3 rounded-lg bg-white border border-slate-200 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-teal"
            >
              <option value="All">All Categories</option>
              {STANDARD_CATEGORIES.map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>

            {/* Method Filter */}
            <select
              value={selectedMethodFilter}
              onChange={(e) => setSelectedMethodFilter(e.target.value)}
              className="h-9 px-3 rounded-lg bg-white border border-slate-200 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-teal"
            >
              <option value="All">All Methods</option>
              <option value="Rule-Based">Rule-Based Only</option>
              <option value="ML Classifier">ML Classifier Only</option>
              <option value="Manual Override">Manual Overrides</option>
            </select>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span>Showing <strong>{filteredTxns.length}</strong> of {transactions.length}</span>
            <button
              onClick={() => classifyStatement()}
              disabled={loading}
              className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 transition-colors"
              title="Re-run classification"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Table Content */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4 w-28">Date</th>
                <th className="py-3 px-6">Transaction Description</th>
                <th className="py-3 px-4 text-right w-28">Debit</th>
                <th className="py-3 px-4 text-right w-28">Credit</th>
                <th className="py-3 px-4 w-44">Assigned Category</th>
                <th className="py-3 px-4 w-36">Method</th>
                <th className="py-3 px-4 w-28">Confidence</th>
                <th className="py-3 px-4 w-32">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredTxns.map((t) => {
                const badgeColor = CATEGORY_COLORS[t.category] || 'bg-slate-100 text-slate-800 border-slate-200';
                return (
                  <tr key={t.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4 font-mono text-slate-700">{t.date}</td>
                    <td className="py-3 px-6">
                      <div className="font-semibold text-slate-900">{t.description}</div>
                      {/* Explainable classification details */}
                      {t.explanation && (
                        <div className="text-[11px] text-slate-500 mt-1 flex flex-wrap items-center gap-1.5">
                          <span className="font-bold text-teal text-[10px] uppercase tracking-wider">Why:</span>
                          <span className="text-slate-600">{t.explanation.reason}</span>
                          {t.explanation.matched_keyword && (
                            <span className="px-1.5 py-0.2 bg-teal-50 text-teal-700 rounded text-[10px] font-mono border border-teal-200">
                              match: "{t.explanation.matched_keyword}"
                            </span>
                          )}
                          {t.explanation.model_probabilities && (
                            <span className="text-[10px] text-slate-400 font-mono" title={JSON.stringify(t.explanation.model_probabilities)}>
                              top probs: {Object.entries(t.explanation.model_probabilities).slice(0, 2).map(([k, v]) => `${k} (${Math.round(v * 100)}%)`).join(', ')}
                            </span>
                          )}
                        </div>
                      )}
                      {t.explanation?.duplicate_warning && (
                        <div className="text-[10px] text-amber-700 font-medium mt-1 flex items-center gap-1 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 w-fit">
                          <span>⚠️ {t.explanation.duplicate_warning}</span>
                        </div>
                      )}
                      {t.ocr_correction && (
                        <div className="text-[10px] text-blue-700 font-medium mt-0.5 flex items-center gap-1 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 w-fit">
                          <span>OCR Corrected: {t.ocr_correction.reason}</span>
                        </div>
                      )}
                    </td>
                    
                    {/* Debit */}
                    <td className="py-3 px-4 text-right font-mono">
                      {t.debit && t.debit > 0 ? (
                        <span className="text-red-600">
                          -{t.debit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </span>
                      ) : <span className="text-slate-300">-</span>}
                    </td>

                    {/* Credit */}
                    <td className="py-3 px-4 text-right font-mono">
                      {t.credit && t.credit > 0 ? (
                        <span className="text-emerald-600">
                          +{t.credit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </span>
                      ) : <span className="text-slate-300">-</span>}
                    </td>

                    {/* Category Selector Dropdown */}
                    <td className="py-3 px-4">
                      <select
                        value={t.category}
                        onChange={(e) => handleManualReclassify(t.id, e.target.value)}
                        className={`h-7 px-2 rounded-lg text-xs font-semibold border ${badgeColor} cursor-pointer focus:outline-none`}
                      >
                        {STANDARD_CATEGORIES.map(c => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </td>

                    {/* Method Badge */}
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

                    {/* Confidence */}
                    <td className="py-3 px-4">
                      {t.classification_method === 'Manual Override' || t.confidence === null || t.confidence === undefined ? (
                        <span className="font-mono text-xs font-semibold text-slate-400">N/A</span>
                      ) : (
                        <div className="flex items-center gap-1.5 font-mono text-xs">
                          <span className="font-semibold text-slate-700">
                            {Math.round((t.confidence || 0) * 100)}%
                          </span>
                          <div className="w-12 bg-slate-200 h-1.5 rounded-full overflow-hidden">
                            <div 
                              className={`h-full rounded-full ${
                                t.confidence >= 0.85 ? 'bg-emerald-500' :
                                t.confidence >= 0.60 ? 'bg-blue-500' : 'bg-amber-500'
                              }`}
                              style={{ width: `${Math.round((t.confidence || 0) * 100)}%` }}
                            />
                          </div>
                        </div>
                      )}
                    </td>

                    {/* Review Status */}
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold flex items-center gap-1 w-fit ${
                        t.review_status === 'Verified'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}>
                        {t.review_status === 'Verified' ? <CheckCircle2 className="w-3 h-3 text-emerald-600" /> : <AlertCircle className="w-3 h-3 text-amber-600" />}
                        <span>{t.review_status}</span>
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Rules & ML Architecture Modal */}
      {showRuleModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-xl border border-slate-200 flex flex-col gap-5 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Sliders className="w-5 h-5 text-teal" />
                <h3 className="font-bold text-navy text-base">Classification Engine Rules & ML Model</h3>
              </div>
              <button 
                onClick={() => setShowRuleModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            {/* Add Custom Keyword Rule Form */}
            <form onSubmit={handleAddRule} className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-3">
              <span className="text-xs font-bold text-navy uppercase tracking-wider">
                Add Custom Heuristic Rule
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="text-[11px] text-slate-500 block mb-1">Target Category</label>
                  <select
                    value={newRuleCategory}
                    onChange={(e) => setNewRuleCategory(e.target.value)}
                    className="w-full h-8 px-2 rounded-lg bg-white border border-slate-200 text-xs text-slate-800 focus:outline-none"
                  >
                    {STANDARD_CATEGORIES.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <label className="text-[11px] text-slate-500 block mb-1">Keywords (comma-separated)</label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="e.g. NETFLIX, SPOTIFY, CANVA"
                      value={newRuleKeywords}
                      onChange={(e) => setNewRuleKeywords(e.target.value)}
                      className="flex-1 h-8 px-3 rounded-lg bg-white border border-slate-200 text-xs text-slate-800 focus:outline-none"
                    />
                    <button
                      type="submit"
                      className="px-3 h-8 bg-teal text-white rounded-lg text-xs font-semibold hover:bg-teal-hover shrink-0 flex items-center gap-1"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add</span>
                    </button>
                  </div>
                </div>
              </div>
            </form>

            {/* Model Architecture Metadata */}
            {modelInfo && (
              <div className="p-4 rounded-xl bg-purple-50/50 border border-purple-100 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-purple-900 uppercase tracking-wider">
                    Supervised Machine Learning Model
                  </span>
                  <button
                    onClick={handleRetrain}
                    disabled={isRetraining}
                    className="px-2.5 py-1 rounded-md bg-purple-600 text-white text-[11px] font-semibold hover:bg-purple-700 flex items-center gap-1 disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3 h-3 ${isRetraining ? 'animate-spin' : ''}`} />
                    <span>{isRetraining ? 'Training...' : 'Train / Retrain ML Model'}</span>
                  </button>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs text-slate-600 pt-1">
                  <div>Model Type: <strong>{modelInfo.model_type}</strong></div>
                  <div>Vocabulary Size: <strong>{modelInfo.vocabulary_size} tokens</strong></div>
                  <div>Target Classes: <strong>{modelInfo.classes?.length || 13} categories</strong></div>
                </div>
              </div>
            )}

            {/* Existing Rules Summary */}
            <div className="flex flex-col gap-2">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Configured Keyword Categories ({Object.keys(rulesList).length})
              </span>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {Object.entries(rulesList).map(([cat, keywords]) => (
                  <div key={cat} className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-xs">
                    <strong className="text-navy">{cat}</strong> ({keywords.length} keywords):
                    <div className="flex flex-wrap gap-1 mt-1">
                      {keywords.slice(0, 10).map((kw, idx) => (
                        <span key={idx} className="px-1.5 py-0.5 rounded bg-slate-200/70 text-slate-700 text-[10px] font-mono">
                          {kw}
                        </span>
                      ))}
                      {keywords.length > 10 && (
                        <span className="text-[10px] text-slate-400 self-center">+{keywords.length - 10} more</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
