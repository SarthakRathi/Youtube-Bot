"""
Installation script for the required dependencies of the enhanced timestamp feature.
Run this script to set up all the necessary packages for high-precision timestamps.
"""

import subprocess
import sys
import os

def install_dependencies():
    print("Installing dependencies for high-precision YouTube NLP Assistant...")
    
    # Core dependencies
    core_packages = [
        "flask",
        "flask-cors",
        "youtube-transcript-api",
        "nltk",
        "scikit-learn",
        "transformers",
        "torch",
        "numpy",
        "scipy"
    ]
    
    # Enhanced dependencies
    enhanced_packages = [
        "sentence-transformers",
        "spacy"
    ]
    
    # Install core packages
    print("\n=== Installing core dependencies ===")
    for package in core_packages:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    # Install enhanced packages
    print("\n=== Installing enhanced dependencies ===")
    for package in enhanced_packages:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        except subprocess.CalledProcessError:
            print(f"⚠️ Warning: Could not install {package}. The system will use fallback methods.")
    
    # Download spaCy model
    try:
        print("\n=== Downloading spaCy language model ===")
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        print("✓ Successfully downloaded spaCy language model")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ Warning: Could not download spaCy language model. The system will use fallback methods.")
    
    # Set up NLTK data
    print("\n=== Setting up NLTK data ===")
    nltk_data_dir = os.path.join(os.getcwd(), 'nltk_data')
    os.makedirs(nltk_data_dir, exist_ok=True)
    
    try:
        import nltk
        nltk.download('punkt', download_dir=nltk_data_dir)
        print("✓ Successfully downloaded NLTK punkt tokenizer")
    except Exception as e:
        print(f"⚠️ Warning: Could not download NLTK data: {e}")
    
    print("\n=== Installation complete ===")
    print("You can now run the YouTube NLP Assistant with enhanced timestamp precision.")

if __name__ == "__main__":
    install_dependencies()