# -*- coding: utf-8 -*-
from utils.scraps.scrape.dumb import bounds_based_parse

question = "В каком рейтинге (по состоянию на 2021 год) ИТМО впервые вошёл в топ-400 мировых университетов?\n1. ARWU (Shanghai Ranking)\n2. Times Higher Education (THE) World University Rankings\n3. QS World University Rankings\n4. U.S. News & World Report Best Global Universities"

with open('prompts/base_instruct.xml') as inst:
    BASE_INSTRUCTIONS = inst.read()

with open('prompts/after_search_instruct.xml') as after_search:
    AFTER_SEARCH_TEMPLATE = after_search.read()

sources = [
    "https://news.itmo.ru/ru/university_live/ratings/news/10169/?ysclid=m6jhm4vgmu584156611",
    "https://www.sobaka.ru/city/science/125026?ysclid=m6jhm5remt94316456",
    "https://www.gov.spb.ru/gov/otrasl/c_science/news/216148/",
    "https://edurank.org/uni/itmo-university/rankings/"
]

scraped_data = {}

print('scraping...')
for i in sources:
    print('scraping', i)
    if attempt := bounds_based_parse(i):
        scraped_data[i] = attempt

print('templating')
after_search_instructions = AFTER_SEARCH_TEMPLATE.replace('{{ question_text }}', question)


chat_history = [
    {
        "role": "system",
        "text": BASE_INSTRUCTIONS,
    },
    {
        "role": "user",
        "text": question,
    },
    {
        "role": "assistant",
        "text": """Чтобы ответить на вопрос, в каком рейтинге ИТМО впервые вошёл в топ-400 мировых университетов по состоянию на 2021 год, нужно найти данные о позициях университета в различных международных рейтингах за указанный период.\n\nДля этого потребуются следующие источники:\n* официальные сайты международных рейтинговых агентств (ARWU, Times Higher Education, QS World University Rankings, U.S. News & World Report);\n* официальный сайт университета ИТМО.\n\nПоисковый запрос: «позиции университета ИТМО в международных рейтингах 2021 года».\n\n---\n{\n"query": "позиции университета ИТМО в международных рейтингах 2021 года"\n}'""",
    },
    {
        "role": "system",
        'text': f"{after_search_instructions}\n# Факты и источники\n{scraped_data}",
    }
]

if __name__ == '__main__':
    print('\n'.join(str(i) for i in chat_history))