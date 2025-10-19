import React, { useState, useEffect } from 'react';
import AnnotationForm from './AnnotationForm';

const FilePairList = () => {
  const [filePairs, setFilePairs] = useState([]);
  const [selectedResult, setSelectedResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch list of file pairs on mount
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

  // Handle clicking a file pair
  const handlePairClick = async (pair) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/api/process-pair', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          case_name: pair.case_name,
          deposition_filename: pair.deposition,
          summary_filename: pair.summary
        })
      });
      const data = await response.json();
      if (data.status === 'success') {
        setSelectedResult(data);
      } else {
        setError('Failed to process file pair');
      }
    } catch (err) {
      setError('Error processing file pair: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Group pairs by case_name
  const groupedPairs = filePairs.reduce((acc, pair) => {
    if (!acc[pair.case_name]) {
      acc[pair.case_name] = [];
    }
    acc[pair.case_name].push(pair);
    return acc;
  }, {});

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6 text-center">Deposition and Summary File Pairs</h1>
      
      {loading && <p className="text-blue-500">Loading...</p>}
      {error && <p className="text-red-500">{error}</p>}
      {Object.keys(groupedPairs).length === 0 && !loading && !error && (
        <p className="text-gray-600">No file pairs available.</p>
      )}

      {/* List cases and their pairs */}
      {Object.entries(groupedPairs).map(([case_name, pairs]) => (
        <div key={case_name} className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Case {case_name}</h2>
          <ul className="space-y-4">
            {pairs.map((pair) => (
              <li
                key={pair.pair_id}
                className="p-4 bg-white rounded-lg shadow-md border-l-4 border-[#6F7D95] hover:bg-gray-50 cursor-pointer"
                onClick={() => handlePairClick(pair)}
              >
                <p className="text-lg font-semibold">Deposition: {pair.deposition}</p>
                <p className="text-sm text-gray-600">Summary: {pair.summary}</p>
              </li>
            ))}
          </ul>
        </div>
      ))}

      {/* Annotation Form Modal */}
      {selectedResult && (
        <AnnotationForm
          result={selectedResult}
          onClose={() => setSelectedResult(null)}
        />
      )}
    </div>
  );
};

export default FilePairList;