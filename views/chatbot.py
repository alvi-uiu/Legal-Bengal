"""
Legal-Bengal Chatbot Module
Hybrid retrieval system combining:
1. Direct JSON lookup for section/article numbers
2. FAISS semantic search for general queries
3. Groq LLM for response generation
Reused from AskLegal.ai architecture, adapted for Bangladesh laws
"""

import json
import os
import re
from typing import Tuple, List, Dict, Optional
from dotenv import load_dotenv

# Groq SDK
from groq import Groq

# LangChain + FAISS
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document

# Redis for chat persistence
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Redis not available, using file-based storage")

load_dotenv()

# ==================== Configuration ====================

# Groq configuration
GROQ_MODEL_NAME = "llama-3.1-8b-instant"
_current_api_key = os.getenv("GROQ_API_KEY", "")
_groq_client = None

def set_groq_key(api_key: str):
    """Set or update Groq API key dynamically"""
    global _current_api_key, _groq_client
    _current_api_key = api_key
    _groq_client = Groq(api_key=api_key)
    print(f"✅ Groq API key configured: {api_key[:10]}...")

# Initialize Groq client
if _current_api_key:
    _groq_client = Groq(api_key=_current_api_key)
    print(f"✅ Groq API key configured: {_current_api_key[:10]}...")
else:
    print("⚠️ No Groq API key found in environment")

# System prompt for Bangladesh legal context
SYSTEM_PROMPT = """You are Legal-Bengal, an AI Legal Assistant specialized in Bangladesh law.

CAPABILITIES:
- Answer questions about the Constitution of Bangladesh, Penal Code 1860, Criminal Procedure Code 1898, and other major laws
- Provide section numbers and legal references
- Explain legal procedures and rights
- Suggest remedies and legal options based on specific law provisions

RULES (MUST FOLLOW):
1. ALWAYS cite specific sections/articles from the provided context
2. Start with the relevant section numbers, then explain the provision
3. For Bribery/Corruption queries: Cite Penal Code Sections 161-171
4. For Murder queries: Cite Penal Code Sections 299-304
5. For Theft queries: Cite Penal Code Sections 378-402
6. For queries about "what can I do" or remedies: Explain the legal procedure based on cited sections
7. For Bengali queries, respond in Bengali (বাংলা) with section numbers in English
8. Add disclaimer at end: "This is educational information, not legal advice. Consult a qualified lawyer."

RESPONSE FORMAT:
- First: List the relevant section numbers and law names
- Second: Explain what the section says in simple terms
- Third: Apply it to the user's specific situation
- Finally: Mention the legal remedy or next steps

LANGUAGE SUPPORT:
- English: Full legal terminology
- Bengali (বাংলা): Use for native language queries, keep section numbers in English

AVOID:
- Giving specific legal strategy advice
- Predicting court outcomes
- Drafting actual court filings without lawyer review
- Generic responses without citing specific sections
"""

