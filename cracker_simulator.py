import zipfile
import time
import sys
import itertools
import string
import argparse
from tqdm import tqdm

def calcular_total_possibilidades(min_len, max_len, charset):
    """Calcula o número total de combinações a serem testadas."""
    total = 0
    for comprimento in range(min_len, max_len + 1):
        total += len(charset) ** comprimento
    return total

def testar_senha_zip_forca_bruta(arquivo_zip, min_len, max_len, charset):
    """
    Função que simula um ataque de força bruta pura em um arquivo .zip
    gerando senhas e exibindo uma barra de progresso.
    """
    total_possibilidades = calcular_total_possibilidades(min_len, max_len, charset)

    print(f"Iniciando simulação para o arquivo '{arquivo_zip}'...")
    print(f"Conjunto de caracteres: {len(charset)} opções")
    print(f"Comprimento da senha: de {min_len} a {max_len} caracteres")
    print("-" * 40)

    try:
        with zipfile.ZipFile(arquivo_zip, 'r') as zip_file:
            tentativas = 0
            inicio = time.time()

            # Usa tqdm para envolver o loop e criar a barra de progresso
            for comprimento in range(min_len, max_len + 1):
                # O total para a barra de progresso agora é o total de possibilidades
                # para o comprimento atual
                total_atual = len(charset) ** comprimento

                # O loop com tqdm
                for combinacao in tqdm(
                    itertools.product(charset, repeat=comprimento),
                    total=total_atual,
                    desc=f"Testando com {comprimento} chars"
                ):
                    senha = "".join(combinacao)
                    tentativas += 1

                    try:
                        zip_file.extractall(pwd=senha.encode('utf-8'))

                        fim = time.time()
                        tempo_total = fim - inicio

                        print("\n" + "-" * 40)
                        print(f"[SUCESSO] Senha encontrada: {senha}")
                        print(f"Tentativas: {tentativas}")
                        print(f"Tempo total gasto: {tempo_total:.2f} segundos")
                        print("-" * 40)

                        return True
                    except (RuntimeError, zipfile.BadZipFile):
                        continue # Continua se a senha estiver errada

    except FileNotFoundError:
        print(f"\nErro: O arquivo .zip '{arquivo_zip}' não foi encontrado.")
        return False
    except Exception as e:
        print(f"\nOcorreu um erro: {e}")
        return False

    print(f"\n[FALHA] A senha não foi encontrada após {tentativas} tentativas.")
    return False

# ----- Configurações e Análise de Argumentos (usando argparse) -----
def main():
    parser = argparse.ArgumentParser(
        description="Simulador de teste de força de senha para arquivos .zip."
    )

    parser.add_argument("arquivo_zip", help="O caminho para o arquivo .zip.")

    parser.add_argument("-min", "--min_len", type=int, default=1,
                        help="Comprimento mínimo da senha (padrão: 1).")
    parser.add_argument("-max", "--max_len", type=int, default=4,
                        help="Comprimento máximo da senha (padrão: 4).")

    # Argumentos para o conjunto de caracteres
    parser.add_argument("-w", "--word", action="store_true",
                        help="Testar apenas letras.")
    parser.add_argument("-d", "--digits", action="store_true",
                        help="Testar apenas dígitos.")
    parser.add_argument("-s", "--symbols", action="store_true",
                        help="Testar apenas símbolos.")
    parser.add_argument("-a", "--alphanum", action="store_true",
                        help="Testar caracteres alfanuméricos.")

    args = parser.parse_args()

    charset = ""

    # Lógica para construir o conjunto de caracteres com base nos argumentos
    if args.word:
        charset = string.ascii_letters
    elif args.digits:
        charset = string.digits
    elif args.symbols:
        charset = string.punctuation
    elif args.alphanum:
        charset = string.ascii_letters + string.digits
    else: # Padrão se nenhum argumento for fornecido
        charset = string.ascii_letters + string.digits + string.punctuation

    testar_senha_zip_forca_bruta(args.arquivo_zip, args.min_len, args.max_len, charset)

if __name__ == "__main__":
    main()