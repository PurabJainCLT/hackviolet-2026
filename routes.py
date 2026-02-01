from flask import Blueprint, request, jsonify
from gemini_service import ask_gemini

main_routes = Blueprint("main", __name__)

@main_routes.route("/ask", methods=["POST"])
def ask():
    prompt = request.json.get("prompt")
    answer = ask_gemini(prompt)
    return jsonify({"response": answer})
