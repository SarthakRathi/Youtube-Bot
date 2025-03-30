// Background script for the YouTube NLP Assistant extension

// Listen for installation
chrome.runtime.onInstalled.addListener(function() {
  console.log('YouTube NLP Assistant has been installed');
  
  // Set default settings
  chrome.storage.local.set({
    enabledFeatures: [
      'summarize', 
      'timestamps', 
      'sentiment', 
      'keypoints', 
      'questions'
    ],
    apiEndpoint: 'https://your-nlp-api-endpoint.com/api'
  });
});

// Listen for messages from content script or popup
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  try {
    if (request.action === 'processVideo') {
      // This would typically make API calls to your NLP backend
      // Here we're just setting up the message structure
      
      const videoId = request.videoId;
      const feature = request.feature;
      
      console.log(`Processing video ${videoId} with feature ${feature}`);
      
      // In a real implementation, you would make an API call here
      // and then send the response back to the popup or content script
      
      // For now, just acknowledge receipt
      sendResponse({status: 'processing', message: 'Request received'});
      
      // Return true to indicate you wish to send a response asynchronously
      return true;
    }
  } catch (error) {
    console.error('Error processing message:', error);
    sendResponse({status: 'error', message: error.message});
    return true;
  }
});

// Add context menu items when on YouTube
chrome.runtime.onInstalled.addListener(() => {
  // Make sure the contextMenus API is available before using it
  if (chrome.contextMenus) {
    // Clear any existing menu items to avoid duplicates
    chrome.contextMenus.removeAll(() => {
      // Create the parent menu item
      chrome.contextMenus.create({
        id: 'youtube-nlp-assistant',
        title: 'YouTube NLP Assistant',
        contexts: ['page'],
        documentUrlPatterns: ['https://www.youtube.com/watch*']
      });
      
      // Create submenu items
      chrome.contextMenus.create({
        id: 'quick-summarize',
        parentId: 'youtube-nlp-assistant',
        title: 'Quick Summarize',
        contexts: ['page'],
        documentUrlPatterns: ['https://www.youtube.com/watch*']
      });
      
      chrome.contextMenus.create({
        id: 'quick-timestamps',
        parentId: 'youtube-nlp-assistant',
        title: 'Generate Timestamps',
        contexts: ['page'],
        documentUrlPatterns: ['https://www.youtube.com/watch*']
      });
    });
    
    // Handle context menu clicks
    chrome.contextMenus.onClicked.addListener((info, tab) => {
      if (info.menuItemId === 'quick-summarize') {
        chrome.tabs.sendMessage(tab.id, {action: 'quickSummarize'});
      } else if (info.menuItemId === 'quick-timestamps') {
        chrome.tabs.sendMessage(tab.id, {action: 'quickTimestamps'});
      }
    });
  }
});