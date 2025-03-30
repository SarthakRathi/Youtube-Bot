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
segment_cache = {}

@app.route('/api/summarize', methods=['POST', 'OPTIONS'])
def summarize_video():
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
        
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

@app.route('/api/timestamps', methods=['POST', 'OPTIONS'])
def generate_video_timestamps():
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
        
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
        
        # Generate timestamps using our improved function
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

@app.route('/api/segment_summary', methods=['POST', 'OPTIONS'])
def summarize_segment():
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
        
    # Get data from request
    data = request.json
    video_id = data.get('videoId')
    segment_id = data.get('segmentId')
    
    if not video_id or segment_id is None:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    # Create cache key
    cache_key = f"{video_id}_{segment_id}"
    if cache_key in segment_cache:
        print(f"Using cached segment summary for video {video_id}, segment {segment_id}")
        return jsonify(segment_cache[cache_key])
    
    try:
        # First, check if we already have the timestamps
        if video_id in timestamps_cache:
            timestamps = timestamps_cache[video_id]['timestamps']
        else:
            # Generate timestamps
            timestamps = timestamps_feature.generate_timestamps(video_id)
            timestamps_cache[video_id] = {
                'status': 'success',
                'videoId': video_id,
                'timestamps': timestamps,
                'timestamp': time.time()
            }
        
        if segment_id >= len(timestamps) or segment_id < 0:
            return jsonify({'error': 'Invalid segment ID'}), 400
        
        # Get the current segment and the next one to determine time range
        current = timestamps[segment_id]
        next_time = timestamps[segment_id + 1]["time"] if segment_id + 1 < len(timestamps) else None
        
        # Get transcript for this time range
        segment_text = timestamps_feature.get_segment_transcript(
            video_id, 
            current["time"], 
            next_time
        )
        
        if not segment_text.strip():
            return jsonify({'error': 'No transcript found for this segment'}), 404
        
        # Generate summary for this segment using the updated parameter names
        try:
            # Try with new parameter names (target_min_length, target_max_length)
            summary = youtube_summarizer.summarize_text(
                segment_text,
                target_min_length=30,
                target_max_length=100
            )
        except TypeError:
            # Fall back to old parameter names if needed
            summary = youtube_summarizer.summarize_text(
                segment_text,
                min_length=30,
                max_length=100
            )
        
        result = {
            'status': 'success',
            'videoId': video_id,
            'segmentId': segment_id,
            'summary': summary,
            'timestamp': current["time"],
            'formatted_time': current["formatted_time"],
            'title': current["title"]
        }
        
        # Cache the result
        segment_cache[cache_key] = result
        
        return jsonify(result)
    
    except Exception as e:
        error_response = {
            'status': 'error',
            'videoId': video_id,
            'segmentId': segment_id,
            'error': str(e)
        }
        return jsonify(error_response), 500

@app.route('/api/keypoints', methods=['POST', 'OPTIONS'])
def extract_keypoints():
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
        
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

@app.route('/api/sentiment', methods=['POST', 'OPTIONS'])
def analyze_sentiment():
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
        
    return jsonify({
        'status': 'success',
        'message': 'Sentiment analysis feature coming soon'
    })

@app.route('/api/keypoints_wiki', methods=['POST', 'OPTIONS'])
def extract_keypoints_with_wiki():
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
        
    # Get data from request
    data = request.json
    video_id = data.get('videoId')
    
    if not video_id:
        return jsonify({'error': 'No video ID provided'}), 400
    
    # Get number of terms requested (default to 8)
    num_terms = int(data.get('numTerms', 8))
    
    # Check if we have a cached result with the correct number of terms
    cache_key = f"keypoints_wiki_{video_id}_{num_terms}"
    if cache_key in summary_cache:
        print(f"Using cached wiki key terms for video {video_id}")
        return jsonify(summary_cache[cache_key])
    
    try:
        # Ensure NLTK resources are downloaded
        try:
            import nltk
            nltk.download('punkt')
            nltk.download('stopwords')
        except Exception as e:
            print(f"Warning: NLTK download issue: {e}")
        
        # Get transcript directly without summarizing
        from youtube_transcript_api import YouTubeTranscriptApi
        
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript = ' '.join([item['text'] for item in transcript_list])
            print(f"Retrieved transcript with {len(transcript.split())} words")
        except Exception as e:
            print(f"Error fetching transcript: {e}")
            return jsonify({'error': 'Could not retrieve transcript'}), 400
        
        # Import the Wikipedia integration module
        import wikipedia_integration
        
        print(f"Generating {num_terms} key terms with Wikipedia information...")
        
        # Generate key terms with Wikipedia information
        key_terms = wikipedia_integration.generate_key_points_with_wikipedia(
            transcript, 
            max_terms=num_terms
        )
        
        print(f"Generated {len(key_terms)} key terms")
        
        # Verify we have the expected number
        if len(key_terms) < num_terms:
            print(f"Warning: Only generated {len(key_terms)} terms, expected {num_terms}")
        
        # Prepare response
        result = {
            'status': 'success',
            'videoId': video_id,
            'keyPoints': key_terms,
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
        print(f"Error in keypoints_wiki: {str(e)}")
        return jsonify(error_response), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok', 
        'message': 'API is running'
    })

if __name__ == '__main__':
    # Create cache directory if it doesn't exist
    os.makedirs('cache', exist_ok=True)
    
    # Ensure NLTK resources are downloaded before server starts
    print("Setting up NLTK resources...")
    try:
        import timestamps_feature
        timestamps_feature.ensure_nltk_data()
    except Exception as e:
        print(f"Warning: Error downloading NLTK resources: {e}")
        print("Please run: python -m nltk.downloader punkt")
    
    print("Starting YouTube NLP API server...")
    app.run(host='0.0.0.0', port=5000, debug=True)