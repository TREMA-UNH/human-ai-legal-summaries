import React, { useState, useRef, useEffect } from 'react';
import { Upload, Play, FileText, Trash2, Eye, AlertCircle, UserCheck } from 'lucide-react';
import EvaluationReport from './EvaluationReport.jsx';
import CitationValidator from './CitationValidator.jsx';
import NuggetViewer from './NuggetViewer.jsx';

const NuggetPipelineUI = () => {
  const [depositionFile, setDepositionFile] = useState(null);
  const [summaryFile, setSummaryFile] = useState(null);
  const [status, setStatus] = useState("ready"); // ready | running | completed | error
  const [currentStep, setCurrentStep] = useState("");
  const [evaluationData, setEvaluationData] = useState(null);
  const [validationData, setValidationData] = useState(null); // For citation validation
  const [comparisonData, setComparisonData] = useState(null); // For nugget comparison


  const [showReport, setShowReport] = useState(false);
  const [showValidator, setShowValidator] = useState(false);
  const [showPairSelector, setShowPairSelector] = useState(false);
  const [showDepositionSelector, setShowDepositionSelector] = useState(false);

  const [filePairs, setFilePairs] = useState([]);
  const [currentPairIndex, setCurrentPairIndex] = useState(-1);
  const [error, setError] = useState('');
  const [logs, setLogs] = useState([]);
  const [showLogger, setShowLogger] = useState(false);
  const depositionInputRef = useRef(null);
  const summaryInputRef = useRef(null);
  const [depositionText, setDepositionText] = useState("");
  const [showNuggetViewer, setShowNuggetViewer] = useState(false);
  const [currentDepositionIndex, setCurrentDepositionIndex] = useState(-1);

  // Fetch file pairs on mount
  useEffect(() => {
    const fetchFilePairs = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/file-pairs');
        const data = await response.json();
        if (data.status === 'success') {
          setFilePairs(data.pairs);
        } else {
          setError('Failed to fetch file pairs');
        }
      } catch (err) {
        setError('Error fetching file pairs: ' + err.message);
      }
    };
    fetchFilePairs();
  }, []);

  const addLogMessage = (message, type = 'info') => {
    setLogs((prevLogs) => [
      ...prevLogs,
      { message, type, timestamp: new Date().toLocaleTimeString() }
    ]);
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const handleDepositionUpload = (event) => {
    const uploadedFile = event.target.files[0];
    if (uploadedFile) {
      setDepositionFile({
        name: uploadedFile.name,
        size: uploadedFile.size,
        path: URL.createObjectURL(uploadedFile),
        file: uploadedFile
      });
      setError('');
    }
  };

  const handleSummaryUpload = (event) => {
    const uploadedFile = event.target.files[0];
    if (uploadedFile) {
      setSummaryFile({
        name: uploadedFile.name,
        size: uploadedFile.size,
        path: URL.createObjectURL(uploadedFile),
        file: uploadedFile
      });
      setError('');
    }
  };

  const formatSize = (bytes) => {
    return (bytes / 1024).toFixed(2) + ' KB';
  };


  const PairSelector = ({ onSelect, onClose }) => {
    const [filePairs, setFilePairs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
      const fetchFilePairs = async () => {
        try {
          setLoading(true);
          const response = await fetch('http://localhost:8000/api/file-pairs');
          const data = await response.json();
          if (data.status === 'success') {
            setFilePairs(data.pairs);
          } else {
            setError('Failed to fetch file pairs');
          }
        } catch (err) {
          setError('Error fetching file pairs: ' + err.message);
        } finally {
          setLoading(false);
        }
      };
      fetchFilePairs();
    }, []);


    // Group pairs by case_name
    const groupedPairs = filePairs.reduce((acc, pair) => {
      if (!acc[pair.case_name]) {
        acc[pair.case_name] = [];
      }
      acc[pair.case_name].push(pair);
      return acc;
    }, {});

    return (
      <div className="fixed inset-0 bg-black bg-opacity-80 z-50 flex items-center justify-center p-4">
        <div className="bg-white text-black w-full max-w-4xl rounded-xl overflow-hidden relative flex flex-col">
          <div className="flex items-center justify-between p-4 border-b bg-white">
            <h2 className="text-xl font-bold">Select Deposition-Summary Pair</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl font-bold leading-none p-1 hover:bg-gray-100 rounded"
            >
              ×
            </button>
          </div>
          <div className="p-6 overflow-auto max-h-[80vh]">
            {loading && <p className="text-blue-500">Loading pairs...</p>}
            {error && <p className="text-red-500">{error}</p>}
            {Object.keys(groupedPairs).length === 0 && !loading && !error && (
              <p className="text-gray-600">No file pairs available.</p>
            )}
            {Object.entries(groupedPairs).map(([case_name, pairs]) => (
              <div key={case_name} className="mb-6">
                <h3 className="text-lg font-semibold mb-3">Case {case_name}</h3>
                <ul className="space-y-3">
                  {pairs.map((pair) => (
                    <li
                      key={pair.pair_id}
                      className="p-4 bg-gray-100 rounded-lg border-l-4 border-[#6F7D95] hover:bg-gray-200 cursor-pointer"
                      onClick={() => onSelect(pair)}
                    >
                      <p className="font-medium">Deposition: {pair.deposition}</p>
                      <p className="text-sm text-gray-600">Summary: {pair.summary}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };



  const DepoSelector = ({ onSelect, onClose }) => {
    const [depositions, setDepositions] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
      const fetchDepositions = async () => {
        try {
          setLoading(true);
          const response = await fetch('http://localhost:8000/api/depositions');
          const data = await response.json();
          if (data.status === 'success') {
            setDepositions(data.depositions);
          } else {
            setError('Failed to fetch depositions');
          }
        } catch (err) {
          setError('Error fetching depositions: ' + err.message);
        } finally {
          setLoading(false);
        }
      };
      fetchDepositions();
    }, []);

    const groupedDepositions = depositions.reduce((acc, deposition) => {
      if (!acc[deposition.case_name]) {
        acc[deposition.case_name] = [];
      }
      acc[deposition.case_name].push(deposition);
      return acc;
    }, {});

    return (
      <div className="fixed inset-0 bg-black bg-opacity-80 z-50 flex items-center justify-center p-4">
        <div className="bg-white text-black w-full max-w-4xl rounded-xl overflow-hidden relative flex flex-col">
          <div className="flex items-center justify-between p-4 border-b bg-white">
            <h2 className="text-xl font-bold">Select A Deposition</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl font-bold leading-none p-1 hover:bg-gray-100 rounded"
            >
              ×
            </button>
          </div>
          <div className="p-6 overflow-auto max-h-[80vh]">
            {loading && <p className="text-blue-500">Loading depositions...</p>}
            {error && <p className="text-red-500">{error}</p>}
            {Object.keys(groupedDepositions).length === 0 && !loading && !error && (
              <p className="text-gray-600">No depositions available.</p>
            )}
            {Object.entries(groupedDepositions).map(([case_name, depositions]) => (
              <div key={case_name} className="mb-6">
                <ul className="space-y-3">
                  {depositions.map((deposition, index) => (
                    <li
                      key={deposition.deposition_id}
                      className="p-4 bg-gray-100 rounded-lg border-l-4 border-[#6F7D95] hover:bg-gray-200 cursor-pointer"
                      onClick={() => onSelect(deposition)}
                    >
                      <p className="font-medium">{deposition.deposition_name}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const runPipeline = async () => {
    if (!depositionFile || !summaryFile) {
      setError('Please upload both deposition and summary files.');
      return;
    }

    setStatus("running");
    setError('');
    setShowLogger(true);
    clearLogs();

    try {
      const formData = new FormData();
      formData.append('deposition', depositionFile.file);
      formData.append('summary', summaryFile.file);
      formData.append('human_annotation', 'false');


      addLogMessage('=== EVALUATION PIPELINE STARTED ===', 'success');
      addLogMessage(`Uploading files: ${depositionFile.name} & ${summaryFile.name}`);

      setCurrentStep("Uploading files and starting pipeline...");

      const response = await fetch('http://localhost:8000/api/run-pipeline', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        addLogMessage(`Backend error response: ${errorText}`, 'error');
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      addLogMessage('Response parsed successfully', 'success');

      setEvaluationData(result);
      addLogMessage('=== PIPELINE COMPLETED SUCCESSFULLY ===', 'success');

      setStatus("completed");
      setCurrentStep("");
      setShowReport(true);
    } catch (err) {
      addLogMessage(`ERROR: ${err.message}`, 'error');
      setError(`Pipeline failed: ${err.message}`);
      setStatus("error");
      setCurrentStep("");
    }
  };

  const runValidationMode = () => {
    if (depositionFile && summaryFile) {
      // Process uploaded files directly
      processUploadedFiles();
    } else {
      // Show pair selector
      setShowPairSelector(true);
    }
  };
  const runComparisonMode = () => {
    if (depositionFile) {
      // Process uploaded files directly
      processUploadedDepositions();
    } else {
      // Show deposition selector
      setShowDepositionSelector(true);

    }
  };

  const processUploadedFiles = async () => {
    if (!depositionFile || !summaryFile) {
      setError('Please upload both deposition and summary files.');
      return;
    }

    setStatus("running");
    setError('');
    setShowLogger(true);
    clearLogs();

    try {
      const formData = new FormData();
      formData.append('deposition', depositionFile.file);
      formData.append('summary', summaryFile.file);
      formData.append('human_annotation', 'true');
      formData.append('citation_tagging', 'true');
      formData.append('nugget_comparison', 'false');



      addLogMessage('=== CITATION VALIDATION MODE STARTED ===', 'success');
      addLogMessage(`Uploading files: ${depositionFile.name} & ${summaryFile.name}`);

      setCurrentStep("Processing files for citation validation...");

      const response = await fetch('http://localhost:8000/api/run-pipeline', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        addLogMessage(`Backend error response: ${errorText}`, 'error');
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      addLogMessage('Response parsed successfully', 'success');

      setValidationData(result);
      addLogMessage('=== READY FOR HUMAN VALIDATION ===', 'success');

      setStatus("completed");
      setCurrentStep("");
      setShowValidator(true);
    } catch (err) {
      addLogMessage(`ERROR: ${err.message}`, 'error');
      setError(`Pipeline failed: ${err.message}`);
      setStatus("error");
      setCurrentStep("");
    }
  };



  const processDepo = async (deposition) => {
    setStatus("running");
    setError('');
    setShowLogger(true);
    clearLogs();

    try {
      addLogMessage('=== DEPOSITION PROCESSING STARTED ===', 'success');
      addLogMessage(`Processing deposition: ${deposition.deposition_name}`);
      setCurrentStep("Processing deposition for nugget generation/loading...");

      // Fetch nuggets
      const response = await fetch('http://localhost:8000/api/process-deposition', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          case_name: deposition.case_name,
          deposition_filename: deposition.deposition_name,
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        addLogMessage(`Backend error response: ${errorText}`, 'error');
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const result = await response.json();
      // console.log('Nuggets result:', result); // Debug log
      addLogMessage('Nuggets response parsed successfully', 'success');

      // Fetch deposition text
      const textResponse = await fetch('http://localhost:8000/api/get-deposition-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          case_name: deposition.case_name,
          deposition_filename: deposition.deposition_name,
        })
      });

      if (!textResponse.ok) {
        const errorText = await textResponse.text();
        addLogMessage(`Backend error fetching deposition text: ${errorText}`, 'error');
        throw new Error(`HTTP ${textResponse.status}: ${errorText}`);
      }

      const textResult = await textResponse.json();
      // console.log('Deposition text result:', textResult); // Debug log
      addLogMessage('Deposition text fetched successfully', 'success');

      setComparisonData(result);
      setDepositionText(textResult.data.deposition_text);
      setCurrentDepositionIndex(0); 
      addLogMessage('=== NUGGETS READY FOR REVIEW ===', 'success');

      setStatus("completed");
      setCurrentStep("");
      setShowNuggetViewer(true); 
      setShowDepositionSelector(false);
    } catch (err) {
      addLogMessage(`ERROR: ${err.message}`, 'error');
      setError(`Processing failed: ${err.message}`);
      setStatus("error");
      setCurrentStep("");
    }
  };

  const processPair = async (pair, index) => {
    setStatus("running");
    setError('');
    setShowLogger(true);
    clearLogs();

    try {
      addLogMessage('=== CITATION VALIDATION MODE STARTED ===', 'success');
      addLogMessage(`Processing pair: ${pair.deposition} & ${pair.summary}`);

      setCurrentStep("Processing files for citation validation...");

      const response = await fetch('http://localhost:8000/api/process-pair', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          case_name: pair.case_name,
          deposition_filename: pair.deposition,
          summary_filename: pair.summary
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        addLogMessage(`Backend error response: ${errorText}`, 'error');
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      addLogMessage('Response parsed successfully', 'success');

      setValidationData(result);
      setCurrentPairIndex(index);
      addLogMessage('=== READY FOR HUMAN VALIDATION ===', 'success');

      setStatus("completed");
      setCurrentStep("");
      setShowValidator(true);
      setShowPairSelector(false);
    } catch (err) {
      addLogMessage(`ERROR: ${err.message}`, 'error');
      setError(`Pipeline failed: ${err.message}`);
      setStatus("error");
      setCurrentStep("");
    }
  };


  const processUploadedDepositions = async () => {
    if (!depositionFile) {
      setError('Please upload deposition file.');
      return;
    }

    setStatus("running");
    setError('');
    setShowLogger(true);
    clearLogs();

    try {
      const formData = new FormData();
      formData.append('deposition', depositionFile.file);
      formData.append('human_annotation', 'true');
      formData.append('nugget_comparison', 'true');
      formData.append('citation_tagging', 'false');



      addLogMessage('=== CITATION COMPARISON MODE STARTED ===', 'success');
      addLogMessage('Uploading files: ${depositionFile.name}');

      setCurrentStep("Processing files for pair wise nugget comparison...");

      const response = await fetch('http://localhost:8000/api/run-pipeline', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        addLogMessage(`Backend error response: ${errorText}`, 'error');
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      addLogMessage('Response parsed successfully', 'success');

      setComparisonData(result);
      addLogMessage('=== READY FOR HUMAN VALIDATION ===', 'success');

      setStatus("completed");
      setCurrentStep("");
      setShowValidator(true);
    } catch (err) {
      addLogMessage(`ERROR: ${err.message}`, 'error');
      setError(`Pipeline failed: ${err.message}`);
      setStatus("error");
      setCurrentStep("");
    }
  };

  const handleNextPair = async () => {
    if (currentPairIndex < filePairs.length - 1) {
      const nextPair = filePairs[currentPairIndex + 1];
      await processPair(nextPair, currentPairIndex + 1);
    } else {
      setError('No more pairs available.');
      setShowValidator(false);
    }
  };

  const reset = () => {
    setDepositionFile(null);
    setSummaryFile(null);
    setStatus("ready");
    setShowReport(false);
    setShowValidator(false);
    setShowPairSelector(false);
    setShowNuggetViewer(false);
    setShowDepositionSelector(false);
    setError('');
    setCurrentStep('');
    setDepositionText("");
    setLogs([]);
    setShowLogger(false);
    // setEvaluationData(null);
    setCurrentPairIndex(-1);
    setCurrentDepositionIndex(-1);
  };

  const removeDepositionFile = () => {
    setDepositionFile(null);
    setError('');
  };

  const removeSummaryFile = () => {
    setSummaryFile(null);
    setError('');
  };






  const canRunPipeline = (depositionFile && summaryFile && status !== "running") || (!depositionFile && !summaryFile && status !== "running");

  return (
    <div className="min-h-screen bg-[#001F3F] text-white px-6 py-10">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-[#F04E24] mb-6">Nugget Generation & Summary Evaluation Pipeline</h1>

        {error && (
          <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 mb-6 flex items-center gap-2">
            <AlertCircle size={20} className="text-red-400" />
            <span className="text-red-200">{error}</span>
          </div>
        )}

        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-6 space-y-6">
          {/* Deposition File Upload */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Deposition File (.txt)</label>
            {!depositionFile ? (
              <div
                onClick={() => depositionInputRef.current.click()}
                className="border-2 border-dashed border-slate-600 rounded-lg p-6 text-center cursor-pointer hover:border-[#F04E24] hover:bg-slate-700/30 transition-all group"
              >
                <Upload size={24} className="mx-auto mb-2 text-slate-400 group-hover:text-[#F04E24]" />
                <p className="text-slate-300 group-hover:text-white">Click to upload deposition transcript</p>
                <input
                  ref={depositionInputRef}
                  type="file"
                  onChange={handleDepositionUpload}
                  className="hidden"
                  accept=".txt"
                />
              </div>
            ) : (
              <div className="flex items-center justify-between bg-slate-700 p-4 rounded-lg">
                <div className="flex items-center gap-3">
                  <FileText size={20} className="text-[#F04E24]" />
                  <div>
                    <p className="font-medium">{depositionFile.name}</p>
                    <p className="text-sm text-slate-400">{formatSize(depositionFile.size)}</p>
                  </div>
                </div>
                <button onClick={removeDepositionFile} className="text-red-400 hover:text-red-600 transition-colors">
                  <Trash2 size={16} />
                </button>
              </div>
            )}
          </div>

          {/* Summary File Upload */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Summary File (.txt)</label>
            {!summaryFile ? (
              <div
                onClick={() => summaryInputRef.current.click()}
                className="border-2 border-dashed border-slate-600 rounded-lg p-6 text-center cursor-pointer hover:border-[#F04E24] hover:bg-slate-700/30 transition-all group"
              >
                <Upload size={24} className="mx-auto mb-2 text-slate-400 group-hover:text-[#F04E24]" />
                <p className="text-slate-300 group-hover:text-white">Click to upload summary file</p>
                <input
                  ref={summaryInputRef}
                  type="file"
                  onChange={handleSummaryUpload}
                  className="hidden"
                  accept=".txt"
                />
              </div>
            ) : (
              <div className="flex items-center justify-between bg-slate-700 p-4 rounded-lg">
                <div className="flex items-center gap-3">
                  <FileText size={20} className="text-[#F04E24]" />
                  <div>
                    <p className="font-medium">{summaryFile.name}</p>
                    <p className="text-sm text-slate-400">{formatSize(summaryFile.size)}</p>
                  </div>
                </div>
                <button onClick={removeSummaryFile} className="text-red-400 hover:text-red-600 transition-colors">
                  <Trash2 size={16} />
                </button>
              </div>
            )}
          </div>

          {/* Pipeline Controls */}
          <div className="flex gap-4">
            <button
              onClick={runPipeline}
              disabled={!depositionFile || !summaryFile || status === "running"}
              className={`flex-1 py-3 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2 ${!depositionFile || !summaryFile || status === "running" ? 'bg-slate-600 cursor-not-allowed' : 'bg-[#F04E24] hover:bg-orange-600'
                }`}
            >
              <Play size={16} />
              {status === 'running' ? 'Running Pipeline...' : 'Run Evaluation Pipeline'}
            </button>

            <button
              onClick={runValidationMode}
              disabled={status === "running"}
              className={`flex-1 py-3 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2 ${status === "running" ? 'bg-slate-600 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
                }`}
            >
              <UserCheck size={16} />
              {status === 'running' ? 'Processing...' : 'Citation Annotation Mode'}
            </button>

            <button
              onClick={runComparisonMode}
              disabled={status === "running"}
              className={`flex-1 py-3 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2 ${status === "running" ? 'bg-slate-600 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
                }`}
            >
              <UserCheck size={16} />
              {status === 'running' ? 'Processing...' : 'Nugget Comparison Mode'}
            </button>

            {(depositionFile || summaryFile || showValidator || showReport) && (
              <button
                onClick={reset}
                className="px-6 py-3 rounded-lg font-semibold bg-slate-600 hover:bg-slate-500 transition-colors"
              >
                Reset
              </button>
            )}
          </div>

          {/* Mode Description */}
          <div className="bg-slate-700/50 border border-slate-600 rounded-lg p-4">
            <h3 className="text-sm font-medium text-slate-300 mb-2">Mode Selection:</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="space-y-1">
                <p className="text-orange-400 font-medium">🔍 Evaluation Pipeline</p>
                <p className="text-slate-400">Runs full automated evaluation and generates comprehensive report with AI assessments. Requires uploaded files.</p>
              </div>
              <div className="space-y-1">
                <p className="text-blue-400 font-medium">👤 Annotation: Citation tagging</p>
                <p className="text-slate-400">Select from pre-organized pairs or upload files for citation annotation. Exports annotated data.</p>
              </div>
              <div className="space-y-1">
                <p className="text-blue-400 font-medium">👤 Annotation: Pair-wise Nugget Comparison</p>
                <p className="text-slate-400">Select from pre-organized pairs for nugget comparison annotation. Exports annotated data.</p>
              </div>
            </div>
          </div>

          {/* Logger Display */}
          {showLogger && (
            <div className="bg-slate-900/80 border border-slate-600 rounded-lg p-4 max-h-60 overflow-auto">
              <h3 className="text-sm font-medium text-slate-300 mb-2">Pipeline Logs</h3>
              {logs.map((log, index) => (
                <p
                  key={index}
                  className={`text-sm ${log.type === 'error' ? 'text-red-400' : log.type === 'success' ? 'text-green-400' : 'text-slate-300'
                    }`}
                >
                  [{log.timestamp}] {log.message}
                </p>
              ))}
            </div>
          )}

          {/* Status Display */}
          {status === 'running' && (
            <div className="bg-blue-900/50 border border-blue-500 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                <span className="text-blue-200 font-medium">Processing...</span>
              </div>
              {currentStep && <p className="text-sm text-blue-300">{currentStep}</p>}
            </div>
          )}

          {status === 'completed' && evaluationData &&(
            <div className="bg-green-900/50 border border-green-500 rounded-lg p-4">
              <div className="flex justify-between items-center">
                <span className="text-green-200 font-medium">✅ Pipeline Completed Successfully</span>
                <button
                  onClick={() => setShowReport(!showReport)}
                  className="flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors"
                >
                  <Eye size={16} />
                  View Evaluation Report
                </button>
              </div>
            </div>
          )}

          {status === 'completed' && showValidator && (
            <div className="bg-blue-900/50 border border-blue-500 rounded-lg p-4">
              <div className="flex justify-between items-center">
                <span className="text-blue-200 font-medium">✅ Ready for Human Annotation</span>
                <button
                  onClick={() => setShowValidator(true)}
                  className="flex items-center gap-2 text-green-400 hover:text-green-300 transition-colors"
                >
                  <UserCheck size={16} />
                  Start Citation Annotation
                </button>
              </div>
            </div>
          )}
          {status === 'completed' && showNuggetViewer && (
            <div className="bg-blue-900/50 border border-blue-500 rounded-lg p-4">
              <div className="flex justify-between items-center">
                <span className="text-blue-200 font-medium">✅ Ready for Nugget Review</span>
                <button
                  onClick={() => setShowNuggetViewer(true)}
                  className="flex items-center gap-2 text-green-400 hover:text-green-300 transition-colors"
                >
                  <UserCheck size={16} />
                  View Deposition and Nuggets
                </button>
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="bg-red-900/50 border border-red-500 rounded-lg p-4">
              <span className="text-red-200 font-medium">❌ Pipeline Failed</span>
            </div>
          )}
        </div>
      </div>

      {/* Pair Selector */}
      {showPairSelector && (
        <PairSelector
          onSelect={(pair, index) => processPair(pair, index)}
          onClose={() => setShowPairSelector(false) && setStatus('completed')}
        />
      )}

      {/* Deposition Selector */}
      {showDepositionSelector && (
        <DepoSelector
          onSelect={(deposition) => processDepo(deposition)}
          onClose={() => setShowDepositionSelector(false) }
        />
      )}

      {/* Evaluation Report */}
      {showReport && evaluationData && (
        <EvaluationReport
          result={evaluationData}
          onClose={() => setShowReport(false)}
        />
      )}

      {/* Citation Validator */}
      {showValidator && validationData && (
        <CitationValidator
          result={validationData}
          onClose={() => setShowValidator(false) }
          // onNext={handleNextPair}
          // hasNext={currentPairIndex < filePairs.length - 1}
        />
      )}
      {/* Nugget Viewer */}
      {showNuggetViewer && depositionText && (
        <NuggetViewer
          result={comparisonData}
          depositionText={depositionText}
          onClose={() => setShowNuggetViewer(false) }
        />
      )}
    </div>
  );
};

export default NuggetPipelineUI;