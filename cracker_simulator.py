import zipfile
import time

def testar_senha_zip(arquivo_zip, wordlist):
    """
    Função que simula um ataque de força bruta em um arquivo .zip
    usando uma wordlist.

    Args:
        arquivo_zip (str): O caminho para o arquivo .zip.
        wordlist (str): O caminho para o arquivo com a wordlist.
    """
    # Exibe uma mensagem de início
    print("Iniciando simulação de teste de força de senha...")
    print("-" * 40)

    # Abre o arquivo zip no modo de leitura
    with zipfile.ZipFile(arquivo_zip, 'r') as zip_file:
        # Abre o arquivo da wordlist
        with open(wordlist, 'r', encoding='utf-8', errors='ignore') as f:
            tentativas = 0
            inicio = time.time()  # Marca o tempo de início do processo

            # Itera sobre cada linha (senha) da wordlist
            for linha in f:
                senha = linha.strip()  # Remove espaços e quebras de linha
                tentativas += 1

                try:
                    # Tenta extrair um arquivo do zip com a senha
                    zip_file.extractall(pwd=senha.encode('utf-8'))

                    # Se a extração for bem-sucedida, a senha foi encontrada
                    fim = time.time()  # Marca o tempo de fim
                    tempo_total = fim - inicio

                    print(f"\n[SUCESSO] Senha encontrada: {senha}")
                    print(f"Tentativas: {tentativas}")
                    print(f"Tempo gasto: {tempo_total:.2f} segundos")
                    print("-" * 40)

                    # Para o loop, pois a senha já foi encontrada
                    return True
                except (RuntimeError, zipfile.BadZipFile):
                    # Se a senha estiver errada, continua para a próxima
                    print(f"[FALHA] Tentativa {tentativas}: {senha}")

            # Se o loop terminar e a senha não for encontrada
            print("\n[FALHA] A senha não foi encontrada na wordlist.")
            return False

# ----- Configurações para a Demonstração -----
nome_arquivo_zip = "seu_arquivo.zip"  # Mude para o nome do seu arquivo .zip
nome_wordlist = "wordlist.txt"

# Chama a função para iniciar a simulação
testar_senha_zip(nome_arquivo_zip, nome_wordlist)