# -*- coding: utf-8 -*-

import zipfile
import time
import itertools
import string
import argparse
from tqdm import tqdm

# A função testar_senha_zip_forca_bruta continua exatamente a mesma da versão anterior.
# Não há necessidade de alterá-la.
def testar_senha_zip_forca_bruta(arquivo_zip: str, min_len: int, max_len: int, charset: str) -> bool:
    """
    Função que simula um ataque de força bruta em um arquivo .zip,
    gerando senhas e exibindo uma barra de progresso.
    """
    print(f"Iniciando simulação para o ficheiro '{arquivo_zip}'...")
    print(f"Conjunto de caracteres: {len(charset)} opções ({charset[:40]}...)")
    print(f"Comprimento da senha: de {min_len} a {max_len} caracteres")
    print("-" * 50)

    try:
        with zipfile.ZipFile(arquivo_zip, 'r') as zip_file:
            tentativas = 0
            inicio = time.time()

            for comprimento in range(min_len, max_len + 1):
                total_combinacoes_atuais = len(charset) ** comprimento
                combinacoes = itertools.product(charset, repeat=comprimento)

                for combinacao in tqdm(combinacoes, total=total_combinacoes_atuais, desc=f"Testando com {comprimento} chars", unit="pwd"):
                    senha = "".join(combinacao)
                    tentativas += 1

                    try:
                        zip_file.extractall(pwd=senha.encode('utf-8'))
                        fim = time.time()
                        tempo_total = fim - inicio

                        print("\n" + "-" * 50)
                        print(f"[SUCESSO] Senha encontrada: {senha}")
                        print(f"Total de tentativas: {tentativas}")
                        print(f"Tempo total gasto: {tempo_total:.2f} segundos")
                        print("-" * 50)

                        return True

                    except (RuntimeError, zipfile.BadZipFile):
                        continue

            print(f"\n[FALHA] A senha não foi encontrada após {tentativas} tentativas.")
            return False

    except FileNotFoundError:
        print(f"\n[ERRO] O ficheiro .zip '{arquivo_zip}' não foi encontrado.")
        return False
    except Exception as e:
        print(f"\n[ERRO] Ocorreu um erro inesperado: {e}")
        return False

def main() -> None:
    """
    Função principal que configura o script, analisa os argumentos da linha de comando
    e inicia o processo de teste de senha.
    """
    parser = argparse.ArgumentParser(
        description="Simulador de teste de força de senha para ficheiros .zip.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("arquivo_zip", help="O caminho para o ficheiro .zip.")
    parser.add_argument("-min", "--min_len", type=int, default=1, help="Comprimento mínimo da senha (padrão: 1).")
    parser.add_argument("-max", "--max_len", type=int, default=8, help="Comprimento máximo da senha (padrão: 8).")

    # --- ARGUMENTOS ATUALIZADOS ---
    # Argumentos de atalho (reintegrados)
    parser.add_argument("-w", "--word", action="store_true", help="Atalho para incluir todas as letras (maiúsculas e minúsculas).")
    parser.add_argument("-a", "--alphanum", action="store_true", help="Atalho para incluir letras e dígitos.")

    # Argumentos granulares
    parser.add_argument("-l", "--letras", action="store_true", help="Incluir letras minúsculas (a-z).")
    parser.add_argument("-u", "--maiusculas", action="store_true", help="Incluir letras maiúsculas (A-Z).")
    parser.add_argument("-d", "--digitos", action="store_true", help="Incluir dígitos (0-9).")
    parser.add_argument("-s", "--simbolos", action="store_true", help="Incluir símbolos (ex: @, #, $).")

    args = parser.parse_args()

    # --- LÓGICA DE CONSTRUÇÃO DO CONJUNTO DE CARACTERES REFINADA ---
    # Usamos um 'set' para evitar caracteres duplicados ao combinar argumentos
    char_set = set()

    # Processa os atalhos primeiro
    if args.word:
        char_set.update(list(string.ascii_letters)) # Adiciona a-z e A-Z

    if args.alphanum:
        char_set.update(list(string.ascii_letters)) # Adiciona a-z e A-Z
        char_set.update(list(string.digits))       # Adiciona 0-9

    # Processa os argumentos granulares
    if args.letras:
        char_set.update(list(string.ascii_lowercase))
    if args.maiusculas:
        char_set.update(list(string.ascii_uppercase))
    if args.digitos:
        char_set.update(list(string.digits))
    if args.simbolos:
        char_set.update(list(string.punctuation))

    # Se nenhum argumento de conjunto de caracteres for fornecido, usamos o padrão completo
    if not char_set:
        print("Nenhum conjunto de caracteres especificado. Usando o padrão (letras, dígitos e símbolos).")
        char_set.update(list(string.ascii_letters + string.digits + string.punctuation))

    # Converte o set para uma string ordenada para uso na função
    charset = "".join(sorted(list(char_set)))

    testar_senha_zip_forca_bruta(args.arquivo_zip, args.min_len, args.max_len, charset)

if __name__ == "__main__":
    main()