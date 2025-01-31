def get_cleanup_prompt(schema, dirty_text):
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