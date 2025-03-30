import nltk
from youtube_transcript_api import YouTubeTranscriptApi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from collections import Counter
import re
import os
import sys

# Global variables for models
sentence_transformer = None
nlp = None

def ensure_nltk_data():
    """Ensure all required NLTK data is properly downloaded."""
    print("Setting up NLTK data path...")
    # Add current directory to NLTK data path
    nltk_data_dir = os.path.join(os.getcwd(), 'nltk_data')
    os.makedirs(nltk_data_dir, exist_ok=True)
    nltk.data.path.insert(0, nltk_data_dir)
    
    # Download punkt to our specified directory
    print(f"Downloading punkt to {nltk_data_dir}")
    nltk.download('punkt', download_dir=nltk_data_dir, quiet=False)
    
    # Add punkt_tab download
    print(f"Downloading punkt_tab to {nltk_data_dir}")
    nltk.download('punkt_tab', download_dir=nltk_data_dir, quiet=False)
    
    # Verify the download worked
    try:
        nltk.data.find('tokenizers/punkt')
        print("NLTK punkt tokenizer is available!")
        return True
    except LookupError:
        print("Failed to find punkt tokenizer even after download attempt")
        return False

def load_models():
    """Load all required NLP models."""
    global sentence_transformer, nlp
    
    # Only load models if they're not already loaded
    if sentence_transformer is None:
        try:
            # Load Sentence Transformer for better semantic similarity
            from sentence_transformers import SentenceTransformer
            print("Loading SentenceTransformer model...")
            sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            print("SentenceTransformer model loaded successfully")
        except ImportError:
            print("SentenceTransformer not available. Using fallback TF-IDF.")
    
    if nlp is None:
        try:
            # Load spaCy for better text processing
            import spacy
            print("Loading spaCy model...")
            nlp = spacy.load("en_core_web_sm")
            print("spaCy model loaded successfully")
        except ImportError:
            print("spaCy not available. Using fallback tokenization.")
        except OSError:
            print("spaCy model not found. Using fallback tokenization.")

def segment_transcript_by_silence(transcript_items, min_silence_duration=1.0):
    """Find natural breaks in the transcript based on pauses in speech."""
    silence_boundaries = []
    
    for i in range(len(transcript_items) - 1):
        current_item = transcript_items[i]
        next_item = transcript_items[i + 1]
        
        # Calculate gap between end of current item and start of next item
        current_end = current_item['start'] + current_item['duration']
        next_start = next_item['start']
        gap_duration = next_start - current_end
        
        # If there's a significant gap, mark it as a potential boundary
        if gap_duration >= min_silence_duration:
            silence_boundaries.append({
                'index': i,
                'time': next_start,
                'duration': gap_duration
            })
    
    return silence_boundaries

def calculate_sentence_embeddings(sentences):
    """Calculate embeddings for each sentence using Sentence Transformers."""
    global sentence_transformer
    
    if sentence_transformer is not None:
        return sentence_transformer.encode(sentences)
    else:
        # Fallback to TF-IDF if sentence transformers not available
        vectorizer = TfidfVectorizer()
        return vectorizer.fit_transform(sentences).toarray()

