// Global variables
let currentVideoId = null;
let currentVideoTitle = null;
let subtitlesText = null;

// Initialize when the page loads
function initialize() {
  if (window.location.href.includes('youtube.com/watch')) {
    const urlParams = new URLSearchParams(window.location.search);
    currentVideoId = urlParams.get('v');
    
    const titleElement = document.querySelector(
      'h1.title.style-scope.ytd-video-primary-info-renderer, ' + 
      'h1.ytd-watch-metadata, ' +
      'yt-formatted-string.ytd-video-primary-info-renderer'
    );
    
    if (titleElement) {
      currentVideoTitle = titleElement.textContent.trim();
      console.log('YouTube NLP Assistant: Found video title:', currentVideoTitle);
    } else {
      console.log('YouTube NLP Assistant: Could not find video title element');
      currentVideoTitle = 'YouTube Video';
    }
    
    tryGetSubtitles();
    observeVideoChanges();
  }
  
  console.log('YouTube NLP Assistant: Content script initialized');
  window.ytNlpAssistantLoaded = true;
}

function observeVideoChanges() {
  const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
      const newUrl = window.location.href;
      if (newUrl.includes('youtube.com/watch')) {
        const urlParams = new URLSearchParams(window.location.search);
        const newVideoId = urlParams.get('v');
        if (newVideoId && newVideoId !== currentVideoId) {
          currentVideoId = newVideoId;
          const titleElement = document.querySelector(
            'h1.title.style-scope.ytd-video-primary-info-renderer, ' + 
            'h1.ytd-watch-metadata, ' +
            'yt-formatted-string.ytd-video-primary-info-renderer'
          );
          if (titleElement) {
            currentVideoTitle = titleElement.textContent.trim();
          }
          tryGetSubtitles();
        }
      }
    });
  });
  
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
}

chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  console.log('YouTube NLP Assistant: Received message:', request.action);
  
  if (request.action === 'navigateToTime') {
    const timeInSeconds = request.time;
    const success = navigateToVideoTime(timeInSeconds);
    sendResponse({status: success ? 'success' : 'error'});
    return true;
  }
  
  if (request.action === 'getVideoDetails') {
    if (!currentVideoTitle || currentVideoTitle === 'YouTube Video') {
      const titleElement = document.querySelector(
        'h1.title.style-scope.ytd-video-primary-info-renderer, ' + 
        'h1.ytd-watch-metadata, ' +
        'yt-formatted-string.ytd-video-primary-info-renderer'
      );
      if (titleElement) {
        currentVideoTitle = titleElement.textContent.trim();
      }
    }
    
    const response = {
      id: currentVideoId,
      title: currentVideoTitle,
      hasSubtitles: !!subtitlesText,
      url: window.location.href
    };
    
    console.log('YouTube NLP Assistant: Sending response:', response);
    sendResponse(response);
    return true;
  }
  
  if (request.action === 'verifyConnection') {
    sendResponse({status: 'connected'});
    return true;
  }
  
  if (request.action === 'quickSummarize') {
    console.log('YouTube NLP Assistant: Generating summary');
    displayQuickResult('Generating summary...', 'summary');
    fetch('http://localhost:5000/api/summarize', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        videoId: currentVideoId,
        minLength: 100,
        maxLength: 200
      })
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`API responded with status ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.status === 'success') {
        const summaryText = `
          <p><strong>Video Summary:</strong></p>
          <p>${data.summary}</p>
          <p class="quick-result-note">Open extension for more options and full transcript</p>
        `;
        updateQuickResult(summaryText);
      } else {
        throw new Error(data.error || 'Unknown error occurred');
      }
    })
    .catch(error => {
      console.error('Error getting summary:', error);
      const errorText = `
        <p class="quick-result-error">Error generating summary: ${error.message}</p>
        <p class="quick-result-note">Make sure the Python backend is running on http://localhost:5000</p>
      `;
      updateQuickResult(errorText);
    });
    
    sendResponse({status: 'processing'});
    return true;
  }

  if (request.action === 'quickKeyPointsWiki') {
    console.log('YouTube NLP Assistant: Generating key points with Wikipedia info');
    displayQuickResult('Generating key points with contextual information...', 'key_points_wiki');
    fetch('http://localhost:5000/api/keypoints_wiki', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        videoId: currentVideoId,
        numPoints: 5
      })
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`API responded with status ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.status === 'success') {
        let keyPointsHtml = '<p><strong>Key Points with Context:</strong></p>';
        data.keyPoints.forEach((point, index) => {
          keyPointsHtml += `
            <div class="key-point-item">
              <div class="key-point-number">${index + 1}</div>
              <div class="key-point-content">
                <div class="key-point-text">${point.key_point}</div>
                ${point.wikipedia_info ? `
                  <div class="wikipedia-info">
                    <div class="wikipedia-title">
                      <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAB/ElEQVQ4jZ2Tv2sUQRTHP7O7l8seEezy4w+IYhFRLFQSBSGF2CgIFoqFhYVYWFj5L1j6B1hZCIKixUVFDKiIRRr9FYyIQdDo3d7e7fpiMXvJ5mLAB9Pswzffb+Z7M/C/pLOQQnYwKSrjEJ8qYkClXR3GXKZYYn3p5jZjdDaRkN9dAo/XqmfVKFELViS+h7dCvdHvCH+9MBCoZAXFD5dQPTVIJCBH8BbFvwBx+cRaMBTw+PJl4PUgvU2kTQ8XZz7uzH+LX6BQPXZfKntmZqZWyodKpVJXVWLnHKlzqCrRWhTDMPA+Auwv5UPj4bCa5WmW51mejccq7U4YhupHgp2iDeDQYrM25KSCZ7ZmYkzZGGNNagICtq0F7sWWy2G7b5tNcE3ANwWf4MWdqPEz7yMDWDQrMnIbBPXbTw5+bbODQnNnrD5y6nzYXUPktcDRLYILU3fX1mG8b4MiJsqCGbYmQHp62tbKjfH1yNM3iqx0Fy9OLB34BHB49G5NRN8qXJidnT35r399fX0NReqK3JqanPy0NTO0+hG+g5WGO1cq77+WXxcj9fGx0SiKojgGGGgE4J7nZf8W6qVa7X24uPgBONwHcAS4BtieiYDQH6Uik73gW4FFoLsJaJAHJoB5YHDzPZADNXqW9csfXkwKBTAogL8AAAAASUVORK5CYII=" class="wiki-icon">
                      <span>${point.wikipedia_info.title}</span>
                    </div>
                    <div class="wikipedia-summary">${point.wikipedia_info.summary}</div>
                    <a href="${point.wikipedia_info.url}" target="_blank" class="wiki-link">Read more on Wikipedia</a>
                  </div>
                ` : ''}
              </div>
            </div>
          `;
        });
        keyPointsHtml += `
          <p class="quick-result-note">Key points extracted from video content with Wikipedia context</p>
          <p class="quick-result-note">Open extension for more options</p>
        `;
        updateQuickResult(keyPointsHtml);
        const style = document.createElement('style');
        style.textContent += `
          .key-point-item {
            display: flex;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid #e0e0e0;
          }
          .key-point-number {
            background-color: #FF0000;
            color: white;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin-right: 10px;
            flex-shrink: 0;
          }
          .key-point-content {
            flex: 1;
          }
          .key-point-text {
            font-weight: 500;
            margin-bottom: 8px;
          }
          .wikipedia-info {
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            margin-top: 5px;
            font-size: 14px;
          }
          .wikipedia-title {
            font-weight: 500;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
          }
          .wiki-icon {
            width: 16px;
            height: 16px;
            margin-right: 5px;
          }
          .wikipedia-summary {
            color: #555;
            line-height: 1.4;
          }
          .wiki-link {
            display: inline-block;
            margin-top: 5px;
            color: #0366d6;
            text-decoration: none;
            font-size: 12px;
          }
          .wiki-link:hover {
            text-decoration: underline;
          }
        `;
        document.head.appendChild(style);
      } else {
        throw new Error(data.error || 'Unknown error occurred');
      }
    })
    .catch(error => {
      console.error('Error processing key points with wiki:', error);
      const errorText = `
        <p class="quick-result-error">Error generating key points: ${error.message}</p>
        <p class="quick-result-note">Make sure the Python backend is running on http://localhost:5000</p>
      `;
      updateQuickResult(errorText);
    });
    
    sendResponse({status: 'processing'});
    return true;
  }
});