# Colloquial to legal keyword mappings (handles informal Bengali/English)
KEYWORD_MAP = {
    # Bribery/Corruption - EXTENSIVE
    "bribe": ["gratification", "undue advantage", "public servant", "corruption", "taking gratification", "giving gratification", "criminal misconduct"],
    "bribery": ["gratification", "undue advantage", "public servant", "corruption", "taking gratification", "giving gratification"],
    "corruption": ["public servant", "gratification", "undue advantage", "criminal misconduct", "bribe"],
    "corrupt": ["public servant", "gratification", "undue advantage", "criminal misconduct"],
    "ghush": ["gratification", "bribe", "undue advantage", "public servant", "corruption", "section 161", "section 165"],
    "ghushi": ["gratification", "bribe", "undue advantage", "public servant", "corruption", "section 161", "section 165"],
    "ঘুষ": ["gratification", "bribe", "undue advantage", "public servant", "corruption", "section 161", "section 165"],
    "ঘুশ": ["gratification", "bribe", "undue advantage", "public servant", "corruption", "section 161", "section 165"],
    "দুর্নীতি": ["corruption", "bribe", "public servant", "gratification", "section 161", "section 165", "section 166"],
    "দুর্নীতিবাজ": ["corruption", "public servant", "criminal misconduct"],
    "hush money": ["gratification", "bribe", "undue advantage"],
    "pay off": ["gratification", "bribe", "undue advantage"],
    "kickback": ["gratification", "bribe", "undue advantage", "public servant"],
    "under table": ["gratification", "bribe", "undue advantage", "public servant"],
    "তলি দেওয়া": ["gratification", "bribe", "undue advantage"],
    "লুকিয়ে টাকা": ["gratification", "bribe", "undue advantage"],
    "speed money": ["gratification", "bribe", "undue advantage", "public servant"],
    " facilitation": ["gratification", "bribe", "undue advantage", "public servant"],
    # Shopkeeper/Business disputes
    "dokandar": ["seller", "vendor", "contract", "cheating", "fraud"],
    "দোকানদার": ["seller", "vendor", "contract", "cheating", "fraud"],
    "beshii tk": ["overcharge", "cheating", "fraud", "dishonest"],
    "বেশি টাকা": ["overcharge", "cheating", "fraud", "dishonest"],
    "tk": ["money", "property", "valuable security"],
    "টাকা": ["money", "property", "valuable security"],
    # General crime
    "mar": ["hurt", "grievous hurt", "assault", "battery"],
    "mair": ["hurt", "assault", "battery"],
    "মার": ["hurt", "assault", "battery"],
    "churi": ["theft", "robbery", "dacoity", "extortion"],
    "চুরি": ["theft", "robbery", "dacoity", "extortion"],
    "mara": ["murder", "culpable homicide", "death"],
    "মারা": ["murder", "culpable homicide", "death"],
    # Legal procedures
    "ki korbo": ["procedure", "remedy", "complaint", "FIR", "police"],
    "কি করব": ["procedure", "remedy", "complaint", "FIR", "police"],
    "ki korte pari": ["procedure", "remedy", "complaint", "FIR", "police"],
    "কি করতে পারি": ["procedure", "remedy", "complaint", "FIR", "police"],
    # Land disputes
    "jomi": ["land", "property", "tenancy", "ejectment"],
    "ভূমি": ["land", "property", "tenancy", "ejectment"],
    "jama": ["land", "property", "possession"],
    "জমা": ["land", "property", "possession"],
    # Marriage/Family
    "bibah": ["marriage", "divorce", "dower", "maintenance"],
    "বিবাহ": ["marriage", "divorce", "dower", "maintenance"],
    "talak": ["divorce", "talaq", "marriage"],
    "তালাক": ["divorce", "talaq", "marriage"],
    # Help/Advice patterns
    "what can i do": ["remedy", "procedure", "legal", "right", "complaint", "section", "article"],
    "what should i do": ["remedy", "procedure", "legal", "right", "complaint"],
    "help": ["remedy", "procedure", "legal", "right"],
    "advice": ["remedy", "procedure", "legal", "right"],
    "সাহায্য": ["remedy", "procedure", "legal", "right"],
    "পরামর্শ": ["remedy", "procedure", "legal", "right"],
}

def expand_query_with_keywords(query: str) -> str:
    """Expand colloquial query with legal keywords for better retrieval"""
    query_lower = query.lower()
    expanded_terms = []
    
    for colloquial, legal_terms in KEYWORD_MAP.items():
        if colloquial in query_lower:
            expanded_terms.extend(legal_terms)
    
    if expanded_terms:
        # Add legal terms to query for better semantic matching
        expanded_query = query + " " + " ".join(expanded_terms)
        print(f"🔤 Expanded query: {query[:50]}... → Added: {expanded_terms[:3]}")
        return expanded_query
    
    return query

# Embedding model - multilingual for Bangla support
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Lazy-loaded globals
_embedding_model = None
_vectorstore = None
_redis_client = None

# Data paths
DATA_DIR = "../bd-law-dataset-main/json" if os.path.exists("../bd-law-dataset-main/json") else "data"
VECTOR_DB_PATH = "bd_embed_db"

# Law files mapping
LAW_FILES = {
    "constitution": "bd-constitution.json",
    "penal_code": "penal-code.json",
    "criminal_procedure": "criminal-procedure.json",
    "registration": "registration-act.json",
    "state_acquisition": "state-aquisition.json",
    "property_transfer": "the-transfer-of-property-act.json"
}

# ==================== Redis / Storage Setup ====================

def get_redis_client():
    """Get or create Redis client"""
    global _redis_client
    if _redis_client is None and REDIS_AVAILABLE:
        try:
            redis_url = os.getenv("UPSTASH_REDIS_URL", "redis://localhost:6379")
            _redis_client = redis.from_url(redis_url, decode_responses=True)
            _redis_client.ping()
            print("✅ Redis connected")
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}, using file storage")
            _redis_client = None
    return _redis_client


