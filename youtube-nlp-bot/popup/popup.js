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
      // Extract video ID from URL
      const url = new URL(tab.url);
      currentVideoId = url.searchParams.get('v');
      
      // First check if the content script is already running
      try {
        // Use executeScript to check if content script is loaded and get video title directly
        chrome.scripting.executeScript({
          target: {tabId: tab.id},
          function: () => {
            // Try to get the video title directly
            const titleElement = document.querySelector('h1.title.style-scope.ytd-video-primary-info-renderer, h1.ytd-watch-metadata');
            return titleElement ? titleElement.textContent.trim() : null;
          }
        }, (results) => {
          if (results && results[0] && results[0].result) {
            currentVideoTitle = results[0].result;
            videoTitleElement.textContent = currentVideoTitle;
          } else {
            // Fallback to sending a message to content script
            chrome.tabs.sendMessage(tab.id, {action: 'getVideoDetails'}, function(response) {
              if (chrome.runtime.lastError) {
                // Content script not ready or not loaded
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
        // If executeScript fails, show a fallback message
        videoTitleElement.textContent = 'Video detected - Ready to analyze';
        console.error('Error executing script:', error);
      }
    } else {
      videoTitleElement.textContent = 'Not a YouTube video page';
      // Disable all feature cards
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
      
      // If we're not on a YouTube video page or the card is disabled, do nothing
      if (!currentVideoId || this.classList.contains('disabled')) {
        return;
      }
      
      // Show the result container and hide the tools grid
      toolsGrid.classList.add('hidden');
      resultContainer.classList.remove('hidden');
      
      // Update the feature title
      featureTitle.textContent = this.querySelector('h3').textContent;
      
      // Show loading indicator
      resultContent.innerHTML = `
        <div class="loading">
          <div class="loading-spinner"></div>
        </div>
      `;
      
      // Try to communicate with the content script first
      chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        chrome.tabs.sendMessage(
          tabs[0].id, 
          {action: 'verifyConnection'}, 
          function(response) {
            // If we get a response, process normally
            if (!chrome.runtime.lastError && response) {
              processFeature(feature, currentVideoId);
            } else {
              // If there's an error, use a fallback method
              console.log('Using fallback method due to content script connection issue');
              processFeatureWithFallback(feature, currentVideoId, tabs[0].id);
            }
          }
        );
      });
    });
  });
  
  // Fallback method to process features when content script isn't responding
  function processFeatureWithFallback(feature, videoId, tabId) {
    // This uses executeScript to work even if the content script isn't responsive
    chrome.scripting.executeScript({
      target: {tabId: tabId},
      function: (featureType) => {
        // Create a notification directly in the page
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
    
    // Process in the popup as usual
    processFeature(feature, videoId);
  }
  
  // Back button handler
  backButton.addEventListener('click', function() {
    toolsGrid.classList.remove('hidden');
    resultContainer.classList.add('hidden');
    
    // Clear any active segment summaries
    const segmentSummaries = document.querySelectorAll('.segment-summary');
    segmentSummaries.forEach(element => {
      element.remove();
    });
  });
  
  // Process the selected feature
  function processFeature(feature, videoId) {
    // API endpoints for different features
    const apiEndpoints = {
      'summarize': 'http://localhost:5000/api/summarize',
      'keypoints': 'http://localhost:5000/api/keypoints',
      'keypoints_wiki': 'http://localhost:5000/api/keypoints_wiki',
      'timestamps': 'http://localhost:5000/api/timestamps',
      'sentiment': 'http://localhost:5000/api/sentiment'
    };
    
    // Get the appropriate API endpoint
    const apiUrl = apiEndpoints[feature];
    
    // If no API endpoint is defined for this feature, use placeholder
    if (!apiUrl) {
      setTimeout(() => {
        let result = '';
        
        switch(feature) {
          // Handle any features that don't have an API yet
          default:
            result = `<div class="feature-placeholder">
                        <h3>Feature Coming Soon</h3>
                        <p>The ${featureTitle.textContent} feature is under development.</p>
                        <p>This would connect to your NLP backend to provide real results.</p>
                      </div>`;
        }
        
        resultContent.innerHTML = result;
      }, 1500); // Simulate API delay
      
      return;
    }
    
    // For features with an API endpoint, make the actual API call
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
      
      // Process the result based on feature type
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
          
        case 'keypoints':
          result = `
            <div class="keypoints-result">
              <h3>Key Points</h3>
              <ul class="keypoints-list">
                ${data.keyPoints.map(point => `<li>${point}</li>`).join('')}
              </ul>
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
          
        case 'sentiment':
          result = `
            <div class="sentiment-result">
              <h3>Sentiment Analysis</h3>
              <p>${data.message || 'Sentiment analysis results will appear here'}</p>
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
              numTerms: 8  // Request 8 terms instead of default 5
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
            
            // Add each key term
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
          break;          

        default:
          result = `<div class="error">Unexpected feature type: ${feature}</div>`;
      }
      
      resultContent.innerHTML = result;
      
      // Add event listeners for interactive elements
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
        // Add click handlers for timestamps
        document.querySelectorAll('.timestamp-item').forEach(item => {
          item.addEventListener('click', function() {
            const timeInSeconds = parseFloat(this.getAttribute('data-time'));
            const segmentId = parseInt(this.getAttribute('data-segment-id'), 10);
            
            // Navigate to this time in the video
            chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
              chrome.tabs.sendMessage(tabs[0].id, {
                action: 'navigateToTime',
                time: timeInSeconds
              });
            });
            
            // Check if summary is already generated
            const summaryContainer = document.getElementById(`segment-container-${segmentId}`);
            
            if (summaryContainer.innerHTML.trim() !== '') {
              // Summary exists, toggle visibility
              if (summaryContainer.classList.contains('hidden')) {
                summaryContainer.classList.remove('hidden');
              } else {
                summaryContainer.classList.add('hidden');
              }
              return;
            }
            
            // Show loading state
            summaryContainer.innerHTML = `
              <div class="segment-summary" id="segment-summary-${segmentId}">
                <h4>Loading segment summary...</h4>
                <div class="loading-spinner"></div>
              </div>
            `;
            
            // Fetch the summary for this segment
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
                
                // Add close button event listener
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
              
              // Add close button event listener
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