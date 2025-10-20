import litellm
import os
import traceback
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_FILEPATH = os.path.join(SCRIPT_DIR, "./analyze_text_document_prompt.md")

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
            model="gemini/gemini-2.5-flash", # gemini-2.5-flash-preview-04-17
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }, # Požiadame o JSON výstup
            # reasoning_effort="medium"
        )

        # Extrahuj obsah odpovede (mal by to byť JSON string)
        analysis_result_str = response.choices[0].message.content
        return analysis_result_str

    except Exception as e:
        print(traceback.format_exc(), file=sys.stderr) # Vypíš detail chyby
        raise RuntimeError(f"Chyba počas LLM analýzy: {e}")