def load_chat(chat_name: str) -> dict:
    """Load chat history"""
    r = get_redis_client()
    if r:
        data = r.get(f"chat:{chat_name}")
        if data:
            return json.loads(data)
    else:
        # File-based fallback
        try:
            with open(f"data/chats/{chat_name}.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"generated": [], "past": [], "source": []}


def save_chat(chat_name: str, chat_data: dict) -> None:
    """Save chat history"""
    r = get_redis_client()
    if r:
        r.set(f"chat:{chat_name}", json.dumps(chat_data))
    else:
        # File-based fallback
        os.makedirs("data/chats", exist_ok=True)
        with open(f"data/chats/{chat_name}.json", "w", encoding="utf-8") as f:
            json.dump(chat_data, f, ensure_ascii=False)


def create_new_chat() -> str:
    """Create new chat session"""
    import uuid
    chat_name = f"chat_{uuid.uuid4().hex[:8]}"
    chat_data = {"generated": [], "past": [], "source": []}
    save_chat(chat_name, chat_data)
    return chat_name


def get_chat_list() -> list:
    """Get all chat names"""
    r = get_redis_client()
    if r:
        keys = r.keys("chat:*")
        return [k.replace("chat:", "") for k in keys]
    else:
        # File-based fallback
        try:
            files = os.listdir("data/chats")
            return [f.replace(".json", "") for f in files if f.endswith(".json")]
        except:
            return []


# ==================== Embedding & Vector Store ====================

def get_embedding_model():
    """Lazy-load embedding model"""
    global _embedding_model
    if _embedding_model is None:
        print(f"⚙️ Loading embedding model: {EMBEDDING_MODEL}")
        _embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        print("✅ Embedding model loaded")
    return _embedding_model


def load_json_laws() -> Dict[str, List[Dict]]:
    """Load all law JSON files"""
    laws_data = {}
    for law_key, filename in LAW_FILES.items():
        filepath = os.path.join(DATA_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                laws_data[law_key] = json.load(f)
        else:
            print(f"⚠️ Law file not found: {filepath}")
    return laws_data


def create_documents_from_laws(laws_data: Dict) -> List[Document]:
    """Convert law data to LangChain Documents"""
    documents = []
    
    for law_key, law_entries in laws_data.items():
        for entry in law_entries:
            # Create rich text content
            law_name = entry.get("law_name_en", "")
            
            # Handle both Constitution (article) and Penal Code (section) structures
            if "article_name_en" in entry:
                # Constitution format
                section_no = entry.get("section_no_en", "")
                section_name = entry.get("article_name_en", "")
                content = entry.get("content", "")
                bn_content = entry.get("article_bn", "")
                
                text = f"{law_name} - Article {section_no}: {section_name}\n\n{content}"
                if bn_content:
                    text += f"\n\n[বাংলা]\n{bn_content}"
                    
                metadata = {
                    "law": law_name,
                    "type": "article",
                    "number": section_no,
                    "title": section_name,
                    "language": "bilingual" if bn_content else "english"
                }
                
            else:
                # Penal Code / other laws format
                section_no = entry.get("section_no_en", "")
                section_name = entry.get("section_name_en", "")
                chapter = entry.get("chapter_name_en", "")
                content = entry.get("content", "")
                
                text = f"{law_name}"
                if chapter:
                    text += f" - {chapter}"
                text += f"\nSection {section_no}: {section_name}\n\n{content}"
                
                metadata = {
                    "law": law_name,
                    "type": "section",
                    "number": section_no,
                    "title": section_name,
                    "chapter": chapter
                }
            
            documents.append(Document(page_content=text, metadata=metadata))
    
    return documents


def build_faiss_index():
    """Build FAISS index from Bangladesh laws"""
    print("⚠️ Building FAISS index from Bangladesh laws...")
    
    laws_data = load_json_laws()
    if not laws_data:
        raise ValueError("No law data found!")
    
    documents = create_documents_from_laws(laws_data)
    print(f"📚 Created {len(documents)} documents from laws")
    
    # Create and save index
    vectorstore = FAISS.from_documents(documents, get_embedding_model())
    vectorstore.save_local(VECTOR_DB_PATH)
    print(f"✅ FAISS index saved to {VECTOR_DB_PATH}")
    return vectorstore


def get_vectorstore():
    """Lazy-load FAISS vector store"""
    global _vectorstore
    if _vectorstore is None:
        try:
            _vectorstore = FAISS.load_local(
                VECTOR_DB_PATH,
                get_embedding_model(),
                allow_dangerous_deserialization=True
            )
            # Test search
            _ = _vectorstore.similarity_search("test", k=1)
            print("✅ FAISS index loaded successfully")
        except Exception as e:
            print(f"❌ Error loading FAISS index: {e}")
            _vectorstore = build_faiss_index()
    return _vectorstore


# ==================== Hybrid Retrieval ====================

def extract_section_reference(query: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract section/article number and law reference from query
    Returns: (law_type, section_number) or (None, None)
    """
    query_lower = query.lower()
    
    # Patterns for section/article references
    section_pattern = r'(?:section|sec|s)\s*(\d+[A-Z]?(?:\.\d+)?)'
    article_pattern = r'(?:article|art)\s*(\d+[A-Z]?)'
    
    # Detect law type
    law_type = None
    if any(word in query_lower for word in ["constitution", "আর্টিকেল", "অনুচ্ছেদ"]):
        law_type = "constitution"
    elif any(word in query_lower for word in ["penal code", "ipc", "দণ্ডবিধি", "ধারা"]):
        law_type = "penal_code"
    elif any(word in query_lower for word in ["criminal procedure", "crpc", "ফৌজদারি"]):
        law_type = "criminal_procedure"
    elif any(word in query_lower for word in ["property", "transfer", "সম্পত্তি"]):
        law_type = "property_transfer"
    elif any(word in query_lower for word in ["registration", "রেজিস্ট্রেশন"]):
        law_type = "registration"
    elif any(word in query_lower for word in ["land", "tenancy", "ভূমি", "জমি"]):
        law_type = "state_acquisition"
    
    # Find section/article number
    section_match = re.search(section_pattern, query_lower)
    article_match = re.search(article_pattern, query_lower)
    
    if article_match:
        return (law_type or "constitution", article_match.group(1))
    elif section_match:
        return (law_type or "penal_code", section_match.group(1))
    
    return (None, None)


def direct_json_lookup(law_type: str, number: str) -> Optional[str]:
    """Direct lookup in JSON files for specific sections"""
    if law_type not in LAW_FILES:
        return None
    
    filepath = os.path.join(DATA_DIR, LAW_FILES[law_type])
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            law_data = json.load(f)
        
        # Search for matching entry
        for entry in law_data:
            entry_number = entry.get("section_no_en", "")
            if entry_number == number or entry_number == str(number):
                law_name = entry.get("law_name_en", "")
                
                if "article_name_en" in entry:
                    # Constitution
                    title = entry.get("article_name_en", "")
                    content = entry.get("content", "")
                    bn_content = entry.get("article_bn", "")
                    
                    result = f"{law_name} - Article {number}: {title}\n\n{content}"
                    if bn_content:
                        result += f"\n\n[বাংলা]\n{bn_content}"
                    return result
                else:
                    # Other laws
                    title = entry.get("section_name_en", "")
                    chapter = entry.get("chapter_name_en", "")
                    content = entry.get("content", "")
                    
                    result = f"{law_name}"
                    if chapter:
                        result += f" - {chapter}"
                    result += f"\nSection {number}: {title}\n\n{content}"
                    return result
        
        return None
    except Exception as e:
        print(f"❌ JSON lookup error: {e}")
        return None


# Common legal topics to section mappings (for topic-based retrieval)
TOPIC_SECTIONS = {
    "bribery": {
        "penal_code": ["161", "162", "163", "164", "165", "165A", "166", "167", "168", "169", "171"],
        "description": "Bribery and corruption by public servants"
    },
    "corruption": {
        "penal_code": ["161", "162", "163", "164", "165", "165A", "166", "167", "168", "169"],
        "description": "Criminal misconduct by public servants"
    },
    "theft": {
        "penal_code": ["378", "379", "380", "381", "382", "383", "384", "385", "386", "387", "388", "389", "390", "391", "392", "393", "394", "395", "396", "397", "398", "399", "400", "401", "402"],
        "description": "Theft, robbery, dacoity, and extortion"
    },
    "murder": {
        "penal_code": ["299", "300", "301", "302", "303", "304", "304A", "304B"],
        "description": "Culpable homicide and murder"
    },
    "hurt": {
        "penal_code": ["319", "320", "321", "322", "323", "324", "325", "326", "327", "328", "329", "330", "331", "332", "333", "334", "335", "336", "337", "338"],
        "description": "Hurt, grievous hurt, and assault"
    },
    "cheating": {
        "penal_code": ["415", "416", "417", "418", "419", "420"],
        "description": "Cheating and dishonest misappropriation"
    },
    "fraud": {
        "penal_code": ["415", "416", "417", "418", "419", "420", "463", "464", "465", "466", "467", "468", "469"],
        "description": "Cheating, forgery, and fraud"
    },
    "defamation": {
        "penal_code": ["499", "500", "501", "502"],
        "description": "Defamation and libel"
    },
    "criminal procedure": {
        "criminal_procedure": ["154", "155", "156", "157", "158", "159", "160", "161", "162", "163", "164", "167", "169", "170", "173"],
        "description": "FIR, investigation, and arrest procedures"
    },
    "fir": {
        "criminal_procedure": ["154"],
        "description": "First Information Report (FIR)"
    },
    "arrest": {
        "criminal_procedure": ["46", "47", "48", "49", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60"],
        "description": "Arrest and bail procedures"
    },
    "bail": {
        "criminal_procedure": ["496", "497", "498", "499"],
        "description": "Bail provisions"
    },
    "fundamental rights": {
        "constitution": ["27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44"],
        "description": "Fundamental rights of citizens"
    }
}


def topic_based_lookup(query: str) -> Optional[str]:
    """Lookup sections based on common legal topics"""
    query_lower = query.lower()
    
    # Map common query terms to topics
    topic_keywords = {
        "bribery": ["bribe", "ghush", "ঘুষ", "corruption", "corrupt", "gratification", "hush money", "kickback", "দুর্নীতি"],
        "theft": ["theft", "steal", "stolen", "churi", "চুরি", "robbery", "dacoity", "extortion"],
        "murder": ["murder", "kill", "killed", "killing", "mara", "মারা", "homicide", "manslaughter"],
        "hurt": ["hurt", "mar", "মার", "mair", "assault", "beat", "battery", "injury", "injured"],
        "cheating": ["cheat", "cheated", "fraud", "scam", "dishonest", "misrepresentation"],
        "defamation": ["defamation", "defame", "libel", "slander", "false accusation", "character assassination"],
        "criminal procedure": ["procedure", "complaint", "police", "investigation", "court process"],
        "fir": ["fir", "complaint", "report to police", "gd", "general diary"],
        "arrest": ["arrest", "arrested", "detain", "detained", " custody"],
        "bail": ["bail", "release", "bond"],
        "fundamental rights": ["fundamental right", "basic right", "constitutional right", "citizen right"]
    }
    
    # Find matching topic
    matched_topic = None
    for topic, keywords in topic_keywords.items():
        if any(kw in query_lower for kw in keywords):
            matched_topic = topic
            break
    
    if not matched_topic or matched_topic not in TOPIC_SECTIONS:
        return None
    
    topic_info = TOPIC_SECTIONS[matched_topic]
    results = []
    
    # Look up sections for this topic
    for law_type, sections in topic_info.items():
        if law_type == "description":
            continue
            
        for section in sections[:2]:  # Get ONLY first 2 most relevant sections (reduced from 3)
            try:
                result = direct_json_lookup(law_type, section)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"⚠️ Error looking up section {section}: {e}")
                continue
    
    if results:
        return f"[TOPIC: {matched_topic.upper()} - {topic_info.get('description', '')}]\n\n" + "\n\n---\n\n".join(results)
    
    return None


def keyword_search_in_laws(query: str, keywords: List[str], max_results: int = 3) -> List[str]:
    """Search for keywords in law documents as fallback"""
    results = []
    query_lower = query.lower()
    
    # First try topic-based lookup
    topic_result = topic_based_lookup(query)
    if topic_result:
        results.append(topic_result)
        return results
    
    # Fallback to keyword search in all law files
    for law_key, filename in LAW_FILES.items():
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            continue
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                law_data = json.load(f)
            
            # Limit scan to first 100 entries for speed
            for i, entry in enumerate(law_data[:100]):
                content = entry.get("content", "").lower()
                section_name = entry.get("section_name_en", "").lower()
                
                # Check if any keyword matches
                match_score = 0
                for keyword in keywords:
                    if keyword.lower() in content or keyword.lower() in section_name:
                        match_score += 1
                
                if match_score > 0:
                    law_name = entry.get("law_name_en", law_key)
                    section_no = entry.get("section_no_en", "")
                    title = entry.get("section_name_en", "")
                    
                    result = f"[{law_name} - Section {section_no}: {title}]\n{entry.get('content', '')[:500]}..."
                    results.append((match_score, result))
                    
                    # Early exit if we have enough results
                    if len(results) >= max_results * 2:
                        break
                        
                # Early exit if we have enough results
                if len(results) >= max_results * 2:
                    break
                    
        except Exception as e:
            print(f"❌ Error searching {law_key}: {e}")
            continue
        
        # Early exit if we have enough results
        if len(results) >= max_results * 2:
            break
    
    # Sort by match score and return top results
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:max_results]]


def hybrid_retrieve(query: str, k: int = 5, score_threshold: float = 2.0) -> Tuple[str, str]:
    """
    Hybrid retrieval combining:
    1. Topic-based lookup for common legal issues (bribery, theft, murder, etc.)
    2. Direct JSON lookup for specific section/article references
    3. FAISS semantic search for general queries
    
    Returns: (context_text, source_type)
    source_type can be: "TOPIC", "JSON", "RAG", "HYBRID", "GEN"
    """
    context_parts = []
    source = "GEN"
    
    # Expand query with legal keywords for colloquial terms
    expanded_query = expand_query_with_keywords(query)
    
    # Step 1: Topic-based lookup for common legal issues (NEW)
    topic_result = topic_based_lookup(query)
    if topic_result:
        context_parts.append(topic_result)
        source = "TOPIC"
        print(f"📋 Topic-based lookup matched for: {query[:50]}...")
    
    # Step 2: Check for direct section/article reference
    law_type, number = extract_section_reference(query)
    if law_type and number:
        direct_result = direct_json_lookup(law_type, number)
        if direct_result:
            if source == "TOPIC":
                # Add to existing topic results
                context_parts.append(direct_result)
                source = "HYBRID"
            else:
                context_parts = [direct_result]
                source = "JSON"
            print(f"📖 Direct JSON lookup: {law_type} {number}")
    
    # Step 3: FAISS semantic search (use expanded query)
    try:
        vectorstore = get_vectorstore()
        results = vectorstore.similarity_search_with_score(expanded_query, k=k)
        
        if results:
            top_doc, top_score = results[0]
            print(f"🔍 FAISS top score: {top_score:.4f}")
            
            # Use RAG if score is good (L2 distance < threshold) OR if query contains legal terms
            legal_terms = ["section", "article", "law", "act", "court", "right", 
                           "penal", "code", "constitution", "crime", "punishment",
                           "আইন", "ধারা", "অধিকার", "অপরাধ", "শাস্তি"]
            is_legal_query = any(term in query.lower() for term in legal_terms)
            
            print(f"   Is legal query: {is_legal_query}, Score: {top_score:.4f}, Threshold: {score_threshold}")
            print(f"   Query: {query[:100]}...")
            
            # For colloquial/conversational queries, be more lenient
            colloquial_terms = ["what can i do", "how to", "what should", "help", "advice", "কি করব", "কি করতে পারি", "সাহায্য"]
            is_colloquial = any(term in query.lower() for term in colloquial_terms)
            
            should_use_rag = (
                top_score < score_threshold or  # Good FAISS match
                is_legal_query or  # Always use RAG for legal queries
                is_colloquial  # Use RAG for help-seeking queries (they need legal context)
            )
            
            if should_use_rag:
                for doc, score in results[:3]:  # Top 3 results
                    meta = doc.metadata
                    doc_text = f"[{meta.get('law', 'Unknown Law')}"
                    if meta.get('type'):
                        doc_text += f" - {meta['type'].title()} {meta.get('number', '')}"
                    if meta.get('title'):
                        doc_text += f": {meta['title']}"
                    doc_text += f"]\n{doc.page_content[:800]}..."
                    context_parts.append(doc_text)
                
                source = "RAG" if source == "GEN" else "HYBRID"
                print(f"✅ Using RAG with {len(results[:3])} documents")
            else:
                print(f"⚠️ FAISS results below threshold ({top_score:.4f})")
    except Exception as e:
        print(f"❌ FAISS retrieval error: {e}")
    
    # Step 4: Keyword fallback for colloquial queries when all else fails
    if source == "GEN":
        # Define legal keywords for fallback search
        legal_keywords = [
            "bribe", "gratification", "undue advantage", "public servant", "corrupt",
            "cheating", "fraud", "dishonest", "misrepresentation", "seller", "vendor",
            "theft", "robbery", "dacoity", "extortion", "stolen",
            "hurt", "assault", "battery", "grievous", "murder", "death",
            "land", "property", "tenancy", "ejectment", "possession",
            "marriage", "divorce", "dower", "talaq", "maintenance",
            "complaint", "fir", "police", "arrest", "bail", "court"
        ]
        
        keyword_results = keyword_search_in_laws(expanded_query, legal_keywords, max_results=3)
        if keyword_results:
            context_parts.extend(keyword_results)
            source = "KEYWORD"
            print(f"✅ Keyword fallback found {len(keyword_results)} matches")
    
    context = "\n\n---\n\n".join(context_parts)
    return context.strip(), source


# ==================== Groq Generation ====================

def groq_generate(prompt: str, temperature: float = 0.2) -> str:
    """Generate response using Groq"""
    try:
        if not _groq_client:
            return "⚠️ Groq API key not configured. Please set your API key in settings."
        
        completion = _groq_client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=2000,
            top_p=0.9
        )
        
        if completion.choices[0].message.content:
            return completion.choices[0].message.content.strip()
        else:
            return "❌ Unable to generate response."
            
    except Exception as e:
        error_str = str(e)
        print(f"❌ Groq generation error: {e}")
        return f"❌ Error generating response: {str(e)[:100]}"


# ==================== Main Processing ====================

def process_input(chat_name: str, user_input: str, return_source: bool = False, language: str = "en"):
    """
    Process user query and generate response
    
    Args:
        chat_name: Chat session identifier
        user_input: User's query
        return_source: Whether to return source type
        language: 'en' for English, 'bn' for Bengali
    """
    # Load chat history
    current_chat = load_chat(chat_name)
    history_pairs = list(zip(current_chat.get("past", []), current_chat.get("generated", [])))
    
    # Format last 4 exchanges for context
    history_prompt = ""
    for q, a in history_pairs[-4:]:
        history_prompt += f"User: {q}\nAssistant: {a}\n\n"
    
    # Hybrid retrieval
    context_text, source_type = hybrid_retrieve(user_input, k=5)
    
    # Build context prompt
    has_meaningful_context = context_text and len(context_text.strip()) > 100 and source_type != "GEN"
    
    if has_meaningful_context:
        context_prompt = f"""Based on the following Bangladesh legal provisions:

{context_text}

Please answer the user's question accurately. Cite specific sections/articles from the above provisions in your answer."""
    else:
        source_type = "GEN"
        context_prompt = "No specific legal provisions were retrieved from the Bangladesh law database. Provide a general response, but mention that you don't have specific legal references for this query."
    
    # Language instruction
    lang_instruction = ""
    if language == "bn":
        lang_instruction = "\nPlease respond in Bengali (বাংলা) as the user asked in Bengali."
    
    # Build full prompt
    full_prompt = f"""{SYSTEM_PROMPT}

{context_prompt}

Previous conversation:
{history_prompt}

User Question: {user_input}{lang_instruction}

Assistant:"""
    
    # Generate response
    response = groq_generate(full_prompt, temperature=0.2)
    
    # Fallback if blocked
    if response.startswith("❌") or "unable" in response.lower():
        # Try without context
        simplified_prompt = f"""You are a legal assistant for Bangladesh law. 

User question: {user_input}

Provide a helpful response about Bangladesh law.{lang_instruction}"""
        response = groq_generate(simplified_prompt, temperature=0.1)
    
    # Save to chat history
    current_chat["past"].append(user_input)
    current_chat["generated"].append(response)
    current_chat["source"].append(source_type)
    save_chat(chat_name, current_chat)
    
    print(f"⚡ Source: {source_type} | Query: {user_input[:50]}...")
    
    if return_source:
        return response, source_type
    return response


# Initialize on module load
if __name__ == "__main__":
    # Test the system
    print("Testing Legal-Bengal chatbot...")
    test_query = "What is section 302 of the Penal Code?"
    response, source = process_input("test_chat", test_query, return_source=True)
    print(f"\nQuery: {test_query}")
    print(f"Source: {source}")
    print(f"Response: {response[:200]}...")
