# Legal-Bengal ⚖️

**Bangladesh Legal AI Assistant** - An intelligent legal assistant for Bangladesh laws, featuring bilingual support (English + বাংলা), hybrid retrieval, and legal document generation.

<p align="center">
  <img src="static/img/legal.png" alt="Legal-Bengal Logo" width="200">
</p>

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-Web%20App-green?style=for-the-badge&logo=flask)
![Groq](https://img.shields.io/badge/Groq-Llama%203.1-orange?style=for-the-badge)

## Features

### Core Capabilities
- **Legal Q&A**: Ask about Bangladesh Penal Code, Constitution, Criminal Procedure, and more
- **Bilingual Support**: Query in English or Bengali (বাংলা)
- **Hybrid Retrieval**: Direct JSON lookup + FAISS semantic search
- **Document Generator**: Create legal documents (GD, Legal Notice, Affidavit, Bail Application, etc.)
- **Chat History**: Persistent chat sessions with Redis (or file-based fallback)
- **Flexible API**: Use default or your own Groq API key

### Available Laws (1,648+ Provisions)

| Law | Sections/Articles | Language |
|-----|-------------------|----------|
| Constitution of Bangladesh | 166 Articles | English + বাংলা |
| Penal Code, 1860 | 557 Sections | English |
| Code of Criminal Procedure, 1898 | 471 Sections | English |
| Registration Act, 1908 | 109 Sections | English |
| State Acquisition & Tenancy Act, 1950 | 203 Sections | English |
| Transfer of Property Act, 1882 | 142 Sections | English |

### Document Templates
- **General Diary (GD)** - Police complaints
- **Legal Notice** - Formal legal warnings
- **Affidavit (হলফনামা)** - Sworn statements
- **Power of Attorney (মোক্তারনামা)** - Legal representation
- **Bail Application** - Court petitions
- **Agreement/Contract** - Legal agreements

## Architecture

Reused and adapted from:
- **AskLegal.ai**: Hybrid retrieval, chat persistence, document generation
- **Nyaya-GPT**: Agent architecture, FAISS vector search, multilingual embeddings

### Tech Stack
| Component | Technology |
|-----------|------------|
| Framework | Flask |
| LLM | Groq (Llama 3.1 8B Instant) |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (Bangla support) |
| Vector DB | FAISS |
| Storage | Redis (primary) / File-based (fallback) |
| Documents | python-docx |

## Quick Start

### Prerequisites
- Python 3.10+
- Redis (optional, for chat persistence)
- Groq API key

### Installation

```bash
# Clone and navigate to project
cd Legal-Bengal

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (optional)
cp .env.example .env
# Edit .env with your API keys if desired
```

### Run the Application

```bash
# Option 1: Use the provided default API key
python app.py

# Option 2: Use your own Groq API key
export GROQ_API_KEY="your-api-key-here"
python app.py
```

Access the application at: **http://localhost:5000**

### Redis Setup (Optional, for chat persistence)

```bash
# Install Redis
sudo apt-get install redis-server  # Ubuntu/Debian
brew install redis                 # macOS

# Start Redis
redis-server
```

Without Redis, chats will be saved to `data/chats/` directory.

## Usage Guide

### 1. Legal Q&A

**Example English Queries:**
- "What is Section 302 of the Penal Code?"
- "Explain Article 27 of the Constitution"
- "How to file a criminal case in Bangladesh?"

**Example Bangla Queries:**
- "ধারা ৩০২ কী?"
- "জিডি করার পদ্ধতি কী?"
- "মৌলিক অধিকারগুলো কী কী?"

### 2. Document Generation

Navigate to the **Documents** tab and describe your needs:

```
"Create a GD for stolen mobile phone. My name is Karim,
address: 45 Gulshan Avenue, Dhaka. Incident happened yesterday
at 3 PM near Gulshan-1 circle."
```

The system will generate a properly formatted Bengali document ready for submission.

### 3. Setting Your Own API Key

Click the **API Key** button in the navigation bar to use your personal Groq API key:

1. Get a free key from [Groq Console](https://console.groq.com)
2. Enter it in the settings modal
3. Your key is stored only in your session

## Project Structure

```
Legal-Bengal/
├── app.py                 # Flask application entry point
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── .gitignore            # Git ignore rules
│
├── views/                 # Business logic modules
│   ├── chatbot.py        # Hybrid retrieval + Groq generation
│   └── docGen.py         # Document generation with Bangla templates
│
├── templates/             # HTML templates
│   ├── index.html        # Main chat interface
│   ├── generate.html     # Document generator UI
│   └── laws.html         # Laws reference page
│
├── static/                # Static assets
│   ├── img/              # Images
│   ├── css/              # Stylesheets
│   ├── js/               # JavaScript
│   └── generated_docs/   # Generated document outputs
│
├── data/                  # Bangladesh law JSON files
│   ├── bd-constitution.json
│   ├── penal-code.json
│   ├── criminal-procedure.json
│   └── ...
│
└── bd_embed_db/          # FAISS vector database (auto-generated)
```

## How It Works

### Hybrid Retrieval System

```
User Query
    ↓
┌─────────────────────────────────────────┐
│ 1. Extract Section/Article Number?      │
│    → Direct JSON lookup (if found)      │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 2. FAISS Semantic Search                │
│    → Multilingual embeddings            │
│    → Score threshold filtering          │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 3. Context + Groq LLM                   │
│    → Legal system prompt                │
│    → Citation of sources                │
│    → Response generation                │
└─────────────────────────────────────────┘
    ↓
Bilingual Response with Source Attribution
```

### Source Attribution

Every response is tagged with its source:
- **JSON**: Direct lookup of specific section/article
- **RAG**: Retrieved from FAISS vector search
- **HYBRID**: Both direct lookup and semantic search
- **GEN**: Groq's general knowledge (no specific source)

## Disclaimer

**This is an educational tool, not a substitute for professional legal advice.**

- Always consult a qualified Bangladeshi lawyer for legal matters
- Verify all legal information with official sources (bdlaws.minlaw.gov.bd)
- Generated documents are templates - have them reviewed by legal professionals before use
- The developers are not responsible for any legal outcomes from using this tool

## Contributing

Contributions welcome! Areas for improvement:
- More Bangla law content and translations
- Additional document templates
- Case law integration
- Voice input/output for accessibility
- Mobile app version

## Data Source

Law data sourced from the official **Bangladesh Law (BDLAW) website**:
https://bdlaws.minlaw.gov.bd/

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Acknowledgments

- Architecture inspired by **AskLegal.ai** (Indian Legal Assistant)
- ReAct pattern and RAG from **Nyaya-GPT**
- Bangladesh law dataset from official government sources
- Multilingual embeddings from HuggingFace

## Contact & Support

For issues or questions:
1. Check the [Issues](https://github.com/alvi-uiu/Legal-Bengal/issues) page
2. Create a new issue with detailed description
3. For legal questions, consult a qualified lawyer

---

**Made with ❤️ for Bangladesh 🇧🇩**

*Empowering citizens with accessible legal knowledge*
