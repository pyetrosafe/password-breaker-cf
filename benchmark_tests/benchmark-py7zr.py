import py7zr
import subprocess
import time
import os

def criar_arquivo_teste(file_path, senha):
    """Cria um arquivo 7z de teste com senha."""
    if os.path.exists(file_path):
        return
    print(f"Criando arquivo de teste '{file_path}' com senha {senha}...")
    text_file = 'documento.txt'
    with open(text_file, "w") as f:
        f.write("Este é um teste de conteúdo para o benchmark.")
    try:
        # Usa a biblioteca para criar o arquivo com senha
        with py7zr.SevenZipFile(file_path, 'x', password=senha) as archive:
            archive.set_encrypted_header(True)
            archive.write(text_file)

        print("Arquivo de teste criado.\n")
    except Exception as e:
        print(f"Erro ao criar arquivo de teste: {e}")
    finally:
        if os.path.exists(text_file):
            os.remove(text_file)

def teste_com_subprocess(file_path, senha):
    """Testa a senha usando o executável 7z via subprocess."""
    try:
        command = ['7z', 't', f'-p{senha}', '-y', file_path]
        # resultado = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        resultado = subprocess.run(command, capture_output=True, text=True)
        if (resultado.returncode != 0):
            print(f"Resultado com subprocess: FALHA (Correto) ({resultado.stderr.strip()})") if DEBUG_METHODS else None
        return resultado.returncode == 0
    except Exception as e:
        print(f"Resultado com subprocess: FALHA (Correto) ({type(e).__name__}: {e})") if DEBUG_METHODS else None
        return False

def teste_com_py7zr(file_path, senha):
    """Testa a senha usando o método .testzip() da biblioteca py7zr."""
    try:
        with py7zr.SevenZipFile(file_path, 'r', password=senha) as archive:
            archive.testzip()
        return True
    except Exception as e:
        # Qualquer erro (senha errada, ficheiro corrompido, etc.) será capturado aqui.
        print(f"Resultado com .testzip(): FALHA (Correto) ({type(e).__name__}: {e})") if DEBUG_METHODS else None
        return False

# --- Início do Teste de Performance ---
NUM_TENTATIVAS = 100
SENHA_CORRETA = '1234'
ARQUIVO = 'benchmark.7z'
DEBUG_METHODS = False
DEBUG_FOR = False

criar_arquivo_teste(ARQUIVO, SENHA_CORRETA)

print(f"--- Testando performance com {NUM_TENTATIVAS} senhas erradas ---")

# Teste com subprocess
start_time = time.time()
for i in range(NUM_TENTATIVAS):
    res = teste_com_subprocess(ARQUIVO, f"senha_errada_{i}")
if DEBUG_FOR:
    if (res):
        print("Resultado com subprocess: SUCESSO (Incorreto). Método falhou em detectar senha errada.")
    else:
        print("Resultado com subprocess: FALHA (Correto).")
end_time = time.time()
diff_time_1 = end_time - start_time
print(f"Tempo com subprocess ('7z t'): {diff_time_1:.4f} segundos")

print('')

# Teste com py7zr
start_time = time.time()
for i in range(NUM_TENTATIVAS):
    res = teste_com_py7zr(ARQUIVO, f"senha_errada_{i}")
if DEBUG_FOR:
    if (res):
        print("Resultado com .testzip(): SUCESSO (Incorreto). Método falhou em detectar senha errada.")
    else:
        print("Resultado com subprocess: FALHA (Correto).")
end_time = time.time()
diff_time_2 = end_time - start_time
print(f"Tempo com py7zr (.testzip()): {diff_time_2:.4f} segundos")

if diff_time_1 < diff_time_2:
    print(f"\nConclusão: O método subprocess continua a ser o mais rápido, ~{diff_time_2/diff_time_1:.2f}x.")
else:
    print(f"\nConclusão: A biblioteca py7zr foi surpreendentemente mais rápida, ~{diff_time_1/diff_time_2:.2f}x.")

# Limpeza
if os.path.exists(ARQUIVO):
    os.remove(ARQUIVO)
