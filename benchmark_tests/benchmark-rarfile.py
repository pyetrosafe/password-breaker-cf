import rarfile
import subprocess
import time
import os

def criar_arquivo_teste(file_path, senha):
    """Cria um arquivo rar de teste com senha."""
    if os.path.exists(file_path):
        return
    print(f"Criando arquivo de teste '{file_path}' com senha {senha}...")
    text_file = 'documento.txt'
    with open(text_file, "w") as f:
        f.write("Este é um teste de conteúdo para o benchmark.")
    try:
        # Usa processo para criar o arquivo com senha
        command = ['rar', 'a', f'-hp{senha}', '-y', file_path, text_file]
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print("Arquivo de teste criado.\n")
    except Exception as e:
        print(f"Erro ao criar arquivo de teste: {e}")
    finally:
        if os.path.exists(text_file):
            os.remove(text_file)

def teste_com_subprocess(file_path, senha):
    """Testa a senha usando o executável unrar via subprocess."""
    try:
        command = ['unrar', 't', f'-p{senha}', '-y', file_path]
        # resultado = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        resultado = subprocess.run(command, capture_output=True, text=True)
        if (resultado.returncode != 0):
            print(f"Resultado com subprocess: FALHA (Correto) ({resultado.stderr.strip()})") if DEBUG_METHODS else None
        return resultado.returncode == 0
    except Exception as e:
        print(f"Resultado com subprocess: FALHA (Correto) ({type(e).__name__}: {e})") if DEBUG_METHODS else None
        return False

def teste_com_unrar(file_path, senha):
    """Testa a senha usando o método .testzip() da biblioteca unrar."""
    try:
        with rarfile.RarFile(file_path, 'r') as archive:
            needs_password = archive.needs_password()
            archive.setpassword(senha)
            archive.testrar()
        return True
    except rarfile.NoCrypto:
        return needs_password
    except Exception as e:
        # Qualquer erro (senha errada, ficheiro corrompido, etc.) será capturado aqui.
        print(f"Resultado com .testrar(): FALHA (Correto) ({type(e).__name__}: {e})") if DEBUG_METHODS else None
        return False

# --- Início do Teste de Performance ---
NUM_TENTATIVAS = 100
SENHA_CORRETA = '1234'
ARQUIVO = 'benchmark.rar'
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
print(f"Tempo com subprocess (unrar t): {diff_time_1:.4f} segundos")

print('')

# Teste com unrar
start_time = time.time()
for i in range(NUM_TENTATIVAS):
    res = teste_com_unrar(ARQUIVO, f"senha_errada_{i}")
if DEBUG_FOR:
    if (res):
        print("Resultado com .testrar(): SUCESSO (Incorreto). Método falhou em detectar senha errada.")
    else:
        print("Resultado com .testrar(): FALHA (Correto).")
end_time = time.time()
diff_time_2 = end_time - start_time
print(f"Tempo com rarfile (.testrar()): {diff_time_2:.4f} segundos")

if diff_time_1 < diff_time_2:
    print(f"\nConclusão: O método subprocess continua a ser o mais rápido, ~{diff_time_2/diff_time_1:.2f}x.")
else:
    print(f"\nConclusão: A biblioteca rarfile foi surpreendentemente mais rápida, ~{diff_time_1/diff_time_2:.2f}x.")

# Limpeza
if os.path.exists(ARQUIVO):
    os.remove(ARQUIVO)
