import React, { useRef, useState } from 'react';

const EvaluationReport = ({ result, onClose }) => {
  console.log(result);
  const { summary, criteria_scores, stats } = result.data;
  // console.log("criteria score:", criteria_scores);
  const citationData = result.citation_data;
  // console.log("citation data [0]:", citationData[0]);
  const depositionRef = useRef(null);
  const [expandedCriteria, setExpandedCriteria] = useState({});

  const handleCitationClick = (link) => {
    if (!link || link === 'None') {
      console.warn('Invalid citation link:', link);
      return;
    }
    const targetId = link.replace('#', '');
    const targetElement = document.getElementById(targetId);
    if (targetElement && depositionRef.current) {
      targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
      targetElement.classList.add('highlight');
      setTimeout(() => targetElement.classList.remove('highlight'), 2000);
    } else {
      console.warn('Target element not found for ID:', targetId);
    }
  };


    const renderNuggetWithCitationLink = (nugget_text_w_citation, citation_str, link) => {
    if (!nugget_text_w_citation || !citation_str || link === 'None') {
      return <span className="text-gray-600">{nugget_text_w_citation || 'No nugget text'}</span>;
    }
    // Replace citation_str (in parentheses) with clickable link
    const regex = new RegExp(`\\(${citation_str}\\)`);
    const renderedText = nugget_text_w_citation.replace(
      regex,
      `(<a href="#" class="text-[#2ecc71] hover:underline" data-link="${link}">${citation_str}</a>)`
    );
    return (
      <span
        dangerouslySetInnerHTML={{ __html: renderedText }}
        onClick={(e) => {
          if (e.target.tagName === 'A') {
            e.preventDefault();
            handleCitationClick(e.target.getAttribute('data-link'));
          }
        }}
      />
    );
  };

  const renderSummaryWithCitations = (text) => {
    if (!text) return <p className="text-gray-600">No summary available.</p>;

    let renderedText = text;
    citationData.forEach(({ citation_part, link }) => {
      if (citation_part && link && link !== 'None') {
        renderedText = renderedText.replace(
          citation_part,
          `<a href="#" class="text-[#2ecc71] hover:underline" data-link="${link}">${citation_part}</a>`
        );
      }
    });

    return renderedText.split('\n').map((line, index) => (
      <span key={index}>
        <span
          dangerouslySetInnerHTML={{ __html: line }}
          onClick={(e) => {
            if (e.target.tagName === 'A') {
              e.preventDefault();
              handleCitationClick(e.target.getAttribute('data-link'));
            }
          }}
        />
        <br />
      </span>
    ));
  };

  const toggleCriterion = (criterion) => {
    setExpandedCriteria((prev) => ({
      ...prev,
      [criterion]: !prev[criterion],
    }));
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-80 z-50 flex items-center justify-center p-4">
      <div className="bg-white text-black w-full max-w-7xl h-5/6 rounded-xl overflow-hidden relative flex flex-col">
        <div className="flex items-center justify-between p-4 border-b bg-white flex-shrink-0 relative z-10">
          <h2 className="text-xl font-bold">Evaluation Report</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl font-bold leading-none p-1 hover:bg-gray-100 rounded transition-colors"
            aria-label="Close modal"
          >
            ×
          </button>
        </div>
        <div className="h-full overflow-auto p-4">
          <h1 className="text-2xl font-bold text-center bg-[#F04E24] text-white p-5">
            Summary -- Evaluation Report
          </h1>
          <div className="flex gap-5 p-8">
            <div
              className="flex-[1.1] bg-white p-5 rounded-lg shadow-md border-l-4 border-[#6F7D95] max-h-[70vh] overflow-y-auto"
              ref={depositionRef}
            >
              <h2 className="text-xl font-bold mb-4">Deposition</h2>
              {citationData
                .reduce((acc, item, index) => {
                  if (!item.cited) {
                    if (
                      acc.length > 0 &&
                      !acc[acc.length - 1].cited &&
                      acc[acc.length - 1].page === item.page
                    ) {
                      acc[acc.length - 1].items.push({ ...item, originalIndex: index });
                    } else {
                      acc.push({ cited: false, page: item.page, items: [{ ...item, originalIndex: index }] });
                    }
                  } else {
                    acc.push({ cited: true, page: item.page, items: [{ ...item, originalIndex: index }] });
                  }
                  return acc;
                }, [])
                .map((group, groupIndex) => (
                  <div
                    key={`group-${groupIndex}`}
                    className={`p-3 rounded-md mb-2 ${group.cited ? 'border-l-4 border-[#2ecc71]' : 'border-l-4 border-gray-300'}`}
                  >
                    <p className="text-sm font-semibold text-gray-600">Page {group.page}</p>
                    {group.items.map((item, itemIndex) => (
                      <div
                        id={item.id || `deposition-segment-${item.originalIndex}`}
                        key={item.id || `deposition-segment-${item.originalIndex}`}
                      >
                        <pre className="text-black whitespace-pre-wrap">
                          {item.text || 'No text available'}
                        </pre>
                        {item.cited && item.citation_str && (
                          <p className="text-sm text-gray-500">
                            <strong>Citation:</strong> {item.citation_str}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ))}
            </div>
            <div className="flex-1 bg-white p-5 rounded-lg shadow-md border-l-4 border-[#6F7D95] max-h-[70vh] overflow-y-auto">
              <h2 className="text-xl font-bold mb-4">Summary</h2>
              <p className="text-black">{renderSummaryWithCitations(summary)}</p>
            </div>
            <div className="flex-[0.6] bg-white p-5 rounded-lg shadow-md border-l-4 border-[#364052] max-h-[70vh] overflow-y-auto">
              <h2 className="text-xl font-bold mb-4">Evaluation Scores</h2>
              {Object.entries(criteria_scores).map(([criterion, data]) => (
                <div key={criterion} className="mb-6">
                  <h3
                    className="text-lg font-semibold cursor-pointer flex items-center justify-between"
                    onClick={() => toggleCriterion(criterion)}
                  >
                    <div class="flex flex-col">
                    <span>{criterion.charAt(0).toUpperCase() + criterion.slice(1)}</span>
                    <span className="text-sm">
                      {criterion.toLowerCase() !== 'structure' &&
                        // criterion.toLowerCase() !== 'citation_analysis' && (
                          <span className="ml-2 text-[#27ae60]">
                            
                            Score: {data.score.toFixed(2)}
                          </span>
                        // )
                        }
                    </span>
                    </div>
                    <div>
                      {expandedCriteria[criterion] ? 'v' : '>'}

                    </div>
                  </h3>
                  {expandedCriteria[criterion] && (
                    <div className="mt-2">
                      {criterion.toLowerCase() === 'structure' && (
                        <div className="bg-gray-100 p-3 rounded-md my-2">
                          {data.score.map((item, idx) => (
                            <p
                              key={idx}
                              className={`text-${item[Object.keys(item)[0]] ? 'green-600' : 'red-600'}`}
                            >
                              <strong>
                                {Object.keys(item)[0].charAt(0).toUpperCase() +
                                  Object.keys(item)[0].slice(1)}
                                :
                              </strong>{' '}
                              {item[Object.keys(item)[0]] ? '✓' : '✗'}
                            </p>
                          ))}
                        </div>
                      )}
                      {criterion.toLowerCase() === 'citation_analysis' && (
                        <div className="space-y-4 mt-3">
                          {data.details &&
                            Array.isArray(data.details) &&
                            data.details.map((citation, idx) => (
                              <div
                                key={idx}
                                className="bg-gray-50 p-4 rounded-md border-l-4 border-blue-400"
                              >
                                <div className="mb-3">
                                  <div className="mb-2">
                                    <div className="flex items-center justify-between mb-2">
                                      <span className="text-sm font-medium text-gray-700">
                                        Citation #{idx + 1}: {citation["summary text"] || citation.summary_text || "No text"}
                                      </span>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                      <span
                                        className={`px-2 py-1 rounded text-xs font-medium ${
                                          citation.accuracy === 'YES'
                                            ? 'bg-green-100 text-green-800'
                                            : citation.accuracy === 'NO'
                                            ? 'bg-red-100 text-red-800'
                                            : 'bg-yellow-100 text-yellow-800'
                                        }`}
                                      >
                                        {citation.accuracy === 'YES'
                                          ? 'Accurate'
                                          : citation.accuracy === 'NO'
                                          ? 'Not Accurate'
                                          : citation.accuracy}
                                      </span>
                                      <span
                                        className={`px-2 py-1 rounded text-xs font-medium ${
                                          citation.coverage === 'COVERED'
                                            ? 'bg-green-100 text-green-800'
                                            : citation.coverage === 'NOT COVERED'
                                            ? 'bg-red-100 text-red-800'
                                            : 'bg-yellow-100 text-yellow-800'
                                        }`}
                                      >
                                        {citation.coverage === 'COVERED'
                                          ? 'Covered'
                                          : citation.coverage === 'Not Covered'
                                          ? 'Not Covered'
                                          : citation.coverage}
                                      </span>
                                      <span
                                        className={`px-2 py-1 rounded text-xs font-medium ${
                                          citation.sufficiency === 'SUFFICIENT'
                                            ? 'bg-green-100 text-green-800'
                                            : 'bg-red-100 text-red-800'
                                        }`}
                                      >
                                        {citation.sufficiency === 'SUFFICIENT' ? 'Sufficient' : 'Insufficient'}
                                      </span>
                                    </div>
                                  </div>
                                  {citation.evidence_quote && (
                                    <div className="mb-2">
                                      <span className="text-sm font-medium text-gray-700">Evidence:</span>
                                      <p className="text-sm text-gray-600 italic bg-blue-50 p-2 rounded mt-1">
                                        "{citation.evidence_quote}"
                                      </p>
                                    </div>
                                  )}
                                  {citation.missing_elements && citation.missing_elements !== 'null' && (
                                    <div className="mb-2">
                                      <span className="text-sm font-medium text-gray-700">Missing Elements:</span>
                                      <ul className="text-sm text-red-600 list-disc list-inside mt-1">
                                        {Array.isArray(citation.missing_elements) ? (
                                          citation.missing_elements.map((element, elemIdx) => (
                                            <li key={elemIdx}>{element}</li>
                                          ))
                                        ) : (
                                          <li>{citation.missing_elements}</li>
                                        )}
                                      </ul>
                                    </div>
                                  )}
                                  {citation.sufficiency_reason && (
                                    <div className="mb-2">
                                      <span className="text-sm font-medium text-gray-700">Reasoning:</span>
                                      <p className="text-sm text-gray-600 mt-1">{citation.sufficiency_reason}</p>
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          {data.details && Array.isArray(data.details) && (
                            <div className="mt-4 bg-blue-50 p-3 rounded-md">
                              <h4 className="text-md font-semibold mb-2">Citation Summary</h4>
                              <div className="text-sm">
                                <div>
                                  <span className="font-medium">Accurate:</span>
                                  <span className="ml-2 text-green-600">
                                    {data.details.filter((c) => c.accuracy === 'YES').length}
                                  </span>
                                  <br />
                                </div>
                                <div>
                                  <span className="font-medium">Covered:</span>
                                  <span className="ml-2 text-green-600">
                                    {data.details.filter((c) => c.coverage === 'COVERED').length}
                                  </span>
                                  <br />
                                </div>
                                <div>
                                  <span className="font-medium">Sufficient:</span>
                                  <span className="ml-2 text-green-600">
                                    {data.details.filter((c) => c.sufficiency === 'SUFFICIENT').length}
                                  </span>
                                  <br />
                                </div>
                              </div>
                              <div className="mt-2 text-sm">
                                <span className="font-medium">Total Citations:</span>
                                <span className="ml-2">{data.details.length}</span>
                                <br />
                                <span className="font-medium">Weighted Score:</span>
                                <span className="ml-2">{data.score}</span>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                      {data.explanation && criterion.toLowerCase() !== 'citation_analysis' && (
                        <p className="text-black">
                          <strong>Explanation:</strong> {data.explanation}
                        </p>
                      )}
                      {data.explanation && criterion.toLowerCase() === 'citation_analysis' && (
                        <p className="text-black mb-3">
                          <strong>Overall Assessment:</strong> {data.explanation}
                        </p>
                      )}
                      {data.details &&
                        criterion.toLowerCase() !== 'structure' &&
                        criterion.toLowerCase() !== 'citation_analysis' && (
                          <ul className="list-none p-0">
                            {Array.isArray(data.details) ? (
                              data.details.map((detail, idx) => (
                                <li key={idx} className="bg-gray-100 p-3 rounded-md my-2">
                                  <span className="text-gray-600">
                                    <strong>Nugget:</strong> {' '}{renderNuggetWithCitationLink(
                                      detail.nugget.nugget_text_w_citation,
                                      detail.nugget.citation_str,
                                      detail.nugget.link
                                    )}
                                  </span>


                                  
                                  <br />
                                  <span className="text-gray-600">
                                    <strong>Presence:</strong> {detail.presence_score}
                                  </span>
                                  <br />
                                  <strong>Explanation:</strong> {detail.explanation}
                                </li>
                              ))
                            ) : (
                              Object.entries(data.details).map(([key, value], idx) => (
                                <li key={idx} className="bg-gray-100 p-3 rounded-md my-2">
                                  <strong>{key}:</strong> {value}
                                </li>
                              ))
                            )}
                          </ul>
                        )}
                    </div>
                  )}
                </div>
              ))}
              <div className="mt-8 bg-gray-100 p-4 rounded-md">
                <h3 className="text-lg font-semibold">Stats</h3>
                <p className="text-[#354051]">
                  <strong>Total Consolidated Nuggets:</strong> {stats.total_consolidated_nuggets}
                </p>
                <p className="text-[#354051]">
                  <strong>Total Original Nuggets:</strong> {stats.total_original_nuggets}
                </p>
                <p className="text-[#354051]">
                  <strong>Summary Length:</strong> {stats.summary_length} words
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EvaluationReport;