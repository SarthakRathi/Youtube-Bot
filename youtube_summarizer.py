from youtube_transcript_api import YouTubeTranscriptApi
import re
import os
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM

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

def create_summarizer(model_name="facebook/bart-large-cnn"):
    """Create a summarization pipeline with the specified model."""
    device = get_device()
    print(f"Using device: {device.upper()}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    model = model.to(device)
    
    summarizer = pipeline(
        "summarization", 
        model=model, 
        tokenizer=tokenizer, 
        device=0 if device == "cuda" else -1
    )
    
    return summarizer

def extract_key_sentences(text, num_sentences=5):
    """Extract key sentences from text as a fallback method."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    if len(sentences) <= num_sentences:
        return ' '.join(sentences)
    
    key_sentences = [sentences[0]]
    
    middle_start = len(sentences) // 4
    middle_end = 3 * len(sentences) // 4
    middle_step = (middle_end - middle_start) // (num_sentences - 2)
    
    if middle_step < 1:
        middle_step = 1
    
    for i in range(middle_start, middle_end, middle_step):
        if len(key_sentences) < num_sentences - 1 and i < len(sentences):
            key_sentences.append(sentences[i])
    
    if sentences[-1] not in key_sentences:
        key_sentences.append(sentences[-1])
    
    return ' '.join(key_sentences)

def summarize_text(text, target_min_length=100, target_max_length=300):
    """Generate a comprehensive summary of the provided text."""
    word_count = len(text.split())
    print(f"Transcript word count: {word_count}")
    
    if word_count < 200:
        print("Text too short for abstractive summarization, using extractive method")
        return extract_key_sentences(text, num_sentences=3)
    
    summarizer = create_summarizer()
    
    min_length = min(target_min_length, max(30, word_count // 10))
    max_length = min(target_max_length, max(min_length + 50, word_count // 3))
    
    print(f"Using min_length={min_length}, max_length={max_length}")
    
    max_chunk_length = 800
    chunks = []
    
    words = text.split()
    for i in range(0, len(words), max_chunk_length):
        chunk = ' '.join(words[i:i + max_chunk_length])
        if len(chunk.split()) >= 50:
            chunks.append(chunk)
    
    if not chunks:
        return extract_key_sentences(text)
    
    all_summaries = []
    for i, chunk in enumerate(chunks):
        print(f"Summarizing chunk {i+1}/{len(chunks)}...")
        
        try:
            result = summarizer(
                chunk, 
                max_length=max_length // len(chunks), 
                min_length=min_length // len(chunks), 
                do_sample=False,
                truncation=True
            )
            
            if result and len(result) > 0:
                all_summaries.append(result[0]['summary_text'])
                continue
        except Exception as e:
            print(f"Initial summarization attempt failed: {e}")
        
        try:
            print(f"Retrying chunk {i+1} with adjusted parameters")
            result = summarizer(
                chunk, 
                max_length=max_length, 
                min_length=10,
                do_sample=True,
                truncation=True
            )
            
            if result and len(result) > 0:
                all_summaries.append(result[0]['summary_text'])
                continue
        except Exception as e:
            print(f"Second summarization attempt failed: {e}")
        
        print(f"Using extractive fallback for chunk {i+1}")
        all_summaries.append(extract_key_sentences(chunk, num_sentences=2))
    
    if not all_summaries:
        return extract_key_sentences(text)
    
    combined_summary = ' '.join(all_summaries)
    
    if len(chunks) <= 1 or word_count < 500:
        return combined_summary
    
    try:
        print("Generating meta-summary for better coherence...")
        meta_result = summarizer(
            combined_summary, 
            max_length=max_length,
            min_length=min_length,
            do_sample=False,
            truncation=True
        )
        
        if meta_result and len(meta_result) > 0:
            return meta_result[0]['summary_text']
    except Exception as e:
        print(f"Meta-summarization failed: {e}")
    
    return combined_summary

def summarize_youtube_video(youtube_url, min_length=100, max_length=300):
    """Main function to summarize a YouTube video from its URL."""
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return "Invalid YouTube URL. Please provide a valid URL.", None
    
    transcript = get_transcript(video_id)
    if not transcript:
        return "Could not retrieve transcript. The video might not have captions.", None
    
    print(f"Generating summary (target length: {min_length}-{max_length} words)...")
    summary = summarize_text(transcript, target_min_length=min_length, target_max_length=max_length)
    
    return summary, transcript

if __name__ == "__main__":
    test_url = input("Enter YouTube URL to test summarization: ")
    summary, transcript = summarize_youtube_video(test_url)
    print("\nSUMMARY:\n", summary)