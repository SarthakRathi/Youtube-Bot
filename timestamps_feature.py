from flask import Flask, request, jsonify
from flask_cors import CORS
import youtube_summarizer
import time
import os

# Import the timestamps feature
import timestamps_feature

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Create a cache to store previously generated results
summary_cache = {}
timestamps_cache = {}

@app.route('/api/summarize', methods=['POST'])
def summarize_video():
    # Get data from request
    data = request.json
    video_id = data.get('videoId')
    
    if not video_id:
        return jsonify({'error': 'No video ID provided'}), 400
    
    # Check if we have a cached result
    cache_key = f"{video_id}_{data.get('minLength', 150)}_{data.get('maxLength', 300)}"
    if cache_key in summary_cache:
        print(f"Using cached summary for video {video_id}")
        return jsonify(summary_cache[cache_key])
    
    # Create YouTube URL from video ID
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        # Set custom lengths for summary
        min_length = int(data.get('minLength', 150))
        max_length = int(data.get('maxLength', 300))
        
        # Call your summarizer
        summary, transcript = youtube_summarizer.summarize_youtube_video(
            youtube_url, 
            min_length=min_length, 
            max_length=max_length
        )
        
        # Prepare response
        result = {
            'status': 'success',
            'videoId': video_id,
            'summary': summary,
            'transcript': transcript,
            'timestamp': time.time()
        }
        
        # Cache the result
        summary_cache[cache_key] = result
        
        # Return result
        return jsonify(result)
    
    except Exception as e:
        error_response = {
            'status': 'error',
            'videoId': video_id,
            'error': str(e)
        }
        return jsonify(error_response), 500

@app.route('/api/timestamps', methods=['POST'])
def generate_video_timestamps():
    # Get data from request
    data = request.json
    video_id = data.get('videoId')
    
    if not video_id:
        return jsonify({'error': 'No video ID provided'}), 400
    
    # Check if we have a cached result
    if video_id in timestamps_cache:
        print(f"Using cached timestamps for video {video_id}")
        return jsonify(timestamps_cache[video_id])
    
    try:
        print(f"Generating timestamps for video {video_id}...")
        
        # Generate timestamps
        timestamps = timestamps_feature.generate_timestamps(video_id)
        
        result = {
            'status': 'success',
            'videoId': video_id,
            'timestamps': timestamps,
            'timestamp': time.time()
        }
        
        # Cache the result
        timestamps_cache[video_id] = result
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error generating timestamps: {e}")
        error_response = {
            'status': 'error',
            'videoId': video_id,
            'error': str(e)
        }
        return jsonify(error_response), 500

@app.route('/api/keypoints', methods=['POST'])
def extract_keypoints():
    # Get data from request
    data = request.json
    video_id = data.get('videoId')
    
    if not video_id:
        return jsonify({'error': 'No video ID provided'}), 400
    
    # Create YouTube URL from video ID
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        # First get the summary
        summary, transcript = youtube_summarizer.summarize_youtube_video(
            youtube_url, 
            min_length=100, 
            max_length=200
        )
        
        if not summary:
            return jsonify({'error': 'Could not generate summary from transcript'}), 400
        
        # Create bullet points by splitting sentences
        import re
        sentences = re.split(r'(?<=[.!?])\s+', summary)
        key_points = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # Return result
        return jsonify({
            'status': 'success',
            'videoId': video_id,
            'keyPoints': key_points,
            'timestamp': time.time()
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'videoId': video_id,
            'error': str(e)
        }), 500

@app.route('/api/sentiment', methods=['POST'])
def analyze_sentiment():
    return jsonify({
        'status': 'success',
        'message': 'Sentiment analysis feature coming soon'
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok', 
        'message': 'API is running'
    })

if __name__ == '__main__':
    # Create cache directory if it doesn't exist
    os.makedirs('cache', exist_ok=True)
    
    # Install required packages for timestamps feature
    try:
        import nltk
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        print("Installing required packages for timestamps feature...")
        os.system("pip install nltk scikit-learn")
    
    print("Starting YouTube NLP API server...")
    app.run(host='0.0.0.0', port=5000, debug=True)