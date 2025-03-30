from youtube_transcript_api import YouTubeTranscriptApi
import re
import os
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM

# Suppress the warnings
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
import warnings
warnings.filterwarnings('ignore')

def extract_video_id(youtube_url):
    """Extract the video ID from a YouTube URL."""
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', youtube_url)
    if video_id_match:
        return video_id_match.group(1)
    return None

def get_transcript(video_id):
    """Fetch the transcript for a YouTube video."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = ' '.join([item['text'] for item in transcript_list])
        return transcript
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None

def get_device():
    """Get the appropriate device (GPU or CPU)."""
    return "cuda" if torch.cuda.is_available() else "cpu"

def create_summarizer(model_name="facebook/bart-large-cnn", min_length=100, max_length=500):
    """Create a summarization pipeline with the specified model."""
    device = get_device()
    print(f"Using device: {device.upper()}")
    
    # Load model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    model = model.to(device)
    
    # Create summarization pipeline
    summarizer = pipeline(
        "summarization", 
        model=model, 
        tokenizer=tokenizer, 
        device=0 if device == "cuda" else -1
    )
    
    return summarizer

def chunk_text(text, max_tokens=1000):
    """Split text into chunks that don't exceed max_tokens."""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_length += 1
        current_chunk.append(word)
        
        if current_length >= max_tokens:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_length = 0
            
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(' '.join(current_chunk))
        
    return chunks

def summarize_text(text, min_length=100, max_length=300):
    """Generate a comprehensive summary of the provided text."""
    # Create summarization pipeline
    summarizer = create_summarizer(min_length=min_length, max_length=max_length)
    
    # Split text into chunks
    chunks = chunk_text(text)
    
    # Don't process if the text is too short
    if len(chunks) == 0:
        return "Text is too short to summarize."
    
    # Process each chunk
    all_summaries = []
    for i, chunk in enumerate(chunks):
        # Skip chunks that are too short
        if len(chunk.split()) < 50:
            continue
            
        print(f"Summarizing chunk {i+1}/{len(chunks)}...")
        
        try:
            summary = summarizer(
                chunk, 
                max_length=max_length, 
                min_length=min_length, 
                do_sample=False,
                truncation=True
            )
            
            if summary and len(summary) > 0:
                all_summaries.append(summary[0]['summary_text'])
        except Exception as e:
            print(f"Error summarizing chunk {i+1}: {e}")
    
    # Combine the summaries
    combined_summary = ' '.join(all_summaries)
    
    # Generate meta-summary for better coherence if needed
    if len(all_summaries) > 1 and len(combined_summary.split()) > 200:
        print("Generating meta-summary for better coherence...")
        meta_summary = summarizer(
            combined_summary, 
            max_length=max(max_length, len(combined_summary.split()) // 2), 
            min_length=min_length,
            do_sample=False,
            truncation=True
        )
        
        if meta_summary and len(meta_summary) > 0:
            return meta_summary[0]['summary_text']
    
    return combined_summary

def summarize_youtube_video(youtube_url, min_length=100, max_length=300):
    """Main function to summarize a YouTube video from its URL."""
    # Extract video ID from URL
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return "Invalid YouTube URL. Please provide a valid URL.", None
    
    # Get transcript
    transcript = get_transcript(video_id)
    if not transcript:
        return "Could not retrieve transcript. The video might not have captions.", None
    
    # Generate summary
    print(f"Generating summary (min_length={min_length}, max_length={max_length})...")
    summary = summarize_text(transcript, min_length=min_length, max_length=max_length)
    
    return summary, transcript