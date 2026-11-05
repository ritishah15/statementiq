import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

const StatementContext = createContext();

export const useStatement = () => {
  const context = useContext(StatementContext);
  if (!context) {
    throw new Error('useStatement must be used within a StatementProvider');
  }
  return context;
};

export const StatementProvider = ({ children }) => {
  const [statements, setStatements] = useState([]);
  const [currentStatementId, setCurrentStatementId] = useState(null);
  const [statementData, setStatementData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [processingStage, setProcessingStage] = useState(1);
  const [error, setError] = useState(null);
  const [activeModule, setActiveModule] = useState('ingestion'); // ingestion, parser, classifier, reconciliation
  const [availableSamples, setAvailableSamples] = useState([]);

  // Load initial statement list and sample files
  useEffect(() => {
    fetchStatements();
    fetchSamples();
  }, []);

  const fetchStatements = async () => {
    try {
      const list = await api.listStatements();
      setStatements(list || []);
      const savedId = localStorage.getItem('statementiq_active_id');
      const targetId = (savedId && list.some(s => s.statement_id === savedId))
        ? savedId
        : (currentStatementId || (list && list.length > 0 ? list[list.length - 1].statement_id : null));
      
      if (targetId && !statementData) {
        selectStatement(targetId);
      }
    } catch (err) {
      console.error('Failed to list statements:', err);
    }
  };

  const fetchSamples = async () => {
    try {
      const samples = await api.listSampleStatements();
      setAvailableSamples(samples || []);
    } catch (err) {
      console.error('Failed to load sample statements:', err);
    }
  };

  const selectStatement = async (id) => {
    if (!id) return;
    setCurrentStatementId(id);
    localStorage.setItem('statementiq_active_id', id);
    setLoading(true);
    setError(null);
    try {
      const data = await api.getStatement(id);
      setStatementData(data);
      if (data?.metadata?.current_stage) {
        setProcessingStage(data.metadata.current_stage);
      }
      setStatements(prev => prev.map(s => s.statement_id === id ? data.metadata : s));
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to fetch statement details');
    } finally {
      setLoading(false);
    }
  };

  const uploadFile = async (file, allowDuplicate = false) => {
    setLoading(true);
    setError(null);
    try {
      const meta = await api.uploadStatement(file, allowDuplicate);
      await fetchStatements();
      await selectStatement(meta.statement_id);
      setActiveModule('ingestion');
      return meta;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to upload PDF statement';
      setError(msg);
      throw new Error(msg);
    } finally {
      setLoading(false);
    }
  };

  const uploadMultipleFiles = async (fileList) => {
    setLoading(true);
    setError(null);
    const errors = [];
    let lastSuccessMeta = null;

    for (const file of fileList) {
      try {
        const meta = await api.uploadStatement(file, false);
        lastSuccessMeta = meta;
      } catch (err) {
        errors.push(`${file.name}: ${err?.response?.data?.detail || err.message}`);
      }
    }

    await fetchStatements();
    if (lastSuccessMeta) {
      await selectStatement(lastSuccessMeta.statement_id);
    }
    setLoading(false);

    if (errors.length > 0) {
      const errorMsg = errors.join(' | ');
      setError(errorMsg);
      return { success: !errors.length, errors };
    }
    return { success: true, errors: [] };
  };

  const loadSample = async (filename) => {
    setLoading(true);
    setError(null);
    try {
      const meta = await api.loadSampleStatement(filename);
      await fetchStatements();
      await selectStatement(meta.statement_id);
      return meta;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to load sample statement';
      setError(msg);
      throw new Error(msg);
    } finally {
      setLoading(false);
    }
  };

  const processStatement = async (id = currentStatementId) => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setProcessingStage(3); // Text/OCR Extraction
      const res = await api.processStatement(id);
      setProcessingStage(4); // Transaction Parsing
      await fetchStatements();
      await selectStatement(id);
      setActiveModule('parser');
      return res;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Extraction failed';
      setError(msg);
      await fetchStatements();
      if (id) await selectStatement(id);
      throw new Error(msg);
    } finally {
      setLoading(false);
    }
  };

  const retryStatement = async (id = currentStatementId) => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.retryStatement(id);
      await fetchStatements();
      await selectStatement(id);
      if (res?.metadata?.current_stage >= 4) {
        setActiveModule('parser');
      }
      return res;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Retry failed';
      setError(msg);
      await fetchStatements();
      if (id) await selectStatement(id);
      throw new Error(msg);
    } finally {
      setLoading(false);
    }
  };

  const classifyStatement = async (id = currentStatementId) => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setProcessingStage(5); // Classifying
      const res = await api.classifyStatement(id);
      setProcessingStage(6); // Completed
      await fetchStatements();
      await selectStatement(id);
      setActiveModule('classifier');
      return res;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Classification failed';
      setError(msg);
      throw new Error(msg);
    } finally {
      setLoading(false);
    }
  };

  const updateTransaction = async (txnId, updateData) => {
    if (!currentStatementId) return;
    try {
      const updatedTxn = await api.updateTransaction(currentStatementId, txnId, updateData);
      const freshData = await api.getStatement(currentStatementId);
      setStatementData(freshData);
      setStatements(prev => prev.map(s => s.statement_id === currentStatementId ? freshData.metadata : s));
      return updatedTxn;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to update transaction';
      setError(msg);
      throw new Error(msg);
    }
  };

  const deleteStatement = async (id) => {
    try {
      await api.deleteStatement(id);
      const remaining = statements.filter(s => s.statement_id !== id);
      setStatements(remaining);
      if (currentStatementId === id) {
        if (remaining.length > 0) {
          selectStatement(remaining[0].statement_id);
        } else {
          setCurrentStatementId(null);
          setStatementData(null);
          localStorage.removeItem('statementiq_active_id');
        }
      }
    } catch (err) {
      setError('Failed to delete statement');
    }
  };

  const clearAllStatements = async () => {
    setLoading(true);
    try {
      await api.clearAllStatements();
      setStatements([]);
      setCurrentStatementId(null);
      setStatementData(null);
      localStorage.removeItem('statementiq_active_id');
    } catch (err) {
      setError('Failed to clear statements queue');
    } finally {
      setLoading(false);
    }
  };

  const value = {
    statements,
    currentStatementId,
    statementData,
    loading,
    processingStage: statementData?.metadata?.current_stage || processingStage,
    error,
    activeModule,
    availableSamples,
    setActiveModule,
    selectStatement,
    uploadFile,
    uploadMultipleFiles,
    retryStatement,
    loadSample,
    processStatement,
    classifyStatement,
    updateTransaction,
    deleteStatement,
    clearAllStatements,
    fetchStatements
  };

  return (
    <StatementContext.Provider value={value}>
      {children}
    </StatementContext.Provider>
  );
};
