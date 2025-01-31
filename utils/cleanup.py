from typing import List, Dict


def get_cleanup_prompt(schema: str, dirty_text: str) -> List[Dict[str, str]]:
    """
    Создает промпт для вспомогательной модели, которая должна
    очистить входные данные, если их не получилось разделить
    программатически
    """
    return [
        {
            "role": "system",
            "text": f"""In the following text there is json. You MUST respond with a valid json from there. 
                use the following schema: {schema}""",
        },
        {
            "role": "user",
            'text': dirty_text
        }
    ]
