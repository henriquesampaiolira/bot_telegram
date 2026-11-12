import os
import json
import re
import telebot
from flask import Flask, request

TOKEN = os.environ.get('TOKEN')

if not TOKEN:
    raise ValueError("A variável de ambiente TOKEN não foi encontrada!")

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

ARQUIVO_DADOS = 'dados_bot.json'

def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"termos": {}, "grupos": []}

def salvar_dados(dados):
    with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    return "Bot de Promoções a funcionar perfeitamente!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Forbidden', 403

@app.errorhandler(404)
def page_not_found(e):
    return "Rota não encontrada", 404

@bot.message_handler(commands=['start'])
def cmd_start(message):
    if message.chat.type != 'private':
        return
    bot.reply_to(
        message, 
        "👋 Olá! O bot de monitoramento de promoções está online.\n\n"
        "Comandos disponíveis:\n"
        "• `/adicionar <termo>`\n"
        "• `/remover <termo>`\n"
        "• `/listar`\n"
        "• `/grupos`"
    )

@bot.message_handler(commands=['adicionar'])
def cmd_adicionar(message):
    if message.chat.type != 'private':
        return
    user_id = str(message.from_user.id)
    texto = message.text.replace('/adicionar', '').strip()
    if not texto:
        bot.reply_to(message, "⚠️ Escreva o termo. Exemplo: `/adicionar monitor 27`")
        return
    dados = carregar_dados()
    if user_id not in dados["termos"]:
        dados["termos"][user_id] = []
    if texto.lower() in [t.lower() for t in dados["termos"][user_id]]:
        bot.reply_to(message, f"⚠️ O termo *{texto}* já está na lista.")
    else:
        dados["termos"][user_id].append(texto)
        salvar_dados(dados)
        bot.reply_to(message, f"✅ Termo *{texto}* adicionado com sucesso!")

@bot.message_handler(commands=['remover'])
def cmd_remover(message):
    if message.chat.type != 'private':
        return
    user_id = str(message.from_user.id)
    texto = message.text.replace('/remover', '').strip()
    dados = carregar_dados()
    if user_id in dados["termos"] and texto:
        lista_antes = len(dados["termos"][user_id])
        dados["termos"][user_id] = [t for t in dados["termos"][user_id] if t.lower() != texto.lower()]
        if len(dados["termos"][user_id]) < lista_antes:
            salvar_dados(dados)
            bot.reply_to(message, f"🗑️ Termo *{texto}* removido.")
        else:
            bot.reply_to(message, "⚠️ Termo não encontrado na lista.")
    else:
        bot.reply_to(message, "⚠️ Lista vazia ou termo inválido.")

@bot.message_handler(commands=['listar'])
def cmd_listar(message):
    if message.chat.type != 'private':
        return
    user_id = str(message.from_user.id)
    dados = carregar_dados()
    termos = dados["termos"].get(user_id, [])
    if not termos:
        bot.reply_to(message, "📝 A sua lista está vazia. Use `/adicionar <termo>`.")
    else:
        lista_str = "\n".join([f"• {t}" for t in termos])
        bot.reply_to(message, f"📝 **Os seus termos monitorizados:**\n\n{lista_str}", parse_mode='Markdown')

@bot.message_handler(commands=['grupos'])
def cmd_grupos(message):
    if message.chat.type != 'private':
        return
    dados = carregar_dados()
    grupos = dados["grupos"]
    if not grupos:
        bot.reply_to(message, "📂 O bot ainda não registou nenhum grupo.")
    else:
        bot.reply_to(message, f"📂 Ativo em {len(grupos)} grupo(s).")

@bot.message_handler(content_types=['text'])
def monitorar_mensagens(message):
    if message.chat.type in ['group', 'supergroup']:
        dados = carregar_dados()
        chat_id = message.chat.id
        if chat_id not in dados["grupos"]:
            dados["grupos"].append(chat_id)
            salvar_dados(dados)
        texto_msg = message.text.lower()
        for user_id, termos in dados["termos"].items():
            for termo in termos:
                padrao = r'\b' + re.escape(termo.lower()) + r'\b'
                if re.search(padrao, texto_msg):
                    try:
                        bot.send_message(
                            int(user_id), 
                            f"🚨 **Promoção Encontrada!**\n\n"
                            f"🔍 Termo: *{termo}*\n"
                            f"💬 Grupo: {message.chat.title}\n\n"
                            f"_{message.text}_", 
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        print(f"Erro ao enviar alerta: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
