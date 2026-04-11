from flask import Flask, request, jsonify
import chromadb
import requests
import uuid

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


def push_to_openclaw_telegram(message):
    """Pushes an alert directly to the Telegram chat so OpenClaw can see it"""
    # Configured for Avinash's Svaya Alerts Bot
    BOT_TOKEN = "8662847867:AAENJtmV-8HwGKCRLn8FGOqAdlPevlYV7dU"
    CHAT_ID = "7041322342"
    
    if BOT_TOKEN == "YOUR_NEW_BOT_TOKEN":
        print("[WARNING] Telegram BOT_TOKEN not set. Skipping Telegram push.")
        return
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": f"🚨 **SVAYA RUNPOD ALERT** 🚨\n{message}", "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("Failed to send Telegram alert:", e)


@app.route('/tmf921/intent', methods=['POST'])
def handle_tmf921_intent():
    """ TM Forum TMF921 Intent Management API Endpoint """
    data = request.json
    
    intent_id = data.get("id", "Unknown_Intent")
    expectations = data.get("intentExpectation", [])
    contexts = data.get("intentContext", [])
    
    # Parse the TMF921 payload into a readable summary for Vector Search
    target_summary = []
    for exp in expectations:
        for target in exp.get("expectationTarget", []):
            target_summary.append(f"{target.get('targetName')} should be {target.get('targetCondition')} {target.get('targetValue')} {target.get('unit')}")
            
    context_summary = []
    for ctx in contexts:
        context_summary.append(f"{ctx.get('contextAttribute')}: {ctx.get('contextValue')}")
        
    search_query = " ".join(target_summary) + " " + " ".join(context_summary)
    
    # Retrieve SON optimization SOPs AND Past Memories
    results = collection.query(query_texts=[search_query], n_results=2)
    kb_context = "\n".join([doc for sublist in results['documents'] for doc in sublist])
    
    prompt = f"""
    You are Svaya, the TMF921 Intent Handler (Level 3 Autonomous Network Engine).
    You have received a declarative Intent from the operator. You must translate this intent into specific network parameter changes.
    
    Intent ID: {intent_id}
    Targets (What must be achieved):
    {chr(10).join(target_summary)}
    
    Context (Where it applies):
    {chr(10).join(context_summary)}
    
    Knowledge Base & Past Lessons:
    {kb_context}
    
    Task:
    1. Evaluate the SOPs and Past Lessons to determine the best parameter changes to satisfy the Targets.
    2. If a past lesson shows an action FAILED to meet these specific targets, do NOT recommend it.
    3. Output the exact Method of Procedure (MOP) to fulfill the intent, specifying the parameters to change.
    """
    
    try:
        response = requests.post("http://127.0.0.1:11434/api/generate", 
                                 json={"model": "llama3", "prompt": prompt, "stream": False})
        
        llm_response_text = response.json().get("response", "Error getting LLM response")
        
        # 🚨 Push the alert to Telegram! 🚨
        push_to_openclaw_telegram(f"Received TMF921 Intent for `{intent_id}`.\n\n*Action Plan:*\n{llm_response_text}")
        
        # In a real TMF921 system, we would immediately return an "Acknowledged" status 
        # and evaluate asynchronously, but for the POC we return the LLM's translation plan.
        return jsonify({
            "intentId": intent_id,
            "handlingState": "Acknowledged",
            "translation_plan": llm_response_text
        })
    except Exception as e:
        return jsonify({"handlingState": "Rejected", "error": f"Error connecting to local Ollama: {str(e)}"})


@app.route('/tmf921/feedback', methods=['POST'])
def feedback():
    """ The Intent-Based Learning Feedback Loop """
    data = request.json
    cell_id = data.get("cell_id", "Unknown")
    intent = data.get("intent", "Unknown Intent")
    action_taken = data.get("action_taken", "Unknown Action")
    success = data.get("success", False)
    outcome_notes = data.get("outcome_notes", "")
    
    status = "SUCCESS" if success else "FAILURE"
    lesson = f"LESSON LEARNED ({status}) - Context: {cell_id} | Intent Targets: {intent} | Action Taken: {action_taken} | Outcome: {outcome_notes}. "
    
    if success:
        lesson += "This action was successful. Prioritize this approach for similar future intents."
    else:
        lesson += "This action FAILED. Avoid this approach for similar future intents and try alternatives."
        
    try:
        memory_id = f"memory_{uuid.uuid4().hex[:8]}"
        collection.add(
            documents=[lesson],
            metadatas=[{"source": "TMF921_Feedback_Loop", "type": "learned_memory"}],
            ids=[memory_id]
        )
        return jsonify({"status": "Memory stored successfully", "lesson_learned": lesson})
    except Exception as e:
        return jsonify({"status": "Error storing memory", "error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)