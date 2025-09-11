# -*- coding: utf-8 -*-

import zipfile
import time
import itertools
import string
import argparse
from tqdm import tqdm
import os
import multiprocessing
import math
import subprocess

try:
    import rarfile
    from rarfile import PasswordRequired
except ImportError:
    rarfile = None
    PasswordRequired = None

# ... (a função testar_senha_rar_subprocess continua a mesma)
def testar_senha_rar_subprocess(file_path: str, senha: str) -> bool:
    command = ['unrar', 't', f'-p{senha}', '-y', file_path]
    try:
        resultado = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return resultado.returncode == 0
    except FileNotFoundError:
        if not getattr(testar_senha_rar_subprocess, 'has_printed_error', False):
            print("\n[ERRO FATAL] O comando 'unrar' não foi encontrado no seu sistema.")
            testar_senha_rar_subprocess.has_printed_error = True
        return False
    except Exception:
        return False

## MODIFICADO: O worker agora é muito mais simples.
## Ele recebe UMA tarefa e retorna o resultado.
def worker(task_args) -> tuple[bool, str | None]:
    time.sleep(0.01)
    """
    Worker que testa UMA senha e retorna se foi bem-sucedido.
    """
    file_path, file_type, senha = task_args
    senha_correta = False

    if file_type == 'zip':
        try:
            # Reabre o ficheiro aqui para segurança entre processos
            with zipfile.ZipFile(file_path, 'r') as zf:
                zf.read(zf.infolist()[0].filename, pwd=senha.encode('utf-8'))
                senha_correta = True
        except Exception:
            senha_correta = False
    elif file_type == 'rar':
        senha_correta = testar_senha_rar_subprocess(file_path, senha)

    if senha_correta:
        return (True, senha)
    return (False, None)

## MODIFICADO: A função agora aceita 'start_step'
def testar_senha_sequencial(file_path: str, file_type: str, min_len: int, max_len: int, charset: str, start_step: int) -> None:
    print("Modo de execução: Sequencial (single-thread)\n")
    inicio = time.time()
    tentativas_totais = 0

    try:
        archive_zip = None
        first_file_zip = None
        if file_type == 'zip':
            archive_zip = zipfile.ZipFile(file_path, 'r')
            if not archive_zip.infolist():
                 print("\n[ERRO] O arquivo ZIP está vazio.")
                 return
            first_file_zip = archive_zip.infolist()[0]

        with archive_zip if archive_zip else open(os.devnull, 'w') as archive:
            for comprimento in range(min_len, max_len + 1):
                combinacoes = itertools.product(charset, repeat=comprimento)
                total_combinacoes = len(charset) ** comprimento

                ## MODIFICADO: Lógica para saltar para o 'step' inicial
                initial_step = 0
                if start_step > 0 and comprimento == min_len:
                    print(f"Saltando para o laço inicial {start_step}...\n")
                    combinacoes = itertools.islice(combinacoes, start_step, None)
                    initial_step = start_step

                ## MODIFICADO: A barra de progresso agora usa o parâmetro 'initial'
                for combinacao in tqdm(combinacoes, total=total_combinacoes, desc=f"Testando {comprimento} chars", unit="pwd", initial=initial_step, dynamic_ncols=True):
                    senha = "".join(combinacao)
                    tentativas_totais += 1
                    senha_correta = False

                    if file_type == 'zip':
                        try:
                            archive_zip.read(first_file_zip.filename, pwd=senha.encode('utf-8'))
                            senha_correta = True
                        except Exception:
                            senha_correta = False
                    elif file_type == 'rar':
                        senha_correta = testar_senha_rar_subprocess(file_path, senha)

                    if senha_correta:
                        fim = time.time()
                        print(f"\n[SUCESSO] Senha encontrada: {senha}")
                        print(f"Total de tentativas: {tentativas_totais}")
                        print(f"Tempo total: {fim - inicio:.2f} segundos")
                        return

        print(f"\n[FALHA] Senha não encontrada após {tentativas_totais} tentativas.")
    except Exception as e:
        print(f"\n[ERRO] Ocorreu um erro inesperado: {e}")

