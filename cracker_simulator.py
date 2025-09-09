import zipfile
import time
import sys
import itertools
import string

def testar_senha_zip_forca_bruta(arquivo_zip, max_comprimento=4):
    """
    Função que simula um ataque de força bruta pura em um arquivo .zip
    gerando senhas aleatoriamente.

    Args:
        arquivo_zip (str): O caminho para o arquivo .zip.
        max_comprimento (int): O comprimento máximo das senhas a serem testadas.
    """
    # Conjunto de caracteres a serem usados na geração de senhas
    caracteres = string.ascii_letters + string.digits  # Letras (a-z, A-Z) e números (0-9)

    print(f"Iniciando simulação de força bruta para o arquivo '{arquivo_zip}'...")
    print(f"Testando senhas com até {max_comprimento} caracteres.")
    print("-" * 40)

    try:
        with zipfile.ZipFile(arquivo_zip, 'r') as zip_file:
            tentativas = 0
            inicio = time.time()  # Marca o tempo de início do processo

            # Itera sobre o comprimento das senhas, de 1 até o comprimento máximo
            for comprimento in range(1, max_comprimento + 1):
                # Usa itertools.product para gerar todas as combinações
                # Exemplo: para comprimento=2, gera 'aa', 'ab', 'ac', etc.
                for combinacao in itertools.product(caracteres, repeat=comprimento):
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
                        # Se a senha estiver errada, continua para a próxima
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

# ----- Configurações e Verificação de Argumentos -----
if len(sys.argv) < 2:
    print("Uso: python cracker_simulador.py <nome_do_arquivo.zip> [comprimento_maximo]")
    sys.exit(1)

nome_arquivo_zip = sys.argv[1]
# Se um segundo argumento for fornecido, ele define o comprimento máximo
max_comprimento = int(sys.argv[2]) if len(sys.argv) > 2 else 4

# Chama a função para iniciar a simulação
testar_senha_zip_forca_bruta(nome_arquivo_zip, max_comprimento)