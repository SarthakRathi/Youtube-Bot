from flask import Flask, request, jsonify
from flask_cors import CORS
import youtube_summarizer
import time
import os

# Import the timestamps feature
import timestamps_feature

# For fact check functionality
from transformers import pipeline
from googleapiclient.discovery import build

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Create caches
summary_cache = {}
timestamps_cache = {}
segment_cache = {}

@app.route('/api/summarize', methods=['POST', 'OPTIONS'])
def summarize_video():
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.json
    video_id = data.get('videoId')
    if not video_id:
        return jsonify({'error': 'No video ID provided'}), 400

    cache_key = f"{video_id}_{data.get('minLength', 150)}_{data.get('maxLength', 300)}"
    if cache_key in summary_cache:
        print(f"Using cached summary for video {video_id}")
        return jsonify(summary_cache[cache_key])
    
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        min_length = int(data.get('minLength', 150))
        max_length = int(data.get('maxLength', 300))
        
        summary, transcript = youtube_summarizer.summarize_youtube_video(
            youtube_url, 
            min_length=min_length, 
            max_length=max_length
        )
        
        result = {
            'status': 'success',
            'videoId': video_id,
            'summary': summary,
            'transcript': transcript,
            'timestamp': time.time()
        }
        
        summary_cache[cache_key] = result
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
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.json
    video_id = data.get('videoId')
    if not video_id:
        return jsonify({'error': 'No video ID provided'}), 400
    
    if video_id in timestamps_cache:
        print(f"Using cached timestamps for video {video_id}")
        return jsonify(timestamps_cache[video_id])
    
    try:
        print(f"Generating timestamps for video {video_id}...")
        timestamps = timestamps_feature.generate_timestamps(video_id)
        
        result = {
            'status': 'success',
            'videoId': video_id,
            'timestamps': timestamps,
            'timestamp': time.time()
        }
        
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
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.json
    video_id = data.get('videoId')
    segment_id = data.get('segmentId')
    
    if not video_id or segment_id is None:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    cache_key = f"{video_id}_{segment_id}"
    if cache_key in segment_cache:
        print(f"Using cached segment summary for video {video_id}, segment {segment_id}")
        return jsonify(segment_cache[cache_key])
    
    try:
        if video_id in timestamps_cache:
            timestamps = timestamps_cache[video_id]['timestamps']
        else:
            timestamps = timestamps_feature.generate_timestamps(video_id)
            timestamps_cache[video_id] = {
                'status': 'success',
                'videoId': video_id,
                'timestamps': timestamps,
                'timestamp': time.time()
            }
        
        if segment_id >= len(timestamps) or segment_id < 0:
            return jsonify({'error': 'Invalid segment ID'}), 400
        
        current = timestamps[segment_id]
        next_time = timestamps[segment_id + 1]["time"] if segment_id + 1 < len(timestamps) else None
        
        segment_text = timestamps_feature.get_segment_transcript(
            video_id, 
            current["time"], 
            next_time
        )
        
        if not segment_text.strip():
            return jsonify({'error': 'No transcript found for this segment'}), 404
        
        try:
            summary = youtube_summarizer.summarize_text(
                segment_text,
                target_min_length=30,
                target_max_length=100
            )
        except TypeError:
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
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.json
    video_id = data.get('videoId')
    if not video_id:
        return jsonify({'error': 'No video ID provided'}), 400
    
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        summary, transcript = youtube_summarizer.summarize_youtube_video(
            youtube_url, 
            min_length=100, 
            max_length=200
        )
        
        if not summary:
            return jsonify({'error': 'Could not generate summary from transcript'}), 400
        
        import re
        sentences = re.split(r'(?<=[.!?])\s+', summary)
        key_points = [s.strip() for s in sentences if len(s.strip()) > 20]
        
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
    if request.method == 'OPTIONS':
        return '', 200
        
    return jsonify({
        'status': 'success',
        'message': 'Sentiment analysis feature coming soon'
    })

