import yaml

def get_variations(words):
    variations = []
    for word in words:
        variations += [
                word,
                word + 's',
                word + 'es',
                word + '\'s',
                word + '!',
                word + 'in',
                word + 'ing',
                word + '\'ll',
                word + '\'d'
        ]

    return variations

with open('./lists/slurs.yaml', 'r') as f:
    slurs = get_variations(yaml.load(f, Loader=yaml.FullLoader)['words'])

with open('./lists/sexual-content.yaml', 'r') as f:
    sexual_content = get_variations(yaml.load(f, Loader=yaml.FullLoader)['words'])

with open('./lists/severe-swear-words.yaml', 'r') as f:
    severe_swear_words = get_variations(yaml.load(f, Loader=yaml.FullLoader)['words'])

with open('./lists/other-swear-words.yaml', 'r') as f:
    other_swear_words = get_variations(yaml.load(f, Loader=yaml.FullLoader)['words'])

with open('./no-slurs-no-sex.txt', 'w') as f:
    f.write(' '.join(slurs + sexual_content))

with open('./conventions.txt', 'w') as f:
    f.write(' '.join(slurs + sexual_content + severe_swear_words))

with open('./child-friendly.txt', 'w') as f:
    f.write(' '.join(slurs + sexual_content + severe_swear_words + other_swear_words))
