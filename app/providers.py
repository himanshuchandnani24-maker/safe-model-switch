"""
LLM Provider integrations for Gemini and Groq using standard httpx.
Handles network calls, token extraction, latency measurement, and error handling.
"""
import time
import httpx
from typing import Dict, Any, Tuple
from app.config import settings


async def call_gemini(
    prompt: str,
    model_name: str,
    api_key: str,
    system_instruction: str = None
) -> Tuple[str, int, int, int]:
    """
    Call Google Gemini generateContent REST endpoint.
    Returns: (text_answer, input_tokens, output_tokens, latency_ms)
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    payload: Dict[str, Any] = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    start_time = time.perf_counter()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
    latency_ms = int((time.perf_counter() - start_time) * 1000)

    if response.status_code != 200:
        raise RuntimeError(f"Gemini API error ({response.status_code}): {response.text}")

    data = response.json()
    try:
        candidates = data.get("candidates", [])
        if not candidates:
            text = ""
        else:
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", len(prompt.split()))
        output_tokens = usage.get("candidatesTokenCount", len(text.split()))
        
        return text.strip(), input_tokens, output_tokens, latency_ms
    except Exception as e:
        raise RuntimeError(f"Failed to parse Gemini response: {e}")


async def call_groq(
    prompt: str,
    model_name: str,
    api_key: str
) -> Tuple[str, int, int, int]:
    """
    Call Groq OpenAI-compatible chat completions REST endpoint.
    Returns: (text_answer, input_tokens, output_tokens, latency_ms)
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    start_time = time.perf_counter()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
    latency_ms = int((time.perf_counter() - start_time) * 1000)

    if response.status_code != 200:
        raise RuntimeError(f"Groq API error ({response.status_code}): {response.text}")

    data = response.json()
    try:
        choices = data.get("choices", [])
        text = choices[0].get("message", {}).get("content", "") if choices else ""
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", len(prompt.split()))
        output_tokens = usage.get("completion_tokens", len(text.split()))

        return text.strip(), input_tokens, output_tokens, latency_ms
    except Exception as e:
        raise RuntimeError(f"Failed to parse Groq response: {e}")
