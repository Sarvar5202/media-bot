import re

with open('handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add TelegramForbiddenError handling
old_except = '''    except Exception as e:
        await bot.send_message(chat_id=chat_id, text=await get_text(user_id, "error"), reply_to_message_id=reply_to_message_id)
        return False'''

new_except = '''    except TelegramForbiddenError:
        # User blocked the bot
        await set_user_inactive(user_id)
        return False
    except Exception as e:
        try:
            await bot.send_message(chat_id=chat_id, text=await get_text(user_id, "error"), reply_to_message_id=reply_to_message_id)
        except Exception:
            pass
        return False'''

content = content.replace(old_except, new_except)

# Same for the ValueError block
old_ve = '''    except ValueError as ve:
        err_key = str(ve)
        if err_key in ["private_video", "timeout", "login_required"]:
            await bot.send_message(chat_id=chat_id, text=await get_text(user_id, err_key), reply_to_message_id=reply_to_message_id)
        else:
            await bot.send_message(chat_id=chat_id, text=await get_text(user_id, "error"), reply_to_message_id=reply_to_message_id)
        return False'''

new_ve = '''    except ValueError as ve:
        err_key = str(ve)
        try:
            if err_key in ["private_video", "timeout", "login_required"]:
                await bot.send_message(chat_id=chat_id, text=await get_text(user_id, err_key), reply_to_message_id=reply_to_message_id)
            else:
                await bot.send_message(chat_id=chat_id, text=await get_text(user_id, "error"), reply_to_message_id=reply_to_message_id)
        except Exception:
            pass
        return False'''

content = content.replace(old_ve, new_ve)

with open('handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)
