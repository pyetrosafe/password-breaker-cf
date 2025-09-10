import zipfile
import time
import sys
import itertools
import string
import argparse

def testar_senha_zip_forca_bruta(arquivo_zip, min_len, max_len, charset):
    """
    Função que simula um ataque de força bruta pura em um arquivo .zip
    gerando senhas com base nos argumentos fornecidos.

    Args:
        arquivo_zip (str): O caminho para o arquivo .zip.
        min_len (int): O comprimento mínimo das senhas.
        max_len (int): O comprimento máximo das senhas.
        charset (str): O conjunto de caracteres a ser usado na geração.
    """
    print(f"Iniciando simulação de força bruta para o arquivo '{arquivo_zip}'...")
    print(f"Testando senhas de {min_len} a {max_len} caracteres.")
    print("-" * 40)

    try:
        with zipfile.ZipFile(arquivo_zip, 'r') as zip_file:
            tentativas = 0
            inicio = time.time()  # Marca o tempo de início do processo

            # Itera sobre o comprimento das senhas, do mínimo ao máximo
            for comprimento in range(min_len, max_len + 1):
                # Usa itertools.product para gerar todas as combinações
                for combinacao in itertools.product(charset, repeat=comprimento):
                    senha = "".join(combinacao)
                    tentativas += 1

                    try:
                        # Tenta extrair um arquivo do zip com a senha
                        zip_file.extractall(pwd=senha.encode('utf-8'))

                        fim = time.time()  # Marca o tempo de fim
                        tempo_total = fim - inicio

                        print(f"\n[SUCESSO] Senha encontrada: {senha}")
                        print(f"Tentativas: {tentativas}")
                        print(f"Tempo gasto: {tempo_total:.2f} segundos")
                        print("-" * 40)

                        return True
                    except (RuntimeError, zipfile.BadZipFile):
                        # Para manter a tela limpa, mostra o progresso a cada X tentativas
                        if tentativas % 100000 == 0:
                            print(f"--> Tentativas: {tentativas} | Tempo: {time.time() - inicio:.2f}s")

    except FileNotFoundError:
        print(f"Erro: O arquivo .zip '{arquivo_zip}' não foi encontrado.")
        return False
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
        return False

    print(f"\n[FALHA] A senha não foi encontrada após {tentativas} tentativas.")
    return False

# ----- Configurações e Análise de Argumentos (usando argparse) -----
def main():
    """Função principal para analisar argumentos e iniciar o teste."""
    parser = argparse.ArgumentParser(
        description="Simulador de teste de força de senha para arquivos .zip."
    )

    # Argumento obrigatório para o nome do arquivo .zip
    parser.add_argument("arquivo_zip", help="O caminho para o arquivo .zip.")

    # Argumentos para o comprimento da senha
    parser.add_argument("-min", "--min_len", type=int, default=1,
                        help="Comprimento mínimo da senha (padrão: 1).")
    parser.add_argument("-max", "--max_len", type=int, default=4,
                        help="Comprimento máximo da senha (padrão: 4).")

    # Argumentos para o conjunto de caracteres
    parser.add_argument("-w", "--word", action="store_true",
                        help="Testar apenas letras (insensitive).")
    parser.add_argument("-d", "--digits", action="store_true",
                        help="Testar apenas dígitos.")
    parser.add_argument("-s", "--symbols", action="store_true",
                        help="Testar apenas símbolos.")
    parser.add_argument("-a", "--alphanum", action="store_true",
                        help="Testar caracteres alfanuméricos (insensitive).")
    parser.add_argument("-u", "--upper", action="store_true",
                        help="Adiciona letras maiúsculas ao conjunto (-a ou -w).")
    parser.add_argument("-l", "--lower", action="store_true",
                        help="Adiciona letras minúsculas ao conjunto (-a ou -w).")

    args = parser.parse_args()

    # Define o conjunto de caracteres padrão
    charset = string.ascii_letters + string.digits + string.punctuation

    # Lógica para construir o conjunto de caracteres com base nos argumentos
    if args.word or args.alphanum:
        charset = ""
        if args.upper or args.lower:
            if args.upper:
                charset += string.ascii_uppercase
            if args.lower:
                charset += string.ascii_lowercase
        else: # Padrão se não for especificado maiúscula ou minúscula
            charset = string.ascii_letters

        if args.alphanum:
            charset += string.digits

    if args.digits:
        charset = string.digits

    if args.symbols:
        charset = string.punctuation

    # Chama a função principal com os argumentos
    testar_senha_zip_forca_bruta(args.arquivo_zip, args.min_len, args.max_len, charset)

if __name__ == "__main__":
    main()