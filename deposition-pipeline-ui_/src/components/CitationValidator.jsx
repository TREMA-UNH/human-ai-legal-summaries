import React, { useRef, useState, useEffect } from 'react';

const AnnotationForm = ({ result, onClose }) => {
  console.log(result);
  const { summary, stats } = result.data;
  const citationData = result.citation_data;
  const uniqueId = result.rand;
  const UnsortedCitationData = result.unsorted_citation_data;
  const depositionRef = useRef(null);
  const [annotations, setAnnotations] = useState({});
  const [expandedCitations, setExpandedCitations] = useState({});

  const definitions = {
    relevance: {
      title: "Relevance Check",
      description: "Does the deposition discuss the same event or topic as the summary fact?",
      options: ["Relevant", "Irrelevant"],
    },
    sufficiency: {
      title: "Sufficiency Check",
      description: "Does the deposition provide enough details to fully support the summary fact?",
      options: ["Sufficient", "Sufficient (Minor Displacement, Approx less than a page surrounding)", "Insufficient"],
    },
    insufficientReason: {
      title: "Reason for Insufficiency",
      description: "If insufficient, why? (Select all that apply)",
      options: ["Missing A Key Detail", "Needs More Context", "Contradictory Information"],
      multiple: true,
    },
  };

  useEffect(() => {
    const autosave = async () => {
      const dataToSave = UnsortedCitationData
        .filter((item) => item.cited)
        .map((citation, idx) => ({
          citation_str: citation.citation_str,
          citation_summary_fact: citation.summary_fact,
          annotation: annotations[idx] || {},
        }));

      const resultId = `${result.summary_file_name?.replaceAll('.txt', '')}_${uniqueId}`;

      await fetch('http://localhost:8000/api/save-annotations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          annotations: dataToSave,
          resultId: resultId, // Use unique file name
        }),
      });
    };

    if (Object.keys(annotations).length > 0) {
      autosave();
    }
  }, [annotations, UnsortedCitationData, result.summary_file_name]);

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

  const toggleCitation = (index) => {
    setExpandedCitations((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  const handleAnnotationChange = (citationIndex, criterion, value) => {
    setAnnotations((prev) => {
      let updatedAnnotation = { ...prev[citationIndex] };

      if (criterion === 'insufficientReason') {
        const currentReasons = updatedAnnotation[criterion] || [];
        const newReasons = currentReasons.includes(value)
          ? currentReasons.filter((reason) => reason !== value)
          : [...currentReasons, value];
        updatedAnnotation[criterion] = newReasons;
      } else {
        updatedAnnotation[criterion] = value;
        // Reset dependent fields when parent changes
        if (criterion === 'relevance' && value === 'Irrelevant') {
          updatedAnnotation.sufficiency = undefined;
          updatedAnnotation.insufficientReason = [];
        } else if (criterion === 'sufficiency' && value !== 'Insufficient') {
          updatedAnnotation.insufficientReason = [];
        }
      }

      return {
        ...prev,
        [citationIndex]: updatedAnnotation,
      };
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-80 z-50 flex items-center justify-center p-4">
      <div className="bg-white text-black w-full max-w-7xl h-5/6 rounded-xl overflow-hidden relative flex flex-col">
        <div className="flex items-center justify-between p-4 border-b bg-white flex-shrink-0 relative z-10">
          <h2 className="text-xl font-bold">Annotation Form</h2>
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
            Summary -- Annotation Form
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
              <h2 className="text-xl font-bold mb-4">Annotation</h2>
              {UnsortedCitationData
                .filter((item) => item.cited)
                .map((citation, idx) => (
                  <div key={idx} className="mb-6">
                    <h3
                      className="text-lg font-semibold cursor-pointer flex items-center justify-between"
                      onClick={() => toggleCitation(idx)}
                    >
                      <span>Citation #{idx + 1}: {citation.citation_str || "No text"}</span>
                      <span>{expandedCitations[idx] ? 'v' : '>'}</span>
                    </h3>
                    {expandedCitations[idx] && (
                      <div className="mt-2 space-y-4">
                        <div className="bg-gray-100 p-3 rounded border border-gray-300">
                          <p className="text-sm text-gray-800">
                            <strong>Citation String:</strong> {citation.citation_str}
                          </p>
                          <p className="text-sm text-gray-800 mt-1">
                            <strong>Text:</strong> {citation.summary_fact}
                          </p>
                        </div>
                        {Object.entries(definitions).map(([criterion, { title, description, options, multiple }]) => {
                          // Conditionally render based on relevance and sufficiency
                          if (criterion === 'sufficiency' && annotations[idx]?.relevance !== 'Relevant') {
                            return null;
                          }
                          if (criterion === 'insufficientReason' && annotations[idx]?.sufficiency !== 'Insufficient') {
                            return null;
                          }
                          return (
                            <div key={criterion} className="bg-gray-50 p-4 rounded-md border-l-4 border-blue-400">
                              <h4 className="text-sm font-medium text-gray-700">{title}</h4>
                              <p className="text-sm text-gray-600 mb-2">{description}</p>
                              <div className="flex gap-2 flex-wrap">
                                {options.map((option) => (
                                  <button
                                    key={option}
                                    className={`px-3 py-1 rounded text-sm font-medium ${
                                      multiple
                                        ? annotations[idx]?.[criterion]?.includes(option)
                                          ? 'bg-blue-500 text-white'
                                          : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                        : annotations[idx]?.[criterion] === option
                                        ? 'bg-blue-500 text-white'
                                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                    }`}
                                    onClick={() => handleAnnotationChange(idx, criterion, option)}
                                  >
                                    {option}
                                  </button>
                                ))}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ))}
              <div className="mt-8 bg-gray-100 p-4 rounded-md">
                <h3 className="text-lg font-semibold">Stats</h3>
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

export default AnnotationForm;