import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import spacy
import time
import wikipedia

def ensure_nltk_data():
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords')

def load_models():
    try:
        nlp = spacy.load("en_core_web_sm")
        return nlp
    except:
        print("Could not load spaCy model. Using fallback methods.")
        return None

def extract_key_terms(text, nlp, max_terms=10):
    ensure_nltk_data()
    
    if nlp:
        sample_text = text[:5000]
        doc = nlp(sample_text)
        
        entities = []
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT', 'WORK_OF_ART', 'FAC', 'NORP']:
                entities.append(ent.text)
        
        from collections import Counter
        entity_counter = Counter(entities)
        common_entities = [e for e, _ in entity_counter.most_common(max_terms)]
        
        if len(common_entities) < max_terms and len(text) > 5000:
            mid_point = len(text) // 2
            mid_sample = text[mid_point:mid_point+2000]
            mid_doc = nlp(mid_sample)
            
            for ent in mid_doc.ents:
                if ent.label_ in ['PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT', 'WORK_OF_ART', 'FAC', 'NORP']:
                    entities.append(ent.text)
            
            if len(text) > 7000:
                end_sample = text[-2000:]
                end_doc = nlp(end_sample)
                for ent in end_doc.ents:
                    if ent.label_ in ['PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT', 'WORK_OF_ART', 'FAC', 'NORP']:
                        entities.append(ent.text)
        
        entity_counter = Counter(entities)
        common_entities = [e for e, _ in entity_counter.most_common(max_terms)]
        
        if len(common_entities) < max_terms:
            noun_phrases = []
            for chunk in doc.noun_chunks:
                if len(chunk.text) > 5:
                    noun_phrases.append(chunk.text)
            
            if len(common_entities) + len(noun_phrases) < max_terms and len(text) > 5000:
                for chunk in mid_doc.noun_chunks:
                    if len(chunk.text) > 5:
                        noun_phrases.append(chunk.text)
            
            noun_counter = Counter(noun_phrases)
            for phrase, _ in noun_counter.most_common(max_terms - len(common_entities)):
                if phrase.lower() not in [e.lower() for e in common_entities]:
                    common_entities.append(phrase)
        
        return common_entities[:max_terms]
    else:
        import re
        from nltk.corpus import stopwords
        stop_words = set(stopwords.words('english'))
        
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        filtered_words = [w for w in words if w not in stop_words]
        
        phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
        
        all_terms = filtered_words + phrases
        
        word_counter = Counter(all_terms)
        
        return [word for word, _ in word_counter.most_common(max_terms)]

def get_wikipedia_info(term, max_length=500):
    term = re.sub(r'[^\w\s]', '', term).strip()
    
    try:
        search_results = wikipedia.search(term, results=1)
        
        if not search_results:
            return None
        
        page_title = search_results[0]
        page = wikipedia.page(page_title, auto_suggest=False)
        
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
    except wikipedia.exceptions.DisambiguationError as e:
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

def generate_key_points_with_wikipedia(transcript, max_terms=8):
    """Generate key terms with Wikipedia information using optimized extraction."""
    ensure_nltk_data()
    nlp = load_models()
    
    print(f"Extracting up to {max_terms} key terms from transcript...")
    
    key_terms = extract_key_terms(transcript, nlp, max_terms*3)
    
    print(f"Found {len(key_terms)} potential terms: {', '.join(key_terms[:10])}...")
    
    results = []
    processed_titles = set()
    
    for i in range(0, len(key_terms), 3):
        batch = key_terms[i:i+3]
        batch_results = []
        
        for term in batch:
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
        
        results.extend(batch_results)
        
        if len(results) >= max_terms:
            print(f"Reached target of {max_terms} terms with Wikipedia info")
            break
        
        time.sleep(0.1)
    
    print(f"Found {len(results)} terms with Wikipedia info")

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