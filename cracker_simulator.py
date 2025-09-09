import zipfile
import time
import sys

def testar_senha_zip(arquivo_zip, wordlist):
    """
    Função que simula um teste de força de senha em um arquivo .zip
    usando uma wordlist.

    Args:
        arquivo_zip (str): O caminho para o arquivo .zip.
        wordlist (str): O caminho para o arquivo com a wordlist.
    """
    print("Iniciando simulação de teste de força de senha...")
    print("-" * 40)

    try:
        with zipfile.ZipFile(arquivo_zip, 'r') as zip_file:
            with open(wordlist, 'r', encoding='utf-8', errors='ignore') as f:
                tentativas = 0
                inicio = time.time()  # Marca o tempo de início do processo

                for linha in f:
                    senha = linha.strip()  # Remove espaços e quebras de linha
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
                        print(f"[FALHA] Tentativa {tentativas}: {senha}")

    except FileNotFoundError:
        print(f"Erro: O arquivo .zip '{arquivo_zip}' ou a wordlist não foram encontrados.")
        return False
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
        return False

    print("\n[FALHA] A senha não foi encontrada na wordlist.")
    return False

# ----- Configurações e Verificação de Argumentos -----

# Verifica se o nome do arquivo .zip foi passado como argumento
if len(sys.argv) < 2:
    print("Uso: python cracker_simulador.py <nome_do_arquivo.zip>")
    sys.exit(1) # Encerra o programa com um código de erro

nome_arquivo_zip = sys.argv[1] # Pega o primeiro argumento da linha de comando
nome_wordlist = "wordlist.txt" # O nome da wordlist continua fixo

# Chama a função para iniciar a simulação
testar_senha_zip(nome_arquivo_zip, nome_wordlist)