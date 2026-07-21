"""
Legal-Bengal: Bangladesh Legal AI Assistant
Reuses architecture from AskLegal.ai and Nyaya-GPT
Adapted for Bangladesh legal system with bilingual support
"""

import os
import logging
import sys
from flask import Flask, render_template, request, jsonify, send_from_directory, session
from dotenv import load_dotenv

try:
    from views.chatbot import process_input, create_new_chat, get_chat_list, load_chat, set_groq_key
except Exception as e:
    print(f"❌ Failed to import chatbot: {e}", file=sys.stderr)
    raise

try:
    from views.docGen import generate_legal_document
except Exception as e:
    print(f"❌ Failed to import docGen: {e}", file=sys.stderr)
    raise

print("🚀 Starting Legal-Bengal Flask app...", file=sys.stderr)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'legal-bengal-secret-key-2024')

# Clear any existing handlers
for handler in app.logger.handlers:
    app.logger.removeHandler(handler)

# Configure Flask logger
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
console_handler.setFormatter(formatter)
app.logger.addHandler(console_handler)
app.logger.setLevel(logging.INFO)


@app.route('/')
def index():
    """Main chat interface"""
    raw_chat_names = get_chat_list()
    chat_list = []

    for name in raw_chat_names:
        chat_data = load_chat(name)
        first_q = chat_data["past"][0] if chat_data["past"] else "New chat"
        truncated_q = first_q[:30] + '...' if len(first_q) > 30 else first_q
        chat_list.append({
            "name": name,
            "title": truncated_q
        })

    chat_name = chat_list[0]["name"] if chat_list else create_new_chat()
    chat_data = load_chat(chat_name) if chat_list else {"past": [], "generated": [], "source": []}

    return render_template('index.html', 
                          chat_name=chat_name, 
                          chat_list=reversed(chat_list), 
                          chat_data=chat_data)


@app.route('/api/set_key', methods=['POST'])
def set_api_key():
    """Allow users to set their own Groq API key"""
    data = request.json
    api_key = data.get('api_key', '').strip()
    
    if not api_key or len(api_key) < 20:
        return jsonify({"error": "Invalid API key provided"}), 400
    
    try:
        set_groq_key(api_key)
        # Store in session for this user
        session['user_groq_key'] = api_key
        app.logger.info("✅ User set custom Groq API key")
        return jsonify({"message": "API key set successfully"})
    except Exception as e:
        app.logger.error(f"❌ Failed to set API key: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/chat_list')
def chat_list():
    """Get list of all chats"""
    raw_chat_names = get_chat_list()
    chat_list = []
    for name in raw_chat_names:
        chat_data = load_chat(name)
        first_q = chat_data["past"][0] if chat_data["past"] else "New chat"
        truncated_q = first_q[:30] + '...' if len(first_q) > 30 else first_q
        chat_list.append({
            "name": name,
            "title": truncated_q
        })
    return jsonify({"chat_list": list(reversed(chat_list))})


@app.route('/chat', methods=['POST'])
def chat():
    """Process chat message"""
    data = request.json
    user_input = data.get('user_input', '')
    chat_name = data.get('chat_name', '')
    language = data.get('language', 'en')  # 'en' or 'bn'

    if not user_input or not chat_name:
        return jsonify({"error": "Missing input or chat name"}), 400

    # Check for user-specific API key in session
    if 'user_groq_key' in session:
        set_groq_key(session['user_groq_key'])

    try:
        # Get response and source
        response, source_type = process_input(
            chat_name, 
            user_input, 
            return_source=True,
            language=language
        )

        # Log the source
        app.logger.info(f"⚡ Answer Source: {source_type} | Chat: {chat_name} | Input: {user_input[:50]}...")

        return jsonify({
            "response": response,
            "source": source_type
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        app.logger.error(f"❌ Chat error: {e}")
        app.logger.error(f"Traceback: {error_trace}")
        return jsonify({"error": str(e), "trace": error_trace[:500]}), 500


@app.route('/new_chat', methods=['POST'])
def new_chat():
    """Create new chat session"""
    chat_name = create_new_chat()
    return jsonify({"chat_name": chat_name})


@app.route('/load_chat', methods=['POST'])
def load_existing_chat():
    """Load existing chat history"""
    data = request.json
    chat_name = data.get('chat_name')
    if not chat_name:
        return jsonify({"error": "Chat name required"}), 400

    chat_data = load_chat(chat_name)
    return jsonify({"chat_data": chat_data})


@app.route('/generate')
def generate():
    """Document generator interface"""
    raw_chat_names = get_chat_list()
    chat_list = []
    for name in raw_chat_names:
        chat_data = load_chat(name)
        first_q = chat_data["past"][0] if chat_data["past"] else "New chat"
        truncated_q = first_q[:30] + '...' if len(first_q) > 30 else first_q
        chat_list.append({
            "name": name,
            "title": truncated_q
        })
    return render_template('generate.html', chat_list=chat_list)


@app.route('/generate_document', methods=['POST'])
def generate_document():
    """Generate legal document"""
    data = request.json
    prompt = data.get('doc_prompt', '')
    language = data.get('language', 'en')
    
    if not prompt:
        return jsonify({'error': 'Prompt required'}), 400

    try:
        file_path, file_name = generate_legal_document(prompt, language=language)
        return jsonify({
            'download_url': f'/download/{file_name}',
            'file_name': file_name
        })
    except Exception as e:
        app.logger.error(f"❌ Document generation error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/download/<filename>')
def download_file(filename):
    """Download generated document"""
    return send_from_directory('static/generated_docs', filename, as_attachment=True)


@app.route('/laws')
def laws_reference():
    """Reference page for available laws"""
    laws_data = {
        "The Constitution of Bangladesh": "166 articles covering fundamental rights, state policy, governance",
        "The Penal Code, 1860": "557 sections - criminal offenses and punishments",
        "The Code of Criminal Procedure, 1898": "471 sections - criminal procedure and court processes",
        "The Registration Act, 1908": "109 sections - property and document registration",
        "The State Acquisition and Tenancy Act, 1950": "203 sections - land laws and tenancy",
        "The Transfer of Property Act, 1882": "142 sections - property transfer rules"
    }
    return render_template('laws.html', laws=laws_data)


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
