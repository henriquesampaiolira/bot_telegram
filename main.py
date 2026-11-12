import os
import json
import re
import telebot
from flask import Flask, request

TOKEN = os.environ.get('TOKEN')

if not TOKEN:
    raise ValueError("A variável de ambiente TOKEN não foi encontrada!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Ficheiros locais para persistência no Render (ou ajuste conforme usava)
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
    return "Bot Multi-usuário de Promoções Rodando com Sucesso!"

# Rota dinâmica do Webhook que aceita exatamente o seu token (evita o erro 404)
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        print(f"Erro ao processar update: {e}")
        return "Error", 400

# --- COMANDOS NO CHAT PRIVADO ---

@bot.message_handler(commands=['start'])
def cmd_start(message):
    if message.chat.type != 'private':
        return
    bot.reply_to(
        message, 
        "👋 Olá! Sou o seu bot de monitorização de promoções.\n\n"
        "Comandos disponíveis:\n"
        "• `/adicionar <termo>` - Adiciona um termo para monitorizar\n"
        "• `/remover <termo>` - Remove um termo\n"
        "• `/listar` - Mostra os seus termos guardados\n"
        "• `/grupos` - Lista os grupos ativos"
    )

@bot.message_handler(commands=['adicionar'])
def cmd_adicionar(message):
    if message.chat.type != 'private':
        return
    
    user_id = str(message.from_user.id)
    texto = message.text.replace('/adicionar', '').strip()
    
    if not texto:
        bot.reply_to(message, "⚠️ Por favor, escreva o termo que deseja adicionar. Exemplo: `/adicionar monitor 27`")
        return
        
    dados = carregar_dados()
    if user_id not in dados["termos"]:
        dados["termos"][user_id] = []
        
    if texto.lower() in [t.lower() for t in dados["termos"][user_id]]:
        bot.reply_to(message, f"⚠️ O termo *{texto}* já consta na sua lista.")
    else:
        dados["termos"][user_id].append(texto)
        salvar_dados(dados)
        bot.reply_to(message, f"✅ Termo *{texto}* adicionado com sucesso à sua lista de monitorização!")

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
            bot.reply_to(message, f"🗑️ Termo *{texto}* removido com sucesso.")
        else:
            bot.reply_to(message, "⚠️ O termo especificado não foi encontrado na sua lista.")
    else:
        bot.reply_to(message, "⚠️ Nenhum termo especificado ou lista vazia.")

@bot.message_handler(commands=['listar'])
def cmd_listar(message):
    if message.chat.type != 'private':
        return
        
    user_id = str(message.from_user.id)
    dados = carregar_dados()
    termos = dados["termos"].get(user_id, [])
    
    if not termos:
        bot.reply_to(message, "📝 A sua lista de monitorização está vazia. Use `/adicionar <termo>` para incluir produtos.")
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
        bot.reply_to(message, "📂 O bot ainda não está registado em nenhum grupo.")
    else:
        bot.reply_to(message, f"📂 O bot está ativo em {len(grupos)} grupo(s).")

# Monitorização de mensagens nos grupos
@bot.message_handler(content_types=['text'])
def monitorar_mensagens(message):
    if message.chat.type in ['group', 'supergroup']:
        dados = carregar_dados()
        chat_id = message.chat.id
        
        # Regista o grupo automaticamente se ainda não estiver guardado
        if chat_id not in dados["grupos"]:
            dados["grupos"].append(chat_id)
            salvar_dados(dados)
            
        # Varrimento de texto usando regex para encontrar correspondências com os termos dos utilizadores
        texto_msg = message.text.lower()
        
        for user_id, termos in dados["termos"].items():
            for termo in termos:
                # Usa regex (\b) para garantir correspondência exata de palavras/termos
                padrao = r'\b' + re.escape(termo.lower()) + r'\b'
                if re.search(padrao, texto_msg):
                    try:
                        bot.send_message(
                            int(user_id), 
                            f"🚨 **Promoção Encontrada!**\n\n"
                            f"🔍 Termo detetado: *{termo}*\n"
                            f"💬 Grupo: {message.chat.title}\n\n"
                            f"Mensagem:\n_{message.text}_", 
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        print(f"Erro ao enviar alerta para o utilizador {user_id}: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
