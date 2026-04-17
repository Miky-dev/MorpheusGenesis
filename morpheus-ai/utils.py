import json
import logging
import streamlit as st

logger = logging.getLogger("morpheus_ai")

def extract_first_json(raw: str) -> str:
    start = raw.find("{")
    if start == -1:
        return raw

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(raw)):
        char = raw[index]
        if char == '"' and not escape:
            in_string = not in_string
        if char == '\\' and not escape:
            escape = True
            continue
        escape = False

        if not in_string:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return raw[start:index + 1]
    return raw


def normalize_agent_output(raw: str) -> str:
    if not isinstance(raw, str):
        return ""
    cleaned = raw.strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    cleaned = extract_first_json(cleaned)
    return cleaned


def parse_json_response(raw: str, context: str = ""):
    if not isinstance(raw, str):
        return None
    raw = normalize_agent_output(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        fallback = extract_first_json(raw)
        if fallback != raw:
            try:
                return json.loads(fallback)
            except json.JSONDecodeError:
                pass
        st.error(f"Risposta non valida da {context}. Riprova.")
        with st.expander("Debug risposta LLM"):
            st.code(raw)
            st.code(str(exc))
        logger.error("JSON decode failed for %s: %s", context, exc)
        return None


def safe_agent_run(agent, prompt, schema=None, context_name=""):
    try:
        result = agent.run(prompt)
        content = getattr(result, "content", result)
        raw = normalize_agent_output(content) if isinstance(content, str) else content
        if schema:
            if isinstance(raw, str):
                try:
                    if hasattr(schema, "model_validate_json"):
                        return schema.model_validate_json(raw)
                    return schema(**json.loads(raw))
                except Exception as exc:
                    parsed = parse_json_response(raw, context_name)
                    if parsed is not None:
                        try:
                            if hasattr(schema, "model_validate"):
                                return schema.model_validate(parsed)
                            return schema(**parsed)
                        except Exception as exc2:
                            exc = exc2
                    st.error(f"Errore di validazione della risposta {context_name}. Controlla il formato della risposta.")
                    with st.expander("Debug validazione"):
                        st.code(raw)
                        st.code(str(exc))
                    logger.error("Schema validation failed for %s: %s", context_name, exc)
                    return None
            elif isinstance(raw, dict):
                try:
                    if hasattr(schema, "model_validate"):
                        return schema.model_validate(raw)
                    return schema(**raw)
                except Exception as exc:
                    st.error(f"Errore di validazione della risposta {context_name}. Controlla il formato della risposta.")
                    with st.expander("Debug validazione"):
                        st.code(raw)
                        st.code(str(exc))
                    logger.error("Schema validation failed for %s: %s", context_name, exc)
                    return None
        return raw
    except Exception as exc:
        st.error(f"Errore durante la chiamata {context_name}. Riprova.")
        with st.expander("Debug errore agente"):
            st.code(str(exc))
        logger.exception("Agent run failed for %s", context_name)
        return None
