import React, { useState, useEffect } from 'react';
import { useStatement } from '../context/StatementContext';
import { api } from '../services/api';
import { 
  CloudUpload, 
  FileText, 
  Cpu, 
  Scale, 
  CheckCircle2, 
  ShieldCheck, 
  Layers,
  Sparkles,
  BarChart3
} from 'lucide-react';

export const Sidebar = () => {
  const { activeModule, setActiveModule, statementData, processingStage } = useStatement();
  const effectiveStage = statementData?.metadata?.current_stage || processingStage || 1;
  const [ocrEngine, setOcrEngine] = useState('Detecting...');

  useEffect(() => {
    api.getSystemInfo().then(info => {
      if (info?.ocr_engine) setOcrEngine(info.ocr_engine);
    }).catch(() => setOcrEngine('Tesseract'));
  }, []);

  const navItems = [
    {
      id: 'ingestion',
      name: 'Statement Upload & Processing',
      stage: 'Stage 1-2',
      icon: CloudUpload,
      desc: 'PDF Upload, Type Detection & Processing Queue'
    },
    {
      id: 'parser',
      name: 'Statement Extraction & Validation',
      stage: 'Stage 3-4',
      icon: FileText,
      desc: 'Account Details, Transaction Extraction & Data Review'
    },
    {
      id: 'classifier',
      name: 'Non-LLM Transaction Classification',
      stage: 'Stage 5',
      icon: Cpu,
      desc: 'Rule-Based Classification & Traditional Machine Learning'
    },
    {
      id: 'reconciliation',
      name: 'Reconciliation & Export',
      stage: 'Stage 6',
      icon: Scale,
      desc: 'Balance Verification, Transaction Summary & Excel/CSV Export'
    }
  ];

  const meta = statementData?.metadata;

  return (
    <aside className="fixed left-0 top-0 h-full w-[260px] bg-white border-r border-slate-200 z-50 flex flex-col justify-between shadow-[0_1px_8px_rgba(0,0,0,0.02)]">
      <div className="flex flex-col">
        {/* Brand Header */}
        <div className="h-16 px-5 flex items-center justify-between border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-navy flex items-center justify-center text-teal-light shadow-sm">
              <ShieldCheck className="w-5 h-5 text-teal" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-base tracking-tight text-navy">StatementIQ</span>
              <span className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">BANK STATEMENT INTELLIGENCE</span>
            </div>
          </div>
          <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-[10px] font-semibold tracking-wider">
            v1.0
          </span>
        </div>

        {/* Section Label */}
        <div className="px-5 pt-5 pb-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Processing Pipeline
          </span>
        </div>

        {/* Nav Links */}
        <nav className="flex flex-col gap-1.5 px-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeModule === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveModule(item.id)}
                className={`flex items-start gap-3 px-3 py-2.5 rounded-xl transition-all text-left relative ${
                  isActive
                    ? 'bg-slate-50 text-navy font-semibold shadow-sm border border-slate-200/80 before:content-[""] before:absolute before:left-0 before:top-2 before:bottom-2 before:w-[3.5px] before:bg-teal before:rounded-r-full'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <Icon className={`w-5 h-5 mt-0.5 shrink-0 ${isActive ? 'text-teal' : 'text-slate-400'}`} />
                <div className="flex flex-col">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-medium leading-tight">{item.name}</span>
                  </div>
                  <span className="text-[11px] text-slate-400 font-normal mt-0.5 leading-tight">
                    {item.desc}
                  </span>
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Status & Engine Health */}
      <div className="p-4 m-3 rounded-2xl bg-slate-50 border border-slate-200/60 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-teal animate-pulse"></span>
            Non-LLM Engine
          </span>
          <span className="text-[11px] font-bold text-teal">Active</span>
        </div>

        <div className="flex flex-col gap-1 text-[11px] text-slate-600">
          <div className="flex justify-between">
            <span className="text-slate-400">OCR Engine:</span>
            <span className="font-medium text-slate-700">{ocrEngine}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">ML Model:</span>
            <span className="font-medium text-slate-700">TF-IDF + Naive Bayes</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Pipeline Stage:</span>
            <span className="font-medium text-navy">{effectiveStage} of 6</span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
          <div 
            className="bg-teal h-full rounded-full transition-all duration-500 ease-out"
            style={{ width: `${Math.round((effectiveStage / 6) * 100)}%` }}
          />
        </div>
      </div>
    </aside>
  );
};