// Handle quick timestamps request
if (request.action === 'quickTimestamps') {
  console.log('YouTube NLP Assistant: Generating timestamps');
  displayQuickResult('Generating timestamps...', 'timestamps');
  
  // Call the timestamps API
  fetch('http://localhost:5000/api/timestamps', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      videoId: currentVideoId
    })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`API responded with status ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    if (data.status === 'success') {
      let timestampsHtml = '<p><strong>Video Timestamps:</strong></p>';
      
      data.timestamps.forEach(ts => {
        timestampsHtml += `
          <div class="timestamp-item" data-time="${ts.time}" data-segment-id="${ts.segment_id}">
            <strong>${ts.formatted_time}</strong> - ${ts.title}
            <div class="segment-summary-container" id="quick-segment-container-${ts.segment_id}"></div>
          </div>
        `;
      });
      
      timestampsHtml += `
        <p class="quick-result-note">Click any timestamp to jump to that point and see a summary</p>
        <p class="quick-result-note">Open extension for more options</p>
      `;
      
      updateQuickResult(timestampsHtml);
      
      // Add click handlers for timestamps
      const timestampItems = document.querySelectorAll('.timestamp-item');
      timestampItems.forEach(item => {
        item.addEventListener('click', function() {
          const timeInSeconds = parseFloat(this.getAttribute('data-time'));
          const segmentId = parseInt(this.getAttribute('data-segment-id'), 10);
          
          // Navigate to this time in the video
          navigateToVideoTime(timeInSeconds);
          
          // Check if summary is already generated
          const summaryContainer = document.getElementById(`quick-segment-container-${segmentId}`);
          
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
            <div class="quick-segment-summary" id="quick-segment-summary-${segmentId}">
              <p>Loading segment summary...</p>
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
              document.getElementById(`quick-segment-summary-${segmentId}`).innerHTML = `
                <div class="quick-segment-summary-content">
                  <p><strong>Summary:</strong> ${data.summary}</p>
                </div>
              `;
            } else {
              throw new Error(data.error || 'Unknown error occurred');
            }
          })
          .catch(error => {
            document.getElementById(`quick-segment-summary-${segmentId}`).innerHTML = `
              <div class="quick-segment-summary-error">
                <p>Error: ${error.message}</p>
              </div>
            `;
          });
        });
      });
    } else {
      throw new Error(data.error || 'Unknown error occurred');
    }
  })
  .catch(error => {
    console.error('Error generating timestamps:', error);
    const errorText = `
      <p class="quick-result-error">Error generating timestamps: ${error.message}</p>
      <p class="quick-result-note">Make sure the Python backend is running on http://localhost:5000</p>
    `;
    updateQuickResult(errorText);
  });
  
  sendResponse({status: 'processing'});
  return true;
}

// Default response for unknown actions
sendResponse({status: 'error', message: 'Unknown action'});
return true;

// Display a quick result overlay on the YouTube page
function displayQuickResult(loadingMessage, resultType) {
// Remove any existing overlay
removeQuickResult();

// Create overlay container
const overlay = document.createElement('div');
overlay.id = 'yt-nlp-assistant-overlay';
overlay.style.cssText = `
  position: fixed;
  top: 70px;
  right: 20px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.2);
  width: 350px;
  max-height: 500px;
  overflow-y: auto;
  z-index: 9999;
  padding: 15px;
  font-family: 'Roboto', Arial, sans-serif;
`;

// Add header
const header = document.createElement('div');
header.style.cssText = `
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e0e0e0;
`;

const title = document.createElement('h3');
title.textContent = 'YouTube NLP Assistant';
title.style.cssText = `
  margin: 0;
  color: #FF0000;
  font-size: 16px;
