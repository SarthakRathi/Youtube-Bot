from flask import Flask, request, jsonify
from flask_cors import CORS
import youtube_summarizer
import time
import os

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# Create a cache to store previously generated summaries
summary_cache = {}
timestamps_cache = {}

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
        
        # Create a simplified implementation of timestamps since we don't have the full module
        from youtube_transcript_api import YouTubeTranscriptApi
        
        # Get the transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Generate simple timestamps at regular intervals
        timestamps = []
        
        if transcript:
            # Group transcript into segments (roughly every 60 seconds)
            segments = []
            current_segment = {"start": transcript[0]["start"], "text": []}
            
            for entry in transcript:
                if entry["start"] - current_segment["start"] > 60:
                    # Start a new segment
                    current_segment["text"] = " ".join(current_segment["text"])
                    segments.append(current_segment)
                    current_segment = {"start": entry["start"], "text": [entry["text"]]}
                else:
                    current_segment["text"].append(entry["text"])
            
            # Add the last segment
            if current_segment["text"]:
                current_segment["text"] = " ".join(current_segment["text"])
                segments.append(current_segment)
            
            # Convert segments to timestamps
            for i, segment in enumerate(segments):
                # Format the time
                seconds = segment["start"]
                minutes = int(seconds // 60)
                seconds_remainder = int(seconds % 60)
                formatted_time = f"{minutes}:{seconds_remainder:02d}"
                
                # Create a title from the first 40 characters of text
                text = segment["text"]
                title = text[:40] + "..." if len(text) > 40 else text
                
                # Extract simple keywords
                words = text.lower().split()
                # Filter out common words
                common_words = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were"}
                keywords = [word for word in words if len(word) > 3 and word not in common_words]
                # Get top 3 keywords by length
                keywords = sorted(set(keywords), key=len, reverse=True)[:3]
                
                timestamps.append({
                    "time": segment["start"],
                    "formatted_time": formatted_time,
                    "title": f"Segment {i+1}: {title}",
                    "keywords": keywords
                })
        
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

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok', 
        'message': 'API is running'
    })

if __name__ == '__main__':
    # Create cache directory if it doesn't exist
    os.makedirs('cache', exist_ok=True)
    
    print("Starting YouTube NLP API server...")
    app.run(host='0.0.0.0', port=5000, debug=True)