def segment_by_topic_shifts(sentences, sentence_timestamps):
    """Identify topic shifts using semantic similarity between sentence windows."""
    window_size = 3  # Number of sentences in each window
    threshold = 0.5  # Similarity threshold for topic change
    
    if len(sentences) <= window_size * 2:
        # Too few sentences for meaningful segmentation
        return [0, len(sentences)-1]
    
    try:
        # Get sentence embeddings
        if sentence_transformer is not None:
            # Using SentenceTransformer
            embeddings = sentence_transformer.encode(sentences)
            
            # Calculate similarity between consecutive windows
            similarities = []
            for i in range(len(sentences) - window_size):
                window1 = embeddings[i:i+window_size]
                window2 = embeddings[i+window_size:i+window_size*2]
                
                # Average the embeddings in each window
                window1_avg = np.mean(window1, axis=0)
                window2_avg = np.mean(window2, axis=0)
                
                # Calculate cosine similarity
                similarity = np.dot(window1_avg, window2_avg) / (np.linalg.norm(window1_avg) * np.linalg.norm(window2_avg))
                similarities.append(similarity)
        else:
            # Fallback to TF-IDF
            vectorizer = TfidfVectorizer(stop_words='english')
            vectors = vectorizer.fit_transform(sentences)
            
            # Calculate similarity between consecutive windows
            similarities = []
            for i in range(len(sentences) - window_size):
                window1 = vectors[i:i+window_size]
                window2 = vectors[i+window_size:i+window_size*2]
                
                # Average the vectors in each window
                window1_avg = window1.mean(axis=0)
                window2_avg = window2.mean(axis=0)
                
                # Calculate cosine similarity
                similarity = cosine_similarity(window1_avg, window2_avg)[0, 0]
                similarities.append(similarity)
        
        # Find boundaries (points of low similarity)
        topic_boundaries = [0]  # Always include the start
        for i in range(1, len(similarities)):
            if similarities[i] < threshold and similarities[i] < similarities[i-1]:
                # Topic change at the start of the second window
                boundary_idx = i + window_size
                if boundary_idx < len(sentences):
                    topic_boundaries.append(boundary_idx)
        
        # Always include the end
        if len(sentences) - 1 not in topic_boundaries:
            topic_boundaries.append(len(sentences) - 1)
        
        return sorted(topic_boundaries)
    
    except Exception as e:
        print(f"Error in topic segmentation: {e}")
        # Fallback to evenly spaced segments
        num_segments = max(3, min(8, len(sentences) // 20))
        boundaries = [0]
        step = len(sentences) // num_segments
        for i in range(1, num_segments):
            boundaries.append(i * step)
        if len(sentences) - 1 not in boundaries:
            boundaries.append(len(sentences) - 1)
        return boundaries

def extract_keywords(segment_text, num_keywords=3):
    """Extract the most important keywords from text."""
    global nlp
    
    if nlp is not None:
        try:
            # Use spaCy for better keyword extraction
            doc = nlp(segment_text)
            
            # Extract nouns and proper nouns as potential keywords
            potential_keywords = []
            for token in doc:
                if token.pos_ in ('NOUN', 'PROPN') and not token.is_stop and len(token.text) > 3:
                    potential_keywords.append(token.text.lower())
            
            # Count occurrences and get top keywords
            keyword_counts = Counter(potential_keywords)
            keywords = [word for word, _ in keyword_counts.most_common(num_keywords)]
            
            # If we don't have enough keywords, add important verbs
            if len(keywords) < num_keywords:
                verbs = [token.text.lower() for token in doc if token.pos_ == 'VERB' and not token.is_stop and len(token.text) > 3]
                verb_counts = Counter(verbs)
                for word, _ in verb_counts.most_common(num_keywords - len(keywords)):
                    keywords.append(word)
                    
            return keywords[:num_keywords]  # Ensure we don't return more than requested
        
        except Exception as e:
            print(f"Error with spaCy keyword extraction: {e}")
            # Fall through to the fallback method
    
    # Fallback: simple TF-IDF
    try:
        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "this", "that", 
                      "you", "i", "it", "he", "she", "they", "we", "to", "of", "in", "on", "at", "for"}
        
        # Tokenize and clean text
        words = re.findall(r'\b\w+\b', segment_text.lower())
        words = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Get most frequent words
        word_counts = Counter(words)
        keywords = [word for word, _ in word_counts.most_common(num_keywords)]
        
        return keywords
    except Exception as e:
        print(f"Error with fallback keyword extraction: {e}")
        return ["keyword"] * min(num_keywords, 3)  # Return placeholder keywords

def generate_timestamps(video_id, min_segment_duration=20, max_segments=12):
    """Generate high-precision timestamps with content-based segmentation."""
    # Ensure NLTK resources are available
    ensure_nltk_data()
    
    # Load NLP models if available
    load_models()
    
    try:
        # Get the transcript
        transcript_items = YouTubeTranscriptApi.get_transcript(video_id)
        
        if not transcript_items:
            return [{
                "time": 0,
                "formatted_time": "0:00",
                "title": "Video Start",
                "keywords": [],
                "segment_id": 0
            }]
        
        # Find natural breaks based on silences/pauses
        silence_boundaries = segment_transcript_by_silence(transcript_items)
        silence_times = [b['time'] for b in silence_boundaries if b['duration'] > 1.5]
        
        # Convert transcript to text with mapping to timestamps
        full_text = ""
        time_mapping = {}
        char_pos = 0
        
        for item in transcript_items:
            text = item["text"] + " "
            full_text += text
            
            # Map each character to its timestamp
            for _ in range(len(text)):
                time_mapping[char_pos] = item["start"]
                char_pos += 1
        
        # Split the text into sentences
        try:
            sentences = nltk.sent_tokenize(full_text)
            print(f"Successfully tokenized into {len(sentences)} sentences")
        except Exception as e:
            print(f"Error with NLTK sentence tokenization: {e}")
            # Fallback to simple regex-based sentence splitting
            sentences = re.findall(r'[^.!?]+[.!?]', full_text)
            print(f"Fallback tokenization found {len(sentences)} sentences")
        
        if not sentences:
            print("WARNING: No sentences were found in transcript")
            # Fallback: create timestamps at regular intervals
            video_duration = transcript_items[-1]["start"] + transcript_items[-1]["duration"]
            interval = max(60, video_duration / 8)  # 8 segments max, minimum 60 seconds each
            
            timestamps = []
            for i in range(min(8, max(3, int(video_duration / interval)))):
                time_point = i * interval
                minutes = int(time_point // 60)
                seconds = int(time_point % 60)
                formatted_time = f"{minutes}:{seconds:02d}"
                
                # Get text around this time point
                nearby_text = ""
                for item in transcript_items:
                    if abs(item["start"] - time_point) < 30:  # 30 seconds around the time point
                        nearby_text += item["text"] + " "
                
                title = f"Segment {i+1}"
                if nearby_text:
                    words = nearby_text.split()
                    if len(words) > 5:
                        title = " ".join(words[:5]) + "..."
                
                timestamps.append({
                    "time": time_point,
                    "formatted_time": formatted_time,
                    "title": title,
                    "keywords": extract_keywords(nearby_text),
                    "segment_id": i
                })
            
            return timestamps
        
        # Store the timestamp for the start of each sentence
        sentence_timestamps = []
        for sentence in sentences:
            # Find position of first character of the sentence in full_text
            start_pos = full_text.find(sentence)
            if start_pos != -1:
                timestamp = time_mapping.get(start_pos, 0)
                sentence_timestamps.append(timestamp)
            else:
                # Fallback to previous timestamp if we can't find the sentence
                timestamp = sentence_timestamps[-1] if sentence_timestamps else 0
                sentence_timestamps.append(timestamp)
        
        # Find topic boundaries using semantic analysis
        topic_boundaries = segment_by_topic_shifts(sentences, sentence_timestamps)
        
        # Combine topic and silence boundaries
        all_boundary_times = []
        
        # Add topic-based boundaries
        for idx in topic_boundaries:
            if idx < len(sentence_timestamps):
                all_boundary_times.append(sentence_timestamps[idx])
        
        # Add silence-based boundaries
        all_boundary_times.extend(silence_times)
        
        # Sort and remove duplicates
        all_boundary_times = sorted(set(all_boundary_times))
        
        # Filter out boundaries that are too close together
        filtered_boundaries = [all_boundary_times[0]]  # Always keep the first boundary
        for time in all_boundary_times[1:]:
            if time - filtered_boundaries[-1] >= min_segment_duration:
                filtered_boundaries.append(time)
        
        # Ensure we don't have too many segments
        if len(filtered_boundaries) > max_segments:
            # Keep the most important boundaries
            step = len(filtered_boundaries) // max_segments
            if step > 1:
                filtered_boundaries = [filtered_boundaries[i] for i in range(0, len(filtered_boundaries), step)]
            
            # Always include the start
            if filtered_boundaries[0] > 0:
                filtered_boundaries.insert(0, 0)
            
            # Ensure we don't exceed the max
            filtered_boundaries = filtered_boundaries[:max_segments]
            
        # Sort one more time
        filtered_boundaries.sort()
        
        # Generate timestamps for each segment
        timestamps = []
        
        for i in range(len(filtered_boundaries)):
            start_time = filtered_boundaries[i]
            
            # Get the end time for this segment
            end_time = filtered_boundaries[i+1] if i < len(filtered_boundaries)-1 else None
            
            # Format time for display
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            formatted_time = f"{minutes}:{seconds:02d}"
            
            # Find transcript in this segment
            segment_text = ""
            for item in transcript_items:
                if item["start"] >= start_time and (end_time is None or item["start"] < end_time):
                    segment_text += item["text"] + " "
            
            # Set title and keywords
            if not segment_text.strip():
                title = f"Segment at {formatted_time}"
                keywords = []
            else:
                # Find sentences in this segment
                segment_sentences = []
                for j, timestamp in enumerate(sentence_timestamps):
                    if timestamp >= start_time and (end_time is None or timestamp < end_time):
                        if j < len(sentences):  # Ensure index is valid
                            segment_sentences.append(sentences[j])
                
                # Get title from first sentence
                if segment_sentences:
                    title = segment_sentences[0]
                    if len(title) > 50:
                        title = title[:47] + "..."
                else:
                    title = f"Segment at {formatted_time}"
                
                # Extract keywords
                keywords = extract_keywords(segment_text)
            
            timestamps.append({
                "time": start_time,
                "formatted_time": formatted_time,
                "title": title,
                "keywords": keywords,
                "segment_id": i
            })
        
        return timestamps
    
    except Exception as e:
        print(f"Error generating timestamps: {e}")
        # Provide a basic fallback
        return [{
            "time": 0,
            "formatted_time": "0:00",
            "title": "Video content",
            "keywords": [],
            "segment_id": 0
        }]

def get_segment_transcript(video_id, start_time, end_time=None):
    """Get transcript text for a specific segment of the video."""
    try:
        # Get full transcript
        transcript_items = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Filter transcript items for this segment
        segment_items = []
        for item in transcript_items:
            # If this item is within our segment time range
            if item["start"] >= start_time and (end_time is None or item["start"] < end_time):
                segment_items.append(item)
        
        # Get text for this segment
        segment_text = " ".join([item["text"] for item in segment_items])
        
        return segment_text
    except Exception as e:
        print(f"Error getting segment transcript: {e}")
        return ""