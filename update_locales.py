import re

with open('locales.py', 'r', encoding='utf-8') as f:
    content = f.read()

uz_new = "'error': \"❌ Kechirasiz, media topilmadi yoki bu post yopiq/xususiy.\",\n        'private_video': \"🔒 Kechirasiz, bu video yopiq (xususiy) yoki o'chirib tashlangan.\",\n        'timeout': \"⏱ Yuklab olish vaqti tugadi yoki tarmoq xatosi yuz berdi. Iltimos qaytadan urinib ko'ring.\",\n        'login_required': \"🔐 Bu videoni yuklab olish uchun akkauntga kirish talab qilinadi. Buni yuklab ololmayman.\","
ru_new = "'error': \"❌ Извините, медиа не найдено или этот пост закрыт/приватный.\",\n        'private_video': \"🔒 Извините, это видео приватное или было удалено.\",\n        'timeout': \"⏱ Время ожидания истекло или произошла ошибка сети. Пожалуйста, попробуйте снова.\",\n        'login_required': \"🔐 Для скачивания этого видео требуется авторизация. Я не могу его скачать.\","
en_new = "'error': \"❌ Sorry, media not found or the post is private.\",\n        'private_video': \"🔒 Sorry, this video is private or has been deleted.\",\n        'timeout': \"⏱ Download timed out or network error occurred. Please try again.\",\n        'login_required': \"🔐 Login is required to download this video. I cannot download it.\","

content = content.replace("'error': \"❌ Kechirasiz, media topilmadi yoki bu post yopiq/xususiy.\",", uz_new)
content = content.replace("'error': \"❌ Извините, медиа не найдено или этот пост закрыт/приватный.\",", ru_new)
content = content.replace("'error': \"❌ Sorry, media not found or the post is private.\",", en_new)

with open('locales.py', 'w', encoding='utf-8') as f:
    f.write(content)
