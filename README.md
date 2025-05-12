# YouTube NLP Assistant

An AI-driven tool that processes YouTube video transcripts and user comments to generate insights about video content.

## Overview

The sheer volume of YouTube videos makes it difficult to locate relevant information quickly. YouTube NLP Assistant addresses this by automatically retrieving a video's transcript, using advanced NLP to summarize the content, segment the video into chapters, identify key entities with Wikipedia context, and gauge community sentiment from user comments.

The result is a more interactive, AI-powered experience for the user:
- Summaries to highlight main ideas
- Timestamp "chapters" for quick navigation
- Key terms enriched with external knowledge
- Sentiment insights to flag potential controversies

## Features

- **Summarization**: Uses a transformer-based model (such as BART) to generate concise, human-like summaries from raw transcripts.
- **Timestamp Generation (Chapters)**: Segments the transcript via semantic analysis, allowing direct jumps to specific sections.
- **Key Point Extraction**: Identifies critical entities or concepts and fetches short Wikipedia summaries for added context.
- **Fact Checking (via Sentiment Analysis)**: Retrieves and analyzes top-level YouTube comments to approximate user reception and highlight potential misinformation signals.
- **Caching**: Reduces redundant computations by storing previously requested summaries, timestamps, and other data.

## Architecture

The system follows a client-server model:

**Browser Extension (Client)**
- Extracts the current YouTube video ID in the user's browser.
- Offers an interface to request Summaries, Timestamps, Key Points, and Fact Checking data from the backend.

**Flask Server (Backend)**
- Hosts NLP modules (summarization, segmentation, entity extraction, sentiment analysis).
- Manages caching to optimize performance.
- Interacts with external services (YouTube Data API for comments, Wikipedia for contextual info).

Conceptually, the browser extension sends requests to the Flask server, which processes the transcript or comments, then returns structured results to be displayed on the YouTube page or in a popup interface.

## Installation

### Clone the Repository
```bash
git clone https://github.com/YourUsername/YouTubeNLPAssistant.git
cd YouTubeNLPAssistant
```

### (Optional) Create a Virtual Environment

On Linux/Mac:
```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Set Your YouTube Data API Key

On Linux/Mac (temporary in current terminal):
```bash
export YOUTUBE_API_KEY="YOUR_ACTUAL_API_KEY"
```

On Windows (Command Prompt):
```bash
set YOUTUBE_API_KEY=YOUR_ACTUAL_API_KEY
```

Using a .env file (with python-dotenv installed):
Create a file named `.env` in the project root containing:
```
YOUTUBE_API_KEY=YOUR_ACTUAL_API_KEY
```

### Launch the Flask Server
```bash
python app.py
```
By default, this starts the app at http://localhost:5000.
(If you prefer another port, edit the server's run configuration in your code.)

## Usage

1. Make sure the Flask server is running on http://localhost:5000 (or whichever port you specified).
2. Use a browser extension (Chrome extension) to interface with the system.
3. Navigate to any YouTube video, open the extension, and select from features such as Summarize, Timestamps, Key Points, or Fact Check.
4. You can also directly call the API endpoints (described below) via tools like cURL or Postman.

## API Endpoints

The Flask server provides several endpoints:

### POST /api/summarize
- Body example: `{"videoId": "<VIDEO_ID>", "minLength": 150, "maxLength": 300}`
- Returns a JSON response with a summarized transcript.

### POST /api/timestamps
- Body example: `{"videoId": "<VIDEO_ID>"}`
- Returns a list of semantic "chapters" (timestamp sections).

### POST /api/keypoints_wiki
- Body example: `{"videoId": "<VIDEO_ID>", "numTerms": 8}`
- Identifies key entities/terms and provides short Wikipedia summaries.

### POST /api/factcheck
- Body example: `{"videoId": "<VIDEO_ID>"}`
- Analyzes user comments for sentiment (positive vs. negative) to gauge potential controversies.

### POST /api/segment_summary
- Body example: `{"videoId": "<VIDEO_ID>", "segmentId": 0}`
- Generates a focused summary of a specific segment previously identified in /api/timestamps.

## Chrome Extension Integration

### Load the Extension in Chrome

1. Go to chrome://extensions/ in Chrome.
2. Enable "Developer Mode."
3. Click "Load unpacked" and select the extension folder (where popup.html, popup.js, manifest.json, etc. exist).

### Adjust popup.js if Necessary

- Ensure the API base URLs match your Flask server location (by default http://localhost:5000).
- Change them if you're using a different port or hosting the server remotely.

### Test on YouTube

1. Open a YouTube video.
2. Click the extension icon to open the YouTube NLP Assistant popup.
3. Try features like Summarize, Timestamps, or Key Points.

## Caching and Performance

Because transformer-based summarization and entity extraction can be computationally heavy, the system stores results in memory (or on disk) for repeated calls to the same video. This caching significantly cuts down on processing time for popular or frequently analyzed videos.

## Roadmap

Potential future improvements and directions:

- Add multilingual support for transcripts and summarization.
- Integrate external fact-checking APIs or knowledge graphs for more rigorous verification.
- Enhance named entity recognition and disambiguation for domain-specific topics.
- Provide an official Docker setup for easier deployment.

## Contributing

Contributions are welcome!

1. Fork the repository on GitHub.
2. Create a new branch for your feature or bug fix.
3. Commit and push your changes.
4. Open a Pull Request explaining the updates.

## License

Unless otherwise specified, this project uses the MIT License. Refer to the LICENSE file for details.

## Contact

For questions or feedback, reach out via:

- GitHub Issues: https://github.com/SarthakRathi/Youtube-Bot/issues
- Email: sarthakrathi89@gmail.com

We appreciate bug reports, feature requests, and general suggestions!
