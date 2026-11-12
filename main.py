import json
import os
import re
import telebot
from flask import Flask, request

TOKEN = os.environ.get("TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

ARQUIVO_USUARIOS = "usuarios.json"


# Carrega as listas de palavras de todos os usuários
def carregar_dados():
  if os.path.exists(ARQUIVO_USUARIOS):
    with open(ARQUIVO_USUARIOS, "r", encoding="utf-8") as f:
      return json.load(f)
  return {}


def salvar_dados(dados):
  with open(ARQUIVO_USUARIOS, "w", encoding="utf-8") as f:
    json.dump(dados, f, ensure_ascii=False, indent=4)


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
  json_string = request.get_data().decode("utf-8")
  update = telebot.types.Update.de_json(json_string)
  bot.process_new_updates([update])
  return "!", 200


@app.route("/")
def index():
  return "Bot Multi-usuário de Promoções Rodando!", 200


# --- COMANDOS DO BOT (Privado para cada usuário) ---


@bot.message_handler(commands=["adicionar"])
def cmd_adicionar(message):
  if message.chat.type != "private":
    return

  user_id = str(message.from_user.id)
  termo = message.text.replace("/adicionar", "").strip().lower()

  if not termo:
    bot.reply_to(
        message,
        "⚠️ Digite o termo que deseja adicionar.\nExemplo: `/adicionar"
        " monitor 27`",
        parse_mode="Markdown",
    )
    return

  dados = carregar_dados()
  if user_id not in dados:
    dados[user_id] = []

  if termo not in dados[user_id]:
    dados[user_id].append(termo)
    salvar_dados(dados)
    bot.reply_to(message, f"✅ Termo adicionado à sua lista: `{termo}`")
  else:
    bot.reply_to(message, f"⚠️ O termo `{termo}` já está na sua lista.")


@bot.message_handler(commands=["remover"])
def cmd_remover(message):
  if message.chat.type != "private":
    return

  user_id = str(message.from_user.id)
  termo = message.text.replace("/remover", "").strip().lower()

  dados = carregar_dados()
  if user_id in dados and termo in dados[user_id]:
    dados[user_id].remove(termo)
    salvar_dados(dados)
    bot.reply_to(message, f"🗑️ Termo removido com sucesso: `{termo}`")
  else:
    bot.reply_to(
        message,
        "❌ Termo não encontrado na sua lista. Use `/listar` para ver os"
        " salvos.",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["listar"])
def cmd_listar(message):
  if message.chat.type != "private":
    return

  user_id = str(message.from_user.id)
  dados = carregar_dados()
  palavras = dados.get(user_id, [])

  if not palavras:
    bot.reply_to(
        message,
        "Sua lista de termos está vazia. Use `/adicionar <termo>` para incluir.",
        parse_mode="Markdown",
    )
  else:
    texto = "📋 **Seus Termos Monitorados:**\n\n"
    for i, p in enumerate(palavras, 1):
      texto += f"{i}. `{p}`\n"
    bot.reply_to(message, texto, parse_mode="Markdown")


# --- MONITORAMENTO DOS GRUPOS COM BUSCA INTELIGENTE ---


@bot.message_handler(func=lambda message: True)
def filtrar_promocoes(message):
  if message.chat.type == "private":
    return

  texto_original = message.text if message.text else ""
  # Limpeza inteligente: substitui pontuações (vírgulas, hífens, pontos) por espaços e padroniza minúsculas
  texto_limpo = re.sub(r"[^\w\s]", " ", texto_original).lower()

  dados = carregar_dados()
  if not dados:
    return

  # Varre todos os usuários cadastrados no bot
  for user_id, palavras in dados.items():
    for termo in palavras:
      partes = termo.lower().split()
      # Verifica se todas as partes do termo aparecem no texto limpo (independente de vírgulas)
      if all(parte in texto_limpo for parte in partes):
        aviso = (
            f"🚨 **PROMOÇÃO ENCONTRADA!** 🚨\n\n"
            f"💬 **Grupo:** {message.chat.title}\n"
            f"🔍 **Seu Termo:** `{termo}`\n\n"
            f"📄 **Mensagem Original:**\n{texto_original}"
        )
        try:
          bot.send_message(int(user_id), aviso, parse_mode="Markdown")
        except Exception:
          pass
        break


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)