## REESCRITO: A função paralela agora usa 'imap_unordered' para latência mínima.
## MODIFICADO: A função agora aceita 'start_step'
def testar_senha_paralelo(file_path: str, file_type: str, min_len: int, max_len: int, charset: str, num_workers: int, start_step: int, chunksize: int) -> None:
    print(f"Modo de execução: Paralelo (usando {num_workers} processo(s))")
    inicio = time.time()
    senha_encontrada = None

    for comprimento in range(min_len, max_len + 1):
        if senha_encontrada: break

        total_combinacoes = len(charset) ** comprimento
        # Cria um gerador de senhas (eficiente em memória)
        senhas_generator = ("".join(p) for p in itertools.product(charset, repeat=comprimento))

        ## MODIFICADO: Lógica para saltar para o 'step' inicial
        initial_step = 0
        if start_step > 0 and comprimento == min_len:
            print(f"Saltando para o laço inicial {start_step}...")
            senhas_generator = itertools.islice(senhas_generator, start_step, None)
            initial_step = start_step

        # Cria um gerador de tarefas para os workers
        tasks_generator = ((file_path, file_type, s) for s in senhas_generator)

        print(f"\nIniciando testes para senhas de {comprimento} caracteres...\n")

        ## MODIFICADO: A barra de progresso agora usa o parâmetro 'initial'
        with multiprocessing.Pool(processes=num_workers) as pool, tqdm(total=total_combinacoes, desc=f"Testando {comprimento} chars", unit="pwd", initial=initial_step, dynamic_ncols=True, mininterval=0.01) as pbar:
            # imap_unordered distribui as tarefas e retorna os resultados assim que ficam prontos
            for sucesso, senha in pool.imap_unordered(worker, tasks_generator, chunksize=1):
                pbar.update(1)
                if sucesso:
                    senha_encontrada = senha
                    pool.terminate()
                    pbar.update(total_combinacoes - pbar.n)
                    break

    fim = time.time()
    if senha_encontrada:
        # A mensagem de sucesso é movida para aqui para garantir que aparece depois da barra de progresso
        print("\n" + "="*50)
        print(f"[SUCESSO] Senha encontrada: {senha_encontrada}")
        print(f"Tempo total: {fim - inicio:.2f} segundos")
        print("="*50)
    else:
        print("\n[FALHA] Senha não encontrada.")

def test(file_path, file_type, args) -> None:
    # Testes de desempenho com diferentes números de workers e chunksizes
    # Adiciona um conjunto padrão de caracteres
    char_set = set()
    charset = char_set.update(list(string.digits))
    charset = "".join(sorted(list(char_set)))

    args.min_len = args.max_len = 4

    print("\n" + ("-" * 50))
    print("# Testes de desempenho\n" )

    print("-" * 50)
    print(f"CPU Count: {multiprocessing.cpu_count()}\n")
    print(f"Alvo: {file_path} (Tipo: {file_type})\n")
    print(f"Charset: '{charset[:40]}...' ({len(charset)} caracteres)\n")
    print(f"Comprimento: de {args.min_len} a {args.max_len}\n")
    print("-" * 50)

    print("\n" + ("-" * 50))
    print("#  Sequencial\n" )
    testar_senha_sequencial(file_path, file_type, args.min_len, args.max_len, charset, args.step)
    print("\n" + ("-" * 50))

    print("\n" + ("-" * 50))
    print("# Paralelos" )

    for workers in [2, 4, 8, 16, 32, 64, 128]:
        args.workers = workers

        for chunksize in [1, 2, 5, 10, 20, 50, 100, 200, 500]:
            print("\n" + ("-" * 50))
            print(f"Workers: {args.workers}, Chunksize: {chunksize}")
            print("-" * 50)
            testar_senha_paralelo(file_path, file_type, args.min_len, args.max_len, charset, args.workers, args.step, chunksize)

