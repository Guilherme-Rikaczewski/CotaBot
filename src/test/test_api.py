import requests
import time
import csv
import os
from datetime import datetime

ARQUIVO_HISTORICO = "historico.csv"
INTERVALO_SEGUNDOS = 300  # 5 minutos

def pegar_cotacao(par):
    """Busca a cotação atual na AwesomeAPI."""
    url = f"https://economia.awesomeapi.com.br/json/last/{par}"
    resp = requests.get(url, timeout=10)
    dados = resp.json()[par.replace("-", "")]
    return {
        "par": par,
        "valor": float(dados["bid"]),
        "variacao": dados["pctChange"],
        "data": dados["create_date"],
    }

def salvar_historico(cotacao):
    """Guarda a cotação no arquivo CSV."""
    arquivo_novo = not os.path.exists(ARQUIVO_HISTORICO)
    with open(ARQUIVO_HISTORICO, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if arquivo_novo:
            writer.writerow(["data", "par", "valor", "variacao"])
        writer.writerow([cotacao["data"], cotacao["par"],
                         cotacao["valor"], cotacao["variacao"]])

def main():
    # Usuário digita a moeda e o valor alvo
    par = input("Digite o par de moedas (ex.: USD-BRL, EUR-BRL, BTC-BRL): ").strip().upper()
    valor_alvo = float(input("Digite o valor que você quer ser avisado: "))

    print(f"\n🟢 Monitorando {par} a cada 5 minutos. Alvo: R$ {valor_alvo:.2f}")
    print("Pressione Ctrl+C para parar.\n")

    avisado = False  # evita repetir a mensagem

    while True:
        try:
            cotacao = pegar_cotacao(par)
            salvar_historico(cotacao)

            agora = datetime.now().strftime('%H:%M:%S')
            print(f"[{agora}] {par}: R$ {cotacao['valor']:.2f} | Variação: {cotacao['variacao']}%")

            # Verifica se atingiu o alvo (e ainda não avisou)
            if not avisado and cotacao["valor"] >= valor_alvo:
                print(f"\n🚨 ATINGIU O VALOR DESEJADO!")
                print(f"   {par} está em R$ {cotacao['valor']:.2f} (alvo: R$ {valor_alvo:.2f})\n")
                avisado = True

        except Exception as erro:
            print(f"⚠️ Erro: {erro}")

        time.sleep(INTERVALO_SEGUNDOS)

if __name__ == "__main__":
    main()