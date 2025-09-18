import py7zr
import os

def criar_arquivo_teste(file_path, senha, encrypted_header=True):
    """Cria um arquivo 7z de teste com senha."""
    if os.path.exists(file_path):
        return
    print(f"Criando arquivo de teste '{file_path}' com senha {senha}...")
    text_file = 'documento.txt'
    with open(text_file, "w") as f:
        f.write("Este é um teste de conteúdo para o benchmark.")
    try:
        # Usa a biblioteca para criar o arquivo com senha
        with py7zr.SevenZipFile(file_path, 'w', password=senha) as archive:
            archive.set_encrypted_header(encrypted_header)
            archive.write(text_file)

        print("Arquivo de teste criado.\n")
    finally:
        if os.path.exists(text_file):
            os.remove(text_file)

def teste_com_py7zr(file_path, senha, metodo='test'):
    """Testa a senha usando a biblioteca py7zr."""
    try:

        print(f"\nTeste com .{metodo}() e senha {'errada' if senha == SENHA_ERRADA else 'certa'}:")

        with py7zr.SevenZipFile(file_path, 'r', password=senha) as archive:
            if metodo == 'list':
                archive.list()
            elif metodo == 'test':
                archive.test()
            elif metodo == 'testzip':
                archive.testzip()  # Força a leitura dos dados encriptados
            elif metodo == 'read':
                files = archive.getnames()
                archive.read([files[0]])  # Força a leitura dos dados encriptados
            else:
                raise ValueError("Método desconhecido.")

        if (senha == SENHA_ERRADA):
            print(f">>> Resultado com .{metodo}(): SUCESSO (Incorreto)")
        else:
            print(f">>> Resultado com .{metodo}(): SUCESSO (Correto)")
    except Exception as e:
        if (senha == SENHA_ERRADA or metodo == 'read'):
            print(f">>> Resultado com .{metodo}(): FALHA (Correto) ({type(e).__name__}: {e})")
        else:
            print(f">>> Resultado com .{metodo}(): FALHA (Incorreto) ({type(e).__name__}: {e})")

SENHA_CORRETA = '1234'
SENHA_ERRADA = '4321'
ARQUIVO_HEADER_ENCRYPTED = 'benchmark_test_read_header.7z'
ARQUIVO_HEADER_NOT_ENCRYPTED = 'benchmark_test_read.7z'

# --- Crie um arquivo de teste ---
criar_arquivo_teste(ARQUIVO_HEADER_ENCRYPTED, SENHA_CORRETA)
criar_arquivo_teste(ARQUIVO_HEADER_NOT_ENCRYPTED, SENHA_CORRETA, False)
# --------------------------------

metodos = ['list', 'test', 'testzip', 'read']

print("--- TESTANDO ARQUIVO COM HEADER CODIFICADO ---\n")

print("--- Tentando verificar com uma senha ERRADA ---")

for metodo in metodos:
    teste_com_py7zr(ARQUIVO_HEADER_ENCRYPTED, SENHA_ERRADA, metodo=metodo)

print("\n--- Tentando verificar com uma senha CORRETA ---")

for metodo in metodos:
    teste_com_py7zr(ARQUIVO_HEADER_ENCRYPTED, SENHA_CORRETA, metodo=metodo)


print("\n\n--- TESTANDO ARQUIVO COM HEADER NÃO CODIFICADO ---\n")

print("--- Tentando verificar com uma senha ERRADA ---")

for metodo in metodos:
    teste_com_py7zr(ARQUIVO_HEADER_NOT_ENCRYPTED, SENHA_ERRADA, metodo=metodo)

print("\n--- Tentando verificar com uma senha CORRETA ---")

for metodo in metodos:
    teste_com_py7zr(ARQUIVO_HEADER_NOT_ENCRYPTED, SENHA_CORRETA, metodo=metodo)

# Limpeza
os.remove(ARQUIVO_HEADER_ENCRYPTED)
os.remove(ARQUIVO_HEADER_NOT_ENCRYPTED)