# ... (A função main continua a mesma)
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulador de teste de força de senha para ficheiros .zip e .rar.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("arquivo", help="O caminho para o ficheiro .zip ou .rar.")
    parser.add_argument("-min", "--min_len", type=int, default=1, help="Comprimento mínimo da senha.")
    parser.add_argument("-max", "--max_len", type=int, default=8, help="Comprimento máximo da senha.")
    parser.add_argument("-d", "--digitos", action="store_true", help="Incluir dígitos (0-9).")
    parser.add_argument("-l", "--lowercase", action="store_true", help="Incluir letras minúsculas (a-z).")
    parser.add_argument("-u", "--uppercase", action="store_true", help="Incluir letras maiúsculas (A-Z).")
    parser.add_argument("-w", "--letters", action="store_true", help="Incluir letras case insensitive (a-zA-Z).")
    parser.add_argument("-s", "--simbolos", action="store_true", help="Incluir símbolos.")
    parser.add_argument("-a", "--alphanum", action="store_true", help="Atalho para letras e dígitos.")
    parser.add_argument("-m", "--multithread", action="store_true", help="Ativar modo paralelo com múltiplos processos.")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help=f"Número de processos a serem utilizados (padrão: {os.cpu_count()}).")
    ## NOVO: Argumento para definir o laço inicial.
    parser.add_argument("--step", type=int, default=0, help="Número do laço (iteração) para iniciar o teste. Aplica-se ao primeiro comprimento do intervalo.")
    parser.add_argument("--test", action="store_true", help="Ativar modo paralelo com múltiplos processos.")
    args = parser.parse_args()

    # ... (lógica de seleção de file_type e charset, sem alterações)
    file_path = args.arquivo
    file_type = None
    if file_path.lower().endswith('.zip'):
        file_type = 'zip'
    elif file_path.lower().endswith('.rar'):
        file_type = 'rar'
    else:
        print(f"[ERRO] Formato de ficheiro não suportado: '{file_path}'. Use .zip ou .rar.")
        return

    # For test execution only
    if args.test:
        test(file_path, file_type, args)
        return

    if args.min_len < 1 or args.max_len < args.min_len:
        print("[ERRO] Valores inválidos para comprimento mínimo/máximo.")
        return

    if args.workers < 2:
        print("[ERRO] O número de processos deve ser pelo menos 2.")
        return

    char_set = set()
    if args.alphanum: char_set.update(list(string.ascii_letters + string.digits))
    if args.digitos: char_set.update(list(string.digits))
    if args.lowercase: char_set.update(list(string.ascii_lowercase))
    if args.uppercase: char_set.update(list(string.ascii_uppercase))
    if args.letters: char_set.update(list(string.ascii_letters))
    if args.simbolos: char_set.update(list(string.punctuation))
    if not char_set: char_set.update(list(string.ascii_letters + string.digits + string.punctuation))
    charset = "".join(sorted(list(char_set)))
    if not os.path.exists(file_path):
        print(f"[ERRO] O ficheiro '{file_path}' não foi encontrado.")
        return

    chunksize=20
    print("-" * 50)
    print(f"CPU Count: {multiprocessing.cpu_count()}")
    print(f"Alvo: {file_path} (Tipo: {file_type})")
    print(f"Charset: '{charset[:40]}...' ({len(charset)} caracteres)")
    print(f"Comprimento: de {args.min_len} a {args.max_len}")
    print("-" * 50)

    ## MODIFICADO: Passa o 'args.step' para as funções de teste
    if args.multithread:
        testar_senha_paralelo(file_path, file_type, args.min_len, args.max_len, charset, args.workers, args.step, chunksize)
    else:
        testar_senha_sequencial(file_path, file_type, args.min_len, args.max_len, charset, args.step)

if __name__ == "__main__":
    try:
        multiprocessing.freeze_support()
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Execução interrompida pelo usuário. Encerrando...")
        try:
            exit(0)
        except SystemExit:
            os._exit(0)
    except Exception as e:
        print(f"\n[ERRO FATAL] Ocorreu um erro inesperado: {e}")
