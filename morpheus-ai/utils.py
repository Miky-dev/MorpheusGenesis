import json
import logging
import re
import streamlit as st

logger = logging.getLogger("morpheus_ai")

def extract_first_json(raw: str) -> str:
    start = raw.find("{")
    if start == -1:
        return raw

    depth = 0
    in_string = False
    escape = False
    
    # We want to find the matching '}' for the first '{'
    for index in range(start, len(raw)):
        char = raw[index]
        
        # Handle string boundaries
        if char == '"' and not escape:
            in_string = not in_string
        
        # Handle escapes
        if char == '\\' and not escape:
            escape = True
            continue
        escape = False

        # Only count braces outside of strings
        if not in_string:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return raw[start:index + 1]
    
    # If we didn't find a matching brace, return what we found from start
    return raw[start:]


def normalize_agent_output(raw: str) -> str:
    if not isinstance(raw, str):
        return ""
    cleaned = raw.strip()
    # Rimuove blocchi markdown ```json ... ```
    cleaned = re.sub(r"```json\s*", "", cleaned)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()
    cleaned = extract_first_json(cleaned)
    return cleaned


def _sanitize_json_string(raw: str) -> str:
    """Tenta di riparare newline letterali inside stringhe JSON che rompono il parser."""
    # Sostituisce newline reali dentro i valori stringa con \n escaped
    # Usa una regex per trovare il contenuto tra doppi apici e sostituisce i newline
    def replace_newlines_in_string(m):
        # Prende il contenuto dentro le virgolette e sostituisce newline reali
        content = m.group(0)
        # Rimpiazza solo i \n letterali non già escapati
        inner = content[1:-1]  # rimuove le virgolette di contorno
        inner = inner.replace('\r\n', '\\n').replace('\r', '\\n').replace('\n', '\\n')
        return '"' + inner + '"'

    return re.sub(r'"(?:[^"\\]|\\.)*"', replace_newlines_in_string, raw, flags=re.DOTALL)


def parse_json_response(raw: str, context: str = ""):
    if not isinstance(raw, str):
        return None
    
    # Try a first pass at normalization
    cleaned = normalize_agent_output(raw)
    
    def try_parse(content):
        # Attempt 1: direct parsing
        try:
            return json.loads(content, strict=False)
        except json.JSONDecodeError:
            pass
        # Attempt 2: sanitization of embedded newlines
        try:
            sanitized = _sanitize_json_string(content)
            return json.loads(sanitized, strict=False)
        except json.JSONDecodeError:
            pass
        return None

    parsed = try_parse(cleaned)
    
    # If parsing failed, try to extract from the raw string again (maybe normalize over-cleaned it)
    if parsed is None:
        fallback = extract_first_json(raw)
        if fallback and fallback != cleaned:
            parsed = try_parse(fallback)
            
    # Check for Groq error wrapper
    if isinstance(parsed, dict) and "error" in parsed:
        rescued = _rescue_from_groq_error(parsed)
        if rescued is not None:
            parsed = rescued
            
    if parsed is None:
        logger.error("JSON decode failed for %s", context)
    return parsed


def _rescue_from_groq_error(data: dict):
    """
    Groq rejects JSON-mode + tool-use combinations with a `tool_use_failed` error,
    but still embeds the model's valid JSON inside `error.failed_generation`.

    The `failed_generation` field is a JSON string shaped like:
        {"name": "json", "arguments": { <actual response fields> }}

    We extract and return the `arguments` dict so the engine can recover.
    """
    try:
        err = data.get("error", {})
        if not isinstance(err, dict):
            return None
        raw_gen = err.get("failed_generation", "")
        if not raw_gen:
            return None
        parsed = json.loads(raw_gen, strict=False)
        # The real payload is in "arguments"
        arguments = parsed.get("arguments")
        if isinstance(arguments, dict):
            logger.info("Recovered payload from Groq failed_generation (%d keys)", len(arguments))
            return arguments
        # Fallback: maybe the whole parsed object IS the payload
        if isinstance(parsed, dict) and "error" not in parsed:
            return parsed
    except Exception as exc:
        logger.debug("_rescue_from_groq_error failed: %s", exc)
    return None


def safe_agent_run(agent, prompt, schema=None, context_name=""):
    try:
        result = agent.run(prompt)
        content = getattr(result, "content", result)
        
        # If it's already a dict (e.g. some providers return parsed JSON or error dicts)
        if isinstance(content, dict):
            data = content
            # Check for Groq error wrapper
            if "error" in data:
                rescued = _rescue_from_groq_error(data)
                if rescued is not None:
                    data = rescued
        else:
            # It's a string, try to parse it
            data = parse_json_response(str(content), context_name)
            if data is None:
                # Fallback to normalized raw string if parsing fails
                data = normalize_agent_output(str(content))

        if schema:
            # Validate against schema
            try:
                if isinstance(data, str):
                    # It's a string, try model_validate_json or parse and validate
                    if hasattr(schema, "model_validate_json"):
                        return schema.model_validate_json(data)
                    parsed = parse_json_response(data, context_name)
                    return schema.model_validate(parsed) if hasattr(schema, "model_validate") else schema(**parsed)
                elif isinstance(data, dict):
                    # It's a dict, use model_validate
                    return schema.model_validate(data) if hasattr(schema, "model_validate") else schema(**data)
            except Exception as exc:
                st.error(f"Errore di validazione della risposta {context_name}.")
                logger.error("Schema validation failed for %s: %s", context_name, exc)
                return None
        
        return data
    except Exception as exc:
        # Check if the exception contains the Groq tool_use_failed error JSON
        exc_str = str(exc)
        if "tool_use_failed" in exc_str and "failed_generation" in exc_str:
            try:
                start_idx = exc_str.find('{')
                if start_idx != -1:
                    err_json_str = exc_str[start_idx:]
                    err_json_str = extract_first_json(err_json_str)
                    err_data = json.loads(err_json_str, strict=False)
                    rescued_payload = _rescue_from_groq_error(err_data)
                    
                    if rescued_payload is not None:
                        logger.info("Successfully rescued payload from exception in safe_agent_run")
                        if schema:
                            if hasattr(schema, "model_validate"):
                                return schema.model_validate(rescued_payload)
                            return schema(**rescued_payload)
                        return rescued_payload
            except Exception as inner_exc:
                logger.debug("Failed to rescue payload from exception: %s", inner_exc)

        st.error(f"Errore durante la chiamata {context_name}. Riprova.")
        logger.exception("Agent run failed for %s", context_name)
        return None
