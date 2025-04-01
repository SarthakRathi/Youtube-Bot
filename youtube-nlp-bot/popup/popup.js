document.addEventListener('DOMContentLoaded', function() {
  // Elements
  const videoTitleElement = document.getElementById('video-title');
  const toolsGrid = document.querySelector('.tools-grid');
  const resultContainer = document.getElementById('result-container');
  const resultContent = document.getElementById('result-content');
  const featureTitle = document.getElementById('feature-title');
  const backButton = document.getElementById('back-button');
  
  // Current video information
  let currentVideoId = null;
  let currentVideoTitle = null;
  
  // Get current YouTube video information
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    const tab = tabs[0];
    
    // Check if we're on a YouTube video page
    if (tab.url && tab.url.includes('youtube.com/watch')) {
      const url = new URL(tab.url);
      currentVideoId = url.searchParams.get('v');
      
      try {
        chrome.scripting.executeScript({
          target: {tabId: tab.id},
          function: () => {
            const titleElement = document.querySelector('h1.title.style-scope.ytd-video-primary-info-renderer, h1.ytd-watch-metadata');
            return titleElement ? titleElement.textContent.trim() : null;
          }
        }, (results) => {
          if (results && results[0] && results[0].result) {
            currentVideoTitle = results[0].result;
            videoTitleElement.textContent = currentVideoTitle;
          } else {
            chrome.tabs.sendMessage(tab.id, {action: 'getVideoDetails'}, function(response) {
              if (chrome.runtime.lastError) {
                videoTitleElement.textContent = 'YouTube NLP Assistant - Ready';
              } else if (response && response.title) {
                currentVideoTitle = response.title;
                videoTitleElement.textContent = currentVideoTitle;
              } else {
                videoTitleElement.textContent = 'Video detected - Title unavailable';
              }
            });
          }
        });
      } catch (error) {
        videoTitleElement.textContent = 'Video detected - Ready to analyze';
        console.error('Error executing script:', error);
      }
    } else {
      videoTitleElement.textContent = 'Not a YouTube video page';
      document.querySelectorAll('.card').forEach(card => {
        card.classList.add('disabled');
        card.style.opacity = '0.5';
        card.style.cursor = 'not-allowed';
      });
    }
  });
  
  // Card click handler
  document.querySelectorAll('.card').forEach(card => {
    card.addEventListener('click', function() {
      const feature = this.getAttribute('data-feature');
      if (!currentVideoId || this.classList.contains('disabled')) {
        return;
      }
      
      toolsGrid.classList.add('hidden');
      resultContainer.classList.remove('hidden');
      featureTitle.textContent = this.querySelector('h3').textContent;
      
      resultContent.innerHTML = `
        <div class="loading">
          <div class="loading-spinner"></div>
        </div>
      `;
      
      chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        chrome.tabs.sendMessage(
          tabs[0].id, 
          {action: 'verifyConnection'}, 
          function(response) {
            if (!chrome.runtime.lastError && response) {
              processFeature(feature, currentVideoId);
            } else {
              console.log('Using fallback method due to content script connection issue');
              processFeatureWithFallback(feature, currentVideoId, tabs[0].id);
            }
          }
        );
      });
    });
  });
  
  function processFeatureWithFallback(feature, videoId, tabId) {
    chrome.scripting.executeScript({
      target: {tabId: tabId},
      function: (featureType) => {
        const overlay = document.createElement('div');
        overlay.style.cssText = `
          position: fixed;
          top: 70px;
          right: 20px;
          background-color: white;
          padding: 15px;
          border-radius: 8px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.2);
          z-index: 9999;
          width: 300px;
        `;
        overlay.innerHTML = `
          <h3 style="margin-top: 0; color: #FF0000;">YouTube NLP Assistant</h3>
          <p>Processing ${featureType} request...</p>
          <p style="font-size: 12px;">Please wait while we analyze this video</p>
        `;
        document.body.appendChild(overlay);
        setTimeout(() => {
          overlay.innerHTML = `
            <h3 style="margin-top: 0; color: #FF0000;">YouTube NLP Assistant</h3>
            <p>Analysis complete!</p>
            <p>Please check the extension popup to view results.</p>
          `;
          setTimeout(() => {
            document.body.removeChild(overlay);
          }, 3000);
        }, 2000);
        return true;
      },
      args: [feature]
    });
    processFeature(feature, videoId);
  }
  
  backButton.addEventListener('click', function() {
    toolsGrid.classList.remove('hidden');
    resultContainer.classList.add('hidden');
    const segmentSummaries = document.querySelectorAll('.segment-summary');
    segmentSummaries.forEach(element => {
      element.remove();
    });
  });
  
  function processFeature(feature, videoId) {
    // Define API endpoints only for the features that have backend support.
    const apiEndpoints = {
      'summarize': 'http://localhost:5000/api/summarize',
      'timestamps': 'http://localhost:5000/api/timestamps',
      'keypoints_wiki': 'http://localhost:5000/api/keypoints_wiki',
      'factcheck': 'http://localhost:5000/api/factcheck'
    };
    
    const apiUrl = apiEndpoints[feature];
    
    // For features without a dedicated API, show a placeholder message.
    if (!apiUrl) {
      setTimeout(() => {
        let result = `<div class="feature-placeholder">
                        <h3>Feature Coming Soon</h3>
                        <p>The ${feature} feature is under development.</p>
                      </div>`;
        resultContent.innerHTML = result;
      }, 1500);
      return;
    }
    
    fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        videoId: videoId,
        minLength: 150,
        maxLength: 300
      })
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`API responded with status ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.status === 'error') {
        throw new Error(data.error || 'Unknown error occurred');
      }
      
      let result = '';
      
      switch(feature) {
        case 'summarize':
          result = `
            <div class="summary-result">
              <h3>Video Summary</h3>
              <p>${data.summary}</p>
              <div class="transcript-toggle">
                <button id="show-transcript">Show Full Transcript</button>
                <div id="transcript-container" class="hidden">
                  <h4>Full Transcript</h4>
                  <div class="transcript-text">${data.transcript}</div>
                </div>
              </div>
            </div>
          `;
          break;
        case 'timestamps':
          result = `
            <div class="timestamps-result">
              <h3>Video Timestamps</h3>
              <p class="timestamps-info">Click on any timestamp to jump to that point in the video and generate a summary for that segment.</p>
              <div class="timestamps-list">
                ${data.timestamps.map(ts => `
                  <div class="timestamp-item" data-time="${ts.time}" data-segment-id="${ts.segment_id}">
                    <span class="timestamp-time">${ts.formatted_time}</span>
                    <span class="timestamp-title">${ts.title}</span>
                    ${ts.keywords && ts.keywords.length > 0 ? 
                      `<div class="timestamp-keywords">
                        ${ts.keywords.map(kw => `<span class="keyword-tag">${kw}</span>`).join('')}
                      </div>` : ''}
                    <div class="segment-summary-container" id="segment-container-${ts.segment_id}"></div>
                  </div>
                `).join('')}
              </div>
            </div>
          `;
          break;
        case 'keypoints_wiki':
          fetch('http://localhost:5000/api/keypoints_wiki', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              videoId: videoId,
              numPoints: 8
            })
          })
          .then(response => {
            if (!response.ok) {
              throw new Error(`API responded with status ${response.status}`);
            }
            return response.json();
          })
          .then(data => {
            if (data.status === 'error') {
              throw new Error(data.error || 'Unknown error occurred');
            }
            
            let keyTermsHtml = `
              <div class="keypoints-wiki-result">
                <h3>Key Terms with Wikipedia Context</h3>
                <p class="feature-description">Important concepts, people, and places mentioned in this video</p>
                <div class="keypoints-wiki-container">
            `;
            
            data.keyPoints.forEach((item, index) => {
              keyTermsHtml += `
                <div class="keypoint-wiki-item">
                  <div class="keypoint-content">
                    ${item.wikipedia_info ? `
                      <div class="keypoint-wiki-info">
                        <div class="wiki-title">
                          <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAB/ElEQVQ4jZ2Tv2sUQRTHP7O7l8seEezy4w+IYhFRLFQSBSGF2CgIFoqFhYVYWFj5L1j6B1hZCIKixUVFDKiIRRr9FYyIQdDo3d7e7fpiMXvJ5mLAB9Pswzffb+Z7M/C/pLOQQnYwKSrjEJ8qYkClXR3GXKZYYn3p5jZjdDaRkN9dAo/XqmfVKFELViS+h7dCvdHvCH+9MBCoZAXFD5dQPTVIJCBH8BbFvwBx+cRaMBTw+PJl4PUgvU2kTQ8XZz7uzH+LX6BQPXZfKntmZqZWyodKpVJXVWLnHKlzqCrRWhTDMPA+Auwv5UPj4bCa5WmW51mejccq7U4YhupHgp2iDeDQYrM25KSCZ7ZmYkzZGGNNagICtq0F7sWWy2G7b5tNcE3ANwWf4MWdqPEz7yMDWDQrMnIbBPXbTw5+bbODQnNnrD5y6nzYXUPktcDRLYILU3fX1mG8b4MiJsqCGbYmQHp62tbKjfH1yNM3iqx0Fy9OLB34BHB49G5NRN8qXJidnT35r399fX0NReqK3JqanPy0NTO0+hG+g5WGO1cq77+WXxcj9fGx0SiKojgGGGgE4J7nZf8W6qVa7X24uPgBONwHcAS4BtieiYDQH6Uik73gW4FFoLsJaJAHJoB5YHDzPZADNXqW9csfXkwKBTAogL8AAAAASUVORK5CYII=" class="wiki-icon">
                          <a href="${item.wikipedia_info.url}" target="_blank" class="wiki-title-link">${item.wikipedia_info.title}</a>
                        </div>
                        <div class="wiki-summary">${item.wikipedia_info.summary}</div>
                        <a href="${item.wikipedia_info.url}" target="_blank" class="wiki-link">Read more on Wikipedia</a>
                      </div>
                    ` : '<div class="no-wiki-info">No Wikipedia information available for this term.</div>'}
                  </div>
                </div>
              `;
            });
            
            keyTermsHtml += `
                </div>
              </div>
            `;
            
            resultContent.innerHTML = keyTermsHtml;
          })
          .catch(error => {
            console.error('Error processing key terms with wiki:', error);
            resultContent.innerHTML = `
              <div class="error-message">
                <h3>Error Processing Request</h3>
                <p>${error.message}</p>
                <p>Make sure the Python backend server is running at http://localhost:5000</p>
              </div>
            `;
          });
          return; // Exit early because keypoints_wiki uses its own fetch.
        
        case 'factcheck':
          // For fact check, display a loading state and then update with sentiment data.
          result = `
            <div class="factcheck-result">
              <h3>Fact Check & Sentiment Analysis</h3>
              <p>Analyzing comments sentiment...</p>
              <div class="factcheck-details"></div>
            </div>
          `;
          break;
          
        default:
          result = `<div class="feature-placeholder">
                      <h3>Feature Coming Soon</h3>
                      <p>The ${feature} feature is under development.</p>
                    </div>`;
      }
      
      // If feature is factcheck, process its result separately
      if (feature === 'factcheck') {
        const details = data.sentiment;
        
        // Calculate percentages for progress bars
        const positiveWidth = details.positive_percentage;
        const negativeWidth = details.negative_percentage;
        
        resultContent.innerHTML = `
          <div class="factcheck-result">
            <h3>Fact Check & Sentiment Analysis</h3>
            <p class="factcheck-info">Analysis based on ${details.total_comments} comments from this video</p>
            
            <div class="sentiment-container">
              <div class="sentiment-item">
                <div class="sentiment-header">
                  <span class="sentiment-label">Positive</span>
                  <span class="sentiment-percentage">${details.positive_percentage}%</span>
                </div>
                <div class="sentiment-bar-container">
                  <div class="sentiment-bar positive" style="width: ${positiveWidth}%"></div>
                </div>
              </div>
              
              <div class="sentiment-item">
                <div class="sentiment-header">
                  <span class="sentiment-label">Negative</span>
                  <span class="sentiment-percentage">${details.negative_percentage}%</span>
                </div>
                <div class="sentiment-bar-container">
                  <div class="sentiment-bar negative" style="width: ${negativeWidth}%"></div>
                </div>
              </div>
            </div>
            
            
            <div class="factcheck-section">
              <h4>Sample Comments</h4>
              <div class="comments-container">
                ${generateCommentsHTML(data.comments_sample || [])}
              </div>
            </div>
          </div>
        `;
        return;
      }

      function generateCommentsHTML(comments) {
        if (!comments.length) {
          return `<div class="no-comments">No comments available</div>`;
        }
        
        return comments.map(comment => {
          return `
            <div class="comment-item">
              <p class="comment-text">${comment}</p>
            </div>
          `;
        }).join('');
      }
      
      resultContent.innerHTML = result;
      
      if (feature === 'summarize') {
        document.getElementById('show-transcript').addEventListener('click', function() {
          const container = document.getElementById('transcript-container');
          const button = document.getElementById('show-transcript');
          if (container.classList.contains('hidden')) {
            container.classList.remove('hidden');
            button.textContent = 'Hide Full Transcript';
          } else {
            container.classList.add('hidden');
            button.textContent = 'Show Full Transcript';
          }
        });
      } else if (feature === 'timestamps') {
        document.querySelectorAll('.timestamp-item').forEach(item => {
          item.addEventListener('click', function() {
            const timeInSeconds = parseFloat(this.getAttribute('data-time'));
            const segmentId = parseInt(this.getAttribute('data-segment-id'), 10);
            chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
              chrome.tabs.sendMessage(tabs[0].id, {
                action: 'navigateToTime',
                time: timeInSeconds
              });
            });
            const summaryContainer = document.getElementById(`segment-container-${segmentId}`);
            if (summaryContainer.innerHTML.trim() !== '') {
              if (summaryContainer.classList.contains('hidden')) {
                summaryContainer.classList.remove('hidden');
              } else {
                summaryContainer.classList.add('hidden');
              }
              return;
            }
            summaryContainer.innerHTML = `
              <div class="segment-summary" id="segment-summary-${segmentId}">
                <h4>Loading segment summary...</h4>
                <div class="loading-spinner"></div>
              </div>
            `;
            fetch('http://localhost:5000/api/segment_summary', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({
                videoId: currentVideoId,
                segmentId: segmentId
              })
            })
            .then(response => response.json())
            .then(data => {
              if (data.status === 'success') {
                document.getElementById(`segment-summary-${segmentId}`).innerHTML = `
                  <div class="segment-summary-content">
                    <h4>Summary for ${data.formatted_time}</h4>
                    <p>${data.summary}</p>
                    <button class="close-summary-btn" data-segment-id="${segmentId}">Hide Summary</button>
                  </div>
                `;
                document.querySelector(`.close-summary-btn[data-segment-id="${segmentId}"]`)
                  .addEventListener('click', function(event) {
                    event.stopPropagation();
                    document.getElementById(`segment-container-${segmentId}`).classList.add('hidden');
                  });
              } else {
                throw new Error(data.error || 'Unknown error occurred');
              }
            })
            .catch(error => {
              document.getElementById(`segment-summary-${segmentId}`).innerHTML = `
                <div class="segment-summary-error">
                  <h4>Error</h4>
                  <p>Could not generate summary: ${error.message}</p>
                  <button class="close-summary-btn" data-segment-id="${segmentId}">Close</button>
                </div>
              `;
              document.querySelector(`.close-summary-btn[data-segment-id="${segmentId}"]`)
                .addEventListener('click', function(event) {
                  event.stopPropagation();
                  document.getElementById(`segment-container-${segmentId}`).classList.add('hidden');
                });
            });
          });
        });
      }
    })
    .catch(error => {
      console.error('Error processing feature:', error);
      resultContent.innerHTML = `
        <div class="error-message">
          <h3>Error Processing Request</h3>
          <p>${error.message}</p>
          <p>Make sure the Python backend server is running at http://localhost:5000</p>
        </div>
      `;
    });
  }
});
