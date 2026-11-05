import axios from 'axios';

const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '') + '/api';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 90000, // 90s timeout for OCR on large scanned PDFs
});

export const api = {
  // Statements & Upload
  uploadStatement: async (file, allowDuplicate = false) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await client.post(`/statements/upload?allow_duplicate=${allowDuplicate}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },

  listStatements: async () => {
    const res = await client.get('/statements');
    return res.data;
  },

  getStatement: async (id) => {
    const res = await client.get(`/statements/${id}`);
    return res.data;
  },

  deleteStatement: async (id) => {
    const res = await client.delete(`/statements/${id}`);
    return res.data;
  },

  clearAllStatements: async () => {
    const res = await client.delete('/statements');
    return res.data;
  },

  getSystemInfo: async () => {
    const res = await client.get('/system');
    return res.data;
  },

  // Processing Pipeline
  processStatement: async (id) => {
    const res = await client.post(`/statements/${id}/process`);
    return res.data;
  },

  retryStatement: async (id) => {
    const res = await client.post(`/statements/${id}/retry`);
    return res.data;
  },

  classifyStatement: async (id) => {
    const res = await client.post(`/statements/${id}/classify`);
    return res.data;
  },

  getTransactions: async (id) => {
    const res = await client.get(`/statements/${id}/transactions`);
    return res.data;
  },

  updateTransaction: async (statementId, txnId, data) => {
    const res = await client.put(`/statements/${statementId}/transactions/${txnId}`, data);
    return res.data;
  },

  getResults: async (id) => {
    const res = await client.get(`/statements/${id}/results`);
    return res.data;
  },

  // Export URLs
  getExcelExportUrl: (id) => `${API_BASE}/statements/${id}/export/excel`,
  getCsvExportUrl: (id) => `${API_BASE}/statements/${id}/export/csv`,
  getAllExcelExportUrl: (ids) => ids ? `${API_BASE}/statements/export/excel?statement_ids=${ids}` : `${API_BASE}/statements/export/excel`,
  getAllCsvExportUrl: (ids) => ids ? `${API_BASE}/statements/export/csv?statement_ids=${ids}` : `${API_BASE}/statements/export/csv`,

  // Classifier Rules & ML management
  getRules: async () => {
    const res = await client.get('/classifier/rules');
    return res.data;
  },

  addRule: async (category, keywords) => {
    const res = await client.post('/classifier/rules', { category, keywords });
    return res.data;
  },

  getClassifierInfo: async () => {
    const res = await client.get('/classifier/info');
    return res.data;
  },

  retrainClassifier: async () => {
    const res = await client.post('/classifier/retrain');
    return res.data;
  },

  // Samples
  listSampleStatements: async () => {
    const res = await client.get('/sample-statements');
    return res.data;
  },

  loadSampleStatement: async (filename) => {
    const res = await client.post(`/sample-statements/${filename}/load`);
    return res.data;
  }
};
