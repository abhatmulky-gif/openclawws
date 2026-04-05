from flask import Flask, request, jsonify
import chromadb
import requests

app = Flask(__name__)
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection(name="telecom_sops")

@app.route('/analyze_alarm', methods=['POST'])
def analyze_alarm():
    data = request.json
    alarms_list = data.get("alarms", [])
    
    # Combine the storm into a single block of text for vector search
    storm_summary = " ".join(alarms_list)
    
    # Retrieve the top 2 pieces of context
    results = collection.query(query_texts=[storm_summary], n_results=2)
    context = "\n".join([doc for sublist in results['documents'] for doc in sublist])
    
    # Build the Correlation Prompt
    prompt = f"""
    You are an expert Tier-3 Telecom NOC AI. Your job is ALARM CORRELATION.
    You have received an ALARM STORM across multiple vendors. 
    
    Incoming Alarm Storm:
    {chr(10).join(alarms_list)}
    
    Topology & SOP Context:
    {context}
    
    Task:
    1. Perform cross-vendor alarm correlation.
    2. Identify the SINGLE Root Cause of this storm. 
    3. State clearly what NOT to do (to save dispatch costs), and what the exact next troubleshooting step is.
    """
    
    try:
        response = requests.post("http://127.0.0.1:11434/api/generate", 
                                 json={"model": "llama3", "prompt": prompt, "stream": False})
        return jsonify({"analysis": response.json().get("response", "Error getting LLM response")})
    except Exception as e:
        return jsonify({"analysis": f"Error connecting to local Ollama: {str(e)}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