@app.route('/api/keypoints_wiki', methods=['POST', 'OPTIONS'])
def extract_keypoints_with_wiki():
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.json
    video_id = data.get('videoId')
    
    if not video_id:
        return jsonify({'error': 'No video ID provided'}), 400
    
    num_terms = int(data.get('numTerms', 8))
    
    cache_key = f"keypoints_wiki_{video_id}_{num_terms}"
    if cache_key in summary_cache:
        print(f"Using cached wiki key terms for video {video_id}")
        return jsonify(summary_cache[cache_key])
    
    try:
        try:
            import nltk
            nltk.download('punkt')
            nltk.download('stopwords')
        except Exception as e:
            print(f"Warning: NLTK download issue: {e}")
        
        from youtube_transcript_api import YouTubeTranscriptApi
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript = ' '.join([item['text'] for item in transcript_list])
            print(f"Retrieved transcript with {len(transcript.split())} words")
        except Exception as e:
            print(f"Error fetching transcript: {e}")
            return jsonify({'error': 'Could not retrieve transcript'}), 400
        
        import wikipedia_integration
        print(f"Generating {num_terms} key terms with Wikipedia information...")
        
        key_terms = wikipedia_integration.generate_key_points_with_wikipedia(
            transcript, 
            max_terms=num_terms
        )
        
        print(f"Generated {len(key_terms)} key terms")
        if len(key_terms) < num_terms:
            print(f"Warning: Only generated {len(key_terms)} terms, expected {num_terms}")
        
        result = {
            'status': 'success',
            'videoId': video_id,
            'keyPoints': key_terms,
            'timestamp': time.time()
        }
        
        summary_cache[cache_key] = result
        return jsonify(result)
    
    except Exception as e:
        error_response = {
            'status': 'error',
            'videoId': video_id,
            'error': str(e)
        }
        print(f"Error in keypoints_wiki: {str(e)}")
        return jsonify(error_response), 500

@app.route('/api/factcheck', methods=['POST', 'OPTIONS'])
def fact_check():
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.json
    video_id = data.get('videoId')
    if not video_id:
        return jsonify({'error': 'No video ID provided'}), 400

    try:
        # Fetch comments using the YouTube Data API
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if not api_key:
            raise Exception("YouTube API key not set. Please set the YOUTUBE_API_KEY environment variable.")
        
        youtube = build('youtube', 'v3', developerKey=api_key)
        comments = []
        request_comments = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            textFormat="plainText",
            maxResults=100
        )
        response = request_comments.execute()
        while response:
            for item in response.get("items", []):
                comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                comments.append(comment)
            if "nextPageToken" in response:
                request_comments = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    textFormat="plainText",
                    maxResults=100,
                    pageToken=response["nextPageToken"]
                )
                response = request_comments.execute()
            else:
                break
        
        if not comments:
            return jsonify({
                'status': 'error',
                'videoId': video_id,
                'error': 'No comments found for this video'
            }), 404

        # Helper function to truncate comments by words (if desired)
        def truncate_text(text, max_words=128):
            words = text.split()
            if len(words) > max_words:
                return " ".join(words[:max_words])
            return text

        # Truncate each comment by words
        truncated_comments = [truncate_text(comment) for comment in comments]

        # Run sentiment analysis with truncation enabled so that inputs beyond the model limit are trimmed
        sentiment_analyzer = pipeline("sentiment-analysis")
        sentiments = sentiment_analyzer(truncated_comments, truncation=True)

        pos_count = sum(1 for s in sentiments if s['label'] == 'POSITIVE')
        neg_count = sum(1 for s in sentiments if s['label'] == 'NEGATIVE')
        total = len(sentiments)
        
        aggregated = {
            'positive_percentage': round((pos_count / total * 100), 2) if total > 0 else 0,
            'negative_percentage': round((neg_count / total * 100), 2) if total > 0 else 0,
            'total_comments': total
        }
        
        return jsonify({
            'status': 'success',
            'videoId': video_id,
            'sentiment': aggregated,
            'comments_sample': comments[:5]
        })
    
    except Exception as e:
        print(f"Error in fact_check endpoint: {e}")
        return jsonify({
            'status': 'error',
            'videoId': video_id,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok', 
        'message': 'API is running'
    })

if __name__ == '__main__':
    os.makedirs('cache', exist_ok=True)
    print("Setting up NLTK resources...")
    try:
        import timestamps_feature
        timestamps_feature.ensure_nltk_data()
    except Exception as e:
        print(f"Warning: Error downloading NLTK resources: {e}")
        print("Please run: python -m nltk.downloader punkt")
    
    print("Starting YouTube NLP API server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
