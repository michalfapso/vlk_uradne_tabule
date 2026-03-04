import litellm
import os
import traceback
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_FILEPATH = os.path.join(SCRIPT_DIR, "analyze_text_document_prompt.md")

def analyze_text_document(text_content: str):
    """
    Analyzuje textový obsah pomocou LLM (cez litellm) a uloží výsledok ako JSON.
    """
    print(f"Spúšťam analýzu textu cez LLM")
    
    try:
        with open(PROMPT_FILEPATH, 'r', encoding='utf-8') as f:
            prompt = f.read()
            prompt += "\n\nText dokumentu:\n" + text_content
    
        # Použi litellm na volanie LLM (napr. gpt-4o-mini alebo iný model)
        # Uisti sa, že máš nastavené API kľúče ako environmentálne premenné
        response = litellm.completion(
            model="gemini/gemini-3-flash-preview", # gemini-2.5-flash
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }, # Požiadame o JSON výstup
            # reasoning_effort="medium"
        )

        # Log cost and token usage
        cost = litellm.completion_cost(completion_response=response)
        print(f"LLM_cost: {json.dumps({'cost': cost})}")
        
        usage = response.usage
        usage_info = {
            "input": getattr(usage, "prompt_tokens", 0),
            "output": getattr(usage, "completion_tokens", 0),
            "total": getattr(usage, "total_tokens", 0)
        }
        # Add cached tokens if available
        if hasattr(usage, "prompt_tokens_details") and usage.prompt_tokens_details:
             usage_info["cached"] = getattr(usage.prompt_tokens_details, "cached_tokens", 0)
        elif hasattr(usage, "cache_read_input_tokens"):
             usage_info["cached"] = usage.cache_read_input_tokens
        
        print(f"LLM_tokens: {json.dumps(usage_info)}")

        # Extrahuj obsah odpovede (mal by to byť JSON string)
        analysis_result_str = response.choices[0].message.content
        return analysis_result_str

    except Exception as e:
        print(traceback.format_exc(), file=sys.stderr) # Vypíš detail chyby
        raise RuntimeError(f"Chyba počas LLM analýzy: {e}")