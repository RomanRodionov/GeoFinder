import json
import requests
from geo import path

# Получение токена и id навыка из json файла
file = open(path('token.json'), 'r', encoding="utf-8")
tokens = json.loads(file.read())
file.close()
token = tokens['token']
skill_id = tokens['skill_id']

# Получение данных об использованной памяти
url = "https://dialogs.yandex.net/api/v1/status"
response = requests.get(url, headers={'Authorization': f'OAuth {token}'})
info = response.json()['images']['quota']

# Отображение её в процентах
total = int(info['total'])
used = int(info['used'])
used_per = round(used / total * 100, 1)
print(f"Использовано {str(used_per)}% памяти.")

# Спрашивает пользователя о дальнейших действиях
print("Удалить все изображения? y/n")
flag = False
while not flag:
    ans = str(input())
    if ans == 'y':
        flag = True
        # Получение списка изображений
        url = f'https://dialogs.yandex.net/api/v1/skills/{skill_id}/images'
        images_id = requests.get(url, headers={'Authorization': f'OAuth {token}'}).json()['images']
        for image in images_id:
            # Удаление изображения
            try:
                url = f'https://dialogs.yandex.net/api/v1/skills/{skill_id}/images/' + str(image['id'])
                res = requests.delete(url, headers={'Authorization': f'OAuth {token}'}).json()
                print(str(image['id']) + ' delete status: ' + res['result'])
            except Exception:
                print('error')
        print('Удаление завершено')
    elif ans == 'n':
        flag = True
print('Сеанс окончен')