`;

const closeButton = document.createElement('button');
closeButton.innerHTML = '&times;';
closeButton.style.cssText = `
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #606060;
`;
closeButton.onclick = removeQuickResult;

header.appendChild(title);
header.appendChild(closeButton);
overlay.appendChild(header);

// Add loading content
const content = document.createElement('div');
content.id = 'yt-nlp-assistant-content';
content.setAttribute('data-result-type', resultType);

// Add loading spinner
const loadingSpinner = document.createElement('div');
loadingSpinner.style.cssText = `
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px 0;
`;

const spinner = document.createElement('div');
spinner.style.cssText = `
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #FF0000;
  border-radius: 50%;
  animation: yt-nlp-spin 1s linear infinite;
`;

const loadingText = document.createElement('p');
loadingText.textContent = loadingMessage;
loadingText.style.cssText = `
  margin-top: 10px;
  color: #606060;
`;

// Add the animation keyframes
const style = document.createElement('style');
style.textContent = `
  @keyframes yt-nlp-spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
  
  .timestamp-item {
    padding: 10px 5px;
    cursor: pointer;
    border-bottom: 1px solid #f0f0f0;
  }
  
  .timestamp-item:hover {
    background-color: #f9f9f9;
  }
  
  .quick-result-note {
    font-size: 12px;
    color: #666;
    margin-top: 10px;
    font-style: italic;
  }
  
  .quick-result-error {
    color: #cc0000;
    margin-bottom: 8px;
  }
  
  .quick-segment-summary {
    background-color: #f5f5f5;
    border-radius: 6px;
    padding: 12px;
    font-size: 14px;
    margin-top: 8px;
    border-left: 3px solid #FF0000;
  }
  
  .segment-summary-container {
    margin-top: 10px;
  }
  
  .hidden {
    display: none !important;
  }
`;
document.head.appendChild(style);

loadingSpinner.appendChild(spinner);
loadingSpinner.appendChild(loadingText);
content.appendChild(loadingSpinner);
overlay.appendChild(content);

// Add to page
document.body.appendChild(overlay);
}

// Update the quick result with actual content
function updateQuickResult(resultHtml) {
const content = document.getElementById('yt-nlp-assistant-content');
if (content) {
  content.innerHTML = resultHtml;
  content.style.cssText = `
    padding: 10px 0;
    line-height: 1.5;
  `;
}
}

// Remove the quick result overlay
function removeQuickResult() {
const overlay = document.getElementById('yt-nlp-assistant-overlay');
if (overlay) {
  document.body.removeChild(overlay);
}
}

// Navigate to a specific time in the video
function navigateToVideoTime(seconds) {
console.log('Navigating to time:', seconds);
// Get the video element
const video = document.querySelector('video');
if (video) {
  // Set the current time
  video.currentTime = seconds;
  
  // Focus the video so the user can immediately pause if needed
  video.focus();
  
  // Add a visual indicator to show the user where they jumped to
  const indicator = document.createElement('div');
  indicator.style.cssText = `
    position: fixed;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    background-color: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 10px 20px;
    border-radius: 20px;
    font-family: 'Roboto', Arial, sans-serif;
    z-index: 9999;
    font-size: 14px;
    animation: fade-out 2s forwards;
  `;
  
  // Format the time for display
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  const formattedTime = `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  
  indicator.textContent = `Jumped to ${formattedTime}`;
  
  // Add fade-out animation
  const fadeStyle = document.createElement('style');
  fadeStyle.textContent = `
    @keyframes fade-out {
      0% { opacity: 1; }
      70% { opacity: 1; }
      100% { opacity: 0; }
    }
  `;
  document.head.appendChild(fadeStyle);
  
  // Add to page and remove after animation
  document.body.appendChild(indicator);
  setTimeout(() => {
    if (indicator.parentNode) {
      document.body.removeChild(indicator);
    }
  }, 2000);
  
  // Return success status
  return true;
} else {
  console.error('No video element found');
  return false;
}
}

// Initialize on page load
if (document.readyState === 'complete') {
initialize();
} else {
window.addEventListener('load', initialize);
}