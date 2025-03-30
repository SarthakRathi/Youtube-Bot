import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import spacy
import time
import wikipedia

# Ensure NLTK data is available
def ensure_nltk_data():
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords')

# Load NLP models
def load_models():
    try:
        # Load spaCy for entity recognition
        nlp = spacy.load("en_core_web_sm")
        return nlp
    except:
        print("Could not load spaCy model. Using fallback methods.")
        return None

# Faster extraction of key terms with less processing
def extract_key_terms(text, nlp, max_terms=10):
    ensure_nltk_data()
    
    if nlp:
        # Process only the first 5000 characters to speed up extraction
        # This is usually enough to get the main topics
        sample_text = text[:5000]
        doc = nlp(sample_text)
        
        # Extract named entities
        entities = []
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT', 'WORK_OF_ART', 'FAC', 'NORP']:
                entities.append(ent.text)
        
        # Count entity occurrences and get most common
        from collections import Counter
        entity_counter = Counter(entities)
        common_entities = [e for e, _ in entity_counter.most_common(max_terms)]
        
        # If we still need more terms, look for additional entities in chunks
        if len(common_entities) < max_terms and len(text) > 5000:
            # Process middle chunk
            mid_point = len(text) // 2
            mid_sample = text[mid_point:mid_point+2000]
            mid_doc = nlp(mid_sample)
            
            for ent in mid_doc.ents:
                if ent.label_ in ['PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT', 'WORK_OF_ART', 'FAC', 'NORP']:
                    entities.append(ent.text)
            
            # Process end chunk for more coverage
            if len(text) > 7000:
                end_sample = text[-2000:]
                end_doc = nlp(end_sample)
                for ent in end_doc.ents:
                    if ent.label_ in ['PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT', 'WORK_OF_ART', 'FAC', 'NORP']:
                        entities.append(ent.text)
        
        # Update counter with any new entities
        entity_counter = Counter(entities)
        common_entities = [e for e, _ in entity_counter.most_common(max_terms)]
        
        # If we still don't have enough entities, extract noun phrases
        if len(common_entities) < max_terms:
            noun_phrases = []
            # From the first chunk
            for chunk in doc.noun_chunks:
                if len(chunk.text) > 5:  # Only substantial phrases
                    noun_phrases.append(chunk.text)
            
            # From middle chunk if needed
            if len(common_entities) + len(noun_phrases) < max_terms and len(text) > 5000:
                for chunk in mid_doc.noun_chunks:
                    if len(chunk.text) > 5:
                        noun_phrases.append(chunk.text)
            
            # Count and add top noun phrases
            noun_counter = Counter(noun_phrases)
            for phrase, _ in noun_counter.most_common(max_terms - len(common_entities)):
                if phrase.lower() not in [e.lower() for e in common_entities]:
                    common_entities.append(phrase)
        
        return common_entities[:max_terms]
    else:
        # Fallback to a simpler word frequency method
        import re
        from nltk.corpus import stopwords
        stop_words = set(stopwords.words('english'))
        
        # Extract words, excluding stop words
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        filtered_words = [w for w in words if w not in stop_words]
        
        # Also try to find multi-word phrases using regex
        phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
        
        # Combine words and phrases
        all_terms = filtered_words + phrases
        
        # Count frequencies
        word_counter = Counter(all_terms)
        
        # Return most common
        return [word for word, _ in word_counter.most_common(max_terms)]

# Get Wikipedia information for a given term
def get_wikipedia_info(term, max_length=500):  # Increased max_length for more complete content
    # Clean term name
    term = re.sub(r'[^\w\s]', '', term).strip()
    
    try:
        # Search for Wikipedia page
        search_results = wikipedia.search(term, results=1)
        
        if not search_results:
            return None
        
        # Get the page
        page_title = search_results[0]
        page = wikipedia.page(page_title, auto_suggest=False)
        
        # Extract the summary
        summary = page.summary
        
        # Get the first 4-5 sentences instead of just 2
        sentences = nltk.sent_tokenize(summary)
        short_summary = " ".join(sentences[:min(5, len(sentences))])
        
        # If still too long, truncate
        if len(short_summary) > max_length:
            short_summary = short_summary[:max_length] + "..."
        
        return {
            "title": page.title,
            "summary": short_summary,
            "url": page.url
        }
    except wikipedia.exceptions.DisambiguationError as e:
        # Handle disambiguation pages by taking the first option
        if e.options:
            try:
                page = wikipedia.page(e.options[0], auto_suggest=False)
                summary = page.summary
                sentences = nltk.sent_tokenize(summary)
                short_summary = " ".join(sentences[:min(5, len(sentences))])
                
                if len(short_summary) > max_length:
                    short_summary = short_summary[:max_length] + "..."
                
                return {
                    "title": page.title,
                    "summary": short_summary,
                    "url": page.url
                }
            except:
                return None
        return None
    except Exception as e:
        print(f"Wikipedia error for term '{term}': {str(e)}")
        return None

# Generate key terms with Wikipedia information
def generate_key_points_with_wikipedia(transcript, max_terms=8):
    """Generate key terms with Wikipedia information using optimized extraction."""
    ensure_nltk_data()
    nlp = load_models()
    
    print(f"Extracting up to {max_terms} key terms from transcript...")
    
    # Extract more key terms than needed to increase chances of finding good Wikipedia matches
    key_terms = extract_key_terms(transcript, nlp, max_terms*3)
    
    print(f"Found {len(key_terms)} potential terms: {', '.join(key_terms[:10])}...")
    
    # Get Wikipedia info for each term in parallel
    results = []
    processed_titles = set()  # To avoid duplicate Wikipedia articles
    
    # Process terms in batches to improve efficiency
    for i in range(0, len(key_terms), 3):
        batch = key_terms[i:i+3]
        batch_results = []
        
        for term in batch:
            # Skip if we already processed this exact term
            if term.lower() in [r.get("key_term", "").lower() for r in results]:
                continue
                
            if len(results) >= max_terms:
                break
                
            print(f"Looking up Wikipedia info for: {term}")
            wiki_info = get_wikipedia_info(term)
            
            if wiki_info and wiki_info["title"] not in processed_titles:
                processed_titles.add(wiki_info["title"])
                batch_results.append({
                    "key_term": term,
                    "wikipedia_info": wiki_info
                })
        
        # Add batch results to main results
        results.extend(batch_results)
        
        # Check if we have enough results
        if len(results) >= max_terms:
            print(f"Reached target of {max_terms} terms with Wikipedia info")
            break
        
        # Add a small delay between batches to avoid rate limiting
        time.sleep(0.1)
    
    print(f"Found {len(results)} terms with Wikipedia info")
    
    # If we still don't have enough terms with Wikipedia info,
    # include some without Wikipedia info
    if len(results) < max_terms:
        print(f"Adding additional terms without Wikipedia info to reach {max_terms}")
        for term in key_terms:
            if not any(r.get("key_term", "").lower() == term.lower() for r in results):
                results.append({
                    "key_term": term,
                    "wikipedia_info": None
                })
                if len(results) >= max_terms:
                    break
    
    print(f"Returning {len(results[:max_terms])} key terms total")
    return results[:max_terms]