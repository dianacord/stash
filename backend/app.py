from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow frontend to call API

# Health check endpoint - test if everything is working
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'Stash API is running!',
        'supabase_configured': bool(os.getenv('SUPABASE_URL')),
        'groq_configured': bool(os.getenv('GROQ_API_KEY'))
    })

# Root endpoint
@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'message': 'Welcome to Stash API!',
        'endpoints': {
            '/api/health': 'Health check',
            '/api/videos': 'Coming soon...'
        }
    })

# Main entry point
if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Starting Stash API...")
    print("="*50)
    
    # Check if API keys are configured
    if os.getenv('SUPABASE_URL'):
        print(f"✅ Supabase: {os.getenv('SUPABASE_URL')[:30]}...")
    else:
        print("❌ Supabase: Not configured")
    
    if os.getenv('GROQ_API_KEY'):
        print("✅ Groq API: Configured")
    else:
        print("❌ Groq API: Not configured")
    
    print("="*50)
    print("📍 Server running at: http://localhost:8080")
    print("📍 Health check: http://localhost:8080/api/health")
    print("="*50 + "\n")
    
    app.run(debug=True, port=8080)