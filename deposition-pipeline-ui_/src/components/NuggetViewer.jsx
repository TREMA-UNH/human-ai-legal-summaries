import React, { useRef } from 'react';

const NuggetViewer = ({ result, depositionText, onClose }) => {
  // console.log('NuggetViewer result:', result); // Debug log
  // console.log('NuggetViewer depositionText:', depositionText); // Debug log

  const depositionRef = useRef(null);

  // Handle different possible data structures
  let nuggets = [];
  if (result?.data?.nuggets) {
    nuggets = result.data.nuggets;
  } else if (result?.nuggets) {
    nuggets = result.nuggets;
  } else if (Array.isArray(result)) {
    nuggets = result;
  }

  // Get citation data if available
  const citationData = result?.citation_data || [];

  // console.log('Extracted nuggets:', nuggets); // Debug log
  // console.log('Citation data:', citationData); // Debug log

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

  const renderDepositionWithIds = () => {
    if (!depositionText || !citationData.length) {
      return <pre className="text-sm text-gray-800 whitespace-pre-wrap">{depositionText || 'No text available'}</pre>;
    }

    // Group citation data by page and create segments with IDs
    const segments = citationData
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
      }, []);

    return segments.map((group, groupIndex) => (
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
    ));
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-80 z-50 flex items-center justify-center p-4">
      <div className="bg-white text-black w-full max-w-5xl rounded-xl overflow-hidden relative flex flex-col">
        <div className="flex items-center justify-between p-4 border-b bg-white">
          <h2 className="text-xl font-bold">Deposition and Nuggets</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl font-bold leading-none p-1 hover:bg-gray-100 rounded"
          >
            ×
          </button>
        </div>
        <div className="flex flex-col md:flex-row p-6 overflow-auto max-h-[80vh] gap-6">
          <div 
            className="flex-1 bg-gray-100 p-4 rounded-lg overflow-auto"
            ref={depositionRef}
          >
            <h3 className="text-lg font-semibold mb-3">Deposition Text</h3>
            {citationData.length > 0 ? renderDepositionWithIds() : (
              <pre className="text-sm text-gray-800 whitespace-pre-wrap">{depositionText || 'No text available'}</pre>
            )}
          </div>
          <div className="flex-1 bg-gray-100 p-4 rounded-lg overflow-auto">
            <h3 className="text-lg font-semibold mb-3">Nuggets</h3>
            {nuggets.length === 0 ? (
              <p className="text-gray-600">No nuggets available.</p>
            ) : (
              <ul className="space-y-3">
                {nuggets.map((nugget) => (
                  <li
                    key={nugget.id}
                    className="p-4 bg-white rounded-lg border-l-4 border-[#6F7D95] hover:bg-gray-50"
                  >
                    <p className="font-medium">
                      {' '}{renderNuggetWithCitationLink(
                                      nugget.text,
                                      nugget.citation_str,
                                      nugget.link
                                    )}
                    </p>
                    {nugget.page && (
                      <p className="text-sm text-gray-600">
                        Page: {nugget.page}, Line: {nugget.line || 'N/A'}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default NuggetViewer;